"""Configuracao da revisao: Biossensores de nanocarbono para agua e sedimento

Escopo refinado em 2026-08-05 a partir do protocolo v2 (Artigo-Tatiana):

  - MATRIZ  : apenas sedimento e agua (doce ou salgada). Solo e ar saem.
  - ANALITO : apenas metais pesados/metaloides e HPAs (hidrocarbonetos
              policiclicos aromaticos). Nutrientes, gases-traco e patogenos saem.
  - SENSOR  : tipo aberto (qualquer transducao / elemento de reconhecimento),
              desde que o nanocarbono seja componente ATIVO da camada sensora.

Escrito a mao (nao pelo assistente interativo) para evitar o problema de
dessincronizacao por colagem descrito no PASSO_A_PASSO.md.
"""

TITULO = 'Biossensores de nanocarbono para metais pesados e HPAs em agua e sedimento'
TIPO = 'escopo'

PCC = {
    "populacao": 'estudos primarios experimentais de biossensores/sensores',
    "conceito": 'biointerfaces de nanocarbono como camada sensora ativa',
    "contexto": 'agua doce ou salgada e sedimento; metais pesados e HPAs; 2020-2026',
}

ANOS = (2020, 2026)

# Revisao AMBIENTAL: nao aplicar a exclusao de animais do PubMed.
# Medido em 2026-08-05: com ela ligada, o estudo 10.1039/d6ay00231e (aptassensor
# de GO-AuNP para Pb e Hg) sumia da busca, embora passasse nos quatro blocos e na
# janela. Motivo: foi validado tambem em matriz alimentar, recebeu 'Animals' no
# MeSH e nao recebeu 'Humans'. A clausula e' convencao de revisao clinica e aqui
# so' derruba evidencia elegivel — sensibilidade subiu de 92% para 100%.
EXCLUIR_ANIMAIS = False

# Termos dentro de um grupo -> OR;  grupos dentro de um bloco -> AND;
# blocos entre si -> AND. Termo com espaco vira frase; com * no fim, curinga.
#
# NOTA sobre termos deliberadamente ausentes:
#   'As'          - preposicao em ingles; o PubMed a trata como stopword e ela
#                   contamina o bloco inteiro. Arsenio entra so como 'arsenic'.
#   'GO'          - verbo comum; 'graphene oxide' e 'rGO' cobrem o material.
#   'benzo[a]pyrene' - os colchetes sao delimitador de campo no PubMed e quebram
#                   o parser mesmo entre aspas. 'pyrene' ja casa com o token.
#   'MXene'       - sozinho traria estudos sem nanocarbono, que o criterio
#                   exclui; hibridos grafeno@MXene ja entram por 'graphene'.
BLOCOS = [
    {
        "nome": '#1 Nanocarbono',
        "grupos": [
            {
                "mesh": [
                    'Nanotubes, Carbon',
                    'Graphite',
                    'Quantum Dots',
                    'Fullerenes',
                    'Nanodiamonds',
                ],
                "termos": [
                    'graphene',
                    'graphene oxide',
                    'graphene quantum dot*',
                    'rGO',
                    'carbon nanotube*',
                    'MWCNT*',
                    'SWCNT*',
                    'CNT',
                    'CNTs',
                    'carbon dot*',
                    'carbon quantum dot*',
                    'nanocarbon*',
                    'carbon nanomaterial*',
                    'carbon-based nanomaterial*',
                    'nanostructured carbon',
                    'carbon nanostructure*',
                    'fullerene*',
                    'nanodiamond*',
                    'carbon nanofiber*',
                    'carbon nanohorn*',
                    'laser-induced graphene',
                    'laser induced graphene',
                    'graphite nanoplatelet*',
                ],
            }
        ],
    },
    {
        "nome": '#2 Sensoriamento',
        "grupos": [
            {
                "mesh": [
                    'Biosensing Techniques',
                    'Electrochemical Techniques',
                    'Electrodes',
                ],
                "termos": [
                    'biosensor*',
                    'bio-sensor*',
                    'sensor*',
                    'sensing',
                    'aptasensor*',
                    'immunosensor*',
                    'genosensor*',
                    'nanosensor*',
                    'electrode*',
                    'biointerface*',
                    'molecularly imprinted',
                    'screen-printed',
                    'voltammetr*',
                    'amperometr*',
                    'potentiometr*',
                    'chemiresist*',
                    'field-effect transistor*',
                    'detection platform*',
                ],
            }
        ],
    },
    {
        "nome": '#3 Analitos (metais pesados OU HPAs)',
        "grupos": [
            {
                "mesh": [
                    'Metals, Heavy',
                    'Polycyclic Aromatic Hydrocarbons',
                    'Lead',
                    'Mercury',
                    'Cadmium',
                    'Arsenic',
                    'Chromium',
                ],
                "termos": [
                    # metais pesados e metaloides
                    'heavy metal*',
                    'trace metal*',
                    'toxic metal*',
                    'potentially toxic element*',
                    'metalloid*',
                    'metal ion*',
                    'lead',
                    'Pb',
                    'cadmium',
                    'Cd',
                    'mercury',
                    'Hg',
                    'arsenic',
                    'chromium',
                    'Cr',
                    'copper',
                    'Cu',
                    'zinc',
                    'Zn',
                    'nickel',
                    # hidrocarbonetos policiclicos aromaticos
                    'polycyclic aromatic hydrocarbon*',
                    'polyaromatic hydrocarbon*',
                    'PAH',
                    'PAHs',
                    'benzopyrene',
                    'pyrene',
                    'phenanthrene',
                    'naphthalene',
                    'anthracene',
                    'fluoranthene',
                    'chrysene',
                    'fluorene',
                    'petroleum hydrocarbon*',
                    'BTEX',
                ],
            }
        ],
    },
    {
        "nome": '#4 Matriz aquatica (agua ou sedimento)',
        "grupos": [
            {
                "mesh": [
                    'Water Pollutants, Chemical',
                    'Geologic Sediments',
                    'Environmental Monitoring',
                    'Seawater',
                    'Fresh Water',
                    'Rivers',
                    'Groundwater',
                ],
                "termos": [
                    'water',
                    'freshwater',
                    'fresh water',
                    'seawater',
                    'sea water',
                    'marine',
                    'estuar*',
                    'river*',
                    'lake*',
                    'ocean*',
                    'coastal',
                    'sediment*',
                    'porewater',
                    'pore water',
                    'groundwater',
                    'aquatic',
                    'water quality',
                    'surface water',
                    'environmental water*',
                    'environmental monitoring',
                    'effluent*',
                    'wastewater',
                ],
            }
        ],
    },
]

# Vertente B: conceitos que escapam da busca principal por nao citarem o termo
# central no titulo/resumo. Deixe vazio se nao for o caso da sua revisao.
BLOCOS_VERTENTE_B = []

# GABARITO. A busca so esta pronta quando recupera estes estudos.
# Todos os 13 foram localizados e conferidos no PubMed em 2026-08-05: DOI real,
# recuperavel pelo campo [AID], dentro da janela 2020-2026, e atendendo aos
# quatro criterios (nanocarbono ativo + sensor + metal/HPA + agua/sedimento).
# A selecao cobre de proposito as tres classes dimensionais (0D/1D/2D), as tres
# modalidades de transducao mais frequentes (eletroquimica, optica, FET), os
# dois grupos de analito e as duas salinidades.
ITENS_CONHECIDOS = {
    # --- HPAs (bloco mais fragil da busca; cobertura deliberada) ---
    '10.3390/molecules28155701': 'Molecules 2023 - imunossensor CNT-quitosana, fenantreno em agua do mar',
    '10.3389/fchem.2022.950854': 'Front Chem 2022 - imunossensor MWCNT, benzo(a)pireno em agua do mar',
    # --- Metais, nanocarbono 2D (grafeno / GO / rGO) ---
    '10.1007/s00604-026-08102-7': 'Microchim Acta 2026 - grafeno a laser Bi/AuNP, Zn e Cd em agua do mar',
    '10.1016/j.talanta.2025.129163': 'Talanta 2026 - grafeno a laser em nanofibra aramida, Cd em agua',
    '10.1038/s41598-026-50889-1': 'Sci Rep 2026 - GO funcionalizado em QCM, Pb em meio aquoso',
    '10.1016/j.aca.2024.342800': 'Anal Chim Acta 2024 - aptassensor rGO/AuNF, Hg e Pb em agua',
    '10.1039/d6ay00231e': 'Anal Methods 2026 - DNAzima-aptamero GO-AuNP, Pb e Hg em agua',
    # --- Metais, nanocarbono 1D (nanotubos) ---
    '10.3390/bios15120779': 'Biosensors 2025 - FET de SWCNT, Hg em agua superficial e sedimento',
    '10.1016/j.talanta.2026.129928': 'Talanta 2026 - pasta de MWCNT, Pb em ambientes aquaticos',
    '10.1016/j.talanta.2026.129897': 'Talanta 2026 - SWCNT com poli-L-lisina, monitoramento de Pb',
    # --- Metais, nanocarbono 0D (carbon dots) ---
    '10.1016/j.talanta.2026.130179': 'Talanta 2026 - carbon dots dupla emissao em microfluidica, Pb e Cr',
    '10.3390/s26072142': 'Sensors 2026 - hidrogel com carbon dots e ML, Cu em agua, uso in loco',
    # --- FET com aptamero em efluente ---
    '10.1039/d2na00416j': 'Nanoscale Adv 2023 - FET aptamero-grafeno, Cd em efluente oleoso',
}

# CONTROLES NEGATIVOS. Artigos reais que a busca provavelmente recupera e que a
# TRIAGEM deve rejeitar. Nao entram no calculo de sensibilidade; servem para
# testar se os criterios de exclusao estao operacionais e para treinar a dupla
# de revisores antes da triagem valer.
ITENS_EXCLUIDOS_ESPERADOS = {
    '10.1021/acssensors.5c04813': 'ACS Sens 2026 - MWCNT, HPAs em MATERIAL PARTICULADO (ar): matriz fora do escopo',
    '10.1016/j.jhazmat.2025.140379': 'J Hazard Mater 2025 - GO/MWCNT como SORVENTE de SPME + AFS: nanocarbono nao e a camada sensora',
}

# Sementes para citation chasing: revisoes proximas ao seu tema.
SEMENTES_REVISOES = {
    '10.3390/molecules31010005': 'Molecules 2025 - revisao: metais pesados em agua com materiais de carbono',
    '10.1016/j.coelec.2025.101749': 'Curr Opin Electrochem 2025 - revisao: metodos eletroquimicos em tempo real para metais',
}

# Bases livres de credencial. O Semantic Scholar foi acrescentado por cobrir os
# periodicos de quimica analitica e eletroquimica que o PubMed nao indexa —
# Sensors and Actuators B, Electrochimica Acta, J Electroanalytical Chemistry,
# Carbon — justamente onde esta o grosso da literatura de sensores. Medido em
# 2026-08-05: 2.538 registros, contra 1.914 do PubMed.
#
# Fora por ora: OpenAlex e Scopus exigem chave (nao ha .env nesta maquina);
# arXiv nao tem cobertura de quimica ambiental; Crossref nao aceita consulta
# booleana (so' `query.bibliographic`, texto livre), o que devolveria ruido
# ordenado por relevancia em vez de um conjunto delimitado — melhor usa-lo no
# citation chasing, a partir de SEMENTES_REVISOES.
BASES = ['pubmed', 'europepmc', 'semanticscholar']
