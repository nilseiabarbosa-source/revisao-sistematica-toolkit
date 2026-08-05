# Wearables para deteccao precoce de hipertensao

Revisão criada em 2026-08-05. Configuração em `config.py`.

## Próximos passos, na ordem

**1. Complete o gabarito.** Abra `config.py` e preencha `ITENS_CONHECIDOS` com
10 a 20 DOIs de estudos que você já sabe serem elegíveis. Sem isso não há como
validar a busca — e uma busca não validada pode estar perdendo metade da
evidência sem dar nenhum sinal.

**2. Calibre e valide, antes de coletar.**

```bash
python -m pipeline.validar --revisao wearables_para_deteccao_precoce_de_hipertensao
```

Mostra o volume por base e quantos estudos do gabarito são recuperados.
Enquanto a sensibilidade não estiver alta, ajuste os blocos e repita. Contagem
é barata; coleta não.

**3. Se a sensibilidade estiver baixa**, descubra qual bloco está barrando:

```bash
python -m pipeline.diagnosticar --revisao wearables_para_deteccao_precoce_de_hipertensao
```

**4. Colete.**

```bash
python -m pipeline.buscar --revisao wearables_para_deteccao_precoce_de_hipertensao
```

**5. Exporte para triagem.** O `.ris` gerado importa direto no Rayyan e no
Covidence.

## Bases selecionadas

- **pubmed** — PubMed/MEDLINE — livre, biomédica, indexação MeSH
- **europepmc** — Europe PMC — livre, biomédica + preprints + texto completo OA
- **arxiv** — arXiv — livre, preprints de computação e estatística

## Credenciais

Bases que exigem chave leem do arquivo `.env` na raiz do projeto. Ele está no
`.gitignore` — nunca versione credenciais.
