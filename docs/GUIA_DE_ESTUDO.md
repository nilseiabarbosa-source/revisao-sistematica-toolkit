# Guia de estudo do código

Este pacote automatiza a etapa de busca de uma revisão de escopo. Foi escrito
para a revisão de IA e detecção pré-clínica de câncer, mas a estrutura serve
para qualquer revisão.

O guia está na ordem em que o código foi construído, que também é a ordem em que
faz sentido lê-lo.

---

## A ideia central

Cada base bibliográfica tem uma API diferente, com sintaxe, paginação e formato
de resposta próprios. Se cada parte do sistema precisasse conhecer essas
diferenças, qualquer mudança se espalharia por todo lado.

A solução é um **esquema comum**: cada adaptador converte a resposta da sua API
para a mesma estrutura (`Registro`), e o restante do sistema — deduplicação,
exportação, triagem — nunca precisa saber de onde o dado veio.

```
PubMed ─────┐
Europe PMC ─┤
Scopus ─────┼──► Registro ──► deduplicar ──► exportar (.ris, .csv)
Crossref ───┤
Sem. Schol.─┘
```

---

## Parte 1 — A fundação (`fontes/base.py`)

Comece por aqui. São três coisas:

**`Registro`** — a `dataclass` que define o esquema comum. Título, resumo,
autores, ano, DOI, PMID e assim por diante. Todos os adaptadores devolvem isto.

**`ClienteHTTP`** — sessão HTTP com limitação de taxa e retentativa com recuo
exponencial. Existe porque as APIs têm tetos: estourar o do NCBI bloqueia seu IP
temporariamente. O parâmetro `req_por_segundo` é o teto documentado de cada base.

**Normalizadores** — `normalizar_doi` e `normalizar_titulo`. Parecem detalhe,
mas são o coração da deduplicação: sem reduzir `10.1038/S41591-023-02332-5` e
`https://doi.org/10.1038/s41591-023-02332-5` à mesma string, o mesmo artigo
entra duas vezes.

> **Conceito:** normalizar antes de comparar. Vale para qualquer chave de junção
> entre fontes heterogêneas, não só para DOI.

---

## Parte 2 — Os adaptadores (`fontes/*.py`)

Todos implementam o mesmo contrato: `buscar()`, `coletar()`, `contar()`. Leia um
e você leu todos.

| Arquivo | O que ensina |
|---|---|
| `europepmc.py` | paginação por cursor — o padrão mais simples |
| `pubmed.py` | busca em duas etapas (esearch → efetch) e parsing de XML |
| `crossref.py` | API sem álgebra booleana, usada como rede complementar |
| `scopus.py` | autenticação por cabeçalho, visões com permissões diferentes |
| `semanticscholar.py` | grafo de citações para *snowballing* |
| `clinicaltrials.py` | registro de ensaios, literatura cinzenta |
| `unpaywall.py` | resolução de DOI para PDF aberto |

**Detalhe que vale estudar em `pubmed.py`:** o comentário grande no
`_converter()`. Ali havia um bug que corrompia silenciosamente todos os DOIs —
ver Parte 6.

**Detalhe que vale estudar em `scopus.py`:** o método `diagnosticar()`. Antes de
tentar coletar milhares de registros, ele verifica em três chamadas o que a
credencial realmente permite. Descobrir cedo que os resumos não vêm vale mais do
que descobrir depois de 40 minutos.

---

## Parte 3 — Deduplicação (`fontes/dedup.py`)

Cascata de quatro passadas, da mais confiável para a mais frouxa:

1. **DOI normalizado** — praticamente sem falso positivo
2. **PMID** — para registros sem DOI
3. **Título normalizado + ano** — para os sem nenhum identificador
4. **Similaridade de título** (`difflib`, limiar 0,93) — pega variação de
   pontuação e truncamento

A ordem importa: começa pelo critério mais seguro e só desce quando não há
alternativa. A quarta passada é a única que pode errar, e por isso registra os
pares unidos em `relatorio_dedup.txt` para conferência humana.

Duas decisões de projeto que valem atenção:

- **O sobrevivente é o registro mais completo**, não o primeiro encontrado (ver
  `_completude()`). Se o Scopus tem o DOI e o PubMed tem o resumo, você quer o
  do PubMed.
- **Nunca unir dois DOIs distintos conhecidos**, mesmo com títulos quase iguais
  — seriam errata, correção ou versão, que são registros diferentes.

> **Conceito:** em deduplicação, falso positivo (unir coisas distintas) é pior
> que falso negativo (deixar duplicata passar). O humano detecta a duplicata na
> triagem; a fusão indevida some para sempre.

---

## Parte 4 — A estratégia de busca (`estrategia_*.py`)

Aqui é metodologia, não programação. As strings ficam em constantes, separadas
do código que as executa, por uma razão: o PRISMA-S exige que a string exata
usada seja publicável e reproduzível.

- `estrategia_busca.py` — o Apêndice A da proposta, transcrito
- `estrategia_final.py` — a versão calibrada, com as correções da Parte 5
- `estrategia_bases_manuais_scopus.py` — as strings do Scopus

Note a duplicação deliberada entre `strings_bases_manuais.md` (para colar na
interface web) e o arquivo `.py` (para a API). São a mesma consulta em dois
formatos; o comentário no arquivo avisa que precisam ser mantidas em sincronia.

---

## Parte 5 — Validação: a parte mais importante

Esta é a diferença entre um script que roda e uma revisão defensável.

**`teste_itens_conhecidos.py`** — o *known-item test*. Você lista estudos que
já sabe serem elegíveis e verifica se a busca os recupera. É simples e é o único
jeito de saber se sua estratégia funciona.

Na primeira execução, a string do Apêndice A recuperava **7 de 16 (44%)**.
Parecia boa: 924 registros, número plausível. Sem esse teste, a revisão teria
seguido perdendo metade da evidência central.

**`diagnosticar_falhas.py`** — para cada estudo perdido, descobre qual bloco da
string o barrou. Transforma "a busca está ruim" em "o bloco #2 barrou 9
estudos", que é acionável.

**`revisar_string.py`** — mede cada variante em duas dimensões:
sensibilidade × volume. Toda ampliação de busca tem custo, e a decisão só é
informada quando os dois números aparecem juntos.

**`vertente_foundation.py`** — testa uma hipótese em vez de assumir. A hipótese
era que Delphi-2M, Med-BERT e ETHOS não têm termo de câncer em título/resumo. O
script confirmou, e isso justificou criar uma segunda vertente de busca — algo
que nenhuma string única resolveria.

> **Conceito:** meça antes de decidir. Quase toda escolha neste projeto
> (ampliar ou não, incluir Scopus ou não, filtrar tipo de documento ou não) foi
> tomada com um número medido ao lado, não por intuição.

---

## Parte 6 — Dois bugs que valem mais que o resto do código

**O DOI da referência errada.** Em `pubmed.py`, o XPath `.//ArticleId` alcançava
também os identificadores dentro de `<ReferenceList>` — a lista de referências
citadas pelo artigo. Como o laço sobrescrevia, o DOI final era o da última
referência. O Delphi-2M apareceu com o DOI do pacote `mice` do R.

Nada quebrou. Nenhuma exceção. Só que a deduplicação passou a comparar chaves
erradas: antes da correção removeu 1.365 duplicatas; depois, 2.559 — quase o
dobro. Um erro de XPath virou erro de contagem no fluxograma PRISMA.

**O diagnóstico que não agia.** Em `buscar_scopus.py`, o código detectava
corretamente que a visão `COMPLETE` não estava autorizada, imprimia o aviso — e
continuava usando `COMPLETE`. Toda requisição voltava 401, a coleta terminou
vazia, e o script gravou as saídas como se tivesse funcionado.

A correção foi de uma linha. A lição não: **detectar um problema não é tratá-lo**,
e qualquer processo que possa terminar vazio precisa abortar em vez de gravar.
Veja a guarda que foi acrescentada logo depois da coleta.

**O filtro que a API ignorava.** Ao restringir o Scopus a artigos e revisões, a
primeira tentativa usou `LIMIT-TO(DOCTYPE,"ar")` — que é a sintaxe de faceta da
**interface web**. A Search API não reconhece o operador e simplesmente o
descarta: a consulta voltou com os mesmos 12.055 registros de antes, como se o
filtro tivesse sido aplicado e nada correspondesse a ele. O operador correto na
API é `DOCTYPE(ar)`, que de fato filtra para 10.276.

Só foi percebido porque o total era idêntico ao da consulta sem filtro. Daí a
prática que virou regra neste projeto: **ao aplicar um filtro, compare a
contagem com e sem ele.** Se não mudou, o filtro não funcionou — não presuma que
simplesmente não havia o que filtrar.

> **Conceito:** falha silenciosa é pior que falha ruidosa. Os três bugs
> produziam resultados de aparência normal. Nenhum levantou exceção. Todos foram
> descobertos porque havia um número esperado para comparar — um DOI conhecido,
> uma contagem anterior, um estudo que tinha de estar lá.

---

## Parte 7 — Execução e integração

| Script | Função |
|---|---|
| `calibrar.py` | contagens por bloco, sem baixar registros — sempre comece por aqui |
| `buscar_final.py` | busca nas APIs livres, valida e exporta |
| `buscar_scopus.py` | Scopus com cache retomável e enriquecimento |
| `snowballing.py` | *citation chasing* pelo grafo de citações |
| `integrar_manuais.py` | absorve exportações de Embase, WoS, Cochrane |
| `exportar.py` | gera `.ris` (Rayyan/Covidence) e `.csv` |
| `importar.py` | lê RIS, BibTeX e CSV do Scopus |

**Sobre o cache em `buscar_scopus.py`:** foi acrescentado depois que uma
execução de 40 minutos morreu no minuto 25 e perdeu tudo. A coleta é gravada ao
terminar; o enriquecimento grava a cada 200 registros. Rodar de novo retoma de
onde parou.

> **Conceito:** processo longo precisa ser retomável. A regra prática é: se
> demora mais que um café, precisa de checkpoint.

---

## Como estudar, em ordem prática

1. Leia `fontes/base.py` inteiro — é curto e define tudo.
2. Leia `fontes/europepmc.py`, o adaptador mais simples.
3. Rode `calibrar.py` e veja as contagens saindo.
4. Leia `fontes/dedup.py`, prestando atenção na ordem das passadas.
5. Leia `teste_itens_conhecidos.py` e entenda por que ele existe.
6. Leia os comentários longos em `pubmed.py` e `buscar_scopus.py` — são os dois
   bugs da Parte 6.
7. Só então leia `buscar_final.py`, que amarra tudo.

Para experimentar sem gastar cota: `calibrar.py` só conta, não baixa. Trocar
termos nas strings e ver a contagem mudar é a forma mais barata de entender o
efeito de cada bloco.

---

## Requisitos

Python 3.10+ e `requests`. Nada mais.

```bash
pip install -r requirements.txt
python3 calibrar.py
```

A chave do Scopus vive em `.env` (que está no `.gitignore`). Todas as outras
bases usadas aqui são livres e não exigem credencial.
