"""arXiv — preprints de computacao, estatistica e quantitativos.

Livre, sem chave. Traz resumo completo, o que o torna imediatamente triavel —
diferente do DBLP, que so devolve metadados.

Sintaxe: campos `ti:`, `abs:`, `all:`, `cat:`; operadores `AND`, `OR`, `ANDNOT`;
frases entre aspas. Categorias uteis aqui: cs.LG, cs.AI, cs.CL, stat.ML, q-bio.

A API pede cortesia: 1 requisicao a cada 3 segundos e paginas de ate 2.000.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Iterator

from .base import ClienteHTTP, FonteBase, Registro, extrair_ano

BASE = "http://export.arxiv.org/api/query"
NS = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
PAGINA = 200


class Arxiv(FonteBase):
    nome = "arxiv"

    def __init__(self, req_por_segundo: float = 0.34) -> None:
        # 1 req a cada ~3 s, conforme pedido na documentacao da API.
        self.http = ClienteHTTP(req_por_segundo)

    def contar(self, consulta: str) -> int:
        r = self.http.get(
            BASE, params={"search_query": consulta, "start": 0, "max_results": 1}
        )
        raiz = ET.fromstring(r.content)
        total = raiz.find("opensearch:totalResults", {
            "opensearch": "http://a9.com/-/spec/opensearch/1.1/"
        })
        return int(total.text) if total is not None and total.text else 0

    def buscar(self, consulta: str, limite: int = 1000) -> Iterator[Registro]:
        colhidos = 0
        while colhidos < limite:
            r = self.http.get(
                BASE,
                params={
                    "search_query": consulta,
                    "start": colhidos,
                    "max_results": min(PAGINA, limite - colhidos),
                    "sortBy": "submittedDate",
                    "sortOrder": "descending",
                },
            )
            raiz = ET.fromstring(r.content)
            entradas = raiz.findall("a:entry", NS)
            if not entradas:
                return
            for e in entradas:
                yield self._converter(e)
                colhidos += 1
                if colhidos >= limite:
                    return

    @staticmethod
    def _texto(no) -> str:
        return " ".join(no.text.split()) if (no is not None and no.text) else ""

    @classmethod
    def _converter(cls, e: ET.Element) -> Registro:
        ident = cls._texto(e.find("a:id", NS))
        arxiv_id = ident.rsplit("/", 1)[-1] if ident else ""

        doi = cls._texto(e.find("arxiv:doi", NS))
        if not doi and arxiv_id:
            doi = f"10.48550/arXiv.{arxiv_id.split('v')[0]}"

        pdf = ""
        for link in e.findall("a:link", NS):
            if link.get("title") == "pdf":
                pdf = link.get("href", "")

        return Registro(
            fonte="arxiv",
            id_fonte=arxiv_id,
            titulo=cls._texto(e.find("a:title", NS)).rstrip("."),
            resumo=cls._texto(e.find("a:summary", NS)),
            autores=[cls._texto(a.find("a:name", NS)) for a in e.findall("a:author", NS)],
            ano=extrair_ano(cls._texto(e.find("a:published", NS))),
            periodico=cls._texto(e.find("arxiv:journal_ref", NS)) or "arXiv",
            doi=doi,
            tipo="preprint",
            termos=[c.get("term", "") for c in e.findall("a:category", NS) if c.get("term")],
            url=ident,
            acesso_aberto=True,
            url_texto_completo=pdf,
        )
