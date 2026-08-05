# Biossensores de nanocarbono para metais pesados e HPAs em água e sedimento

Revisão de escopo, janela 2020–2026. Configuração em `config.py`.

Criada em 2026-08-05. **A busca já foi validada e executada** — o que segue
descreve o estado real, não um roteiro a cumprir do zero.

## Onde está

| Etapa | Situação |
|---|---|
| Blocos de busca | prontos — 4 blocos (nanocarbono, sensoriamento, analito, matriz aquática) |
| Gabarito | 13 DOIs reais, conferidos no PubMed |
| Validação | **13/13 (100%)** em 2026-08-05 |
| Coleta nas bases com API | feita — 3.600 registros únicos |
| Bases sem API | **pendente** — WoS, Scopus, ScienceDirect, IEEE, GeoRef |
| Triagem | não iniciada |

## Resultado da coleta

```
pubmed_A            1.914
europepmc_A         1.517
semanticscholar_A   2.538
---------------------------
identificados       5.969
duplicatas          2.369  (2.334 por DOI, 28 por título, 7 por similaridade)
para triagem        3.600  (88% com resumo)
gabarito            13/13
```

Saídas em `resultados/`. O `registros_para_triagem.ris` importa direto no
Rayyan.

## O que ainda falta, na ordem

**1. Rodar as bases sem API.** As strings estão em
`OneDrive\Pos doc-IME- 2026\Artigo-Tatiana\Strings_de_Busca_v3.txt`, uma seção
por base. Copie **de lá**, nunca do Word — o Word troca aspas retas por curvas
e o parser das bases não reconhece, sem dar erro.

Atenção a duas: o ScienceDirect tem teto de 8 conectores booleanos e por isso
são **seis buscas separadas** (mais seis na variante marinha); o IEEE Xplore
limita a 25 termos por cláusula e 9 curingas, e por isso usa string reduzida.

**2. Importar as exportações.** Salve os arquivos numa pasta e rode:

```bash
python -m pipeline.importar --revisao biossensores_nanocarbono_agua_sedimento --pasta manuais
```

Ele junta ao que já foi coletado, deduplica tudo de novo e reescreve o `.ris`.
Pode rodar quantas vezes quiser — reimportar o mesmo arquivo não duplica nada.

**3. Anotar as contagens** na aba *Log de Buscas* da planilha de extração, e
nas linhas 8 a 13 da aba *Fluxo PRISMA-ScR*. As três bases automáticas já estão
preenchidas.

**4. Triar em dupla** no Rayyan, começando pelos dois controles negativos
(`ITENS_EXCLUIDOS_ESPERADOS` no `config.py`), que já estão na aba de triagem da
planilha para calibrar os revisores.

**5. Citation chasing** a partir de `SEMENTES_REVISOES`, depois da triagem.

## Para revalidar depois de mexer nos termos

Leva menos de um minuto e não baixa nada:

```bash
python -m pipeline.validar --revisao biossensores_nanocarbono_agua_sedimento
```

Se cair abaixo de 90%, descubra qual bloco está barrando:

```bash
python -m pipeline.diagnosticar --revisao biossensores_nanocarbono_agua_sedimento
```

Para forçar nova coleta numa base, apague o arquivo dela em `cache/` — o
`buscar` reaproveita o cache e só rebaixa o que faltar.

## Duas decisões que não são óbvias no `config.py`

**`EXCLUIR_ANIMAIS = False`.** Não é descuido. A exclusão de animais do PubMed é
convenção de revisão clínica e aqui derrubava evidência elegível em silêncio:
sensor validado em peixe ou molusco recebe `Animals` no MeSH, não recebe
`Humans`, e some. Custava 96 registros e um dos 13 estudos do gabarito.

**Semantic Scholar entre as bases.** Não é redundância com o PubMed: cobre
*Sensors and Actuators B: Chemical*, *Electrochimica Acta*, *J. Electroanalytical
Chemistry* e *Carbon*, que o MEDLINE não indexa — e é justamente onde está o
grosso da literatura de sensores. Trouxe 1.411 registros que nenhuma das outras
duas bases tinha.

## Bases selecionadas

- **pubmed** — livre, indexação MeSH
- **europepmc** — livre, superconjunto do MEDLINE + preprints
- **semanticscholar** — livre, cobre química analítica e eletroquímica

Fora por ora: **Scopus** e **OpenAlex** exigem chave (não há `.env` nesta
máquina); **arXiv** não tem cobertura de química ambiental; **Crossref** não
aceita consulta booleana, só texto livre — serve melhor para citation chasing.
