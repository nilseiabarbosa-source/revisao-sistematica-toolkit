"""Importa exportacoes manuais (Scopus, Embase, WoS, CENTRAL, IEEE) para o
mesmo esquema `Registro` usado pelos adaptadores de API.

Formatos aceitos: RIS (.ris/.txt/.nbib), BibTeX (.bib) e CSV do Scopus (.csv).
O nome do arquivo vira o rotulo da fonte no log PRISMA-S, entao vale nomear
como `scopus_vertenteA.ris`, `wos.ris`, `ieee.csv`, etc.

Como biblioteca:

    from pipeline.importar import importar
    regs = importar("wos.ris")

Como comando, para fundir as exportacoes manuais ao que as APIs ja coletaram:

    python3 -m pipeline.importar --revisao <slug> --arquivo wos.ris ieee.ris
    python3 -m pipeline.importar --revisao <slug> --pasta manuais/

O comando le `resultados/registros.json` (saida de `pipeline.buscar`), junta os
arquivos manuais, aplica a janela de anos, deduplica o conjunto inteiro de novo
e reescreve as saidas de triagem. E' idempotente: reimportar o mesmo arquivo nao
duplica nada, porque a deduplicacao roda sobre tudo junto a cada execucao.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from fontes import Registro, normalizar_doi
from fontes.base import extrair_ano
from fontes.dedup import deduplicar

# ---------------------------------------------------------------------- RIS

# Varias bases usam tags diferentes para o mesmo campo.
RIS_TITULO = ("TI", "T1", "CT")
RIS_AUTOR = ("AU", "A1", "A2")
RIS_ANO = ("PY", "Y1", "DA")
RIS_PERIODICO = ("JO", "JF", "T2", "JA", "J2")
RIS_RESUMO = ("AB", "N2")
RIS_PALAVRA = ("KW",)


def importar_ris(caminho: str | Path, fonte: str | None = None) -> list[Registro]:
    caminho = Path(caminho)
    fonte = fonte or caminho.stem
    texto = caminho.read_text(encoding="utf-8-sig", errors="replace")

    registros: list[Registro] = []
    atual: dict[str, list[str]] = {}
    ultima_tag: str | None = None

    def fechar():
        if atual:
            registros.append(_ris_para_registro(atual, fonte))
        atual.clear()

    for linha in texto.splitlines():
        if not linha.strip():
            continue
        m = re.match(r"^([A-Z][A-Z0-9])  - ?(.*)$", linha)
        if m:
            tag, valor = m.group(1), m.group(2).strip()
            if tag == "ER":
                fechar()
                ultima_tag = None
                continue
            if tag == "TY":
                fechar()
            atual.setdefault(tag, []).append(valor)
            ultima_tag = tag
        elif ultima_tag and atual.get(ultima_tag):
            # continuacao da linha anterior (resumos longos vem quebrados)
            atual[ultima_tag][-1] += " " + linha.strip()
    fechar()
    return registros


def _primeiro(d: dict[str, list[str]], tags: tuple[str, ...]) -> str:
    for t in tags:
        if d.get(t):
            return d[t][0]
    return ""


def _todos(d: dict[str, list[str]], tags: tuple[str, ...]) -> list[str]:
    saida: list[str] = []
    for t in tags:
        saida.extend(d.get(t, []))
    return saida


def _ris_para_registro(d: dict[str, list[str]], fonte: str) -> Registro:
    doi = _primeiro(d, ("DO", "DI"))
    if not doi:  # algumas bases enfiam o DOI em UR ou N1
        for campo in _todos(d, ("UR", "N1", "L3")):
            m = re.search(r"10\.\d{4,9}/[^\s\"'<>]+", campo)
            if m:
                doi = m.group(0).rstrip(".,;")
                break

    pmid = ""
    for campo in _todos(d, ("AN", "ID", "N1", "UR")):
        m = re.search(r"(?:PMID:?\s*|pubmed/)(\d{7,8})", campo, re.I)
        if m:
            pmid = m.group(1)
            break

    return Registro(
        fonte=fonte,
        id_fonte=_primeiro(d, ("ID", "AN", "UR")),
        titulo=_primeiro(d, RIS_TITULO).rstrip("."),
        resumo=_primeiro(d, RIS_RESUMO),
        autores=_todos(d, RIS_AUTOR),
        ano=extrair_ano(_primeiro(d, RIS_ANO)),
        periodico=_primeiro(d, RIS_PERIODICO),
        doi=doi,
        pmid=pmid,
        tipo=_primeiro(d, ("TY",)),
        idioma=_primeiro(d, ("LA",)),
        termos=_todos(d, RIS_PALAVRA),
        url=_primeiro(d, ("UR",)),
    )


# ------------------------------------------------------------------- BibTeX

def importar_bibtex(caminho: str | Path, fonte: str | None = None) -> list[Registro]:
    caminho = Path(caminho)
    fonte = fonte or caminho.stem
    texto = caminho.read_text(encoding="utf-8-sig", errors="replace")

    registros = []
    for bloco in re.finditer(r"@(\w+)\s*\{([^,]*),(.*?)\n\}", texto, re.S):
        tipo, chave, corpo = bloco.group(1), bloco.group(2).strip(), bloco.group(3)
        campos = {}
        for m in re.finditer(r"(\w+)\s*=\s*[{\"](.*?)[}\"]\s*,?\s*(?=\n\s*\w+\s*=|\Z)", corpo, re.S):
            campos[m.group(1).lower()] = " ".join(m.group(2).split())
        registros.append(
            Registro(
                fonte=fonte,
                id_fonte=chave,
                titulo=campos.get("title", "").strip("{} ").rstrip("."),
                resumo=campos.get("abstract", ""),
                autores=[a.strip() for a in campos.get("author", "").split(" and ") if a.strip()],
                ano=extrair_ano(campos.get("year")),
                periodico=campos.get("journal") or campos.get("booktitle", ""),
                doi=campos.get("doi", ""),
                tipo=tipo,
                termos=[k.strip() for k in campos.get("keywords", "").split(";") if k.strip()],
                url=campos.get("url", ""),
            )
        )
    return registros


# --------------------------------------------------------------- CSV Scopus

COL_SCOPUS = {
    "titulo": ("Title", "Document Title"),
    "resumo": ("Abstract",),
    "autores": ("Authors", "Author full names"),
    "ano": ("Year",),
    "periodico": ("Source title",),
    "doi": ("DOI",),
    "pmid": ("PubMed ID",),
    "tipo": ("Document Type",),
    "idioma": ("Language of Original Document",),
    "url": ("Link",),
    "id": ("EID",),
}


def _col(linha: dict, nomes: tuple[str, ...]) -> str:
    for n in nomes:
        if linha.get(n):
            return linha[n].strip()
    return ""


def importar_csv_scopus(caminho: str | Path, fonte: str | None = None) -> list[Registro]:
    caminho = Path(caminho)
    fonte = fonte or caminho.stem
    registros = []
    with caminho.open(encoding="utf-8-sig", errors="replace", newline="") as f:
        amostra = f.read(8192)
        f.seek(0)
        try:
            dialeto = csv.Sniffer().sniff(amostra, delimiters=",;\t")
        except csv.Error:
            dialeto = csv.excel
        for linha in csv.DictReader(f, dialect=dialeto):
            autores = _col(linha, COL_SCOPUS["autores"])
            termos = []
            for c in ("Author Keywords", "Index Keywords"):
                if linha.get(c):
                    termos += [t.strip() for t in linha[c].split(";") if t.strip()]
            registros.append(
                Registro(
                    fonte=fonte,
                    id_fonte=_col(linha, COL_SCOPUS["id"]),
                    titulo=_col(linha, COL_SCOPUS["titulo"]).rstrip("."),
                    resumo=_col(linha, COL_SCOPUS["resumo"]),
                    autores=[a.strip() for a in autores.split(";") if a.strip()]
                    or [a.strip() for a in autores.split(",") if a.strip()],
                    ano=extrair_ano(_col(linha, COL_SCOPUS["ano"])),
                    periodico=_col(linha, COL_SCOPUS["periodico"]),
                    doi=_col(linha, COL_SCOPUS["doi"]),
                    pmid=_col(linha, COL_SCOPUS["pmid"]),
                    tipo=_col(linha, COL_SCOPUS["tipo"]),
                    idioma=_col(linha, COL_SCOPUS["idioma"]),
                    termos=termos,
                    url=_col(linha, COL_SCOPUS["url"]),
                    acesso_aberto="open access" in (linha.get("Open Access", "") or "").lower(),
                )
            )
    return registros


# ------------------------------------------------------------------ despacho

def importar(caminho: str | Path, fonte: str | None = None) -> list[Registro]:
    """Escolhe o leitor pela extensao. Para .csv assume o layout do Scopus."""
    caminho = Path(caminho)
    ext = caminho.suffix.lower()
    if ext in (".ris", ".txt", ".nbib"):
        return importar_ris(caminho, fonte)
    if ext == ".bib":
        return importar_bibtex(caminho, fonte)
    if ext == ".csv":
        return importar_csv_scopus(caminho, fonte)
    raise ValueError(f"extensao nao suportada: {ext}")


# --------------------------------------------------------------------- CLI

EXTENSOES = (".ris", ".txt", ".nbib", ".bib", ".csv")


def main() -> None:
    # Import tardio: `pipeline.validar` importa `modelo.tradutor`, e deixar isso
    # no topo faria o uso deste modulo como biblioteca arrastar o pipeline todo.
    from pipeline.exportar import exportar_csv, exportar_ris
    from pipeline.validar import carregar_config

    ap = argparse.ArgumentParser(
        description="Funde exportacoes manuais de bases sem API ao conjunto "
                    "ja coletado por pipeline.buscar."
    )
    ap.add_argument("--revisao", required=True, help="slug da pasta em revisoes/")
    ap.add_argument("--arquivo", nargs="*", default=[],
                    help="um ou mais arquivos .ris/.bib/.csv exportados")
    ap.add_argument("--pasta", default=None,
                    help="pasta de onde importar todos os arquivos suportados")
    args = ap.parse_args()

    cfg = carregar_config(args.revisao)
    pasta_revisao = RAIZ / "revisoes" / args.revisao
    saida = pasta_revisao / "resultados"
    saida.mkdir(parents=True, exist_ok=True)

    caminhos = [Path(a) for a in args.arquivo]
    if args.pasta:
        caminhos += sorted(
            p for p in Path(args.pasta).iterdir()
            if p.suffix.lower() in EXTENSOES
        )
    if not caminhos:
        sys.exit("Nada a importar. Use --arquivo <caminho> ou --pasta <caminho>.")

    print("=" * 70)
    print(cfg.TITULO)
    print("=" * 70)

    # ------------------------------------------------ o que as APIs ja trouxeram
    brutos: list[Registro] = []
    anterior = saida / "registros.json"
    if anterior.exists():
        dados = json.loads(anterior.read_text(encoding="utf-8"))
        brutos = [Registro(**{**d, "bruto": {}}) for d in dados]
        print(f"\nJa coletado por API: {len(brutos)} registros")
    else:
        print("\nSem coleta previa de API — importando so os arquivos manuais.")

    # ------------------------------------------------------- arquivos manuais
    logs_novos = []
    print("\nImportando:")
    for caminho in caminhos:
        if not caminho.exists():
            print(f"  {caminho.name:<38} ARQUIVO NAO ENCONTRADO")
            continue
        rotulo = f"manual_{caminho.stem}"
        try:
            regs = importar(caminho, fonte=rotulo)
        except Exception as e:
            print(f"  {caminho.name:<38} ERRO {type(e).__name__}: {str(e)[:40]}")
            continue
        com_doi = sum(1 for r in regs if r.doi)
        print(f"  {caminho.name:<38} {len(regs):>5} registros "
              f"({com_doi} com DOI)")
        brutos.extend(regs)
        logs_novos.append({
            "fonte": rotulo,
            "consulta": f"exportacao manual do arquivo {caminho.name}",
            "data_hora": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "n_recuperados": len(regs),
            "n_total_disponivel": None,
            "erro": "",
        })

    if not logs_novos:
        sys.exit("\nNenhum arquivo foi importado. Nada foi gravado.")

    # Mesma janela aplicada pelo buscar: exportacao manual costuma vir com o
    # filtro de ano frouxo, ou sem filtro nenhum.
    antes = len(brutos)
    brutos = [r for r in brutos if not r.ano or cfg.ANOS[0] <= r.ano <= cfg.ANOS[1]]
    if antes != len(brutos):
        print(f"\nFora da janela {cfg.ANOS[0]}–{cfg.ANOS[1]}: "
              f"{antes - len(brutos)} removidos")

    print("\n" + "=" * 70)
    print("DEDUPLICAÇÃO (conjunto inteiro, API + manual)")
    res = deduplicar(brutos)
    print(res.resumo_prisma())

    if cfg.ITENS_CONHECIDOS:
        dois = {normalizar_doi(r.doi) for r in res.unicos if r.doi}
        achados = [d for d in cfg.ITENS_CONHECIDOS if normalizar_doi(d) in dois]
        pct = 100 * len(achados) / len(cfg.ITENS_CONHECIDOS)
        print(f"\nGabarito recuperado: {len(achados)}/"
              f"{len(cfg.ITENS_CONHECIDOS)} ({pct:.0f}%)")

    com_resumo = sum(1 for r in res.unicos if r.resumo)
    print(f"\nCom resumo: {com_resumo}/{len(res.unicos)} "
          f"({100 * com_resumo / max(1, len(res.unicos)):.0f}%)")

    # ------------------------------------------------------------------ saidas
    (saida / "registros.json").write_text(
        json.dumps([r.para_dict() for r in res.unicos], ensure_ascii=False, indent=2),
        encoding="utf-8")

    log = saida / "log_prisma_s.json"
    anteriores = json.loads(log.read_text(encoding="utf-8")) if log.exists() else []
    # Reimportar o mesmo arquivo substitui a linha de log em vez de empilhar
    # outra, senao o log PRISMA-S passa a contar a mesma fonte duas vezes.
    novos_rotulos = {l["fonte"] for l in logs_novos}
    anteriores = [l for l in anteriores if l.get("fonte") not in novos_rotulos]
    log.write_text(
        json.dumps(anteriores + logs_novos, ensure_ascii=False, indent=2),
        encoding="utf-8")

    (saida / "relatorio_dedup.txt").write_text(res.resumo_prisma(), encoding="utf-8")
    exportar_ris(res.unicos, saida / "registros_para_triagem.ris")
    exportar_csv(res.unicos, saida / "registros_para_triagem.csv",
                 res.fontes_por_registro)

    print(f"\nGravado em {saida}:")
    for p in sorted(saida.iterdir()):
        print(f"  {p.name}  ({p.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
