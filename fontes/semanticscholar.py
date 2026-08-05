"""Semantic Scholar Academic Graph — cobertura ampla, livre, sem chave.

Candidato a substituto parcial de Scopus/Web of Science: indexa literatura
biomedica e de computacao (a segunda mal coberta pelo PubMed), traz resumo, e
nao exige assinatura institucional.

Usa o endpoint `search/bulk`, que pagina por token e devolve ate 1.000 por
chamada. A sintaxe de consulta e propria: `+` para AND, `|` para OR, `-` para
NOT, aspas para frase e `*` como curinga de sufixo.
"""

from __future__ import annotations

from typing import Iterator

from .base import ClienteHTTP, FonteBase, Registro, extrair_ano

BASE = "https://api.semanticscholar.org/graph/v1"

CAMPOS = ",".join([
    "paperId", "externalIds", "title", "abstract", "year", "venue",
    "authors", "publicationTypes", "openAccessPdf", "fieldsOfStudy",
    "publicationDate", "journal",
])


class SemanticScholar(FonteBase):
    nome = "semanticscholar"

    def __init__(
        self,
        api_key: str | None = None,
        req_por_segundo: float = 1.0,
        anos: tuple[int, int] | None = None,
    ) -> None:
        # Sem chave o limite e compartilhado entre todos os usuarios anonimos;
        # 1 req/s evita 429 na maior parte do tempo.
        self.http = ClienteHTTP(req_por_segundo)
        if api_key:
            self.http.sessao.headers["x-api-key"] = api_key
        # A janela vem da revisao. Sem ela o padrao historico e' mantido, mas
        # coletar fora do recorte custa chamadas e tempo para registros que o
        # filtro de ano do pipeline descarta logo em seguida.
        self.faixa_anos = f"{anos[0]}-{anos[1]}" if anos else "2016-2026"

    def contar(self, consulta: str, ano: str | None = None) -> int:
        ano = ano or self.faixa_anos
        params = {"query": consulta, "fields": "paperId"}
        if ano:
            params["year"] = ano
        r = self.http.get(f"{BASE}/paper/search/bulk", params=params)
        return int(r.json().get("total", 0))

    def buscar(
        self,
        consulta: str,
        limite: int = 1000,
        ano: str | None = None,
    ) -> Iterator[Registro]:
        ano = ano or self.faixa_anos
        token = None
        colhidos = 0
        while colhidos < limite:
            params = {"query": consulta, "fields": CAMPOS}
            if ano:
                params["year"] = ano
            if token:
                params["token"] = token
            r = self.http.get(f"{BASE}/paper/search/bulk", params=params)
            dados = r.json()
            itens = dados.get("data") or []
            if not itens:
                return
            for item in itens:
                yield self._converter(item)
                colhidos += 1
                if colhidos >= limite:
                    return
            token = dados.get("token")
            if not token:
                return

    # ------------------------------------------------------- snowballing
    # O protocolo (secao 5) exige citation chasing para a frente e para tras.
    # O grafo do S2 faz as duas direcoes de graca, e com precisao muito maior
    # que alargar a string de busca.

    def referencias(self, doi: str, limite: int = 1000) -> list[Registro]:
        """Para tras: o que este artigo cita."""
        return self._grafo(doi, "references", "citedPaper", limite)

    def citacoes(self, doi: str, limite: int = 1000) -> list[Registro]:
        """Para a frente: quem cita este artigo."""
        return self._grafo(doi, "citations", "citingPaper", limite)

    def _grafo(self, doi: str, endpoint: str, chave: str, limite: int) -> list[Registro]:
        saida: list[Registro] = []
        offset = 0
        while len(saida) < limite:
            try:
                r = self.http.get(
                    f"{BASE}/paper/DOI:{doi}/{endpoint}",
                    params={
                        "fields": CAMPOS,
                        "limit": min(1000, limite - len(saida)),
                        "offset": offset,
                    },
                )
            except RuntimeError:
                break
            dados = r.json()
            itens = dados.get("data") or []
            if not itens:
                break
            for it in itens:
                artigo = it.get(chave) or {}
                if artigo.get("title"):
                    reg = self._converter(artigo)
                    reg.fonte = f"snowball_{endpoint}"
                    saida.append(reg)
            if dados.get("next") is None:
                break
            offset = dados["next"]
        return saida

    @staticmethod
    def _converter(item: dict) -> Registro:
        ext = item.get("externalIds") or {}
        pdf = item.get("openAccessPdf") or {}
        revista = item.get("journal") or {}
        pmcid = ext.get("PubMedCentral") or ""

        return Registro(
            fonte="semanticscholar",
            id_fonte=item.get("paperId", ""),
            titulo=(item.get("title") or "").strip().rstrip("."),
            resumo=item.get("abstract") or "",
            autores=[a.get("name", "") for a in (item.get("authors") or []) if a.get("name")],
            ano=extrair_ano(item.get("year") or item.get("publicationDate")),
            periodico=revista.get("name") or item.get("venue") or "",
            doi=ext.get("DOI") or "",
            pmid=str(ext.get("PubMed") or ""),
            pmcid=f"PMC{pmcid}" if pmcid and not str(pmcid).startswith("PMC") else str(pmcid),
            tipo=", ".join(item.get("publicationTypes") or []),
            termos=item.get("fieldsOfStudy") or [],
            url=f"https://www.semanticscholar.org/paper/{item.get('paperId', '')}",
            acesso_aberto=bool(pdf.get("url")),
            url_texto_completo=pdf.get("url") or "",
            bruto=item,
        )
