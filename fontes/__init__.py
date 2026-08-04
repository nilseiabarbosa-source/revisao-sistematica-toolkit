"""Adaptadores de bases bibliograficas com API aberta, em esquema unico.

Uso minimo:

    from fontes import buscar_multiplas_fontes

    res = buscar_multiplas_fontes(
        "immunotherapy AND pancreatic cancer",
        fontes=["europepmc", "pubmed"],
        limite_por_fonte=500,
    )
    print(res.dedup.resumo_prisma())
    res.salvar("resultados/busca_01")
"""

from .arxiv import Arxiv
from .base import EMAIL_CONTATO, FonteBase, Registro, normalizar_doi, normalizar_titulo
from .busca import FONTES_DISPONIVEIS, LogBusca, ResultadoBusca, buscar_multiplas_fontes
from .clinicaltrials import ClinicalTrials
from .crossref import Crossref
from .dblp import DBLP
from .dedup import ResultadoDedup, deduplicar
from .europepmc import EuropePMC
from .openalex import OpenAlex
from .pubmed import PubMed
from .semanticscholar import SemanticScholar
from .unpaywall import Unpaywall

# CORE e Scopus exigem chave e por isso nao sao importados aqui — importar
# diretamente (`from fontes.core import CORE`) para que a falta da credencial
# nao quebre o import do pacote inteiro.

__all__ = [
    "EMAIL_CONTATO",
    "FONTES_DISPONIVEIS",
    "Arxiv",
    "ClinicalTrials",
    "Crossref",
    "DBLP",
    "EuropePMC",
    "FonteBase",
    "LogBusca",
    "OpenAlex",
    "PubMed",
    "Registro",
    "ResultadoBusca",
    "ResultadoDedup",
    "SemanticScholar",
    "Unpaywall",
    "buscar_multiplas_fontes",
    "deduplicar",
    "normalizar_doi",
    "normalizar_titulo",
]

__version__ = "1.0.0"
