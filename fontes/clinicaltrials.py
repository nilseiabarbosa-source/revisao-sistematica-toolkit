"""ClinicalTrials.gov API v2 — literatura cinzenta e vies de publicacao.

Sem chave. Cobrir registros de ensaios e exigencia metodologica em revisoes de
intervencao: ensaios registrados e nunca publicados sao a evidencia direta de
vies de publicacao, e nao aparecem em nenhuma base bibliografica.
"""

from __future__ import annotations

from typing import Iterator

from .base import ClienteHTTP, FonteBase, Registro, extrair_ano

BASE = "https://clinicaltrials.gov/api/v2/studies"


class ClinicalTrials(FonteBase):
    nome = "clinicaltrials"

    def __init__(self, req_por_segundo: float = 5.0) -> None:
        self.http = ClienteHTTP(req_por_segundo)

    def buscar(
        self,
        consulta: str,
        limite: int = 1000,
        condicao: str | None = None,
        intervencao: str | None = None,
    ) -> Iterator[Registro]:
        token = None
        colhidos = 0
        while colhidos < limite:
            params = {
                "query.term": consulta,
                "pageSize": min(1000, limite - colhidos),
                "format": "json",
            }
            if condicao:
                params["query.cond"] = condicao
            if intervencao:
                params["query.intr"] = intervencao
            if token:
                params["pageToken"] = token

            r = self.http.get(BASE, params=params)
            dados = r.json()
            estudos = dados.get("studies", [])
            if not estudos:
                return
            for e in estudos:
                yield self._converter(e)
                colhidos += 1
            token = dados.get("nextPageToken")
            if not token:
                return

    @staticmethod
    def _converter(estudo: dict) -> Registro:
        prot = estudo.get("protocolSection", {})
        ident = prot.get("identificationModule", {})
        desc = prot.get("descriptionModule", {})
        status = prot.get("statusModule", {})
        cond = prot.get("conditionsModule", {})
        design = prot.get("designModule", {})

        nct = ident.get("nctId", "")
        patrocinador = (
            prot.get("sponsorCollaboratorsModule", {})
            .get("leadSponsor", {})
            .get("name", "")
        )

        return Registro(
            fonte="clinicaltrials",
            id_fonte=nct,
            titulo=ident.get("officialTitle") or ident.get("briefTitle", ""),
            resumo=desc.get("detailedDescription") or desc.get("briefSummary", ""),
            autores=[patrocinador] if patrocinador else [],
            ano=extrair_ano(
                (status.get("startDateStruct") or {}).get("date")
                or (status.get("primaryCompletionDateStruct") or {}).get("date")
            ),
            periodico="ClinicalTrials.gov",
            tipo=design.get("studyType", ""),
            termos=(cond.get("conditions") or []) + (cond.get("keywords") or []),
            url=f"https://clinicaltrials.gov/study/{nct}" if nct else "",
            acesso_aberto=True,
            bruto=estudo,
        )
