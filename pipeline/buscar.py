"""Executa a busca de uma revisão em todas as bases configuradas.

Coleta, deduplica, valida contra o gabarito e exporta para triagem — gravando o
log que o PRISMA-S exige.

    python3 -m pipeline.buscar --revisao <slug>
    python3 -m pipeline.buscar --revisao <slug> --limite 500   # teste rápido

A coleta é gravada em cache por base; reexecutar retoma o que faltou em vez de
recomeçar. Processo longo precisa ser retomável.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from fontes import Registro, normalizar_doi  # noqa: E402
from fontes.dedup import deduplicar  # noqa: E402
from modelo.tradutor import gerar_todas  # noqa: E402
from pipeline.exportar import exportar_csv, exportar_ris  # noqa: E402
from pipeline.validar import PY, adaptador, carregar_config, consulta_para  # noqa: E402


def agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def coletar(base: str, cfg, blocos, rotulo: str, limite: int, cache: Path):
    """Coleta uma vertente de uma base, reaproveitando cache quando existir."""
    arquivo = cache / f"{rotulo}.json"
    if arquivo.exists():
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
        regs = [Registro(**{**d, "bruto": {}}) for d in dados["registros"]]
        print(f"  [cache] {rotulo}: {len(regs)} registros")
        return regs, dados.get("log")

    try:
        q = consulta_para(base, cfg, blocos)
    except ValueError as e:
        print(f"  {rotulo}: {e}")
        return [], None

    try:
        ad = adaptador(base, cfg.ANOS)
        total = ad.contar(q)
        print(f"  {rotulo}: {total} disponíveis", end="", flush=True)
        regs = ad.coletar(q, limite=min(limite, total) if total else limite)
        for r in regs:
            r.fonte = rotulo
        print(f" → {len(regs)} coletados")
        log = {"fonte": rotulo, "consulta": q, "data_hora": agora(),
               "n_recuperados": len(regs), "n_total_disponivel": total, "erro": ""}
    except Exception as e:
        print(f"\n  {rotulo}: ERRO {type(e).__name__}: {str(e)[:70]}")
        return [], {"fonte": rotulo, "consulta": q, "data_hora": agora(),
                    "n_recuperados": 0, "n_total_disponivel": None,
                    "erro": f"{type(e).__name__}: {e}"}

    cache.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(
        json.dumps({"registros": [r.para_dict() for r in regs], "log": log},
                   ensure_ascii=False),
        encoding="utf-8",
    )
    return regs, log


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--revisao", required=True)
    ap.add_argument("--limite", type=int, default=20000,
                    help="teto por base e vertente (padrão 20000)")
    args = ap.parse_args()

    cfg = carregar_config(args.revisao)
    pasta = RAIZ / "revisoes" / args.revisao
    saida = pasta / "resultados"
    cache = pasta / "cache"
    saida.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(cfg.TITULO)
    print("=" * 70)

    brutos: list[Registro] = []
    logs: list[dict] = []

    print("\nVertente A")
    for base in cfg.BASES:
        regs, log = coletar(base, cfg, cfg.BLOCOS, f"{base}_A", args.limite, cache)
        brutos.extend(regs)
        if log:
            logs.append(log)

    if getattr(cfg, "BLOCOS_VERTENTE_B", None):
        print("\nVertente B")
        for base in cfg.BASES:
            regs, log = coletar(base, cfg, cfg.BLOCOS_VERTENTE_B,
                                f"{base}_B", args.limite, cache)
            brutos.extend(regs)
            if log:
                logs.append(log)

    if not brutos:
        sys.exit("\nERRO: nenhuma base devolveu registros. Nada foi gravado.")

    # Janela temporal — bases como o arXiv não aceitam filtro de ano na consulta.
    antes = len(brutos)
    brutos = [r for r in brutos if not r.ano or cfg.ANOS[0] <= r.ano <= cfg.ANOS[1]]
    if antes != len(brutos):
        print(f"\nFora da janela {cfg.ANOS[0]}–{cfg.ANOS[1]}: {antes - len(brutos)} removidos")

    print("\n" + "=" * 70)
    print("DEDUPLICAÇÃO")
    res = deduplicar(brutos)
    print(res.resumo_prisma())

    # ------------------------------------------------------------ validação
    dois = {normalizar_doi(r.doi) for r in res.unicos if r.doi}
    achados = [d for d in cfg.ITENS_CONHECIDOS if normalizar_doi(d) in dois]
    # O aviso so faz sentido quando --limite foi de fato o fator limitante.
    # Comparar recuperado < disponivel disparava o alerta por diferencas de
    # uma ou duas unidades — registros que o parser ignora, como capitulos de
    # livro sem o elemento esperado — e dizia "truncada por --limite" mesmo
    # quando o usuario nao usou a opcao.
    truncou = any(
        l.get("n_total_disponivel") and l["n_total_disponivel"] > args.limite
        for l in logs
    )
    perdidos_parser = sum(
        l["n_total_disponivel"] - l["n_recuperados"]
        for l in logs
        if l.get("n_total_disponivel")
        and l["n_total_disponivel"] <= args.limite
        and l["n_recuperados"] < l["n_total_disponivel"]
    )
    if cfg.ITENS_CONHECIDOS:
        pct = 100 * len(achados) / len(cfg.ITENS_CONHECIDOS)
        print(f"\nGabarito recuperado: {len(achados)}/{len(cfg.ITENS_CONHECIDOS)} ({pct:.0f}%)")
        for doi, desc in cfg.ITENS_CONHECIDOS.items():
            if normalizar_doi(doi) not in dois:
                print(f"  [ ] {desc}")
        if truncou:
            # Com --limite, a coleta e um recorte arbitrario do total: um estudo
            # do gabarito pode simplesmente nao ter entrado. Sem este aviso, o
            # numero seria lido como falha da estrategia.
            print("\n  AVISO: a coleta foi truncada por --limite, entao esta taxa"
                  "\n  NAO mede a sensibilidade da busca. Para isso, rode:"
                  f"\n    {PY} -m pipeline.validar --revisao {args.revisao}")

    if perdidos_parser:
        print(f"\nNota: {perdidos_parser} registro(s) vieram da base mas nao "
              "puderam ser convertidos\n(tipicamente capitulos de livro ou "
              "registros retirados). Diferenca esperada e pequena.")

    # ------------------------------------------------------------- perfil
    com_resumo = sum(1 for r in res.unicos if r.resumo)
    print(f"\nCom resumo: {com_resumo}/{len(res.unicos)} "
          f"({100 * com_resumo / max(1, len(res.unicos)):.0f}%)")
    print("Origem:")
    for f, n in Counter(r.fonte for r in res.unicos).most_common():
        print(f"  {n:>6}  {f}")

    # -------------------------------------------------------------- saídas
    (saida / "registros.json").write_text(
        json.dumps([r.para_dict() for r in res.unicos], ensure_ascii=False, indent=2),
        encoding="utf-8")
    (saida / "log_prisma_s.json").write_text(
        json.dumps(logs, ensure_ascii=False, indent=2), encoding="utf-8")
    (saida / "strings_de_busca.txt").write_text(
        "\n\n".join(f"### {k}\n{v}" for k, v in
                    gerar_todas(cfg.BLOCOS, cfg.ANOS,
                                getattr(cfg, "EXCLUIR_ANIMAIS", True)).items()),
        encoding="utf-8")
    (saida / "relatorio_dedup.txt").write_text(res.resumo_prisma(), encoding="utf-8")
    exportar_ris(res.unicos, saida / "registros_para_triagem.ris")
    exportar_csv(res.unicos, saida / "registros_para_triagem.csv", res.fontes_por_registro)

    print(f"\nGravado em {saida}:")
    for p in sorted(saida.iterdir()):
        print(f"  {p.name}  ({p.stat().st_size / 1024:.0f} KB)")
    print("\nImporte o .ris no Rayyan ou Covidence para a triagem dupla.")


if __name__ == "__main__":
    main()
