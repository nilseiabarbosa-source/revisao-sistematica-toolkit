"""Deduplicacao entre bases, com relatorio auditavel.

Estrategia em tres passadas, da mais confiavel para a mais frouxa:

1. DOI normalizado — praticamente sem falso positivo.
2. PMID.
3. Titulo normalizado + ano proximo — pega o mesmo artigo indexado sem DOI.
4. Titulo similar (difflib) + mesmo ano — opcional, para variacoes de pontuacao
   e truncamento; e a unica passada que pode errar, por isso vem registrada em
   `dedup.pares_fuzzy` para conferencia manual.

O registro sobrevivente e o mais completo (mais campos preenchidos), e ele
acumula em `fontes_originais` todas as bases onde apareceu — informacao que o
fluxograma PRISMA exige.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher

from .base import Registro, normalizar_doi, normalizar_titulo


def _completude(r: Registro) -> int:
    """Quantos campos uteis o registro tem preenchidos."""
    pontos = 0
    for campo in (r.titulo, r.resumo, r.periodico, r.doi, r.pmid, r.pmcid, r.idioma):
        if campo:
            pontos += 1
    pontos += 2 if r.autores else 0
    pontos += 1 if r.ano else 0
    pontos += 1 if r.termos else 0
    pontos += 2 if r.resumo and len(r.resumo) > 200 else 0
    return pontos


@dataclass
class ResultadoDedup:
    unicos: list[Registro] = field(default_factory=list)
    total_entrada: int = 0
    removidos_doi: int = 0
    removidos_pmid: int = 0
    removidos_titulo: int = 0
    removidos_fuzzy: int = 0
    pares_fuzzy: list[tuple[str, str, float]] = field(default_factory=list)
    fontes_por_registro: dict[str, set[str]] = field(default_factory=dict)

    @property
    def total_removidos(self) -> int:
        return (
            self.removidos_doi
            + self.removidos_pmid
            + self.removidos_titulo
            + self.removidos_fuzzy
        )

    def resumo_prisma(self) -> str:
        return (
            f"Registros identificados: {self.total_entrada}\n"
            f"Duplicatas removidas: {self.total_removidos} "
            f"(DOI {self.removidos_doi}, PMID {self.removidos_pmid}, "
            f"titulo {self.removidos_titulo}, similaridade {self.removidos_fuzzy})\n"
            f"Registros para triagem: {len(self.unicos)}"
        )


def deduplicar(
    registros: list[Registro],
    usar_fuzzy: bool = True,
    limiar_fuzzy: float = 0.93,
) -> ResultadoDedup:
    res = ResultadoDedup(total_entrada=len(registros))
    por_doi: dict[str, Registro] = {}
    por_pmid: dict[str, Registro] = {}
    por_titulo: dict[tuple[str, int | None], Registro] = {}
    sem_chave: list[Registro] = []
    fontes: dict[int, set[str]] = {}

    def registrar_fonte(mantido: Registro, novo: Registro) -> None:
        fontes.setdefault(id(mantido), {mantido.fonte}).add(novo.fonte)

    def substituir_se_melhor(atual: Registro, novo: Registro) -> Registro:
        """Mantem o mais completo, preservando o rastro de fontes."""
        if _completude(novo) > _completude(atual):
            fontes.setdefault(id(novo), set()).update(
                fontes.get(id(atual), {atual.fonte})
            )
            fontes[id(novo)].add(novo.fonte)
            return novo
        registrar_fonte(atual, novo)
        return atual

    for r in registros:
        doi = normalizar_doi(r.doi)
        if doi:
            if doi in por_doi:
                res.removidos_doi += 1
                por_doi[doi] = substituir_se_melhor(por_doi[doi], r)
            else:
                por_doi[doi] = r
                fontes.setdefault(id(r), {r.fonte})
            continue

        if r.pmid:
            if r.pmid in por_pmid:
                res.removidos_pmid += 1
                por_pmid[r.pmid] = substituir_se_melhor(por_pmid[r.pmid], r)
            else:
                por_pmid[r.pmid] = r
                fontes.setdefault(id(r), {r.fonte})
            continue

        chave = (normalizar_titulo(r.titulo), r.ano)
        if chave[0] and chave in por_titulo:
            res.removidos_titulo += 1
            por_titulo[chave] = substituir_se_melhor(por_titulo[chave], r)
        elif chave[0]:
            por_titulo[chave] = r
            fontes.setdefault(id(r), {r.fonte})
        else:
            sem_chave.append(r)

    # Cruzamento entre os buckets: o mesmo artigo pode ter entrado por DOI numa
    # base e so por titulo em outra.
    candidatos = list(por_doi.values()) + list(por_pmid.values())
    titulos_com_doi = {
        (normalizar_titulo(r.titulo), r.ano): r for r in candidatos if r.titulo
    }
    for chave, r in list(por_titulo.items()):
        if chave in titulos_com_doi:
            res.removidos_titulo += 1
            registrar_fonte(titulos_com_doi[chave], r)
            del por_titulo[chave]

    unicos = candidatos + list(por_titulo.values()) + sem_chave

    if usar_fuzzy and len(unicos) > 1:
        unicos = _passada_fuzzy(unicos, limiar_fuzzy, res, fontes)

    res.unicos = unicos
    res.fontes_por_registro = {
        (r.doi or r.pmid or r.id_fonte): fontes.get(id(r), {r.fonte}) for r in unicos
    }
    return res


def _passada_fuzzy(
    registros: list[Registro],
    limiar: float,
    res: ResultadoDedup,
    fontes: dict[int, set[str]],
) -> list[Registro]:
    """Compara so dentro do mesmo ano — evita o custo quadratico no conjunto todo."""
    por_ano: dict[int | None, list[Registro]] = {}
    for r in registros:
        por_ano.setdefault(r.ano, []).append(r)

    sobreviventes: list[Registro] = []
    for _, grupo in por_ano.items():
        mantidos: list[Registro] = []
        for r in grupo:
            chave_r = normalizar_titulo(r.titulo)
            duplicata = None
            if chave_r:
                for m in mantidos:
                    chave_m = normalizar_titulo(m.titulo)
                    if not chave_m:
                        continue
                    # DOIs distintos e conhecidos indicam artigos distintos
                    # (errata, correcao, versao) — nao unificar.
                    if r.doi and m.doi and normalizar_doi(r.doi) != normalizar_doi(m.doi):
                        continue
                    razao = SequenceMatcher(None, chave_r, chave_m).ratio()
                    if razao >= limiar:
                        duplicata = (m, razao)
                        break
            if duplicata:
                m, razao = duplicata
                res.removidos_fuzzy += 1
                res.pares_fuzzy.append((m.titulo, r.titulo, round(razao, 4)))
                fontes.setdefault(id(m), {m.fonte}).add(r.fonte)
            else:
                mantidos.append(r)
        sobreviventes.extend(mantidos)
    return sobreviventes
