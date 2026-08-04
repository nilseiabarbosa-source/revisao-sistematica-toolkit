#!/usr/bin/env python3
"""Gera o esqueleto de uma revisão nova a partir de perguntas.

Cria `revisoes/<slug>/config.py` já preenchido e um README com os próximos
passos. Depois disso, o pipeline inteiro funciona sem que você toque em mais
nenhum arquivo.

    python3 iniciar_revisao.py                 # interativo
    python3 iniciar_revisao.py --exemplo       # gera um exemplo, sem perguntar

O modo `--exemplo` existe para testar a instalação e para servir de referência
de preenchimento.
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
REVISOES = RAIZ / "revisoes"

BASES_DISPONIVEIS = {
    "pubmed": "PubMed/MEDLINE — livre, biomédica, indexação MeSH",
    "europepmc": "Europe PMC — livre, biomédica + preprints + texto completo OA",
    "scopus": "Scopus — exige chave (dev.elsevier.com) e direito institucional",
    "arxiv": "arXiv — livre, preprints de computação e estatística",
    "openalex": "OpenAlex — amplo e multidisciplinar; chave recomendada",
    "semanticscholar": "Semantic Scholar — livre, bom para citation chasing",
    "crossref": "Crossref — livre, rede complementar sem álgebra booleana",
    "core": "CORE — exige chave gratuita; traz texto completo",
    "dblp": "DBLP — livre, anais de computação; NÃO devolve resumo",
    "clinicaltrials": "ClinicalTrials.gov — livre, registros de ensaios",
}


def slugificar(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto)
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    t = re.sub(r"[^a-z0-9]+", "_", t).strip("_")
    return t or "revisao"


def perguntar(rotulo: str, padrao: str = "") -> str:
    sufixo = f" [{padrao}]" if padrao else ""
    try:
        resp = input(f"{rotulo}{sufixo}: ").strip()
    except EOFError:
        print("\n(sem entrada interativa — use --exemplo)", file=sys.stderr)
        sys.exit(1)
    return resp or padrao


def perguntar_lista(rotulo: str) -> list[str]:
    print(f"\n{rotulo}")
    print("  Um termo por linha. Frases com espaço viram busca exata;")
    print("  terminar em * usa curinga (ex.: cancer*). Linha vazia encerra.")
    itens = []
    while True:
        try:
            linha = input("  > ").strip()
        except EOFError:
            break
        if not linha:
            break
        itens.append(linha)
    return itens


def coletar_blocos() -> list[dict]:
    print("\n" + "=" * 66)
    print("BLOCOS DA BUSCA")
    print("=" * 66)
    print("Cada bloco é um conceito da sua pergunta. Blocos são combinados por")
    print("AND; termos dentro de um bloco, por OR.")
    print("Exemplo clássico: #1 intervenção, #2 população/doença, #3 desfecho.")

    blocos = []
    n = 1
    while True:
        nome = perguntar(f"\nNome do bloco #{n} (vazio encerra)", "")
        if not nome:
            break
        termos = perguntar_lista(f"Termos do bloco '{nome}'")
        if not termos:
            print("  (bloco sem termos — ignorado)")
            continue
        mesh = perguntar_lista(
            f"Descritores MeSH do bloco '{nome}' (opcional, Enter para pular)"
        )
        grupo = {"termos": termos}
        if mesh:
            grupo["mesh"] = mesh
        blocos.append({"nome": f"#{n} {nome}", "grupos": [grupo]})
        n += 1
    return blocos


def coletar_itens_conhecidos() -> dict[str, str]:
    print("\n" + "=" * 66)
    print("GABARITO DE VALIDAÇÃO")
    print("=" * 66)
    print("DOIs de estudos que você JÁ SABE serem elegíveis. É com eles que a")
    print("busca será validada — sem gabarito não há como saber se ela funciona.")
    print("Formato: DOI ; descrição curta. Linha vazia encerra.")
    print("Recomendado: 10 a 20 itens, tirados das revisões mais próximas.")

    itens = {}
    while True:
        try:
            linha = input("  > ").strip()
        except EOFError:
            break
        if not linha:
            break
        if ";" in linha:
            doi, desc = linha.split(";", 1)
        else:
            doi, desc = linha, "(sem descrição)"
        itens[doi.strip()] = desc.strip()
    return itens


def escolher_bases() -> list[str]:
    print("\n" + "=" * 66)
    print("BASES A CONSULTAR")
    print("=" * 66)
    for k, v in BASES_DISPONIVEIS.items():
        print(f"  {k:<18} {v}")
    resp = perguntar(
        "\nBases separadas por vírgula", "pubmed,europepmc,arxiv"
    )
    escolhidas = [b.strip() for b in resp.split(",") if b.strip()]
    invalidas = [b for b in escolhidas if b not in BASES_DISPONIVEIS]
    if invalidas:
        print(f"  AVISO: ignorando bases desconhecidas: {', '.join(invalidas)}")
    return [b for b in escolhidas if b in BASES_DISPONIVEIS]


# --------------------------------------------------------------- exemplo
EXEMPLO = {
    "slug": "exemplo_wearables_hipertensao",
    "titulo": "Wearables para detecção precoce de hipertensão: revisão de escopo",
    "tipo": "escopo",
    "pcc": {
        "populacao": "adultos sem diagnóstico de hipertensão",
        "conceito": "detecção ou predição precoce por sinais de wearables",
        "contexto": "qualquer país ou sistema de saúde",
    },
    "anos": (2015, 2026),
    "blocos": [
        {"nome": "#1 Wearables", "grupos": [{
            "mesh": ["Wearable Electronic Devices"],
            "termos": ["wearable*", "smartwatch*", "activity tracker*",
                       "photoplethysmograph*", "continuous monitoring"],
        }]},
        {"nome": "#2 Hipertensão", "grupos": [{
            "mesh": ["Hypertension", "Blood Pressure"],
            "termos": ["hypertension", "blood pressure", "hypertensive"],
        }]},
        {"nome": "#3 Detecção", "grupos": [{
            "termos": ["early detection", "predict*", "screening",
                       "risk stratification"],
        }]},
    ],
    "itens": {
        "10.1038/s41746-019-0136-7": "Exemplo — substituir pelos seus",
    },
    "bases": ["pubmed", "europepmc", "arxiv"],
}


def gerar_config(dados: dict) -> str:
    def fmt_lista(itens, ind=16):
        if not itens:
            return "[]"
        sep = ",\n" + " " * ind
        return "[\n" + " " * ind + sep.join(repr(t) for t in itens) + ",\n" + " " * (ind - 4) + "]"

    blocos_txt = []
    for b in dados["blocos"]:
        grupos_txt = []
        for g in b["grupos"]:
            linhas = []
            if g.get("mesh"):
                linhas.append(f'            "mesh": {fmt_lista(g["mesh"])},')
            if g.get("emtree"):
                linhas.append(f'            "emtree": {fmt_lista(g["emtree"])},')
            linhas.append(f'            "termos": {fmt_lista(g["termos"])},')
            grupos_txt.append("        {\n" + "\n".join(linhas) + "\n        }")
        blocos_txt.append(
            f'    {{\n        "nome": {b["nome"]!r},\n'
            f'        "grupos": [\n' + ",\n".join(grupos_txt) + "\n        ],\n    }"
        )

    itens_txt = "\n".join(
        f"    {doi!r}: {desc!r}," for doi, desc in dados["itens"].items()
    ) or "    # PREENCHA: 10 a 20 DOIs de estudos que voce ja sabe serem elegiveis"

    return f'''"""Configuracao da revisao: {dados["titulo"]}

Gerado por iniciar_revisao.py em {date.today().isoformat()}.
Este e o unico arquivo que voce precisa editar.
"""

TITULO = {dados["titulo"]!r}
TIPO = {dados["tipo"]!r}

PCC = {{
    "populacao": {dados["pcc"]["populacao"]!r},
    "conceito": {dados["pcc"]["conceito"]!r},
    "contexto": {dados["pcc"]["contexto"]!r},
}}

ANOS = {dados["anos"]!r}

# Termos dentro de um grupo -> OR;  grupos dentro de um bloco -> AND;
# blocos entre si -> AND. Termo com espaco vira frase; com * no fim, curinga.
BLOCOS = [
{",".join(blocos_txt)}
]

# Vertente B: conceitos que escapam da busca principal por nao citarem o termo
# central no titulo/resumo. Deixe vazio se nao for o caso da sua revisao.
BLOCOS_VERTENTE_B = []

# GABARITO. A busca so esta pronta quando recupera estes estudos.
ITENS_CONHECIDOS = {{
{itens_txt}
}}

# Sementes para citation chasing: revisoes proximas ao seu tema.
SEMENTES_REVISOES = {{}}

BASES = {dados["bases"]!r}
'''


PROXIMOS_PASSOS = """# {titulo}

Revisão criada em {data}. Configuração em `config.py`.

## Próximos passos, na ordem

**1. Complete o gabarito.** Abra `config.py` e preencha `ITENS_CONHECIDOS` com
10 a 20 DOIs de estudos que você já sabe serem elegíveis. Sem isso não há como
validar a busca — e uma busca não validada pode estar perdendo metade da
evidência sem dar nenhum sinal.

**2. Calibre e valide, antes de coletar.**

```bash
python3 -m pipeline.validar --revisao {slug}
```

Mostra o volume por base e quantos estudos do gabarito são recuperados.
Enquanto a sensibilidade não estiver alta, ajuste os blocos e repita. Contagem
é barata; coleta não.

**3. Se a sensibilidade estiver baixa**, descubra qual bloco está barrando:

```bash
python3 -m pipeline.diagnosticar --revisao {slug}
```

**4. Colete.**

```bash
python3 -m pipeline.buscar --revisao {slug}
```

**5. Exporte para triagem.** O `.ris` gerado importa direto no Rayyan e no
Covidence.

## Bases selecionadas

{bases}

## Credenciais

Bases que exigem chave leem do arquivo `.env` na raiz do projeto. Ele está no
`.gitignore` — nunca versione credenciais.
"""


def main() -> None:
    ap = argparse.ArgumentParser(description="Cria o esqueleto de uma revisão.")
    ap.add_argument("--exemplo", action="store_true",
                    help="gera um exemplo pronto, sem perguntas")
    ap.add_argument("--slug", help="nome curto da pasta (padrão: derivado do título)")
    args = ap.parse_args()

    if args.exemplo:
        dados = dict(EXEMPLO)
        slug = args.slug or dados["slug"]
    else:
        print("=" * 66)
        print("NOVA REVISÃO")
        print("=" * 66)
        titulo = perguntar("Título da revisão")
        if not titulo:
            print("Título é obrigatório.")
            sys.exit(1)
        tipo = perguntar("Tipo (escopo / sistematica)", "escopo")
        print("\nPergunta em formato PCC (revisão de escopo) ou PICO:")
        pcc = {
            "populacao": perguntar("  População"),
            "conceito": perguntar("  Conceito / Intervenção"),
            "contexto": perguntar("  Contexto"),
        }
        ano_i = int(perguntar("Ano inicial", "2015"))
        ano_f = int(perguntar("Ano final", str(date.today().year)))
        blocos = coletar_blocos()
        if not blocos:
            print("Nenhum bloco definido — não dá para montar a busca.")
            sys.exit(1)
        itens = coletar_itens_conhecidos()
        bases = escolher_bases()
        slug = args.slug or slugificar(titulo)[:48]
        dados = {"titulo": titulo, "tipo": tipo, "pcc": pcc,
                 "anos": (ano_i, ano_f), "blocos": blocos,
                 "itens": itens, "bases": bases}

    destino = REVISOES / slug
    if destino.exists():
        print(f"\nERRO: {destino} já existe. Use --slug para outro nome.")
        sys.exit(1)
    destino.mkdir(parents=True)

    (destino / "config.py").write_text(gerar_config(dados), encoding="utf-8")
    (destino / "README.md").write_text(
        PROXIMOS_PASSOS.format(
            titulo=dados["titulo"], data=date.today().isoformat(), slug=slug,
            bases="\n".join(f"- **{b}** — {BASES_DISPONIVEIS[b]}" for b in dados["bases"]),
        ),
        encoding="utf-8",
    )
    (destino / "resultados").mkdir()

    print(f"\n{'=' * 66}")
    print(f"Revisão criada em revisoes/{slug}/")
    print(f"{'=' * 66}")
    print(f"  config.py   — {len(dados['blocos'])} bloco(s), "
          f"{len(dados['itens'])} item(ns) no gabarito, "
          f"{len(dados['bases'])} base(s)")
    print("  README.md   — próximos passos")
    if len(dados["itens"]) < 5:
        print("\n  ATENÇÃO: gabarito com menos de 5 itens. Complete antes de")
        print("  validar — é ele que diz se a busca funciona.")
    print(f"\nPróximo passo:  python3 -m pipeline.validar --revisao {slug}")


if __name__ == "__main__":
    main()
