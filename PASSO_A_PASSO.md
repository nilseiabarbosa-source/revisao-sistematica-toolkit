# Passo a passo — para quem não programa

Guia para criar e rodar uma revisão nova. Não é preciso saber programar: você
responde perguntas e lê o que aparece na tela.

Reserve uns 30 minutos na primeira vez.

> **Este guia foi reescrito depois do primeiro uso real.** Tudo que deu errado
> naquela sessão está aqui, com a solução. Os avisos em destaque não são
> hipotéticos — são as coisas que efetivamente falharam.

---

## Antes de começar: monte o gabarito

Uma coisa só, e é a mais importante: **uma lista de 10 a 20 artigos que você já
sabe que deveriam entrar na sua revisão**, com o DOI de cada.

O DOI é o código que começa com `10.` — por exemplo `10.1161/JAHA.126.050501`.
Está na primeira página do artigo, na página do periódico, ou pesquisando o
título no Google Scholar.

De onde tirar: das revisões publicadas mais próximas do seu tema. Olhe as
referências e escolha as que claramente atendem aos seus critérios.

**Por que isso decide tudo.** É com essa lista que o programa testa se a busca
funciona. Na revisão de câncer que originou este código, a estratégia inicial
parecia ótima — 924 resultados, string revisada por especialistas — e recuperava
menos da metade dos estudos que a própria proposta citava como centrais. Só
apareceu porque havia gabarito para comparar.

Deixe a lista pronta num arquivo de texto antes de abrir o programa.

---

## Passo 1 — Ver as extensões dos arquivos

Faça isto uma vez e evita confusão depois. O Windows esconde a extensão dos
arquivos, então `iniciar.bat` e `iniciar_revisao.py` aparecem os dois como
"iniciar…" e é fácil clicar no errado.

No Explorador de Arquivos:

- **Windows 11** — botão **Ver** → **Mostrar** → marque **Extensões de nomes de arquivos**
- **Windows 10** — aba **Exibir** → marque **Extensões de nomes de arquivos**

---

## Passo 2 — Abrir o programa

### Jeito mais simples: clique duplo

1. Abra o Explorador de Arquivos
2. Cole na barra de endereço: `C:\Users\nilse\projetos\revisao-sistematica-toolkit`
3. Dois cliques em **`iniciar.bat`** (o do ícone de engrenagem)

O `iniciar.bat` procura o Python sozinho, mesmo que ele não esteja configurado
no sistema. Se o Windows avisar que o arquivo pode ser perigoso, clique em
**Mais informações** → **Executar assim mesmo**.

### Jeito pelo terminal

Aperte **Windows**, digite `powershell`, abra, e cole:

```
cd C:\Users\nilse\projetos\revisao-sistematica-toolkit
```

```
python iniciar_revisao.py
```

> ### ⚠ Se aparecer "python não é reconhecido"
>
> Não significa que o Python não está instalado. Janelas abertas pelo menu
> Iniciar herdam uma cópia antiga das configurações do sistema, e **nem abrir
> uma janela nova resolve** — só reiniciar o computador.
>
> Use este comando, que funciona sempre porque não depende de configuração:
>
> ```
> & "C:\Users\nilse\AppData\Local\Programs\Python\Python312\python.exe" iniciar_revisao.py
> ```
>
> O `&` no início é obrigatório. Ou simplesmente use o `iniciar.bat`, que já
> resolve isso.

---

## Passo 3 — ⚠ A regra mais importante

> **Digite ou cole uma linha de cada vez. Nunca cole um bloco de várias linhas
> de uma vez.**
>
> Isso não é preciosismo. No primeiro uso real, a colagem em bloco
> dessincronizou a leitura: o programa gravou só o primeiro bloco de termos, e
> o segundo bloco inteiro foi parar dentro do gabarito, no lugar dos DOIs. O
> arquivo saiu corrompido e o trabalho teve que ser refeito.
>
> O programa lê linha por linha, esperando o Enter. Colar tudo de uma vez
> atropela essa espera.

---

## Passo 4 — As perguntas iniciais

Digite a resposta e Enter. Quando aparecer algo entre colchetes, como
`[escopo]`, é a resposta padrão — só Enter já aceita.

| Pergunta | Exemplo de resposta |
|---|---|
| Título da revisão | `Wearables para deteccao precoce de hipertensao` |
| Tipo (escopo / sistematica) | Enter (aceita `escopo`) |
| População | `adultos sem diagnostico de hipertensao` |
| Conceito / Intervenção | `deteccao precoce por sinais de wearables` |
| Contexto | `qualquer pais` |
| Ano inicial | `2015` |
| Ano final | `2026` |

Se o título já tiver sido usado antes, o programa avisa **na hora** e oferece as
saídas: outro título, apagar a pasta antiga, ou continuar com outro nome.

---

## Passo 5 — Os blocos de busca

É a parte conceitual, e é onde a revisão se decide.

**A lógica.** Cada bloco é um conceito da sua pergunta. Os blocos se combinam
com "E" — o artigo só entra se atender a **todos**. Dentro de um bloco, os
termos se combinam com "OU" — basta atender a **um**.

O arranjo típico são três:

| Bloco | O que é | Termos de exemplo |
|---|---|---|
| #1 | tecnologia ou intervenção | `wearable*`, `smartwatch*`, `photoplethysmograph*` |
| #2 | doença ou população | `hypertension`, `hypertensive`, `blood pressure` |
| #3 | desfecho | `early detection`, `screening`, `predict*` |

**Como digitar.** Ele pede o nome do bloco, depois os termos, um por linha:

```
Nome do bloco #1 (vazio encerra): Wearables

Termos do bloco 'Wearables'
  > wearable*
  > smartwatch*
  > photoplethysmograph*
  >
```

Aquele último `>` com **Enter sozinho** é o que encerra a lista. Se você digitar
e nada acontecer, provavelmente ainda está dentro dela.

Depois ele pede os **descritores MeSH** do bloco. É opcional — Enter sozinho
pula. MeSH é o vocabulário controlado do PubMed (`Hypertension`, `Wearable
Electronic Devices`); se você conhece os do seu tema, melhora a busca.

Repita para os blocos #2 e #3. Quando não quiser mais nenhum, deixe o **nome
vazio** e Enter.

**Duas regras sobre termos:**

- **Terminar em `*`** pega as variações: `predict*` encontra *predict*,
  *prediction*, *predictive*, *predictor*. Use bastante — evita perder artigo
  por diferença de plural ou forma verbal.
- **Termos em inglês.** As bases internacionais indexam em inglês. Os textos
  livres (título, população) podem ser em português, com acento.

---

## Passo 6 — O gabarito

Agora os DOIs que você separou. Um por linha, no formato `DOI ; descrição`:

```
> 10.1161/JAHA.126.050501 ; JAHA 2026 - validacao de manguito por PPG
> 10.3390/jpm16070377 ; J Pers Med 2026 - wearables e ML
>
```

Enter vazio encerra. Se puser menos de 5, o programa avisa.

---

## Passo 7 — As bases

Ele mostra a lista e sugere `pubmed,europepmc,arxiv`. Enter aceita.

Essas três não pedem cadastro nem senha, e dão conta de uma revisão inteira.
Scopus, OpenAlex e CORE exigem chave e podem entrar depois — basta editar a
linha `BASES` no `config.py` e rodar de novo.

---

## Passo 8 — ⚠ Conferir o arquivo gerado

**Não pule este passo.** É o que teria evitado o retrabalho no primeiro uso.

Abra o arquivo `config.py` da sua revisão — no Bloco de Notas mesmo. Ele fica em:

```
revisoes\NOME_DA_SUA_REVISAO\config.py
```

Confira três coisas:

1. **`BLOCOS` tem todos os blocos que você digitou?** Procure por `"nome":` —
   deve aparecer uma vez para cada bloco.
2. **`ITENS_CONHECIDOS` tem só DOIs?** Todas as chaves devem começar com `10.`.
   Se aparecer texto solto ali, a leitura embaralhou.
3. **Os termos estão nos blocos certos?**

Se algo estiver errado, você pode **corrigir o arquivo à mão** no Bloco de
Notas, sem refazer nada. É um arquivo de texto comum — mantenha as aspas e as
vírgulas como estão nos exemplos.

---

## Passo 9 — Testar antes de coletar

```
python -m pipeline.validar --revisao NOME_DA_SUA_REVISAO
```

Não baixa nada, só conta e testa. Leva menos de um minuto. Saída real:

```
Base                 Vertente A
pubmed                    1.161
europepmc                 1.147
arxiv                        87

SENSIBILIDADE — o gabarito é recuperado?
  [x] EMBC 2021 — BP sem manguito por PPG de pulso
  [ ] JAHA 2026 — validacao clinica de manguito de dedo
  ...
  9/10 (90%)

Sensibilidade alta. Pode coletar.
```

**Como ler:**

Os números de cima são quantos artigos existem em cada base — servem para
dimensionar a triagem. A conta prática é cerca de 100 registros por hora, por
revisor, e a triagem é feita em dupla.

Os `[x]` e `[ ]` são o teste que importa. O veredito da última linha:

| Sensibilidade | O que fazer |
|---|---|
| 90% ou mais | pode coletar |
| 70 a 89% | vale investigar antes |
| menos de 70% | **não colete** — a busca está perdendo evidência conhecida |

---

## Passo 10 — Quando a sensibilidade está baixa

```
python -m pipeline.diagnosticar --revisao NOME_DA_SUA_REVISAO
```

Ele testa cada estudo perdido contra cada bloco e diz **qual bloco está
barrando** — o que transforma "a busca está ruim" em algo acionável.

O erro mais comum, e que aconteceu na revisão de câncer: o bloco só aceitava a
forma nominal (`risk prediction`) e não a verbal (`predict*`). Artigos
intitulados "Predicting cancer risk" ficavam de fora.

Para corrigir: abra o `config.py`, acrescente os termos que faltam no bloco
problemático, salve, e rode o `validar` de novo. Cada rodada custa segundos —
repita quantas vezes precisar.

---

## Passo 11 — Coletar

```
python -m pipeline.buscar --revisao NOME_DA_SUA_REVISAO
```

Demora de minutos a horas, conforme o volume. Pode deixar rodando. Se for
interrompido, rodar de novo continua de onde parou.

Resultado real da revisão de wearables:

```
Registros identificados: 2394
Duplicatas removidas: 1047
Registros para triagem: 1347
Com resumo: 1344/1347 (100%)
```

Os arquivos ficam em `revisoes\NOME\resultados\`:

| Arquivo | Para que serve |
|---|---|
| `registros_para_triagem.ris` | importar no Rayyan ou Covidence |
| `registros_para_triagem.csv` | abrir no Excel |
| `strings_de_busca.txt` | as buscas exatas, para o pré-registro no OSF |
| `log_prisma_s.json` | anexo metodológico do artigo |

**O número mais importante é o "com resumo".** Registro sem resumo tem que ser
triado só pelo título, o que é bem pior. 100% é o ideal.

---

## Quando der errado

**"python não é reconhecido"**
Ver o quadro do passo 2. Use o caminho completo ou o `iniciar.bat`.

**"python3 não é reconhecido"**
No Windows é `python`, sem o 3.

**"No module named 'requests'"**
Rode uma vez: `python -m pip install -r requirements.txt`

**"já existe uma revisão chamada..."**
O nome está em uso. Escolha outro título, apague a pasta antiga, ou rode com
`--slug outro_nome`.

**"Configuração não encontrada"**
O nome da revisão está errado. Veja os disponíveis com `dir revisoes`

**O `config.py` saiu embaralhado**
Foi colagem em bloco. Corrija à mão no Bloco de Notas — é mais rápido que
refazer — e da próxima vez digite linha a linha.

**Uma base deu erro e as outras funcionaram**
Normal, serviços saem do ar. O programa segue com as demais e registra no log.
Tente aquela base mais tarde.

**A janela preta fecha sozinha**
Se usou o `iniciar.bat`, ele segura a janela. Pelo PowerShell a janela não
fecha — role para cima.

---

## Passo 12 — Bases sem API: exportar e importar

Web of Science, ScienceDirect, IEEE Xplore, GeoRef e Embase não têm API aberta.
Para essas, a busca é colada na interface e o resultado exportado em RIS. Depois:

```
python -m pipeline.importar --revisao NOME --arquivo wos.ris ieee.ris
```

ou, para uma pasta inteira:

```
python -m pipeline.importar --revisao NOME --pasta manuais
```

Ele junta os arquivos ao que as APIs já trouxeram, aplica a janela de anos,
deduplica **tudo de novo** e reescreve o `.ris` e o `.csv` de triagem. Pode
rodar quantas vezes quiser: reimportar o mesmo arquivo não duplica nada e não
empilha linha repetida no log PRISMA-S.

O nome do arquivo vira o rótulo da fonte no log, então vale nomear direito —
`wos.ris` e não `savedrecs(3).ris`.

---

## Revisão ambiental? Desligue a exclusão de animais

Vale para qualquer revisão que não seja clínica.

O tradutor acrescenta `NOT (animals[Mesh] NOT humans[Mesh])` à consulta do
PubMed. É convenção de revisão clínica, e numa revisão ambiental ela **derruba
evidência elegível em silêncio**: artigo de sensor validado em peixe, molusco
ou ensaio de ecotoxicidade recebe `Animals` no MeSH, não recebe `Humans`, e
some da busca.

Medido na revisão de biossensores de nanocarbono: um dos 13 estudos do gabarito
desaparecia, e o total do PubMed caía de 1.914 para 1.818. Os quatro blocos
passavam, a janela passava — não havia como perceber olhando.

Para desligar, acrescente uma linha ao `config.py` da revisão:

```
EXCLUIR_ANIMAIS = False
```

Rode o `validar` antes e depois e compare a contagem. Se não mudou nada, ou a
sua literatura não tem estudo com animal, ou a linha está no lugar errado.

---

## Resumo dos comandos

```
python iniciar_revisao.py                          criar a revisão
python -m pipeline.validar --revisao NOME          testar (rápido)
python -m pipeline.diagnosticar --revisao NOME     ver o que falha
python -m pipeline.buscar --revisao NOME           coletar (demorado)
python -m pipeline.importar --revisao NOME --arquivo X.ris    juntar base sem API
dir revisoes                                       listar as revisões
```

Substitua `NOME` pelo nome que o programa mostrou ao criar a revisão.

## Depois da coleta

O toolkit cobre a busca. As etapas seguintes — pré-registro no OSF, triagem
dupla, extração de dados, avaliação de risco de viés e redação — continuam
sendo trabalho humano. O `.ris` gerado é o ponto de entrada para o Rayyan ou o
Covidence, onde a triagem acontece.
