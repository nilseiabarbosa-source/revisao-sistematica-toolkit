"""Unpaywall — resolve DOI para o melhor link de acesso aberto disponivel.

Sem chave; exige apenas o parametro `email`. E o primeiro degrau da cascata de
aquisicao de texto completo. Para artigos ja identificados com PMCID, prefira o
XML do Europe PMC: vem estruturado, o PDF nao.
"""

from __future__ import annotations

from .base import EMAIL_CONTATO, ClienteHTTP, Registro, normalizar_doi

BASE = "https://api.unpaywall.org/v2"


class Unpaywall:
    def __init__(self, email: str = EMAIL_CONTATO, req_por_segundo: float = 8.0) -> None:
        self.email = email
        self.http = ClienteHTTP(req_por_segundo)

    def consultar(self, doi: str) -> dict | None:
        doi = normalizar_doi(doi)
        if not doi:
            return None
        try:
            r = self.http.get(f"{BASE}/{doi}", params={"email": self.email})
        except RuntimeError:
            return None
        return r.json()

    def melhor_pdf(self, doi: str) -> str | None:
        dados = self.consultar(doi)
        if not dados:
            return None
        melhor = dados.get("best_oa_location") or {}
        return melhor.get("url_for_pdf") or melhor.get("url") or None

    def locais_abertos(self, doi: str) -> list[str]:
        """Todos os locais abertos, repositorio primeiro.

        O `best_oa_location` do Unpaywall costuma apontar para o site da
        editora, que e a copia de melhor qualidade — mas tambem a que bloqueia
        acesso automatizado. Wiley, RSC, ACS e Science devolvem 403 mesmo em
        artigo aberto. Repositorio (PMC, institucional, arXiv) nao bloqueia,
        entao vale tentar por ele antes.
        """
        dados = self.consultar(doi)
        if not dados:
            return []
        locais = dados.get("oa_locations") or []
        if not locais and dados.get("best_oa_location"):
            locais = [dados["best_oa_location"]]

        def prioridade(l: dict) -> int:
            return 0 if (l.get("host_type") or "") == "repository" else 1

        urls: list[str] = []
        for l in sorted(locais, key=prioridade):
            for u in (l.get("url_for_pdf"), l.get("url")):
                if u and u not in urls:
                    urls.append(u)
        return urls

    def enriquecer(self, registro: Registro) -> Registro:
        """Preenche acesso_aberto e url_texto_completo quando ainda vazios."""
        if registro.url_texto_completo or not registro.doi:
            return registro
        dados = self.consultar(registro.doi)
        if not dados:
            return registro
        registro.acesso_aberto = bool(dados.get("is_oa"))
        melhor = dados.get("best_oa_location") or {}
        registro.url_texto_completo = (
            melhor.get("url_for_pdf") or melhor.get("url") or ""
        )
        return registro
