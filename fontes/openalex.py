"""OpenAlex — cobertura multidisciplinar ampla, inclusive computacao.

ATENCAO: desde 13/02/2026 exige chave de API e adotou cobranca por uso. Cada
chave tem uma cota diaria gratuita modesta; busca e filtro em massa a consomem,
enquanto consulta de registro unico por DOI segue livre. Sem chave o servico
concede ~100 creditos de teste e depois devolve 409.

Chave gratuita em https://openalex.org — colocar no .env como OPENALEX_API_KEY.

O resumo vem como indice invertido (`abstract_inverted_index`), nao como texto;
a reconstrucao esta em `_resumo()`.
"""

from __future__ import annotations

import os
from typing import Iterator

from .base import EMAIL_CONTATO, ClienteHTTP, FonteBase, Registro, extrair_ano

BASE = "https://api.openalex.org/works"


class OpenAlex(FonteBase):
    nome = "openalex"

    def __init__(self, api_key: str | None = None, req_por_segundo: float = 5.0) -> None:
        self.api_key = api_key or os.environ.get("OPENALEX_API_KEY", "")
        self.http = ClienteHTTP(req_por_segundo)

    def _params(self, extra: dict) -> dict:
        p = {"mailto": EMAIL_CONTATO, **extra}
        if self.api_key:
            p["api_key"] = self.api_key
        return p

    # ATENCAO ao campo de busca. `default.search` ordena por relevancia e
    # devolve qualquer coisa vagamente proxima: usado com uma lista de palavras,
    # produziu 3% de precisao nesta revisao. `title_and_abstract.search` aceita
    # AND/OR/aspas e se comporta como busca booleana — verificado em
    # testar_openalex_booleano.py. Use `booleana=True` sempre que a consulta
    # tiver estrutura logica.
    def _filtro(self, consulta: str, filtros: str, booleana: bool) -> str:
        campo = "title_and_abstract.search" if booleana else "default.search"
        alvo = f"{campo}:{consulta}"
        return f"{filtros},{alvo}" if filtros else alvo

    def contar(self, consulta: str, filtros: str = "", booleana: bool = True) -> int:
        f = self._filtro(consulta, filtros, booleana)
        r = self.http.get(BASE, params=self._params({"filter": f, "per-page": 1}))
        return int(r.json().get("meta", {}).get("count", 0))

    def buscar(
        self, consulta: str, limite: int = 1000, filtros: str = "",
        booleana: bool = True,
    ) -> Iterator[Registro]:
        f = self._filtro(consulta, filtros, booleana)
        cursor = "*"
        colhidos = 0
        while colhidos < limite:
            r = self.http.get(
                BASE,
                params=self._params({
                    "filter": f,
                    "per-page": min(200, limite - colhidos),
                    "cursor": cursor,
                }),
            )
            dados = r.json()
            itens = dados.get("results", [])
            if not itens:
                return
            for it in itens:
                yield self._converter(it)
                colhidos += 1
                if colhidos >= limite:
                    return
            cursor = dados.get("meta", {}).get("next_cursor")
            if not cursor:
                return

    @staticmethod
    def _resumo(indice: dict | None) -> str:
        """Reconstroi o texto a partir do indice invertido."""
        if not indice:
            return ""
        posicoes: list[tuple[int, str]] = []
        for palavra, idxs in indice.items():
            posicoes.extend((i, palavra) for i in idxs)
        return " ".join(p for _, p in sorted(posicoes))

    @classmethod
    def _converter(cls, it: dict) -> Registro:
        ids = it.get("ids", {}) or {}
        local = it.get("primary_location") or {}
        fonte = (local.get("source") or {}) if isinstance(local, dict) else {}
        oa = it.get("open_access", {}) or {}

        pmid = (ids.get("pmid") or "").rsplit("/", 1)[-1] if ids.get("pmid") else ""

        return Registro(
            fonte="openalex",
            id_fonte=(it.get("id") or "").rsplit("/", 1)[-1],
            titulo=(it.get("title") or "").strip().rstrip("."),
            resumo=cls._resumo(it.get("abstract_inverted_index")),
            autores=[
                (a.get("author") or {}).get("display_name", "")
                for a in (it.get("authorships") or [])
            ],
            ano=extrair_ano(it.get("publication_year") or it.get("publication_date")),
            periodico=fonte.get("display_name", "") or "",
            doi=(it.get("doi") or "").replace("https://doi.org/", ""),
            pmid=pmid,
            tipo=it.get("type", "") or "",
            idioma=it.get("language", "") or "",
            termos=[
                (c.get("display_name") or "")
                for c in (it.get("concepts") or [])[:12]
            ],
            url=it.get("id", ""),
            acesso_aberto=bool(oa.get("is_oa")),
            url_texto_completo=oa.get("oa_url") or "",
            bruto=it,
        )
