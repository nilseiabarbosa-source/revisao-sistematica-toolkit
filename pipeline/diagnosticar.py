"""Descobre qual bloco da busca está barrando cada estudo do gabarito.

Quando a sensibilidade está baixa, esta é a ferramenta que transforma "a busca
está ruim" em algo acionável: para cada estudo perdido, diz se ele falha no
bloco #1, #2, #3 ou no filtro temporal.

    python3 -m pipeline.diagnosticar --revisao <slug>

Funciona via PubMed, a única das bases suportadas que permite testar um registro
específico contra um trecho de consulta (operador `[uid]`).
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from fontes import PubMed  # noqa: E402
from modelo.tradutor import bloco_pubmed, consulta_pubmed  # noqa: E402
from pipeline.validar import carregar_config  # noqa: E402


def resolver_pmid(pm: PubMed, doi: str) -> str | None:
    for consulta in (f'"{doi}"[AID]', f'"{doi}"[All Fields]'):
        try:
            ids = pm.buscar_ids(consulta, limite=2)
        except Exception:
            continue
        if ids:
            return ids[0]
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--revisao", required=True)
    args = ap.parse_args()

    cfg = carregar_config(args.revisao)
    if not cfg.ITENS_CONHECIDOS:
        sys.exit("Sem gabarito em ITENS_CONHECIDOS — nada a diagnosticar.")

    pm = PubMed()
    consulta_completa = consulta_pubmed(cfg.BLOCOS, cfg.ANOS)

    print("=" * 78)
    print(f"DIAGNÓSTICO — {cfg.TITULO}")
    print("=" * 78)

    perdidos = []
    for doi, desc in cfg.ITENS_CONHECIDOS.items():
        try:
            if pm.contar(f'({consulta_completa}) AND "{doi}"[AID]'):
                continue
        except Exception:
            pass
        perdidos.append((doi, desc))

    if not perdidos:
        print("\nTodos os estudos do gabarito são recuperados. Nada a corrigir.")
        return

    print(f"\n{len(perdidos)} de {len(cfg.ITENS_CONHECIDOS)} não recuperados.")
    print("Testando cada um bloco a bloco.\n")

    cabecalho = f"{'Estudo':<40}{'PMID':>10}  "
    cabecalho += "".join(f"{b['nome'][:9]:<11}" for b in cfg.BLOCOS)
    cabecalho += "janela"
    print(cabecalho)
    print("-" * len(cabecalho))

    falhas = Counter()
    nao_indexados = []
    janela = (f'("{cfg.ANOS[0]}/01/01"[Date - Publication] : '
              f'"{cfg.ANOS[1]}/12/31"[Date - Publication])')

    for doi, desc in perdidos:
        pmid = resolver_pmid(pm, doi)
        if not pmid:
            print(f"{desc[:39]:<40}{'-':>10}  não indexado no PubMed")
            nao_indexados.append(desc)
            continue

        marcas = []
        for b in cfg.BLOCOS:
            try:
                ok = pm.contar(f"{pmid}[uid] AND {bloco_pubmed(b)}") > 0
            except Exception:
                ok = False
            marcas.append(f"{'ok' if ok else 'NÃO':<11}")
            if not ok:
                falhas[b["nome"]] += 1

        try:
            na_janela = pm.contar(f"{pmid}[uid] AND {janela}") > 0
        except Exception:
            na_janela = False
        if not na_janela:
            falhas["(fora da janela)"] += 1

        print(f"{desc[:39]:<40}{pmid:>10}  " + "".join(marcas)
              + ("ok" if na_janela else "FORA"))

    print("\n" + "=" * 78)
    print("ONDE A ESTRATÉGIA PERDE")
    print("=" * 78)
    for nome, n in falhas.most_common():
        print(f"  {nome:<34} barrou {n} estudo(s)")
    if nao_indexados:
        print(f"\n  Fora do PubMed ({len(nao_indexados)}): "
              + "; ".join(d[:40] for d in nao_indexados))

    print("\nComo corrigir, por padrão de falha:")
    print("  • um bloco barra vários estudos  -> faltam sinônimos nele;")
    print("    verifique se aceita a forma verbal (predict*), não só a nominal")
    print("    ('risk prediction').")
    print("  • o estudo não tem o termo central no título/resumo -> nenhuma")
    print("    string ancorada nele o alcança. Crie uma vertente B, sem esse")
    print("    bloco, e triе pelo desfecho.")
    print("  • cai na janela -> confira se o filtro não descarta registros")
    print("    ainda não indexados no MeSH.")


if __name__ == "__main__":
    main()
