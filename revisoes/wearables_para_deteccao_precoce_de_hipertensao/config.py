"""Configuracao da revisao: Wearables para deteccao precoce de hipertensao

Gerado por iniciar_revisao.py em 2026-08-05 e corrigido manualmente.

NOTA. O arquivo gerado pela primeira execucao saiu corrompido: a colagem de
varias linhas de uma vez no PowerShell dessincronizou a leitura, de modo que o
bloco #2 foi lido como se fosse gabarito. Este arquivo foi refeito a mao, com
os tres blocos e com DOIs reais obtidos por busca no PubMed.
"""

TITULO = 'Wearables para deteccao precoce de hipertensao'
TIPO = 'escopo'

PCC = {
    "populacao": 'adultos sem diagnostico de hipertensao',
    "conceito": 'deteccao precoce por sinais de wearables',
    "contexto": 'qualquer pais',
}

ANOS = (2015, 2026)

# Termos dentro de um grupo -> OR;  grupos dentro de um bloco -> AND;
# blocos entre si -> AND. Termo com espaco vira frase; com * no fim, curinga.
BLOCOS = [
    {
        "nome": '#1 Wearables',
        "grupos": [
            {
                "mesh": ['Wearable Electronic Devices'],
                "termos": [
                    'wearable*',
                    'smartwatch*',
                    'activity tracker*',
                    'photoplethysmograph*',
                    'PPG',
                    'cuffless',
                ],
            }
        ],
    },
    {
        "nome": '#2 Hipertensao',
        "grupos": [
            {
                "mesh": ['Hypertension', 'Blood Pressure'],
                "termos": [
                    'hypertension',
                    'hypertensive',
                    'blood pressure',
                ],
            }
        ],
    },
    {
        "nome": '#3 Deteccao',
        "grupos": [
            {
                "mesh": ['Early Diagnosis'],
                "termos": [
                    'early detection',
                    'early diagnosis',
                    'screening',
                    'predict*',
                    'estimation',
                    'risk stratification',
                ],
            }
        ],
    },
]

# Vertente B: conceitos que escapam da busca principal por nao citarem o termo
# central no titulo/resumo. Deixe vazio se nao for o caso da sua revisao.
BLOCOS_VERTENTE_B = []

# GABARITO. A busca so esta pronta quando recupera estes estudos.
# Todos verificados no PubMed em 2026-08-05 — sao artigos reais, nao exemplos.
ITENS_CONHECIDOS = {
    '10.1109/EMBC46164.2021.9629544': 'EMBC 2021 — BP sem manguito por PPG de pulso',
    '10.1109/EMBC46164.2021.9629687': 'EMBC 2021 — deep learning para prever PA a partir de PPG',
    '10.1109/EMBC46164.2021.9630319': 'EMBC 2021 — redes recorrentes para monitorar PA',
    '10.1109/EMBC46164.2021.9630557': 'EMBC 2021 — CNN pequena para PA sem manguito',
    '10.1109/EMBC46164.2021.9629594': 'EMBC 2021 — metodo novo de PA sem manguito',
    '10.1161/JAHA.126.050501': 'JAHA 2026 — validacao clinica de manguito de dedo por PPG',
    '10.1088/1361-6579/ae944f': 'Physiol Meas 2026 — otimizacao de DL para PA sem manguito',
    '10.3389/fphys.2026.1779262': 'Front Physiol 2026 — modelo interpretavel por PPG',
    '10.3390/jpm16070377': 'J Pers Med 2026 — wearables e ML em monitoramento cardiovascular',
    '10.1186/s12872-026-06073-4': 'BMC Cardiovasc 2026 — metricas de smartwatch como preditoras',
}

# Sementes para citation chasing: revisoes proximas ao seu tema.
SEMENTES_REVISOES = {}

BASES = ['pubmed', 'europepmc', 'arxiv']
