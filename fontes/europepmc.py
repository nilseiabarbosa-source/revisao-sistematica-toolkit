"""Europe PMC — base primaria recomendada.

Sem chave de API. Indexa todo o PubMed/MEDLINE mais preprints, teses e patentes,
e devolve texto completo em XML para o subconjunto de acesso aberto.

Sintaxe de consulta: https://europepmc.org/searchsyntax
Exemplo: '(cancer AND immunotherapy) AND (PUB_YEAR:2020 TO 2026) AND SRC:MED'
"""

from __future__ import annotations

from typing import Iterator

from .base import ClienteHTTP, FonteBase, Registro, extrair_ano, normalizar_doi

BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"


class EuropePMC(FonteBase):
    nome = "europepmc"

    def __init__(self, req_por_segundo: float = 5.0) -> None:
        self.http = ClienteHTTP(req_por_segundo)

    def buscar(self, consulta: str, limite: int = 1000) -> Iterator[Registro]:
        cursor = "*"
        colhidos = 0
        while colhidos < limite:
            r = self.http.get(
                f"{BASE}/search",
                params={
                    "query": consulta,
                    "format": "json",
                    "pageSize": min(1000, limite - colhidos),
                    "cursorMark": cursor,
                    "resultType": "core",   # inclui resumo, autores, MeSH
                },
            )
            dados = r.json()
            itens = dados.get("resultList", {}).get("result", [])
            if not itens:
                return
            for item in itens:
                yield self._converter(item)
                colhidos += 1
            proximo = dados.get("nextCursorMark")
            if not proximo or proximo == cursor:
                return
            cursor = proximo

    def contar(self, consulta: str) -> int:
        """Numero total de resultados — util para o log PRISMA-S sem baixar tudo."""
        r = self.http.get(
            f"{BASE}/search",
            params={"query": consulta, "format": "json", "pageSize": 1},
        )
        return int(r.json().get("hitCount", 0))

    def por_dois(self, dois: list[str], por_lote: int = 25) -> dict[str, Registro]:
        """Recupera varios DOIs de uma vez. Devolve {doi_normalizado: Registro}.

        Uma requisicao por DOI e' desperdicio: a sintaxe do Europe PMC aceita OR,
        e 25 por chamada transforma 400 requisicoes em 16. O lote nao vai muito
        alem disso porque a consulta viaja na URL e estoura o limite de tamanho.

        DOIs que a base nao conhece simplesmente nao aparecem no resultado — o
        chamador compara o que pediu com o que voltou.
        """
        achados: dict[str, Registro] = {}
        limpos = [d for d in (normalizar_doi(x) for x in dois) if d]
        for i in range(0, len(limpos), por_lote):
            lote = limpos[i : i + por_lote]
            consulta = " OR ".join(f'DOI:"{d}"' for d in lote)
            try:
                r = self.http.get(
                    f"{BASE}/search",
                    params={
                        "query": consulta,
                        "format": "json",
                        "pageSize": por_lote,
                        "resultType": "core",
                    },
                )
            except RuntimeError:
                continue  # lote falhou; os demais seguem
            for item in r.json().get("resultList", {}).get("result", []):
                reg = self._converter(item)
                chave = normalizar_doi(reg.doi)
                if chave:
                    achados[chave] = reg
        return achados

    def texto_completo_xml(self, pmcid: str) -> str | None:
        """XML JATS do texto completo, quando o artigo esta no subconjunto OA.

        XML e muito superior a PDF para extracao de dados: secoes, tabelas e
        referencias vem estruturadas.
        """
        if not pmcid:
            return None
        try:
            r = self.http.get(f"{BASE}/{pmcid}/fullTextXML")
        except RuntimeError:
            return None
        return r.text or None

    @staticmethod
    def _converter(item: dict) -> Registro:
        autores = [
            a.get("fullName", "").strip()
            for a in (item.get("authorList", {}) or {}).get("author", [])
            if a.get("fullName")
        ]
        if not autores and item.get("authorString"):
            autores = [p.strip() for p in item["authorString"].split(",") if p.strip()]

        termos = [
            m.get("descriptorName", "")
            for m in (item.get("meshHeadingList", {}) or {}).get("meshHeading", [])
            if m.get("descriptorName")
        ]
        termos += [
            k for k in (item.get("keywordList", {}) or {}).get("keyword", []) if k
        ]

        aberto = item.get("isOpenAccess") == "Y"
        pmcid = item.get("pmcid", "") or ""

        return Registro(
            fonte="europepmc",
            id_fonte=item.get("id", ""),
            titulo=(item.get("title") or "").strip().rstrip("."),
            resumo=item.get("abstractText", "") or "",
            autores=autores,
            ano=extrair_ano(item.get("pubYear") or item.get("firstPublicationDate")),
            periodico=item.get("journalTitle", "") or item.get("bookOrReportDetails", {}).get("publisher", ""),
            doi=item.get("doi", "") or "",
            pmid=item.get("pmid", "") or "",
            pmcid=pmcid,
            tipo=", ".join(item.get("pubTypeList", {}).get("pubType", []))
            if isinstance(item.get("pubTypeList"), dict)
            else (item.get("pubType", "") or ""),
            idioma=item.get("language", "") or "",
            termos=termos,
            url=f"https://europepmc.org/article/{item.get('source', 'MED')}/{item.get('id', '')}",
            acesso_aberto=aberto,
            url_texto_completo=(
                f"{BASE}/{pmcid}/fullTextXML" if aberto and pmcid else ""
            ),
            bruto=item,
        )
