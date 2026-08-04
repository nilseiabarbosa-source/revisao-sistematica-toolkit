"""Scopus Search API (Elsevier).

Requer chave de `dev.elsevier.com`. A chave sozinha só funciona a partir de um IP
da instituição assinante; para uso remoto é preciso o *Institutional Token*
(cabeçalho `X-ELS-Insttoken`), emitido pela Elsevier mediante solicitação.

Duas visões (`view`) importam:

- `STANDARD` — funciona com qualquer chave válida, mas **não traz resumo**.
- `COMPLETE` — traz resumo (`dc:description`) e palavras-chave, e exige que a
  instituição tenha direito de API sobre o Scopus.

Como sem resumo não há triagem por título/resumo, o teste em `testar_scopus.py`
verifica qual visão a sua credencial libera antes de rodar a busca inteira.
"""

from __future__ import annotations

import os
from typing import Iterator

from .base import ClienteHTTP, FonteBase, Registro, extrair_ano

BASE = "https://api.elsevier.com/content/search/scopus"

# A API recusa `start` a partir de 5.000; alem desse ponto e preciso fatiar a
# consulta (por ano, tipo de documento etc.).
MAX_START = 5000


class Scopus(FonteBase):
    nome = "scopus"

    def __init__(
        self,
        api_key: str | None = None,
        insttoken: str | None = None,
        view: str = "COMPLETE",
        req_por_segundo: float = 3.0,
    ) -> None:
        self.api_key = api_key or os.environ.get("SCOPUS_API_KEY", "")
        self.insttoken = insttoken or os.environ.get("SCOPUS_INSTTOKEN", "")
        if not self.api_key:
            raise ValueError(
                "Defina SCOPUS_API_KEY no ambiente ou passe api_key= ao construtor."
            )
        self.view = view
        self.http = ClienteHTTP(req_por_segundo)
        self.http.sessao.headers.update(
            {"X-ELS-APIKey": self.api_key, "Accept": "application/json"}
        )
        if self.insttoken:
            self.http.sessao.headers["X-ELS-Insttoken"] = self.insttoken

    # ------------------------------------------------------------------
    def diagnosticar(self) -> dict:
        """Verifica o que a credencial libera: acesso, visão e resumo."""
        info = {
            "chave_presente": bool(self.api_key),
            "insttoken_presente": bool(self.insttoken),
            "acesso": False,
            "view_completa": False,
            "traz_resumo": False,
            "erro": "",
        }
        try:
            r = self.http.get(
                BASE, params={"query": "TITLE(cancer)", "count": 1, "view": "COMPLETE"}
            )
            info["acesso"] = True
            info["view_completa"] = True
            entradas = r.json().get("search-results", {}).get("entry", [])
            info["traz_resumo"] = bool(entradas and entradas[0].get("dc:description"))
        except Exception as e:
            info["erro"] = f"COMPLETE: {type(e).__name__}: {str(e)[:120]}"
            try:
                self.http.get(
                    BASE, params={"query": "TITLE(cancer)", "count": 1, "view": "STANDARD"}
                )
                info["acesso"] = True
            except Exception as e2:
                info["erro"] += f" | STANDARD: {type(e2).__name__}: {str(e2)[:120]}"
        return info

    def contar(self, consulta: str) -> int:
        r = self.http.get(BASE, params={"query": consulta, "count": 1, "view": self.view})
        return int(
            r.json().get("search-results", {}).get("opensearch:totalResults", 0)
        )

    def buscar(
        self, consulta: str, limite: int = 20000, ano_inicio: int = 2016, ano_fim: int = 2026
    ) -> Iterator[Registro]:
        """Coleta com fatiamento automático por ano quando necessário.

        Duas restrições da API moldam este método:

        - `cursor` exige *entitlement* que a chave comum não tem (403
          ENTITLEMENTS_ERROR), então a paginação é por `start`;
        - `start` trava em 5.000 registros por consulta.

        Quando o total passa de 5.000, a consulta é fatiada por ano de
        publicação — cada fatia cabe no teto e a união cobre o conjunto todo.
        """
        total = self.contar(consulta)
        if total <= MAX_START:
            yield from self._paginar(consulta, min(limite, total))
            return

        colhidos = 0
        for ano in range(ano_inicio, ano_fim + 1):
            if colhidos >= limite:
                return
            fatia = f"({consulta}) AND PUBYEAR IS {ano}"
            n = self.contar(fatia)
            if n == 0:
                continue
            if n > MAX_START:
                # Improvável nesta revisão, mas não deve passar silenciosamente:
                # um ano acima do teto significa perda de registros.
                print(
                    f"    AVISO: {ano} tem {n} registros, acima do teto de "
                    f"{MAX_START}. Fatie também por tipo de documento."
                )
            for reg in self._paginar(fatia, min(n, limite - colhidos)):
                yield reg
                colhidos += 1

    def _paginar(self, consulta: str, limite: int) -> Iterator[Registro]:
        inicio = 0
        colhidos = 0
        while colhidos < limite and inicio < MAX_START:
            r = self.http.get(
                BASE,
                params={
                    # Teto da Scopus Search API e 25 por pagina, em qualquer
                    # visao. Pedir mais devolve 400 Bad Request.
                    "query": consulta,
                    "count": 25,
                    "start": inicio,
                    "view": self.view,
                },
            )
            dados = r.json().get("search-results", {})
            entradas = dados.get("entry", [])
            if not entradas or "error" in entradas[0]:
                return
            for e in entradas:
                yield self._converter(e)
                colhidos += 1
                if colhidos >= limite:
                    return
            inicio += len(entradas)

    @staticmethod
    def _converter(e: dict) -> Registro:
        autores = []
        if e.get("dc:creator"):
            autores.append(e["dc:creator"])

        termos = []
        if e.get("authkeywords"):
            termos = [t.strip() for t in e["authkeywords"].split("|") if t.strip()]

        return Registro(
            fonte="scopus",
            id_fonte=e.get("eid", "") or e.get("dc:identifier", ""),
            titulo=(e.get("dc:title") or "").strip().rstrip("."),
            resumo=e.get("dc:description") or "",
            autores=autores,
            ano=extrair_ano(e.get("prism:coverDate")),
            periodico=e.get("prism:publicationName", "") or "",
            doi=e.get("prism:doi", "") or "",
            pmid=str(e.get("pubmed-id") or ""),
            tipo=e.get("subtypeDescription", "") or "",
            termos=termos,
            url=next(
                (l.get("@href", "") for l in e.get("link", []) if l.get("@ref") == "scopus"),
                "",
            ),
            acesso_aberto=str(e.get("openaccess", "0")) == "1",
            bruto=e,
        )
