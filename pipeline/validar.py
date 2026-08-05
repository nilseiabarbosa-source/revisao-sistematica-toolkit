"""Calibra e valida a busca de uma revisão, sem baixar registros.

Duas perguntas, respondidas antes de gastar tempo com coleta:
  1. Qual o volume por base? (viabilidade da triagem)
  2. A busca recupera os estudos que já sabemos serem elegíveis? (sensibilidade)

    python3 -m pipeline.validar --revisao <slug>
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

# No PowerShell do Windows nao existe `python3` — as instrucoes impressas
# precisam usar o nome certo da plataforma.
PY = "python" if os.name == "nt" else "python3"

from modelo.tradutor import (  # noqa: E402
    consulta_arxiv,
    consulta_europepmc,
    consulta_pubmed,
    consulta_scopus,
)


def carregar_config(slug: str):
    caminho = RAIZ / "revisoes" / slug / "config.py"
    if not caminho.exists():
        sys.exit(f"Configuração não encontrada: {caminho}\n"
                 f"Crie com: python3 iniciar_revisao.py")
    spec = importlib.util.spec_from_file_location(f"config_{slug}", caminho)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def adaptador(base: str):
    """Importa sob demanda — bases com credencial não devem quebrar o resto."""
    if base == "pubmed":
        from fontes import PubMed
        return PubMed()
    if base == "europepmc":
        from fontes import EuropePMC
        return EuropePMC()
    if base == "arxiv":
        from fontes import Arxiv
        return Arxiv()
    if base == "openalex":
        from fontes import OpenAlex
        return OpenAlex()
    if base == "scopus":
        from fontes.scopus import Scopus
        return Scopus(view="STANDARD")
    if base == "semanticscholar":
        from fontes import SemanticScholar
        return SemanticScholar()
    if base == "dblp":
        from fontes import DBLP
        return DBLP()
    if base == "core":
        from fontes.core import CORE
        return CORE()
    raise ValueError(f"sem tradutor de consulta para '{base}'")


def consulta_para(base: str, cfg, blocos):
    if base == "pubmed":
        return consulta_pubmed(blocos, cfg.ANOS)
    if base == "europepmc":
        return consulta_europepmc(blocos, cfg.ANOS)
    if base == "scopus":
        return consulta_scopus(blocos, cfg.ANOS)
    if base == "arxiv":
        return consulta_arxiv(blocos)
    raise ValueError(f"sem tradutor de consulta para '{base}'")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--revisao", required=True, help="slug da pasta em revisoes/")
    args = ap.parse_args()

    cfg = carregar_config(args.revisao)
    print("=" * 70)
    print(cfg.TITULO)
    print("=" * 70)
    print(f"Recorte: {cfg.ANOS[0]}–{cfg.ANOS[1]} | "
          f"{len(cfg.BLOCOS)} bloco(s) | {len(cfg.BASES)} base(s)")

    # ------------------------------------------------------------- volume
    print(f"\n{'Base':<18}{'Vertente A':>13}{'Vertente B':>13}")
    print("-" * 70)
    consultas = {}
    for base in cfg.BASES:
        try:
            qa = consulta_para(base, cfg, cfg.BLOCOS)
            consultas[base] = qa
            ad = adaptador(base)
            na = ad.contar(qa)
            nb = ""
            if getattr(cfg, "BLOCOS_VERTENTE_B", None):
                nb = ad.contar(consulta_para(base, cfg, cfg.BLOCOS_VERTENTE_B))
            print(f"{base:<18}{na:>13,}{str(nb):>13}".replace(",", "."))
        except Exception as e:
            print(f"{base:<18}{'ERRO':>13}  {type(e).__name__}: {str(e)[:28]}")

    # ------------------------------------------------------ sensibilidade
    if not cfg.ITENS_CONHECIDOS:
        print("\nSem gabarito em ITENS_CONHECIDOS — impossível validar.")
        print("Preencha config.py antes de coletar.")
        return

    print("\n" + "=" * 70)
    print("SENSIBILIDADE — o gabarito é recuperado?")
    print("=" * 70)

    if "pubmed" not in cfg.BASES:
        print("(teste disponível apenas via PubMed; inclua-o em BASES)")
        return

    from fontes import PubMed
    pm = PubMed()
    q = consultas.get("pubmed")
    achados, perdidos = 0, []
    for doi, desc in cfg.ITENS_CONHECIDOS.items():
        try:
            n = pm.contar(f'({q}) AND "{doi}"[AID]')
        except Exception:
            n = 0
        if n:
            achados += 1
        else:
            perdidos.append(desc)
        print(f"  [{'x' if n else ' '}] {desc}")

    total = len(cfg.ITENS_CONHECIDOS)
    pct = 100 * achados / total
    print(f"\n  {achados}/{total} ({pct:.0f}%)")

    print("\n" + "=" * 70)
    if pct >= 90:
        print("Sensibilidade alta. Pode coletar.")
    elif pct >= 70:
        print("Sensibilidade intermediária. Vale investigar antes de coletar:")
        print(f"  {PY} -m pipeline.diagnosticar --revisao {args.revisao}")
    else:
        print("Sensibilidade BAIXA. Não colete ainda — a busca está perdendo")
        print("evidência conhecida. Rode o diagnóstico para ver qual bloco barra:")
        print(f"  {PY} -m pipeline.diagnosticar --revisao {args.revisao}")
    if perdidos:
        print(f"\nPerdidos: {len(perdidos)}")


if __name__ == "__main__":
    main()
