"""Importa exportacoes manuais (Scopus, Embase, WoS, CENTRAL, IEEE) para o
mesmo esquema `Registro` usado pelos adaptadores de API.

Formatos aceitos: RIS (.ris/.txt), BibTeX (.bib) e CSV do Scopus (.csv).
O nome do arquivo vira o rotulo da fonte no log PRISMA-S, entao vale nomear
como `scopus_vertenteA.ris`, `embase.ris`, etc.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

from fontes import Registro
from fontes.base import extrair_ano

# ---------------------------------------------------------------------- RIS

# Varias bases usam tags diferentes para o mesmo campo.
RIS_TITULO = ("TI", "T1", "CT")
RIS_AUTOR = ("AU", "A1", "A2")
RIS_ANO = ("PY", "Y1", "DA")
RIS_PERIODICO = ("JO", "JF", "T2", "JA", "J2")
RIS_RESUMO = ("AB", "N2")
RIS_PALAVRA = ("KW",)


def importar_ris(caminho: str | Path, fonte: str | None = None) -> list[Registro]:
    caminho = Path(caminho)
    fonte = fonte or caminho.stem
    texto = caminho.read_text(encoding="utf-8-sig", errors="replace")

    registros: list[Registro] = []
    atual: dict[str, list[str]] = {}
    ultima_tag: str | None = None

    def fechar():
        if atual:
            registros.append(_ris_para_registro(atual, fonte))
        atual.clear()

    for linha in texto.splitlines():
        if not linha.strip():
            continue
        m = re.match(r"^([A-Z][A-Z0-9])  - ?(.*)$", linha)
        if m:
            tag, valor = m.group(1), m.group(2).strip()
            if tag == "ER":
                fechar()
                ultima_tag = None
                continue
            if tag == "TY":
                fechar()
            atual.setdefault(tag, []).append(valor)
            ultima_tag = tag
        elif ultima_tag and atual.get(ultima_tag):
            # continuacao da linha anterior (resumos longos vem quebrados)
            atual[ultima_tag][-1] += " " + linha.strip()
    fechar()
    return registros


def _primeiro(d: dict[str, list[str]], tags: tuple[str, ...]) -> str:
    for t in tags:
        if d.get(t):
            return d[t][0]
    return ""


def _todos(d: dict[str, list[str]], tags: tuple[str, ...]) -> list[str]:
    saida: list[str] = []
    for t in tags:
        saida.extend(d.get(t, []))
    return saida


def _ris_para_registro(d: dict[str, list[str]], fonte: str) -> Registro:
    doi = _primeiro(d, ("DO", "DI"))
    if not doi:  # algumas bases enfiam o DOI em UR ou N1
        for campo in _todos(d, ("UR", "N1", "L3")):
            m = re.search(r"10\.\d{4,9}/[^\s\"'<>]+", campo)
            if m:
                doi = m.group(0).rstrip(".,;")
                break

    pmid = ""
    for campo in _todos(d, ("AN", "ID", "N1", "UR")):
        m = re.search(r"(?:PMID:?\s*|pubmed/)(\d{7,8})", campo, re.I)
        if m:
            pmid = m.group(1)
            break

    return Registro(
        fonte=fonte,
        id_fonte=_primeiro(d, ("ID", "AN", "UR")),
        titulo=_primeiro(d, RIS_TITULO).rstrip("."),
        resumo=_primeiro(d, RIS_RESUMO),
        autores=_todos(d, RIS_AUTOR),
        ano=extrair_ano(_primeiro(d, RIS_ANO)),
        periodico=_primeiro(d, RIS_PERIODICO),
        doi=doi,
        pmid=pmid,
        tipo=_primeiro(d, ("TY",)),
        idioma=_primeiro(d, ("LA",)),
        termos=_todos(d, RIS_PALAVRA),
        url=_primeiro(d, ("UR",)),
    )


# ------------------------------------------------------------------- BibTeX

def importar_bibtex(caminho: str | Path, fonte: str | None = None) -> list[Registro]:
    caminho = Path(caminho)
    fonte = fonte or caminho.stem
    texto = caminho.read_text(encoding="utf-8-sig", errors="replace")

    registros = []
    for bloco in re.finditer(r"@(\w+)\s*\{([^,]*),(.*?)\n\}", texto, re.S):
        tipo, chave, corpo = bloco.group(1), bloco.group(2).strip(), bloco.group(3)
        campos = {}
        for m in re.finditer(r"(\w+)\s*=\s*[{\"](.*?)[}\"]\s*,?\s*(?=\n\s*\w+\s*=|\Z)", corpo, re.S):
            campos[m.group(1).lower()] = " ".join(m.group(2).split())
        registros.append(
            Registro(
                fonte=fonte,
                id_fonte=chave,
                titulo=campos.get("title", "").strip("{} ").rstrip("."),
                resumo=campos.get("abstract", ""),
                autores=[a.strip() for a in campos.get("author", "").split(" and ") if a.strip()],
                ano=extrair_ano(campos.get("year")),
                periodico=campos.get("journal") or campos.get("booktitle", ""),
                doi=campos.get("doi", ""),
                tipo=tipo,
                termos=[k.strip() for k in campos.get("keywords", "").split(";") if k.strip()],
                url=campos.get("url", ""),
            )
        )
    return registros


# --------------------------------------------------------------- CSV Scopus

COL_SCOPUS = {
    "titulo": ("Title", "Document Title"),
    "resumo": ("Abstract",),
    "autores": ("Authors", "Author full names"),
    "ano": ("Year",),
    "periodico": ("Source title",),
    "doi": ("DOI",),
    "pmid": ("PubMed ID",),
    "tipo": ("Document Type",),
    "idioma": ("Language of Original Document",),
    "url": ("Link",),
    "id": ("EID",),
}


def _col(linha: dict, nomes: tuple[str, ...]) -> str:
    for n in nomes:
        if linha.get(n):
            return linha[n].strip()
    return ""


def importar_csv_scopus(caminho: str | Path, fonte: str | None = None) -> list[Registro]:
    caminho = Path(caminho)
    fonte = fonte or caminho.stem
    registros = []
    with caminho.open(encoding="utf-8-sig", errors="replace", newline="") as f:
        amostra = f.read(8192)
        f.seek(0)
        try:
            dialeto = csv.Sniffer().sniff(amostra, delimiters=",;\t")
        except csv.Error:
            dialeto = csv.excel
        for linha in csv.DictReader(f, dialect=dialeto):
            autores = _col(linha, COL_SCOPUS["autores"])
            termos = []
            for c in ("Author Keywords", "Index Keywords"):
                if linha.get(c):
                    termos += [t.strip() for t in linha[c].split(";") if t.strip()]
            registros.append(
                Registro(
                    fonte=fonte,
                    id_fonte=_col(linha, COL_SCOPUS["id"]),
                    titulo=_col(linha, COL_SCOPUS["titulo"]).rstrip("."),
                    resumo=_col(linha, COL_SCOPUS["resumo"]),
                    autores=[a.strip() for a in autores.split(";") if a.strip()]
                    or [a.strip() for a in autores.split(",") if a.strip()],
                    ano=extrair_ano(_col(linha, COL_SCOPUS["ano"])),
                    periodico=_col(linha, COL_SCOPUS["periodico"]),
                    doi=_col(linha, COL_SCOPUS["doi"]),
                    pmid=_col(linha, COL_SCOPUS["pmid"]),
                    tipo=_col(linha, COL_SCOPUS["tipo"]),
                    idioma=_col(linha, COL_SCOPUS["idioma"]),
                    termos=termos,
                    url=_col(linha, COL_SCOPUS["url"]),
                    acesso_aberto="open access" in (linha.get("Open Access", "") or "").lower(),
                )
            )
    return registros


# ------------------------------------------------------------------ despacho

def importar(caminho: str | Path, fonte: str | None = None) -> list[Registro]:
    """Escolhe o leitor pela extensao. Para .csv assume o layout do Scopus."""
    caminho = Path(caminho)
    ext = caminho.suffix.lower()
    if ext in (".ris", ".txt", ".nbib"):
        return importar_ris(caminho, fonte)
    if ext == ".bib":
        return importar_bibtex(caminho, fonte)
    if ext == ".csv":
        return importar_csv_scopus(caminho, fonte)
    raise ValueError(f"extensao nao suportada: {ext}")
