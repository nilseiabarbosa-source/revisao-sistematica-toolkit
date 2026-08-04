"""Exportacao dos registros para as ferramentas de triagem.

RIS e o formato que Rayyan e Covidence importam; CSV serve para conferencia em
planilha e para a extracao (charting) do Apendice B.
"""

from __future__ import annotations

import csv
from pathlib import Path

from fontes import Registro

TIPO_RIS = {
    "clinicaltrials": "UNPB",
    "preprint": "UNPB",
}


def _tipo_ris(r: Registro) -> str:
    if r.fonte == "clinicaltrials":
        return "UNPB"
    tipo = (r.tipo or "").lower()
    if "preprint" in tipo:
        return "UNPB"
    if "conference" in tipo or "proceedings" in tipo:
        return "CPAPER"
    return "JOUR"


def exportar_ris(registros: list[Registro], caminho: str | Path) -> Path:
    caminho = Path(caminho)
    with caminho.open("w", encoding="utf-8", newline="") as f:
        for r in registros:
            f.write(f"TY  - {_tipo_ris(r)}\n")
            if r.titulo:
                f.write(f"TI  - {r.titulo}\n")
            for a in r.autores:
                f.write(f"AU  - {a}\n")
            if r.ano:
                f.write(f"PY  - {r.ano}\n")
            if r.periodico:
                f.write(f"JO  - {r.periodico}\n")
            if r.resumo:
                # RIS nao aceita quebra de linha crua dentro do campo
                f.write(f"AB  - {r.resumo.replace(chr(10), ' ').replace(chr(13), ' ')}\n")
            if r.doi:
                f.write(f"DO  - {r.doi}\n")
            if r.url:
                f.write(f"UR  - {r.url}\n")
            for t in r.termos[:30]:
                f.write(f"KW  - {t}\n")
            if r.idioma:
                f.write(f"LA  - {r.idioma}\n")
            ident = r.pmid or r.doi or r.id_fonte
            if ident:
                f.write(f"ID  - {ident}\n")
            f.write(f"DB  - {r.fonte}\n")
            f.write("ER  - \n\n")
    return caminho


COLUNAS = [
    "n", "fonte", "fontes_todas", "titulo", "autores", "ano", "periodico",
    "doi", "pmid", "pmcid", "tipo", "idioma", "acesso_aberto",
    "url", "url_texto_completo", "termos", "resumo",
]


def exportar_csv(
    registros: list[Registro],
    caminho: str | Path,
    fontes_por_registro: dict[str, set[str]] | None = None,
) -> Path:
    caminho = Path(caminho)
    fontes_por_registro = fontes_por_registro or {}
    with caminho.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS, delimiter=";")
        w.writeheader()
        for i, r in enumerate(registros, 1):
            chave = r.doi or r.pmid or r.id_fonte
            w.writerow(
                {
                    "n": i,
                    "fonte": r.fonte,
                    "fontes_todas": "|".join(sorted(fontes_por_registro.get(chave, {r.fonte}))),
                    "titulo": r.titulo,
                    "autores": "; ".join(r.autores[:15]),
                    "ano": r.ano or "",
                    "periodico": r.periodico,
                    "doi": r.doi,
                    "pmid": r.pmid,
                    "pmcid": r.pmcid,
                    "tipo": r.tipo,
                    "idioma": r.idioma,
                    "acesso_aberto": "sim" if r.acesso_aberto else "nao",
                    "url": r.url,
                    "url_texto_completo": r.url_texto_completo,
                    "termos": "; ".join(r.termos[:25]),
                    "resumo": (r.resumo or "").replace("\n", " ").replace("\r", " "),
                }
            )
    return caminho
