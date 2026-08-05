"""Preenche resumos faltantes buscando por DOI.

Registro sem resumo tem que ser triado so' pelo titulo, o que e' muito pior:
titulo de artigo de sensor raramente diz a matriz testada nem o estagio de
validacao, que sao dois dos quatro criterios de inclusao. O revisor acaba
excluindo por falta de informacao, e a perda nao aparece em lugar nenhum.

O buraco nao e' uniforme entre as bases. Medido na revisao de biossensores de
nanocarbono em 2026-08-05: o PubMed devolveu 2 registros sem resumo em 1.913
(0,1%), enquanto o Semantic Scholar devolveu 412 em 1.411 (29,2%). O Semantic
Scholar cobre periodicos que o PubMed nao indexa — e' por isso que esta na
busca —, mas o resumo vem faltando com frequencia. Enriquecer por DOI recupera
boa parte sem precisar refazer busca nenhuma.

    python3 -m pipeline.enriquecer --revisao <slug>

Cascata, na ordem em que efetivamente rendem (medido nos 378 desta revisao):

  1. Europe PMC — 25 DOIs por requisicao, resumo em texto puro. Rende pouco
                  fora da area biomedica: os que faltam sao de periodico de
                  ciencia dos materiais, que nao esta no MEDLINE. 1 de 378 aqui.
  2. OpenAlex   — o melhor rendimento, ~42% da amostra. Consulta por DOI unico
                  continua livre sem chave; foi a busca em massa que passou a
                  exigir credencial em 13/02/2026.
  3. Crossref   — ultimo recurso, so' pega o que a editora depositou, e vem em
                  JATS com marcacao a limpar. 9 de 377 aqui.

TETO CONHECIDO: quem publica na Springer nao aparece em nenhuma das tres. A
Springer nao deposita resumo no Crossref nem o libera ao OpenAlex, e seus
periodicos de materiais nao estao no MEDLINE. Nesta revisao sao 245 dos 378
registros sem resumo — ou seja, cerca de dois tercos do buraco e' estrutural e
so' se resolve abrindo o artigo. O Semantic Scholar tambem nao ajuda: foi ele
que trouxe esses registros, e o endpoint individual devolve vazio igual ao de
lote (0 de 12 testados).

E' idempotente e retomavel: so' mexe em registro com resumo vazio e DOI
presente, entao rodar de novo apenas tenta os que continuam faltando.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from fontes import Registro, normalizar_doi  # noqa: E402
from fontes.crossref import Crossref  # noqa: E402
from fontes.europepmc import EuropePMC  # noqa: E402
from fontes.openalex import OpenAlex  # noqa: E402
from pipeline.exportar import exportar_csv, exportar_ris  # noqa: E402
from pipeline.validar import carregar_config  # noqa: E402

# Resumo mais curto que isso e' rotulo ("Abstract", "No abstract available")
# ou fragmento truncado, e polui a triagem mais do que ajuda.
MINIMO_UTIL = 80


def limpar_jats(texto: str) -> str:
    """Converte o resumo do Crossref (JATS/HTML) em texto corrido.

    O Crossref devolve o que a editora depositou, e isso vem com marcacao:
    <jats:p>, <jats:title>Abstract</jats:title>, secoes rotuladas, entidades
    HTML escapadas. Sem limpeza, o RIS exportado leva as tags junto e o Rayyan
    as exibe cruas para o revisor.
    """
    if not texto:
        return ""
    t = re.sub(r"<jats:title>\s*abstract\s*</jats:title>", " ", texto, flags=re.I)
    t = re.sub(r"</?[a-zA-Z][^>]*>", " ", t)     # qualquer tag restante
    t = html.unescape(t)
    t = re.sub(r"\s+", " ", t).strip()
    # Alguns depositos ainda comecam com o rotulo solto.
    t = re.sub(r"^abstract[:\s\-–]+", "", t, flags=re.I).strip()
    return t


def util(texto: str) -> bool:
    return len(limpar_jats(texto or "")) >= MINIMO_UTIL


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Preenche resumos faltantes por DOI, via Europe PMC e Crossref."
    )
    ap.add_argument("--revisao", required=True, help="slug da pasta em revisoes/")
    ap.add_argument("--limite", type=int, default=0,
                    help="teto de registros a tentar (0 = todos); util para teste")
    ap.add_argument("--sem-crossref", action="store_true",
                    help="pula o Crossref, que e' a etapa de menor rendimento")
    args = ap.parse_args()

    cfg = carregar_config(args.revisao)
    saida = RAIZ / "revisoes" / args.revisao / "resultados"
    arquivo = saida / "registros.json"
    if not arquivo.exists():
        sys.exit(f"Nao encontrei {arquivo}\n"
                 f"Rode antes: python -m pipeline.buscar --revisao {args.revisao}")

    regs = [Registro(**{**d, "bruto": {}})
            for d in json.loads(arquivo.read_text(encoding="utf-8"))]

    print("=" * 70)
    print(cfg.TITULO)
    print("=" * 70)

    faltando = [r for r in regs if not util(r.resumo)]
    sem_doi = [r for r in faltando if not normalizar_doi(r.doi)]
    alvo = [r for r in faltando if normalizar_doi(r.doi)]
    if args.limite:
        alvo = alvo[: args.limite]

    print(f"\nRegistros no conjunto      : {len(regs)}")
    print(f"Sem resumo aproveitavel    : {len(faltando)} "
          f"({100 * len(faltando) / max(1, len(regs)):.1f}%)")
    print(f"  destes, com DOI          : {len(alvo)}  <- da para tentar")
    print(f"  destes, sem DOI          : {len(sem_doi)}  <- so' por busca manual")
    if not alvo:
        print("\nNada a enriquecer.")
        return

    por_doi = {normalizar_doi(r.doi): r for r in alvo}
    recuperados = {"europepmc": 0, "openalex": 0, "crossref": 0}

    # ------------------------------------------------------------ Europe PMC
    print(f"\nEurope PMC — {len(por_doi)} DOIs, 25 por requisicao...")
    try:
        achados = EuropePMC().por_dois(list(por_doi))
    except Exception as e:
        print(f"  falhou: {type(e).__name__}: {str(e)[:60]}")
        achados = {}
    for doi, encontrado in achados.items():
        destino = por_doi.get(doi)
        if destino is not None and util(encontrado.resumo):
            destino.resumo = limpar_jats(encontrado.resumo)
            # Aproveita o que mais veio junto e estava vazio.
            destino.pmid = destino.pmid or encontrado.pmid
            destino.pmcid = destino.pmcid or encontrado.pmcid
            destino.termos = destino.termos or encontrado.termos
            recuperados["europepmc"] += 1
    print(f"  recuperados: {recuperados['europepmc']}")

    # --------------------------------------------------------------- OpenAlex
    restantes = [d for d, r in por_doi.items() if not util(r.resumo)]
    if restantes:
        print(f"\nOpenAlex — {len(restantes)} restantes, um por requisicao "
              f"(~{max(1, round(len(restantes) / 5 / 60))} min)...")
        oa = OpenAlex()
        for i, doi in enumerate(restantes, 1):
            if i % 50 == 0:
                print(f"  {i}/{len(restantes)}... "
                      f"({recuperados['openalex']} recuperados ate aqui)")
            try:
                encontrado = oa.por_doi(doi)
            except Exception:
                continue
            if encontrado is not None and util(encontrado.resumo):
                por_doi[doi].resumo = limpar_jats(encontrado.resumo)
                recuperados["openalex"] += 1
        print(f"  recuperados: {recuperados['openalex']}")

    # --------------------------------------------------------------- Crossref
    restantes = [d for d, r in por_doi.items() if not util(r.resumo)]
    if restantes and not args.sem_crossref:
        print(f"\nCrossref — {len(restantes)} restantes, um por requisicao "
              f"(~{len(restantes) / 5 / 60:.0f} min)...")
        cr = Crossref()
        for i, doi in enumerate(restantes, 1):
            if i % 50 == 0:
                print(f"  {i}/{len(restantes)}... "
                      f"({recuperados['crossref']} recuperados ate aqui)")
            try:
                encontrado = cr.por_doi(doi)
            except Exception:
                continue
            if encontrado is None:
                continue
            limpo = limpar_jats(encontrado.resumo)
            if len(limpo) >= MINIMO_UTIL:
                por_doi[doi].resumo = limpo
                recuperados["crossref"] += 1
        print(f"  recuperados: {recuperados['crossref']}")
    elif restantes:
        print(f"\nCrossref pulado (--sem-crossref); {len(restantes)} ficaram sem resumo.")

    # ----------------------------------------------------------------- saidas
    total = sum(recuperados.values())
    com_resumo = sum(1 for r in regs if util(r.resumo))

    print("\n" + "=" * 70)
    print(f"Resumos recuperados: {total}  ("
          + ", ".join(f"{k} {v}" for k, v in recuperados.items() if v) + ")")
    print(f"Com resumo agora   : {com_resumo}/{len(regs)} "
          f"({100 * com_resumo / max(1, len(regs)):.1f}%)  "
          f"— era {100 * (com_resumo - total) / max(1, len(regs)):.1f}%")
    ainda = len(regs) - com_resumo
    print(f"Ainda sem resumo   : {ainda} — triar por titulo, ou buscar a mao")

    if not total:
        print("\nNada mudou; arquivos preservados.")
        return

    arquivo.write_text(
        json.dumps([r.para_dict() for r in regs], ensure_ascii=False, indent=2),
        encoding="utf-8")
    exportar_ris(regs, saida / "registros_para_triagem.ris")
    exportar_csv(regs, saida / "registros_para_triagem.csv")

    # O enriquecimento nao e' busca, mas altera o que a dupla vai triar, entao
    # precisa ficar registrado junto com o resto para o PRISMA-S fazer sentido.
    log = saida / "log_prisma_s.json"
    linhas = json.loads(log.read_text(encoding="utf-8")) if log.exists() else []
    linhas = [l for l in linhas if l.get("fonte") != "enriquecimento_resumos"]
    linhas.append({
        "fonte": "enriquecimento_resumos",
        "consulta": "recuperacao de resumos faltantes por DOI (Europe PMC, depois Crossref)",
        "data_hora": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_recuperados": total,
        "n_total_disponivel": len(alvo),
        "erro": "",
    })
    log.write_text(json.dumps(linhas, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nAtualizados em {saida}:")
    for nome in ("registros.json", "registros_para_triagem.ris",
                 "registros_para_triagem.csv", "log_prisma_s.json"):
        p = saida / nome
        if p.exists():
            print(f"  {nome}  ({p.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
