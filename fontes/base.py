"""Esquema comum de registro e utilidades compartilhadas pelos adaptadores.

Todo adaptador converte a resposta da sua API para `Registro`, de modo que o
restante do pipeline (deduplicacao, triagem, exportacao) nunca precise saber de
qual base o dado veio.
"""

from __future__ import annotations

import os
import re
import time
import unicodedata
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Iterator

import requests


def carregar_env() -> None:
    """Carrega um arquivo `.env` local para as variaveis de ambiente.

    Existe para que credenciais nunca precisem ser digitadas na linha de comando
    (onde ficam no historico do shell) nem coladas em codigo (onde acabam no
    repositorio). O `.env` esta no .gitignore.

    Formato, uma variavel por linha:

        SCOPUS_API_KEY=sua_chave
        SCOPUS_INSTTOKEN=seu_token

    Valores ja presentes no ambiente tem precedencia e nao sao sobrescritos.
    """
    for base in (Path.cwd(), Path(__file__).resolve().parent.parent):
        env = base / ".env"
        if not env.exists():
            continue
        for linha in env.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            chave, _, valor = linha.partition("=")
            chave = chave.strip()
            valor = valor.strip().strip('"').strip("'")
            if chave and chave not in os.environ:
                os.environ[chave] = valor
        return


carregar_env()

USER_AGENT = "RevisaoSistematica/1.0 (pesquisa academica; mailto:{email})"

# Muitas APIs pedem ou premiam a identificacao por e-mail (NCBI, Crossref,
# Unpaywall, OpenAlex): o endereco vai em cada requisicao e no User-Agent.
#
# Vem do .env para que cada pessoa que usar o toolkit se identifique com o
# proprio endereco. Rodar com o e-mail de outra pessoa nao e' detalhe de
# cortesia: o NCBI bloqueia por e-mail quando o limite de requisicao e'
# estourado, e o bloqueio recai sobre quem nao rodou nada. O padrao abaixo
# existe so' para nao quebrar a maquina de origem do projeto.
EMAIL_CONTATO = os.environ.get("EMAIL_CONTATO", "nilseia.barbosa@ime.eb.br")


@dataclass
class Registro:
    """Registro bibliografico normalizado."""

    fonte: str
    id_fonte: str
    titulo: str = ""
    resumo: str = ""
    autores: list[str] = field(default_factory=list)
    ano: int | None = None
    periodico: str = ""
    doi: str = ""
    pmid: str = ""
    pmcid: str = ""
    tipo: str = ""
    idioma: str = ""
    termos: list[str] = field(default_factory=list)   # MeSH, keywords, condicoes
    url: str = ""
    acesso_aberto: bool = False
    url_texto_completo: str = ""
    bruto: dict[str, Any] = field(default_factory=dict, repr=False)

    def para_dict(self, incluir_bruto: bool = False) -> dict[str, Any]:
        d = asdict(self)
        if not incluir_bruto:
            d.pop("bruto", None)
        return d

    @property
    def chave_doi(self) -> str:
        return normalizar_doi(self.doi)

    @property
    def chave_titulo(self) -> str:
        return normalizar_titulo(self.titulo)


def normalizar_doi(doi: str) -> str:
    """Reduz um DOI a forma canonica comparavel (minusculo, sem prefixo de URL)."""
    if not doi:
        return ""
    d = doi.strip().lower()
    d = re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", d)
    d = re.sub(r"^doi:\s*", "", d)
    return d.strip()


def normalizar_titulo(titulo: str) -> str:
    """Chave de comparacao: sem acentos, sem pontuacao, espacos colapsados."""
    if not titulo:
        return ""
    t = unicodedata.normalize("NFKD", titulo)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.lower()
    t = re.sub(r"<[^>]+>", " ", t)          # tags HTML/JATS que vazam de algumas APIs
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return " ".join(t.split())


def extrair_ano(valor: Any) -> int | None:
    """Aceita int, '2023', '2023-05-01', 'May 2023' e devolve o ano ou None."""
    if valor is None:
        return None
    if isinstance(valor, int):
        return valor if 1500 < valor < 2200 else None
    m = re.search(r"(1[5-9]\d{2}|2[01]\d{2})", str(valor))
    return int(m.group(1)) if m else None


class ClienteHTTP:
    """Sessao HTTP com limitacao de taxa e retentativa simples.

    `req_por_segundo` deve refletir o teto documentado da API — estourar o limite
    do NCBI, por exemplo, resulta em bloqueio temporario do IP.
    """

    def __init__(self, req_por_segundo: float = 3.0, tentativas: int = 3) -> None:
        self.intervalo = 1.0 / req_por_segundo if req_por_segundo > 0 else 0.0
        self.tentativas = tentativas
        self._ultimo = 0.0
        self.sessao = requests.Session()
        self.sessao.headers["User-Agent"] = USER_AGENT.format(email=EMAIL_CONTATO)

    def get(self, url: str, params: dict | None = None, **kwargs) -> requests.Response:
        ultimo_erro: Exception | None = None
        for tentativa in range(self.tentativas):
            espera = self.intervalo - (time.monotonic() - self._ultimo)
            if espera > 0:
                time.sleep(espera)
            self._ultimo = time.monotonic()
            try:
                r = self.sessao.get(url, params=params, timeout=60, **kwargs)
                if r.status_code in (429, 500, 502, 503, 504):
                    time.sleep(2 ** tentativa)
                    ultimo_erro = requests.HTTPError(f"HTTP {r.status_code} em {url}")
                    continue
                r.raise_for_status()
                return r
            except requests.RequestException as e:
                ultimo_erro = e
                time.sleep(2 ** tentativa)
        raise RuntimeError(f"Falha apos {self.tentativas} tentativas: {ultimo_erro}")


class FonteBase:
    """Contrato que todo adaptador implementa."""

    nome = "base"

    def buscar(self, consulta: str, limite: int = 1000) -> Iterator[Registro]:
        raise NotImplementedError

    def coletar(self, consulta: str, limite: int = 1000) -> list[Registro]:
        return list(self.buscar(consulta, limite))
