# Passo a passo — para quem não programa

Guia detalhado para criar e rodar uma revisão nova. Não é preciso saber
programar: você vai responder perguntas e ler o que aparece na tela.

Reserve uns 20 minutos para a primeira vez.

---

## O que preparar antes

Uma coisa só, e é a mais importante: **uma lista de 10 a 20 artigos que você já
sabe que deveriam entrar na sua revisão**, com o DOI de cada um.

O DOI é aquele código que começa com `10.` — por exemplo
`10.1038/s41591-023-02332-5`. Aparece na primeira página do artigo, na página do
periódico, ou pesquisando o título no Google Scholar.

De onde tirar essa lista: das revisões já publicadas mais próximas do seu tema.
Olhe as referências delas e escolha as que claramente atendem aos seus critérios.

**Por que isso importa tanto.** É com essa lista que o programa testa se a sua
busca funciona. Na revisão da Karina, a estratégia inicial parecia ótima — 924
resultados, string revisada por especialistas — e recuperava menos da metade dos
estudos que a própria proposta citava como centrais. Sem esse teste, ninguém
teria percebido.

Anote também, antes de começar: o título da revisão, o recorte de anos, e os
grupos de termos de busca (falo deles no passo 4).

---

## Passo 1 — Abrir o programa

**Você não abre o Python.** Se abrir o Python vai aparecer `>>>` e nada vai
funcionar.

### Jeito mais fácil: clique duplo

1. Abra o Explorador de Arquivos (a pastinha amarela na barra de tarefas)
2. Cole este caminho na barra de endereço e dê Enter:
   `C:\Users\nilse\projetos\revisao-sistematica-toolkit`
3. Procure o arquivo **`iniciar.bat`** e dê **dois cliques**

Abre uma janela preta e o programa começa. Pode pular para o passo 3.

> Se o Windows avisar que o arquivo pode ser perigoso, é só porque foi baixado
> ou criado recentemente. Clique em "Mais informações" → "Executar assim mesmo".

### Jeito pelo terminal

Se preferir, ou se o clique duplo não funcionar:

1. Aperte a tecla **Windows**
2. Digite `powershell`
3. Clique em **Windows PowerShell** (ícone azul)
4. Na janela que abrir, cole a linha abaixo e dê Enter:

```
cd C:\Users\nilse\projetos\revisao-sistematica-toolkit
```

5. Cole esta e dê Enter:

```
python iniciar_revisao.py
```

> **Como colar no PowerShell:** `Ctrl+V` funciona. Clicar com o botão direito
> também cola.
>
> **Atenção:** é `python`, não `python3`. No Windows o `python3` não existe.

---

## Passo 2 — Dar uma olhada sem compromisso (opcional)

Se quiser ver como fica antes de responder qualquer coisa, rode:

```
python iniciar_revisao.py --exemplo
```

Isso cria uma revisão de exemplo — sobre wearables e hipertensão — sem fazer
nenhuma pergunta. Você pode abrir a pasta `revisoes\exemplo_wearables_hipertensao`
e ver o arquivo `config.py`, que é o que o programa gera.

Não interfere em nada. É só para você ver o formato.

---

## Passo 3 — Responder as perguntas

O programa vai perguntando, uma coisa de cada vez. Digite a resposta e dê Enter.

Quando aparecer algo entre colchetes, tipo `[escopo]`, aquilo é a resposta
padrão: se você só apertar Enter sem digitar nada, ele usa aquela.

**Título da revisão** — como você chamaria o trabalho.
Exemplo: `Wearables para detecção precoce de hipertensão`

**Tipo (escopo / sistematica)** — em geral `escopo`, se o objetivo é mapear um
campo, e `sistematica` se é responder a uma pergunta fechada de efeito.

**População / Conceito / Contexto** — a sua pergunta destrinchada em três.
São só para documentação, não afetam a busca. Exemplo:
- População: `adultos sem diagnóstico de hipertensão`
- Conceito: `detecção precoce por sinais de wearables`
- Contexto: `qualquer país`

**Ano inicial e Ano final** — o recorte temporal. Exemplo: `2015` e `2026`.

---

## Passo 4 — Os blocos de busca

Aqui é a parte que exige mais atenção, e é onde a revisão se decide.

**A ideia.** Um bloco é um conceito da sua pergunta. O programa combina os
blocos com "E" — ou seja, um artigo só entra se atender a **todos**. Dentro de
um bloco, os termos são combinados com "OU" — basta atender a **um**.

O arranjo mais comum são três blocos:

| Bloco | O que é | Termos de exemplo |
|---|---|---|
| #1 | a tecnologia ou intervenção | `wearable`, `smartwatch` |
| #2 | a doença ou população | `hypertension`, `blood pressure` |
| #3 | o desfecho | `early detection`, `screening` |

**Como digitar.** Ele pede o nome do bloco, depois os termos — **um por linha**.
Quando terminar os termos, dê Enter numa linha vazia para encerrar.

Assim:

```
Nome do bloco #1 (vazio encerra): Wearables

Termos do bloco 'Wearables'
  Um termo por linha. Frases com espaço viram busca exata;
  terminar em * usa curinga (ex.: cancer*). Linha vazia encerra.
  > wearable*
  > smartwatch*
  > activity tracker*
  >
```

Aquele último `>` vazio, seguido de Enter, é o que encerra a lista.

**Duas regras sobre os termos:**

- **Termo terminado em `*`** pega todas as variações. `cancer*` encontra
  *cancer*, *cancers*, *cancerous*. Use bastante — é o que evita perder artigo
  por diferença de plural.
- **Termo com espaço** é tratado como expressão exata. `early detection` só
  encontra as duas palavras juntas, nessa ordem.

**Termos em inglês.** As bases internacionais indexam em inglês. Termos em
português só encontrariam artigos brasileiros no SciELO.

Depois dos termos ele pergunta os **descritores MeSH** do bloco. É opcional —
pode dar Enter direto e pular. MeSH é o vocabulário controlado do PubMed
(`Hypertension`, `Wearable Electronic Devices`); se você conhece os do seu tema,
melhora bastante a busca.

Quando não quiser mais blocos, deixe o **nome do bloco vazio** e dê Enter.

---

## Passo 5 — O gabarito

Agora entram os DOIs que você separou no começo. Um por linha, no formato:

```
10.1038/s41591-023-02332-5 ; Placido 2023 — modelo de pâncreas
```

O ponto e vírgula separa o DOI da descrição. A descrição é só para você se
localizar depois.

Linha vazia encerra.

Se você puser menos de 5, o programa avisa. Ele deixa continuar, mas com 2 ou 3
o teste não diz grande coisa.

---

## Passo 6 — Escolher as bases

Ele mostra a lista e sugere `pubmed,europepmc,arxiv`. Para começar, aceite a
sugestão dando Enter.

Essas três não precisam de senha nem cadastro. Dá para fazer uma revisão inteira
só com elas. Scopus, OpenAlex e CORE exigem chave e podem ficar para depois.

---

## Passo 7 — Ver se a busca funciona

Terminadas as perguntas, ele mostra algo como:

```
Revisão criada em revisoes/wearables_hipertensao/
Próximo passo:  python -m pipeline.validar --revisao wearables_hipertensao
```

**Copie essa última linha e rode.** Ela não baixa nada — só conta e testa. Leva
menos de um minuto.

O resultado se parece com isto:

```
Base                 Vertente A
pubmed                      742
europepmc                   741
arxiv                        34

SENSIBILIDADE — o gabarito é recuperado?
  [x] Placido 2023 — modelo de pâncreas
  [ ] Kinar 2016 — ColonFlag
  ...
  14/16 (88%)

Sensibilidade alta. Pode coletar.
```

**Como ler:**

Os números de cima são quantos artigos existem em cada base. Servem para você
dimensionar o trabalho de triagem — a conta prática é cerca de 100 registros por
hora, por revisor.

Os `[x]` e `[ ]` são o teste que importa: quais do seu gabarito a busca
encontrou. `[x]` achou, `[ ]` não.

A última linha é o veredito:

- **Sensibilidade alta** (90% ou mais) — pode seguir
- **Intermediária** (70 a 89%) — vale investigar
- **BAIXA** (menos de 70%) — **não colete ainda**, a busca está perdendo coisa
  que você sabe que deveria entrar

---

## Passo 8 — Quando a sensibilidade está baixa

Rode o diagnóstico:

```
python -m pipeline.diagnosticar --revisao NOME_DA_SUA_REVISAO
```

Ele testa cada estudo perdido contra cada bloco e diz **qual bloco está
barrando**. A saída indica coisas como "o bloco #2 barrou 9 estudos" — o que
significa que faltam sinônimos ali.

O erro mais comum, e que aconteceu na revisão da Karina: o bloco só aceitava a
forma nominal (`risk prediction`) e não a verbal (`predict*`). Artigos
intitulados "Predicting cancer risk" ficavam de fora.

**Como corrigir:** abra o arquivo `config.py` da sua revisão, no Bloco de Notas
mesmo. Ele fica em `revisoes\NOME_DA_SUA_REVISAO\config.py`. Acrescente os
termos que faltam na lista do bloco problemático, salve, e rode o `validar` de
novo.

Repita até a sensibilidade subir. Cada rodada custa segundos.

---

## Passo 9 — Coletar

Só depois que a sensibilidade estiver alta:

```
python -m pipeline.buscar --revisao NOME_DA_SUA_REVISAO
```

Este demora — de minutos a algumas horas, conforme o volume. Pode deixar
rodando e ir fazer outra coisa. Se for interrompido, rodar de novo continua de
onde parou.

Ao terminar, os arquivos ficam em `revisoes\NOME_DA_SUA_REVISAO\resultados\`:

| Arquivo | Para que serve |
|---|---|
| `registros_para_triagem.ris` | importar no Rayyan ou Covidence |
| `registros_para_triagem.csv` | abrir no Excel |
| `log_prisma_s.json` | anexo metodológico do artigo |
| `strings_de_busca.txt` | as buscas exatas, para o pré-registro |

---

## Quando der errado

**"python não é reconhecido como nome de cmdlet"**
O Python não está instalado ou não foi adicionado ao PATH. Baixe em
python.org/downloads e, na primeira tela do instalador, **marque a caixa "Add
python.exe to PATH"** antes de clicar em Install. É a caixa que quase todo mundo
esquece.

**"python3 não é reconhecido"**
No Windows é `python`, sem o 3.

**"No module named 'requests'"**
Rode uma vez: `python -m pip install -r requirements.txt`

**"Configuração não encontrada"**
O nome da revisão está errado. Veja os nomes disponíveis com:
`dir revisoes`

**A janela preta fecha sozinha**
Se estiver usando o `iniciar.bat`, ele já segura a janela aberta. Se rodou pelo
PowerShell, a janela não fecha — role para cima para ler.

**Uma base deu erro e as outras funcionaram**
Normal. Serviços saem do ar de vez em quando. O programa continua com as demais
e registra o erro no log. Tente aquela base de novo mais tarde.

---

## Resumo dos comandos

```
python iniciar_revisao.py                                  criar a revisão
python -m pipeline.validar --revisao NOME                  testar (rápido)
python -m pipeline.diagnosticar --revisao NOME             ver o que falha
python -m pipeline.buscar --revisao NOME                   coletar (demorado)
```

Substitua `NOME` pelo nome que o programa mostrou ao criar a revisão.
