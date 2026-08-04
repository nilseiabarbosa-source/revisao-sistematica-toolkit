"""Crossref — cobertura multidisciplinar ampla, sem chave.

Informar `mailto` coloca as requisicoes no "polite pool", com limites mais
generosos e melhor estabilidade. Nem todo registro traz resumo (depende do que
a editora depositou), entao o Crossref serve melhor como rede de captura
complementar do que como base primaria de triagem por resumo.
"""

from __future__ import annotations

from typing import Iterator

from .base import EMAIL_CONTATO, ClienteHTTP, FonteBase, Registro, extrair_ano

BASE = "https://api.crossref.org/works"


class Crossref(FonteBase):
    nome = "crossref"

    def __init__(self, req_por_segundo: float = 5.0) -> None:
        self.http = ClienteHTTP(req_por_segundo)

    def buscar(
        self,
        consulta: str,
        limite: int = 1000,
        ano_inicio: int | None = None,
        ano_fim: int | None = None,
        tipo: str | None = "journal-article",
    ) -> Iterator[Registro]:
        filtros = []
        if ano_inicio:
            filtros.append(f"from-pub-date:{ano_inicio}-01-01")
        if ano_fim:
            filtros.append(f"until-pub-date:{ano_fim}-12-31")
        if tipo:
            filtros.append(f"type:{tipo}")

        cursor = "*"
        colhidos = 0
        while colhidos < limite:
            params = {
                "query.bibliographic": consulta,
                "rows": min(1000, limite - colhidos),
                "cursor": cursor,
                "mailto": EMAIL_CONTATO,
            }
            if filtros:
                params["filter"] = ",".join(filtros)

            r = self.http.get(BASE, params=params)
            msg = r.json().get("message", {})
            itens = msg.get("items", [])
            if not itens:
                return
            for item in itens:
                yield self._converter(item)
                colhidos += 1
            proximo = msg.get("next-cursor")
            if not proximo or proximo == cursor:
                return
            cursor = proximo

    def por_doi(self, doi: str) -> Registro | None:
        try:
            r = self.http.get(f"{BASE}/{doi}", params={"mailto": EMAIL_CONTATO})
        except RuntimeError:
            return None
        return self._converter(r.json().get("message", {}))

    @staticmethod
    def _converter(item: dict) -> Registro:
        titulo = " ".join(item.get("title") or []).strip()
        autores = []
        for a in item.get("author", []) or []:
            nome = " ".join(p for p in (a.get("family"), a.get("given")) if p)
            autores.append(nome or a.get("name", ""))

        data = (
            item.get("published-print")
            or item.get("published-online")
            or item.get("issued")
            or {}
        )
        partes = data.get("date-parts") or [[None]]
        ano = extrair_ano(partes[0][0] if partes and partes[0] else None)

        # Alguns depositos trazem o resumo em JATS; a limpeza de tags fica no
        # normalizador de titulo/texto do pipeline.
        resumo = item.get("abstract", "") or ""

        licencas = item.get("license", []) or []
        aberto = any("creativecommons" in (l.get("URL") or "") for l in licencas)

        return Registro(
            fonte="crossref",
            id_fonte=item.get("DOI", ""),
            titulo=titulo,
            resumo=resumo,
            autores=[a for a in autores if a],
            ano=ano,
            periodico=" ".join(item.get("container-title") or []),
            doi=item.get("DOI", "") or "",
            tipo=item.get("type", "") or "",
            idioma=item.get("language", "") or "",
            termos=item.get("subject", []) or [],
            url=item.get("URL", "") or "",
            acesso_aberto=aberto,
            bruto=item,
        )
