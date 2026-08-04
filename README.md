# revisao-sistematica-toolkit

Automatiza a etapa de busca de revisões sistemáticas e de escopo: consulta as
bases por API, deduplica, valida a estratégia contra estudos conhecidos e
exporta para Rayyan ou Covidence — com o log que o PRISMA-S exige.

Para uma revisão nova você edita **um arquivo de configuração**. O resto do
pipeline não muda.

## Início rápido

```bash
pip install -r requirements.txt
python3 iniciar_revisao.py
```

O assistente pergunta o título, a pergunta em PCC/PICO, os blocos de termos e o
gabarito de validação, e gera `revisoes/<slug>/config.py`.

Depois:

```bash
python3 -m pipeline.validar --revisao <slug>      # calibra, sem baixar nada
python3 -m pipeline.buscar  --revisao <slug>      # coleta
```

Para ver o formato de preenchimento sem responder perguntas:

```bash
python3 iniciar_revisao.py --exemplo
```

## Por que validar antes de coletar

Esta é a parte que costuma ser pulada e a que mais importa.

O gabarito (`ITENS_CONHECIDOS`) é uma lista de 10 a 20 DOIs de estudos que você
**já sabe** serem elegíveis, tirados das revisões mais próximas do seu tema. Se
a busca não os recupera, ela não está pronta — não importa quantos registros
devolva.

Na revisão que originou este código, a estratégia inicial parecia boa: 924
registros, número plausível, string revisada por especialistas. Recuperava
**44% dos estudos conhecidos**. Quatro correções depois, chegou a 100%. Sem o
teste, a revisão teria sido publicada perdendo metade da evidência central.

## Bases suportadas

| Base | Chave | Resumo | Observação |
|---|---|---|---|
| PubMed/MEDLINE | não | sim | indexação MeSH |
| Europe PMC | não | sim | preprints e texto completo OA |
| arXiv | não | sim | computação e estatística |
| OpenAlex | recomendada | sim | amplo; cota gratuita diária |
| Semantic Scholar | opcional | sim | grafo de citações |
| Crossref | não | parcial | rede complementar |
| ClinicalTrials.gov | não | sim | registros de ensaios |
| Scopus | sim | não ¹ | exige direito institucional de API |
| CORE | sim (grátis) | sim | traz texto completo |
| DBLP | não | **não** | anais de computação |

¹ A visão `STANDARD` do Scopus não devolve resumo; o pipeline recupera via
Europe PMC por DOI (rendimento medido: 59% no conjunto completo, 77% entre
artigos de periódico).

**Sem API:** Embase, Web of Science, Cochrane CENTRAL, IEEE Xplore, ACM DL,
Google Scholar. Para essas, o tradutor gera a string na sintaxe de cada uma
para colar na interface, e `pipeline/importar.py` absorve o RIS exportado.

## Como funciona

```
revisoes/<slug>/config.py      <-- você edita só isto
   │
   ├─ modelo/tradutor.py       uma especificação -> N sintaxes
   ├─ fontes/*.py              adaptadores das APIs -> esquema comum
   ├─ fontes/dedup.py          deduplicação em cascata
   └─ pipeline/                calibrar, validar, buscar, exportar
```

O **tradutor** é o que torna o modelo reutilizável. Sem ele, uma revisão em
cinco bases exige cinco strings escritas à mão e mantidas em sincronia — e elas
divergem. Aconteceu no projeto de origem: as versões do PubMed e do Europe PMC
passaram a buscar coisas diferentes por um termo omitido, com 24% de diferença
no resultado, sem que ninguém notasse.

## Armadilhas que este código já encapsula

Cada uma custou uma sessão de depuração, e nenhuma levanta erro — todas
produzem resultados de aparência normal:

| Base | Armadilha |
|---|---|
| PubMed | `.//ArticleId` alcança os DOIs da lista de referências; o registro recebe o DOI do último artigo citado |
| PubMed | `humans[Filter]` descarta o que ainda não foi indexado no MeSH — a literatura recente |
| Europe PMC | `MESH:` combinado com `TITLE_ABS:` por OR faz a API cair para busca em texto completo, em silêncio |
| Scopus | `LIMIT-TO(DOCTYPE,...)` é sintaxe da interface web; a API ignora sem avisar |
| Scopus | `cursor` exige entitlement; `start` trava em 5.000 — a saída é fatiar por ano |

Regra prática que saiu daí: **ao aplicar um filtro, compare a contagem com e sem
ele.** Se não mudou, o filtro não funcionou.

Detalhes em [`docs/GUIA_DE_ESTUDO.md`](docs/GUIA_DE_ESTUDO.md).

## Credenciais

Bases que exigem chave leem de um arquivo `.env` na raiz:

```
SCOPUS_API_KEY=...
OPENALEX_API_KEY=...
CORE_API_KEY=...
```

O `.env` está no `.gitignore`. Nunca versione credenciais — e se uma vazar,
revogue-a no portal do provedor: criar uma chave nova geralmente **não** invalida
a anterior.

## O que não automatiza

Pré-registro (OSF), triagem, extração de dados, avaliação de risco de viés e
síntese continuam humanos. O objetivo aqui é que a busca seja reprodutível e
auditável, não substituir julgamento metodológico.

## Origem

Extraído de uma revisão de escopo real sobre IA para detecção pré-clínica de
câncer (IME, 2026), onde produziu 13.754 registros com 100% de sensibilidade
sobre o gabarito de validação.

## Licença

MIT — veja [LICENSE](LICENSE).
