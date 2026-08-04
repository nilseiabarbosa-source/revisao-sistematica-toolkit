"""DBLP — a bibliografia canonica da ciencia da computacao.

Livre, sem chave. Cobre anais de conferencia (NeurIPS, ICML, MICCAI, AMIA, CHIL)
com rigor que nenhuma base biomedica alcanca.

Limitacao decisiva: **nao devolve resumo**. Como o Web of Science Starter, serve
para obter DOIs e titulos, que depois sao enriquecidos via Crossref/Europe PMC.
Sem essa etapa, os registros so podem ser triados por titulo.

A busca do DBLP e por palavras-chave com prefixo, nao booleana completa: nao ha
OR/AND explicitos entre grupos como no PubMed. Na pratica isso significa rodar
varias consultas curtas em vez de uma longa.
"""

from __future__ import annotations

from typing import Iterator

from .base import ClienteHTTP, FonteBase, Registro, extrair_ano

BASE = "https://dblp.org/search/publ/api"
PAGINA = 1000


class DBLP(FonteBase):
    nome = "dblp"

    def __init__(self, req_por_segundo: float = 1.0) -> None:
        self.http = ClienteHTTP(req_por_segundo)

    def contar(self, consulta: str) -> int:
        # `h=0` devolve HTTP 500 nesta API — o minimo aceito e 1.
        r = self.http.get(
            BASE, params={"q": consulta, "format": "json", "h": 1}
        )
        hits = r.json().get("result", {}).get("hits", {})
        return int(hits.get("@total", 0))

    def buscar(self, consulta: str, limite: int = 1000) -> Iterator[Registro]:
        colhidos = 0
        while colhidos < limite:
            r = self.http.get(
                BASE,
                params={
                    "q": consulta,
                    "format": "json",
                    "h": min(PAGINA, limite - colhidos),
                    "f": colhidos,
                },
            )
            hits = r.json().get("result", {}).get("hits", {})
            itens = hits.get("hit", [])
            if not itens:
                return
            for it in itens:
                yield self._converter(it.get("info", {}))
                colhidos += 1
                if colhidos >= limite:
                    return
            if colhidos >= int(hits.get("@total", 0)):
                return

    @staticmethod
    def _converter(info: dict) -> Registro:
        autores = info.get("authors", {}).get("author", [])
        if isinstance(autores, dict):
            autores = [autores]
        nomes = [a.get("text", "") for a in autores if isinstance(a, dict)]

        return Registro(
            fonte="dblp",
            id_fonte=info.get("key", ""),
            titulo=(info.get("title") or "").strip().rstrip("."),
            resumo="",  # DBLP nao fornece — enriquecer depois
            autores=nomes,
            ano=extrair_ano(info.get("year")),
            periodico=info.get("venue", "") if isinstance(info.get("venue"), str)
            else ", ".join(info.get("venue", [])),
            doi=info.get("doi", "") or "",
            tipo=info.get("type", ""),
            url=info.get("ee", "") or info.get("url", ""),
        )
