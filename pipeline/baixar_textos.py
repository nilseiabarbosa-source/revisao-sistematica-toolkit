"""Baixa o texto completo dos registros em ACESSO ABERTO.

    python3 -m pipeline.baixar_textos --revisao <slug>
    python3 -m pipeline.baixar_textos --revisao <slug> --dois incluidos.txt
    python3 -m pipeline.baixar_textos --revisao <slug> --limite 20   # teste

## O que este script faz e o que nao faz

Baixa **apenas** o que a propria fonte declara aberto: PDF indicado pelo
Unpaywall, XML de texto completo do Europe PMC, PDF do arXiv. Nao tenta
contornar paywall, nao usa credencial de biblioteca e nao raspa pagina de
editora — nada disso seria acesso autorizado.

Artigo fechado entra em `_faltantes.csv`, com DOI e link, para ser obtido pelo
acesso institucional. Essa lista costuma ser a maior parte do trabalho manual
da etapa de texto completo, e ter ela pronta ja ajuda.

## Ordem de preferencia

1. **XML do Europe PMC** (quando ha PMCID) — melhor que PDF: secoes, tabelas e
   referencias vem separadas, o que serve a extracao de dados.
2. **PDF do Unpaywall** — resolve o DOI para a melhor copia aberta.
3. **Link ja registrado** no proprio registro.

## Cortesia com os servidores

Uma requisicao por segundo, identificacao no User-Agent com e-mail de contato,
e nada de retentativa agressiva. Servidor de repositorio academico e
infraestrutura publica: derrubar um por excesso de requisicao prejudica todo
mundo e costuma render bloqueio de IP.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from fontes import EuropePMC, Unpaywall, normalizar_doi  # noqa: E402
from fontes.base import EMAIL_CONTATO, ClienteHTTP  # noqa: E402
from pipeline.validar import carregar_config  # noqa: E402

MAX_MB = 60


def nome_arquivo(reg: dict, ext: str) -> str:
    """Nome estavel e legivel: ano_primeiroautor_inicio-do-titulo.ext"""
    ano = reg.get("ano") or "sd"
    autores = reg.get("autores") or []
    autor = re.sub(r"[^A-Za-z]", "", (autores[0].split()[0] if autores else "sem"))[:14]
    titulo = re.sub(r"[^A-Za-z0-9 ]", "", reg.get("titulo") or "")[:48].strip()
    titulo = re.sub(r"\s+", "-", titulo)
    ident = normalizar_doi(reg.get("doi", "")) or reg.get("pmid") or reg.get("id_fonte", "")
    ident = re.sub(r"[^A-Za-z0-9.]", "_", ident)[:32]
    return f"{ano}_{autor}_{titulo}_{ident}.{ext}".strip("_")


def baixar(http: ClienteHTTP, url: str, destino: Path) -> tuple[bool, str]:
    """Grava a resposta se for mesmo um documento. Devolve (ok, motivo)."""
    try:
        r = http.sessao.get(url, timeout=90, stream=True, allow_redirects=True)
    except Exception as e:
        return False, f"{type(e).__name__}"
    if r.status_code != 200:
        return False, f"HTTP {r.status_code}"

    tipo = (r.headers.get("Content-Type") or "").lower()
    # Muito link "de PDF" devolve na verdade a pagina de destino da editora.
    # Gravar isso encheria a pasta de HTML disfarcado de artigo.
    if "pdf" not in tipo and "xml" not in tipo:
        return False, f"nao e documento ({tipo.split(';')[0] or 'sem tipo'})"

    tamanho = int(r.headers.get("Content-Length") or 0)
    if tamanho > MAX_MB * 1024 * 1024:
        return False, f"grande demais ({tamanho // 1024 // 1024} MB)"

    destino.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with destino.open("wb") as f:
        for parte in r.iter_content(chunk_size=65536):
            total += len(parte)
            if total > MAX_MB * 1024 * 1024:
                f.close()
                destino.unlink(missing_ok=True)
                return False, "grande demais"
            f.write(parte)

    if total < 2048:  # PDF de 1 KB e pagina de erro, nao artigo
        destino.unlink(missing_ok=True)
        return False, "arquivo suspeito de tao pequeno"
    return True, f"{total // 1024} KB"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--revisao", help="slug da revisao; opcional se usar --dois")
    ap.add_argument("--dois", help="arquivo com um DOI (ou link doi.org) por linha")
    ap.add_argument("--saida", help="pasta de destino (padrao: revisoes/<slug>/textos)")
    ap.add_argument("--limite", type=int, help="para testar com poucos")
    args = ap.parse_args()

    if not args.revisao and not args.dois:
        sys.exit("Informe --revisao, --dois, ou os dois.")

    titulo = "Lista avulsa de DOIs"
    regs: list[dict] = []
    pasta = RAIZ

    if args.revisao:
        cfg = carregar_config(args.revisao)
        titulo = cfg.TITULO
        pasta = RAIZ / "revisoes" / args.revisao
        origem = pasta / "resultados" / "registros.json"
        if origem.exists():
            regs = json.loads(origem.read_text(encoding="utf-8"))
        elif not args.dois:
            sys.exit(f"Nao encontrei {origem}. Rode pipeline.buscar antes.")

    if args.dois:
        # Aceita tanto DOI puro quanto link https://doi.org/... — normalizar_doi
        # tira o prefixo. Ordem preservada, duplicatas removidas.
        pedidos, vistos = [], set()
        for linha in Path(args.dois).read_text(encoding="utf-8").splitlines():
            d = normalizar_doi(linha.strip())
            if d and d not in vistos:
                vistos.add(d)
                pedidos.append(d)

        por_doi = {normalizar_doi(r.get("doi", "")): r for r in regs if r.get("doi")}
        # DOI que nao esta na revisao ainda pode ser baixado: os metadados sao
        # buscados na hora. Isso permite usar a lista sozinha, sem revisao.
        faltam_meta = [d for d in pedidos if d not in por_doi]
        if faltam_meta:
            print(f"Buscando metadados de {len(faltam_meta)} DOI(s) nao presentes "
                  f"na revisao...")
            from fontes import Crossref
            cr = Crossref()
            for d in faltam_meta:
                reg = None
                try:
                    reg = cr.por_doi(d)
                except Exception:
                    pass
                por_doi[d] = reg.para_dict() if reg else {
                    "doi": d, "titulo": f"(metadados nao obtidos) {d}",
                    "autores": [], "ano": None, "pmcid": "", "pmid": "",
                    "url_texto_completo": "", "url": f"https://doi.org/{d}",
                }

        regs = [por_doi[d] for d in pedidos if d in por_doi]
        print(f"Lista {args.dois}: {len(regs)} registros")

    if args.limite:
        regs = regs[: args.limite]

    destino = Path(args.saida) if args.saida else (pasta / "textos")
    destino.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(f"{titulo}")
    print("=" * 70)
    print(f"Registros a tentar: {len(regs)}")
    print(f"Destino: {destino}")
    if len(regs) > 500 and not args.dois:
        print("\nAVISO: isto vai tentar centenas de downloads. Normalmente so faz")
        print("sentido baixar o texto do que sobreviveu a triagem — use --dois")
        print("com a lista dos incluidos.\n")

    http = ClienteHTTP(req_por_segundo=1.0)
    http.sessao.headers["User-Agent"] = (
        f"RevisaoSistematica/1.0 (pesquisa academica; mailto:{EMAIL_CONTATO})"
    )
    epmc = EuropePMC()
    up = Unpaywall()

    baixados = pulados = falhas = 0
    faltantes = []
    inicio = time.monotonic()

    for i, r in enumerate(regs, 1):
        doi = normalizar_doi(r.get("doi", ""))
        titulo = (r.get("titulo") or "")[:52]

        # ------------------------------------------- 1. XML do Europe PMC
        # O PMC e a rota mais confiavel: e repositorio publico e nao bloqueia
        # acesso automatizado, ao contrario dos sites de editora, que devolvem
        # 403 mesmo para artigo aberto. Quando o registro nao traz PMCID — caso
        # dos metadados vindos do Crossref — vale consultar pelo DOI.
        pmcid = r.get("pmcid") or ""
        if not pmcid and doi:
            try:
                achados = epmc.coletar(f'DOI:"{doi}"', limite=1)
                if achados and achados[0].pmcid:
                    pmcid = achados[0].pmcid
            except Exception:
                pass

        if pmcid:
            alvo = destino / nome_arquivo(r, "xml")
            if alvo.exists():
                pulados += 1
                continue
            xml = None
            try:
                xml = epmc.texto_completo_xml(pmcid)
            except Exception:
                pass
            if xml and len(xml) > 2048:
                alvo.write_text(xml, encoding="utf-8")
                baixados += 1
                print(f"[{i}/{len(regs)}] XML  {titulo}")
                continue

        # -------------------------------- 2. link ja conhecido, 3. Unpaywall
        alvo = destino / nome_arquivo(r, "pdf")
        if alvo.exists():
            pulados += 1
            continue

        urls = []
        if r.get("url_texto_completo"):
            urls.append(r["url_texto_completo"])
        if doi:
            try:
                pdf = up.melhor_pdf(doi)
                if pdf and pdf not in urls:
                    urls.append(pdf)
            except Exception:
                pass

        if not urls:
            faltantes.append({"doi": doi, "titulo": r.get("titulo", ""),
                              "motivo": "sem copia aberta localizada",
                              "url": r.get("url", "")})
            falhas += 1
            continue

        sucesso = motivo = None
        for u in urls:
            sucesso, motivo = baixar(http, u, alvo)
            if sucesso:
                break
        if sucesso:
            baixados += 1
            print(f"[{i}/{len(regs)}] PDF  {titulo}  ({motivo})")
        else:
            falhas += 1
            faltantes.append({"doi": doi, "titulo": r.get("titulo", ""),
                              "motivo": motivo or "sem link", "url": urls[0]})

        if i % 25 == 0:
            decorrido = time.monotonic() - inicio
            print(f"    ... {i}/{len(regs)} | {baixados} obtidos | "
                  f"{decorrido/60:.1f} min")

    # ------------------------------------------------------------ relatorio
    if faltantes:
        rel = destino / "_faltantes.csv"
        with rel.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["doi", "titulo", "motivo", "url"],
                               delimiter=";")
            w.writeheader()
            w.writerows(faltantes)

    total = max(1, len(regs))
    print("\n" + "=" * 70)
    print(f"  Baixados ......... {baixados} ({100*baixados/total:.0f}%)")
    print(f"  Ja existiam ...... {pulados}")
    print(f"  Nao obtidos ...... {falhas} ({100*falhas/total:.0f}%)")
    if faltantes:
        motivos = {}
        for f_ in faltantes:
            motivos[f_["motivo"]] = motivos.get(f_["motivo"], 0) + 1
        print("\n  Por que nao vieram:")
        for m, n in sorted(motivos.items(), key=lambda x: -x[1])[:6]:
            print(f"    {n:>5}  {m}")
        print(f"\n  Lista para busca manual: {destino / '_faltantes.csv'}")
        print("  Use o acesso institucional (Portal CAPES) para esses.")
    print(f"\n  Arquivos em: {destino}")


if __name__ == "__main__":
    main()
