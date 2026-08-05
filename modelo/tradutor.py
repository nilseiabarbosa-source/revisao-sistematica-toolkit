"""Gera a string de busca de cada base a partir de UMA especificacao neutra.

Este e o nucleo do modelo reutilizavel. Sem ele, adaptar a revisao a um novo
tema significa reescrever a consulta cinco vezes, em cinco sintaxes, e manter as
cinco em sincronia — que foi exatamente o que produziu os erros da primeira
versao deste projeto.

## O modelo de dados

    BLOCOS = [
        {"nome": "IA",     "grupos": [{"termos": [...], "mesh": [...]}]},
        {"nome": "Cancer", "grupos": [{"termos": [...]}, {"termos": [...]}]},
    ]

- termos dentro de um grupo sao combinados por OR;
- grupos dentro de um bloco, por AND;
- blocos entre si, por AND.

Um termo com espaco vira frase entre aspas; terminado em `*`, curinga.

## Peculiaridades de cada base que este modulo encapsula

Cada uma custou uma sessao de depuracao. Estao aqui para nao serem redescobertas:

- **Europe PMC**: NUNCA combinar `MESH:` com `TITLE_ABS:` por OR. A API descarta
  as restricoes de campo dos dois lados e cai para busca em texto completo, sem
  avisar. O sintoma e blocos distintos retornando contagens identicas.
- **Europe PMC**: curinga dentro de frase entre aspas e' ignorado em silencio —
  `"carbon nanotube*"` devolve o mesmo que `"carbon nanotube"` e perde todo o
  plural. Em palavra solta o curinga funciona. Ver `_termo_europepmc`.
- **PubMed**: `humans[Filter]` descarta registros ainda nao indexados no MeSH —
  ou seja, a literatura mais recente, que costuma ser o alvo. Usar exclusao de
  animais.
- **PubMed**: a exclusao de animais so faz sentido em revisao clinica, e por
  isso e' desligavel por `EXCLUIR_ANIMAIS = False` no config da revisao. Em
  revisao AMBIENTAL ela derruba evidencia elegivel em silencio: artigo de
  sensor validado em peixe, molusco ou ensaio de ecotoxicidade recebe
  `Animals` no MeSH e nao recebe `Humans`, e some da busca. Medido na revisao
  de biossensores de nanocarbono: 1 de 13 estudos do gabarito, com os quatro
  blocos passando individualmente — falha invisivel para o `diagnosticar`
  antes de a checagem da clausula ser acrescentada a ele.
- **Scopus**: `LIMIT-TO(DOCTYPE,...)` e sintaxe da interface web; a Search API
  ignora em silencio. O operador correto e `DOCTYPE(...)`.
- **Scopus**: `TITLE-ABS-KEY` inclui palavras-chave indexadas e quase dobra o
  volume em relacao a `TITLE-ABS`. E uma decisao de escopo, nao um detalhe.
"""

from __future__ import annotations


def _frase(t: str) -> bool:
    return " " in t.strip()


# --------------------------------------------------------------- PubMed
def bloco_pubmed(bloco: dict, campo: str = "tiab") -> str:
    partes_grupo = []
    for g in bloco["grupos"]:
        itens = [f'"{m}"[Mesh]' for m in g.get("mesh", [])]
        for t in g["termos"]:
            itens.append(f'"{t}"[{campo}]' if _frase(t) else f"{t}[{campo}]")
        partes_grupo.append("(" + " OR ".join(itens) + ")")
    return "(" + " AND ".join(partes_grupo) + ")"


def consulta_pubmed(
    blocos: list[dict],
    anos: tuple[int, int],
    excluir_animais: bool = True,
) -> str:
    corpo = " AND ".join(bloco_pubmed(b) for b in blocos)
    data = f'("{anos[0]}/01/01"[Date - Publication] : "{anos[1]}/12/31"[Date - Publication])'
    q = f"{corpo} AND {data}"
    if excluir_animais:
        # Exclusao de animais em vez de humans[Filter] — ver docstring do modulo.
        q += " NOT (animals[Mesh] NOT humans[Mesh])"
    return q


# ------------------------------------------------------------ Europe PMC
def _termo_europepmc(t: str) -> str:
    """Um termo na sintaxe do Europe PMC.

    ARMADILHA: o curinga funciona em palavra solta, mas dentro de frase entre
    aspas e' descartado em silencio — a consulta nao falha, so' devolve menos.
    Medido em 2026-08-05:

        TITLE_ABS:"carbon nanotube"    18.793
        TITLE_ABS:"carbon nanotubes"   36.530
        TITLE_ABS:"carbon nanotube*"   18.793   <-- curinga ignorado
        TITLE_ABS:sediment             71.042
        TITLE_ABS:sediment*           158.907   <-- aqui funciona

    Ou seja, `"carbon nanotube*"` perdia todo o plural. Numa revisao com muitos
    termos compostos isso derrubou o total de 1.914 (PubMed) para 783.

    A saida e' trocar a frase-com-curinga por conjuncao de palavras. Perde-se a
    adjacencia — 'carbon' e 'nanotube*' podem aparecer separados no resumo —, o
    que e' troca aceitavel numa revisao de escopo, onde a precisao volta pelos
    demais blocos e pela triagem. Frase sem curinga continua entre aspas.
    """
    t = t.strip()
    if " " not in t:
        return f"TITLE_ABS:{t}"
    if not t.endswith("*"):
        return f'TITLE_ABS:"{t}"'
    partes = [
        f"TITLE_ABS:{p}" if p.endswith("*") or p.isalnum() else f'TITLE_ABS:"{p}"'
        for p in t.split()
    ]
    return "(" + " AND ".join(partes) + ")"


def bloco_europepmc(bloco: dict) -> str:
    partes_grupo = []
    for g in bloco["grupos"]:
        # MESH deliberadamente ignorado aqui — ver docstring do modulo.
        itens = [_termo_europepmc(t) for t in g["termos"]]
        partes_grupo.append("(" + " OR ".join(itens) + ")")
    return "(" + " AND ".join(partes_grupo) + ")"


def consulta_europepmc(blocos: list[dict], anos: tuple[int, int]) -> str:
    corpo = " AND ".join(bloco_europepmc(b) for b in blocos)
    return f"{corpo} AND (PUB_YEAR:[{anos[0]} TO {anos[1]}])"


# ---------------------------------------------------------------- Scopus
def bloco_scopus(bloco: dict, campo: str = "TITLE-ABS-KEY") -> str:
    partes_grupo = []
    for g in bloco["grupos"]:
        itens = [f'"{t}"' if _frase(t) else t for t in g["termos"]]
        partes_grupo.append(f"{campo}(" + " OR ".join(itens) + ")")
    return "(" + " AND ".join(partes_grupo) + ")"


def consulta_scopus(
    blocos: list[dict],
    anos: tuple[int, int],
    campo: str = "TITLE-ABS-KEY",
    tipos: tuple[str, ...] = ("ar", "re"),
) -> str:
    corpo = " AND ".join(bloco_scopus(b, campo) for b in blocos)
    q = f"{corpo} AND PUBYEAR > {anos[0] - 1} AND PUBYEAR < {anos[1] + 1}"
    if tipos:
        # DOCTYPE(), nao LIMIT-TO() — ver docstring do modulo.
        q += " AND (" + " OR ".join(f"DOCTYPE({t})" for t in tipos) + ")"
    return q


# ------------------------------------------------------- Semantic Scholar
def consulta_semanticscholar(blocos: list[dict]) -> str:
    partes = []
    for b in blocos:
        for g in b["grupos"]:
            itens = [f'"{t}"' if _frase(t) else t for t in g["termos"]]
            partes.append("(" + " | ".join(itens) + ")")
    return " + ".join(partes)


# ------------------------------------------------- bases sem API (colar)
def consulta_wos(blocos: list[dict]) -> str:
    partes = []
    for b in blocos:
        for g in b["grupos"]:
            itens = [f'"{t}"' if _frase(t) else t for t in g["termos"]]
            partes.append("TS=(" + " OR ".join(itens) + ")")
    return "\nAND ".join(partes)


def consulta_embase(blocos: list[dict], anos: tuple[int, int]) -> str:
    partes = []
    for b in blocos:
        for g in b["grupos"]:
            itens = [f"'{e}'/exp" for e in g.get("emtree", [])]
            itens += [f"'{t}':ti,ab" for t in g["termos"]]
            partes.append("(" + " OR ".join(itens) + ")")
    return " AND ".join(partes) + f" AND [{anos[0]}-{anos[1]}]/py"


# ---------------------------------------------------------------- arXiv
def consulta_arxiv(blocos: list[dict]) -> str:
    """Sintaxe do arXiv: campo `all:`, operadores AND/OR em maiusculas.

    A API nao aceita filtro de ano na consulta — a janela e aplicada depois,
    sobre o campo `ano` do Registro.
    """
    partes = []
    for b in blocos:
        for g in b["grupos"]:
            itens = [f'all:"{t}"' if _frase(t) else f"all:{t}" for t in g["termos"]]
            partes.append("(" + " OR ".join(itens) + ")")
    return " AND ".join(partes)


TRADUTORES = {
    "pubmed": consulta_pubmed,
    "europepmc": consulta_europepmc,
    "scopus": consulta_scopus,
    "arxiv": consulta_arxiv,
}


def gerar_todas(
    blocos: list[dict],
    anos: tuple[int, int],
    excluir_animais: bool = True,
) -> dict[str, str]:
    """Todas as strings de uma vez, para gravar no log PRISMA-S."""
    return {
        "pubmed": consulta_pubmed(blocos, anos, excluir_animais),
        "europepmc": consulta_europepmc(blocos, anos),
        "scopus": consulta_scopus(blocos, anos),
        "arxiv": consulta_arxiv(blocos),
        "semanticscholar": consulta_semanticscholar(blocos),
        "web_of_science": consulta_wos(blocos),
        "embase": consulta_embase(blocos, anos),
    }
