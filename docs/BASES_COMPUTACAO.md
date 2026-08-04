# Bases de literatura de computação — o que foi automatizado

Testado contra as APIs reais em 01/08/2026. A lacuna que o protocolo destinava
ao IEEE Xplore e à ACM Digital Library.

## Resultado do teste

| Base | Chave? | Status | Resumo | Novos ¹ |
|---|---|---|---|---|
| **arXiv** | não | ✅ funcionando | 100% | 68% |
| **OpenAlex** | ver nota | ✅ funcionando | 90% | 78% |
| **Semantic Scholar** | não | ✅ já em uso | 89% | 50% |
| **CORE** | sim (grátis) | ⚠ aguarda chave | — | — |
| **DBLP** | não | ⚠ API fora do ar | 0% (nunca traz) | — |
| IEEE Xplore | sim (solicitar) | ✋ manual | — | — |
| ACM Digital Library | — | ✋ manual | — | — |

¹ Percentual da amostra ausente do conjunto atual de 13.754 registros.

---

## ✅ arXiv — `fontes/arxiv.py`

Livre, sem chave. **100% dos registros trazem resumo e DOI**, o que os torna
imediatamente triáveis — a diferença decisiva em relação ao DBLP.

Sintaxe: campos `ti:`, `abs:`, `all:`, `cat:`; operadores `AND`, `OR`, `ANDNOT`.
Categorias relevantes: `cs.LG`, `cs.AI`, `cs.CL`, `stat.ML`, `q-bio`.

Calibração medida para esta revisão:

| Consulta | Resultados |
|---|---|
| `abs:` com frases exatas | 48 |
| `all:` equivalente | 47 |
| ampla (EHR OR claims OR clinical notes) | **85** |
| `cat:cs.LG` + cancer + EHR | 60 |

Volume baixo, e isso é esperado: o arXiv concentra o método, não a aplicação
clínica. Dos 60 registros da amostra ampla, **44 eram novos** — o retorno por
registro é alto justamente porque quase nada disso aparece nas bases biomédicas.

A API pede cortesia de uma requisição a cada três segundos; o adaptador já
respeita.

## ✅ OpenAlex — `fontes/openalex.py`

Cobertura multidisciplinar ampla, com boa penetração em computação. Na amostra,
**90% com resumo e 78% de registros novos** — a maior contribuição relativa
entre as testadas.

**Nota sobre a chave.** A documentação indica que desde 13/02/2026 a API exige
chave e adotou cobrança por uso. No teste, as chamadas **funcionaram sem chave**
— provavelmente pelos créditos de avaliação, que se esgotam e passam a devolver
HTTP 409. Para uso de produção, obter chave gratuita em `openalex.org` e
declarar `OPENALEX_API_KEY` no `.env`.

O resumo vem como índice invertido, não como texto corrido; o adaptador
reconstrói.

## ⚠ CORE — `fontes/core.py`

Agrega mais de 300 milhões de documentos de repositórios institucionais e
frequentemente traz o **texto completo**, o que serve à etapa de extração e não
só à triagem. Exige chave gratuita em `core.ac.uk/services/api`.

O adaptador está escrito e falha com mensagem clara enquanto a chave não existe.
Não foi possível testá-lo.

## ⚠ DBLP — `fontes/dblp.py`

É a bibliografia canônica da computação, com cobertura de anais (NeurIPS, ICML,
MICCAI, AMIA, CHIL) que nenhuma base biomédica alcança.

**Não consegui testar:** a API devolveu HTTP 500 para toda requisição, inclusive
por `curl` simples e sem cabeçalhos personalizados, enquanto `dblp.org` responde
normalmente. É indisponibilidade do serviço, não do adaptador — que segue a
especificação documentada e deve ser testado antes de entrar em produção.

Vale registrar a limitação estrutural: **o DBLP não fornece resumo**. Como o Web
of Science Starter, serve para obter DOIs e títulos, que precisam ser
enriquecidos depois via Crossref ou Europe PMC.

## ✋ IEEE Xplore e ACM Digital Library

O IEEE tem API mediante solicitação institucional; a ACM não expõe API pública.
Seguem como exportação manual — as strings estão em `strings_bases_manuais.md` e
o `integrar_manuais.py` absorve o RIS.

Na prática, arXiv e OpenAlex cobrem boa parte do que viria dessas duas, já que a
maioria dos artigos de IEEE e ACM na interseção deste tema tem preprint no arXiv.

---

## Uma ressalva que a evidência deste projeto sustenta

Acrescentar bases de computação aumenta a cobertura, mas a análise da
contribuição do Scopus mostrou o outro lado: **anais de conferência raramente
trazem detalhe suficiente** para o *charting* de antecedência, tipo de validação
e disponibilidade de código que o protocolo exige. Dos registros de anais que o
Scopus trouxe, apenas 1% tinha resumo recuperável, e a maioria seria excluída na
leitura de texto completo.

O arXiv é o caso oposto e por isso vale mais a pena: preprint tem texto completo
aberto, resumo estruturado e código com frequência muito maior.

Recomendação: **incluir arXiv e OpenAlex**; tratar DBLP e CORE como opcionais,
condicionados a disponibilidade e chave; manter IEEE e ACM como exportação
manual ou declarar a limitação.
