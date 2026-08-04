"""PubMed / MEDLINE via E-utilities do NCBI.

Sem chave: 3 requisicoes por segundo. Com chave gratuita (obtida na conta NCBI):
10 por segundo. Estourar o teto resulta em bloqueio temporario do IP, entao o
limitador do ClienteHTTP nao deve ser afrouxado.

Vale manter o PubMed mesmo usando Europe PMC: aqui a consulta passa pelo
tradutor automatico de MeSH do NCBI, que expande termos de forma diferente.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Iterator

from .base import ClienteHTTP, FonteBase, Registro, extrair_ano

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
LOTE = 200


class PubMed(FonteBase):
    nome = "pubmed"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key
        self.http = ClienteHTTP(10.0 if api_key else 3.0)

    def _params(self, extra: dict) -> dict:
        p = {"db": "pubmed", "tool": "RevisaoSistematica", **extra}
        if self.api_key:
            p["api_key"] = self.api_key
        return p

    def buscar_ids(self, consulta: str, limite: int = 1000) -> list[str]:
        ids: list[str] = []
        while len(ids) < limite:
            r = self.http.get(
                f"{BASE}/esearch.fcgi",
                params=self._params(
                    {
                        "term": consulta,
                        "retmode": "json",
                        "retmax": min(LOTE, limite - len(ids)),
                        "retstart": len(ids),
                    }
                ),
            )
            res = r.json().get("esearchresult", {})
            lote = res.get("idlist", [])
            if not lote:
                break
            ids.extend(lote)
            if len(ids) >= int(res.get("count", 0)):
                break
        return ids[:limite]

    def contar(self, consulta: str) -> int:
        r = self.http.get(
            f"{BASE}/esearch.fcgi",
            params=self._params({"term": consulta, "retmode": "json", "retmax": 0}),
        )
        return int(r.json().get("esearchresult", {}).get("count", 0))

    def buscar(self, consulta: str, limite: int = 1000) -> Iterator[Registro]:
        ids = self.buscar_ids(consulta, limite)
        for i in range(0, len(ids), LOTE):
            lote = ids[i : i + LOTE]
            r = self.http.get(
                f"{BASE}/efetch.fcgi",
                params=self._params({"id": ",".join(lote), "retmode": "xml"}),
            )
            raiz = ET.fromstring(r.content)
            for art in raiz.findall(".//PubmedArticle"):
                yield self._converter(art)

    @staticmethod
    def _texto(no: ET.Element | None) -> str:
        if no is None:
            return ""
        return "".join(no.itertext()).strip()

    @classmethod
    def _converter(cls, art: ET.Element) -> Registro:
        # ATENCAO: nao usar `.//` aqui. O elemento PubmedArticle contem
        # <PubmedData><ReferenceList>, onde cada referencia citada traz o
        # proprio <ArticleIdList><ArticleId IdType="doi">. Um XPath descendente
        # captura o DOI da ultima referencia em vez do DOI do artigo — o que
        # corrompe silenciosamente identificador, deduplicacao e validacao.
        # Todos os caminhos abaixo sao ancorados a partir da raiz do registro.
        pmid = cls._texto(art.find("./MedlineCitation/PMID"))
        artigo = art.find("./MedlineCitation/Article")
        if artigo is None:
            artigo = ET.Element("Article")

        # O resumo pode vir fatiado em secoes rotuladas (Background, Methods...).
        partes = []
        for ab in artigo.findall("./Abstract/AbstractText"):
            rotulo = ab.get("Label")
            texto = cls._texto(ab)
            partes.append(f"{rotulo}: {texto}" if rotulo else texto)
        resumo = "\n".join(p for p in partes if p)

        autores = []
        for a in artigo.findall("./AuthorList/Author"):
            sobrenome = cls._texto(a.find("LastName"))
            iniciais = cls._texto(a.find("Initials"))
            coletivo = cls._texto(a.find("CollectiveName"))
            if sobrenome:
                autores.append(f"{sobrenome} {iniciais}".strip())
            elif coletivo:
                autores.append(coletivo)

        doi = pmcid = ""
        for aid in art.findall("./PubmedData/ArticleIdList/ArticleId"):
            tipo = aid.get("IdType")
            if tipo == "doi" and not doi:
                doi = cls._texto(aid)
            elif tipo == "pmc" and not pmcid:
                pmcid = cls._texto(aid)
        if not doi:  # alguns registros trazem o DOI so como ELocationID
            for el in artigo.findall("./ELocationID"):
                if el.get("EIdType") == "doi":
                    doi = cls._texto(el)
                    break

        ano = extrair_ano(
            cls._texto(artigo.find("./Journal/JournalIssue/PubDate/Year"))
            or cls._texto(artigo.find("./Journal/JournalIssue/PubDate/MedlineDate"))
            or cls._texto(artigo.find("./ArticleDate/Year"))
        )

        termos = [
            cls._texto(d)
            for d in art.findall("./MedlineCitation/MeshHeadingList/MeshHeading/DescriptorName")
        ]
        termos += [
            cls._texto(k) for k in art.findall("./MedlineCitation/KeywordList/Keyword")
        ]

        return Registro(
            fonte="pubmed",
            id_fonte=pmid,
            titulo=cls._texto(artigo.find("./ArticleTitle")).rstrip("."),
            resumo=resumo,
            autores=autores,
            ano=ano,
            periodico=cls._texto(artigo.find("./Journal/Title")),
            doi=doi,
            pmid=pmid,
            pmcid=pmcid,
            tipo=", ".join(
                cls._texto(p) for p in artigo.findall("./PublicationTypeList/PublicationType")
            ),
            idioma=cls._texto(artigo.find("./Language")),
            termos=[t for t in termos if t],
            url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
            acesso_aberto=bool(pmcid),
            url_texto_completo=(
                f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/" if pmcid else ""
            ),
        )
