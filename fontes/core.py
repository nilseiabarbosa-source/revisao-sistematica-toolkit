"""CORE — agregador de repositorios de acesso aberto (300M+ documentos).

Exige chave gratuita, obtida em https://core.ac.uk/services/api. Colocar no .env
como CORE_API_KEY.

Relevante aqui por dois motivos: agrega repositorios institucionais que indexam
anais de computacao, e frequentemente traz o **texto completo** — util para a
etapa de extracao, nao so para a triagem.

Sintaxe booleana com campos: `title:`, `abstract:`, `fullText:`, `yearPublished:`.
"""

from __future__ import annotations

import os
from typing import Iterator

from .base import ClienteHTTP, FonteBase, Registro, extrair_ano

BASE = "https://api.core.ac.uk/v3/search/works"


class CORE(FonteBase):
    nome = "core"

    def __init__(self, api_key: str | None = None, req_por_segundo: float = 1.0) -> None:
        self.api_key = api_key or os.environ.get("CORE_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "CORE exige chave gratuita. Registre em core.ac.uk/services/api "
                "e defina CORE_API_KEY no .env."
            )
        self.http = ClienteHTTP(req_por_segundo)
        self.http.sessao.headers["Authorization"] = f"Bearer {self.api_key}"

    def contar(self, consulta: str) -> int:
        r = self.http.get(BASE, params={"q": consulta, "limit": 1})
        return int(r.json().get("totalHits", 0))

    def buscar(self, consulta: str, limite: int = 1000) -> Iterator[Registro]:
        offset = 0
        colhidos = 0
        while colhidos < limite:
            r = self.http.get(
                BASE,
                params={"q": consulta, "limit": min(100, limite - colhidos), "offset": offset},
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
            offset += len(itens)

    @staticmethod
    def _converter(it: dict) -> Registro:
        autores = [a.get("name", "") for a in (it.get("authors") or []) if a.get("name")]
        doi = it.get("doi") or ""
        return Registro(
            fonte="core",
            id_fonte=str(it.get("id", "")),
            titulo=(it.get("title") or "").strip().rstrip("."),
            resumo=it.get("abstract") or "",
            autores=autores,
            ano=extrair_ano(it.get("yearPublished") or it.get("publishedDate")),
            periodico=(it.get("publisher") or "")
            or ", ".join(j.get("title", "") for j in (it.get("journals") or [])),
            doi=doi,
            tipo=it.get("documentType", "") or "",
            idioma=(it.get("language") or {}).get("code", "") if isinstance(it.get("language"), dict) else "",
            url=it.get("downloadUrl") or "",
            acesso_aberto=True,
            url_texto_completo=it.get("downloadUrl") or "",
        )
