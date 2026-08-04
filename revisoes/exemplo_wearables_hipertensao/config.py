"""Configuracao da revisao: Wearables para detecção precoce de hipertensão: revisão de escopo

Gerado por iniciar_revisao.py em 2026-08-04.
Este e o unico arquivo que voce precisa editar.
"""

TITULO = 'Wearables para detecção precoce de hipertensão: revisão de escopo'
TIPO = 'escopo'

PCC = {
    "populacao": 'adultos sem diagnóstico de hipertensão',
    "conceito": 'detecção ou predição precoce por sinais de wearables',
    "contexto": 'qualquer país ou sistema de saúde',
}

ANOS = (2015, 2026)

# Termos dentro de um grupo -> OR;  grupos dentro de um bloco -> AND;
# blocos entre si -> AND. Termo com espaco vira frase; com * no fim, curinga.
BLOCOS = [
    {
        "nome": '#1 Wearables',
        "grupos": [
        {
            "mesh": [
                'Wearable Electronic Devices',
            ],
            "termos": [
                'wearable*',
                'smartwatch*',
                'activity tracker*',
                'photoplethysmograph*',
                'continuous monitoring',
            ],
        }
        ],
    },    {
        "nome": '#2 Hipertensão',
        "grupos": [
        {
            "mesh": [
                'Hypertension',
                'Blood Pressure',
            ],
            "termos": [
                'hypertension',
                'blood pressure',
                'hypertensive',
            ],
        }
        ],
    },    {
        "nome": '#3 Detecção',
        "grupos": [
        {
            "termos": [
                'early detection',
                'predict*',
                'screening',
                'risk stratification',
            ],
        }
        ],
    }
]

# Vertente B: conceitos que escapam da busca principal por nao citarem o termo
# central no titulo/resumo. Deixe vazio se nao for o caso da sua revisao.
BLOCOS_VERTENTE_B = []

# GABARITO. A busca so esta pronta quando recupera estes estudos.
ITENS_CONHECIDOS = {
    '10.1038/s41746-019-0136-7': 'Exemplo — substituir pelos seus',
}

# Sementes para citation chasing: revisoes proximas ao seu tema.
SEMENTES_REVISOES = {}

BASES = ['pubmed', 'europepmc', 'arxiv']
