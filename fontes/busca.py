"""Orquestrador: executa a mesma pergunta em varias bases, deduplica e registra.

O log por base (string exata, data, contagem) e requisito do PRISMA-S. Sem ele a
revisao nao e reproduzivel, entao ele e gravado automaticamente, nao opcional.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .base import Registro
from .clinicaltrials import ClinicalTrials
from .crossref import Crossref
from .dedup import ResultadoDedup, deduplicar
from .europepmc import EuropePMC
from .pubmed import PubMed
from .unpaywall import Unpaywall

FONTES_DISPONIVEIS = {
    "europepmc": EuropePMC,
    "pubmed": PubMed,
    "crossref": Crossref,
    "clinicaltrials": ClinicalTrials,
}


@dataclass
class LogBusca:
    """Uma linha do log PRISMA-S."""

    fonte: str
    consulta: str
    data_hora: str
    n_recuperados: int
    n_total_disponivel: int | None = None
    erro: str = ""


@dataclass
class ResultadoBusca:
    registros: list[Registro] = field(default_factory=list)
    dedup: ResultadoDedup | None = None
    logs: list[LogBusca] = field(default_factory=list)

    def salvar(self, diretorio: str | Path) -> Path:
        """Grava registros, log PRISMA-S e pares fuzzy para conferencia."""
        d = Path(diretorio)
        d.mkdir(parents=True, exist_ok=True)

        (d / "registros.json").write_text(
            json.dumps(
                [r.para_dict() for r in self.registros], ensure_ascii=False, indent=2
            ),
            encoding="utf-8",
        )
        (d / "log_prisma_s.json").write_text(
            json.dumps([vars(l) for l in self.logs], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if self.dedup:
            texto = self.dedup.resumo_prisma()
            if self.dedup.pares_fuzzy:
                texto += "\n\nPares unidos por similaridade (conferir manualmente):\n"
                for a, b, razao in self.dedup.pares_fuzzy:
                    texto += f"  [{razao}] {a}\n            {b}\n"
            (d / "relatorio_dedup.txt").write_text(texto, encoding="utf-8")
        return d


def buscar_multiplas_fontes(
    consulta: str,
    fontes: list[str] | None = None,
    limite_por_fonte: int = 1000,
    ncbi_api_key: str | None = None,
    enriquecer_oa: bool = False,
    usar_fuzzy: bool = True,
) -> ResultadoBusca:
    """Executa a consulta nas bases pedidas e devolve o conjunto deduplicado.

    A consulta e passada literalmente a cada API. As sintaxes divergem (o
    PubMed aceita [MeSH Terms], o Europe PMC usa SRC:MED, o Crossref e texto
    livre), entao para uma revisao formal vale montar uma string por base e
    chamar cada adaptador individualmente, registrando ambas no log.
    """
    fontes = fontes or ["europepmc", "pubmed", "crossref"]
    resultado = ResultadoBusca()
    brutos: list[Registro] = []

    for nome in fontes:
        classe = FONTES_DISPONIVEIS.get(nome)
        if classe is None:
            resultado.logs.append(
                LogBusca(nome, consulta, _agora(), 0, erro="fonte desconhecida")
            )
            continue

        adaptador = classe(api_key=ncbi_api_key) if nome == "pubmed" else classe()
        try:
            total = adaptador.contar(consulta) if hasattr(adaptador, "contar") else None
            colhidos = adaptador.coletar(consulta, limite_por_fonte)
            brutos.extend(colhidos)
            resultado.logs.append(
                LogBusca(nome, consulta, _agora(), len(colhidos), total)
            )
        except Exception as e:  # uma base fora do ar nao derruba a coleta inteira
            resultado.logs.append(
                LogBusca(nome, consulta, _agora(), 0, erro=f"{type(e).__name__}: {e}")
            )

    resultado.dedup = deduplicar(brutos, usar_fuzzy=usar_fuzzy)
    resultado.registros = resultado.dedup.unicos

    if enriquecer_oa:
        up = Unpaywall()
        for r in resultado.registros:
            up.enriquecer(r)

    return resultado


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
