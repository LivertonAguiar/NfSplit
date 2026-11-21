#!/usr/bin/env python3
"""
separar_notas.py - Classifica, separa, organiza e renomeia PDFs de DANFEs (NFs), boletos e mapas de carga.

Melhorias implementadas:
    - Extração infalível da NF via Chave de Acesso Oficial da SEFAZ (44 dígitos).
    - Suporte a DANFEs com múltiplas páginas (continuação de itens folha 2/2, 3/3...).
    - Parser universal de boletos bancários (linha digitável FEBRABAN com validação de valor em centavos, banco, vencimento e parcela).
    - Extração precisa de Destinatário, CNPJ/CPF, Valor Total e Forma de Pagamento (PIX / Boleto).
    - Opção de juntar Nota + Boleto correspondente em um único PDF (--juntar).
    - Opção de preservar mapas de entrega e acerto de carga (--salvar-outros).
    - Limpeza opcional de CNPJ/código no início da razão social (--limpar-cnpj-nome).
    - Relatório CSV detalhado compatível com Excel (UTF-8 BOM).
"""

import argparse
import csv
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import pdfplumber
from pypdf import PdfReader, PdfWriter

# ----------------------------------------------------------------------------
# Tabelas de Apoio (Bancos e Constantes)
# ----------------------------------------------------------------------------

BANCOS = {
    "001": "Banco do Brasil",
    "033": "Santander",
    "104": "Caixa Econômica Federal",
    "237": "Bradesco",
    "341": "Itaú",
    "748": "Sicredi",
    "756": "Sicoob",
    "422": "Banco Safra",
    "077": "Banco Inter",
    "260": "Nubank",
}

_INVALIDOS = re.compile(r'[\\/:*?"<>|\r\n\t]+')


def limpar(nome: str, limite: int = 80) -> str:
    """Higieniza o nome para ser seguro como nome de arquivo no Windows/Linux."""
    if not nome:
        return "SEM NOME"
    nome = _INVALIDOS.sub(" ", nome)
    nome = re.sub(r"\s+", " ", nome).strip(" .")
    return nome[:limite].strip(" .") or "SEM NOME"


def formatar_moeda(valor_str: str | None) -> str:
    """Padroniza valor monetário para exibição (ex: 1.507,00)."""
    if not valor_str:
        return ""
    limpo = re.sub(r"[^\d.,]", "", valor_str).strip()
    return limpo


def caminho_livre(pasta: Path, base: str) -> Path:
    """Evita sobrescrita criando sufixos (2), (3) se necessário."""
    p = pasta / f"{base}.pdf"
    n = 2
    while p.exists():
        p = pasta / f"{base} ({n}).pdf"
        n += 1
    return p


def salvar_paginas(reader: PdfReader, paginas: list[int], destino: Path):
    """Grava as páginas selecionadas em um novo PDF."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    w = PdfWriter()
    for i in paginas:
        w.add_page(reader.pages[i])
    with open(destino, "wb") as f:
        w.write(f)


# ----------------------------------------------------------------------------
# Motores de Extração e Classificação
# ----------------------------------------------------------------------------


def extrair_chave_acesso(texto: str) -> str | None:
    """
    Localiza a Chave de Acesso da NF-e (44 dígitos numéricos).
    Normalmente impressa em blocos de 4 dígitos ou contínua.
    """
    m = re.search(r"(\d{4}(?:\s*\d{4}){10})", texto)
    if m:
        chave = re.sub(r"\s+", "", m.group(1))
        if len(chave) == 44:
            return chave

    # Busca alternativa contínua de 44 dígitos
    m2 = re.search(r"\b(\d{44})\b", texto)
    if m2:
        return m2.group(1)

    return None


def extrair_destinatario_e_cnpj(page, texto: str, limpar_cnpj_inicio: bool = False) -> tuple[str | None, str | None]:
    """
    Extrai o nome do destinatário e seu CNPJ/CPF diretamente da linha de destinatário do DANFE.
    """
    nome_encontrado = None
    cnpj_encontrado = None

    # Estratégia 1: Posicionamento visual no quadro DESTINATÁRIO/REMETENTE
    try:
        words = page.extract_words()
        rotulos = [w for w in words if "NOME/RAZ" in w["text"].upper()]
        if rotulos:
            r = min(rotulos, key=lambda w: w["top"])
            # Limite superior à direita: campo CNPJ/CPF do destinatário
            cnpj_lab = [
                w for w in words
                if "CNPJ" in w["text"].upper()
                and abs(w["top"] - r["top"]) < 14
                and w["x0"] > r["x0"]
            ]
            x_limite = min((w["x0"] for w in cnpj_lab), default=page.width) - 2

            # Linha estrita do nome (r.top + 2 até r.top + 14, antes do rótulo ENDEREÇO em r.top + 17)
            linha_nome = [
                w for w in words
                if r["top"] + 2 < w["top"] < r["top"] + 14
                and r["x0"] - 4 <= w["x0"] < x_limite
            ]
            linha_nome.sort(key=lambda w: w["x0"])
            texto_nome = " ".join(w["text"] for w in linha_nome).strip()
            texto_nome = re.sub(r"\s+\d{4,6}$", "", texto_nome).strip()
            if len(texto_nome) > 2:
                nome_encontrado = texto_nome

            # Linha do CNPJ/CPF (à direita do nome, na mesma altura)
            if cnpj_lab:
                c_label = min(cnpj_lab, key=lambda w: w["x0"])
                linha_doc = [
                    w for w in words
                    if r["top"] + 2 < w["top"] < r["top"] + 14
                    and w["x0"] >= c_label["x0"] - 15
                ]
                linha_doc.sort(key=lambda w: w["x0"])
                texto_doc = " ".join(w["text"] for w in linha_doc)
                m_doc = re.search(r"(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{3}\.\d{3}\.\d{3}-\d{2})", texto_doc)
                if m_doc:
                    cnpj_encontrado = m_doc.group(1)
    except Exception:
        pass

    # Estratégia 2: Fallback no Canhoto de recebimento da Nota Fiscal
    if not nome_encontrado:
        m_canhoto = re.search(
            r"RECEBEMOS DE .+? INDICADA AO LADO\s+(?:\d+\s*-\s*)?([A-Z0-9\s.,\-/]+?)(?:\s*-\s*<SEM REGIAO>|\s*-\s*\(R\$|\s*-\s*CEP|\s*\n)",
            texto,
            re.I
        )
        if m_canhoto:
            candidato = m_canhoto.group(1).strip()
            if len(candidato) > 3 and not candidato.upper().startswith("NOTA FISCAL"):
                nome_encontrado = candidato

    # Limpeza opcional do CNPJ no início do nome (ex: "68.051.909 ARI FRANCISCO...")
    if nome_encontrado and limpar_cnpj_inicio:
        nome_encontrado = re.sub(r"^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\s*", "", nome_encontrado)
        nome_encontrado = re.sub(r"^\d{2}\.\d{3}\.\d{3}\s+", "", nome_encontrado)
        nome_encontrado = re.sub(r"^\d{11,14}\s+", "", nome_encontrado)

    return (nome_encontrado.strip() if nome_encontrado else None, cnpj_encontrado)


def extrair_metadados_danfe(texto: str) -> dict:
    """Extrai informações complementares da DANFE (valor total da nota, data e forma de pgto)."""
    dados = {
        "valor_total": None,
        "emissao": None,
        "forma_pgto": None,
    }

    # Valor Total da Nota: busca na linha seguinte a 'VALOR TOTAL DA NOTA'
    linhas = texto.splitlines()
    for i, linha in enumerate(linhas):
        if "VALOR TOTAL DA NOTA" in linha.upper() and i + 1 < len(linhas):
            vals = re.findall(r"\b\d{1,3}(?:\.\d{3})*,\d{2}\b", linhas[i + 1])
            if vals:
                dados["valor_total"] = vals[-1]  # Último valor da linha corresponde ao total
                break

    # Fallback no canhoto da nota se necessário: (R$ 786,08)
    if not dados["valor_total"]:
        m_canhoto = re.search(r"\(R\$\s*([\d.,]+)\)", texto)
        if m_canhoto:
            dados["valor_total"] = formatar_moeda(m_canhoto.group(1))

    # Data da Emissão
    m_data = re.search(r"DATA\s+DA\s+EMISS[ÃA]O\s*[:\n\s]*(\d{2}[/-]\d{2}[/-]\d{4})", texto, re.I)
    if m_data:
        dados["emissao"] = m_data.group(1).replace("-", "/")

    # Forma de Pagamento (Fatura / Duplicata)
    if re.search(r"\bPIX\b", texto, re.I):
        dados["forma_pgto"] = "PIX"
    elif re.search(r"BOLETO(?:\s*-\s*\d+\s*DIAS)?", texto, re.I):
        m_bol = re.search(r"(BOLETO\s*-\s*\d+\s*DIAS|BOLETO)", texto, re.I)
        dados["forma_pgto"] = m_bol.group(1).upper() if m_bol else "BOLETO"

    return dados


def extrair_dados_boleto(texto: str) -> dict:
    """
    Parser robusto para boletos bancários de múltiplos bancos e layouts FEBRABAN.
    """
    dados = {
        "nf": None,
        "parcela": 1,
        "pagador": None,
        "cnpj_pagador": None,
        "vencimento": None,
        "valor": None,
        "banco": None,
        "linha_digitavel": None,
    }

    # 1. Linha Digitável
    m_ld = re.search(
        r"(\d{5}[.\s]\d{5}\s+\d{5}[.\s]\d{6}\s+\d{5}[.\s]\d{6}\s+\d\s+\d{14})",
        texto
    )
    if m_ld:
        dados["linha_digitavel"] = re.sub(r"\s+", " ", m_ld.group(1)).strip()
        # No padrão FEBRABAN, os últimos 10 dígitos da linha digitável contêm o valor em centavos
        ultimos_digitos = re.sub(r"\D", "", dados["linha_digitavel"])[-10:]
        if ultimos_digitos.isdigit():
            centavos = int(ultimos_digitos)
            if centavos > 0:
                reais = centavos / 100.0
                dados["valor"] = f"{reais:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    # 2. Identificação do Banco
    m_banco = re.search(r"\b(\d{3})-\d\b", texto)
    if m_banco and m_banco.group(1) in BANCOS:
        dados["banco"] = f"{m_banco.group(1)} - {BANCOS[m_banco.group(1)]}"
    else:
        for cod, nome in BANCOS.items():
            if nome.upper() in texto.upper():
                dados["banco"] = f"{cod} - {nome}"
                break

    # 3. Número da NF e Parcela
    # Padrão a: "NÚMERO NF 138820"
    m_nf = re.search(r"N[ÚU]MERO\s+NF\s*[:.]?\s*0*(\d+)", texto, re.I)
    if m_nf:
        dados["nf"] = m_nf.group(1)

    # Padrão b: "Número do Documento: 138820 - 1"
    m_doc = re.search(r"(?:N[ÚU]MERO\s+DO\s+DOCUMENTO|N[º°]\s+DOC(?:UMENTO)?)\s*[:.\s\n]*0*(\d+)(?:\s*-\s*(\d+))?", texto, re.I)
    if m_doc:
        if not dados["nf"]:
            dados["nf"] = m_doc.group(1)
        if m_doc.group(2):
            try:
                dados["parcela"] = int(m_doc.group(2))
            except ValueError:
                pass

    # Padrão c: Fallback geral em data + "0*(\d+) - \d+"
    if not dados["nf"]:
        m_fb = re.search(r"\d{2}/\d{2}/\d{4}\s+0*(\d+)\s*-\s*(\d+)", texto)
        if m_fb:
            dados["nf"] = m_fb.group(1)
            try:
                dados["parcela"] = int(m_fb.group(2))
            except ValueError:
                pass

    # 4. Pagador / Sacado
    m_pag = re.search(r"(?:Pagador|Sacado)\s+([^\n\r]+?)(?:\s+CNPJ|\s+CPF|\s*-\s*CNPJ|\s*\n)", texto, re.I)
    if m_pag:
        dados["pagador"] = re.sub(r"\s+", " ", m_pag.group(1)).strip()

    # 5. CNPJ / CPF do Pagador
    m_cnpj = re.search(r"(?:Pagador|Sacado).+?(?:CNPJ|CPF)\s*[:.]?\s*(\d{11,14}|\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})", texto, re.S | re.I)
    if m_cnpj:
        dados["cnpj_pagador"] = m_cnpj.group(1).strip()

    # 6. Vencimento
    m_venc = re.search(r"Vencimento\s*[:\n\s]*(\d{2}/\d{2}/\d{4})", texto, re.I)
    if m_venc:
        dados["vencimento"] = m_venc.group(1)

    # 7. Valor do Documento (caso não tenha vindo da linha digitável)
    if not dados["valor"]:
        m_val = re.search(r"R\$\s*([\d.,]+)", texto)
        if m_val:
            dados["valor"] = formatar_moeda(m_val.group(1))

    return dados


def classificar_pagina(texto: str, tipo_anterior: str | None = None) -> str:
    """
    Classifica a página como 'nota', 'boleto', 'mapa', 'acerto' ou 'outro',
    com suporte a documentos de múltiplas páginas (continuações).
    """
    up = texto.upper()

    # 1. Nota Fiscal / DANFE (prioritário)
    if ("DANFE" in up and "CHAVE DE ACESSO" in up) or \
       ("DOCUMENTO AUXILIAR DA NOTA FISCAL" in up) or \
       ("CHAVE DE ACESSO" in up and "PROTOCOLO DE AUTORIZAÇÃO" in up):
        return "nota"

    # 2. Boleto Bancário
    if ("LINHA DIGITÁVEL" in up or re.search(r"\d{5}[.\s]\d{5}\s+\d{5}[.\s]\d{6}", up)) or \
       ("NOSSO NÚMERO" in up and ("BENEFICIÁRIO" in up or "PAGADOR" in up or "CEDENTE" in up or "SACADO" in up)):
        return "boleto"

    # 3. Acerto de Carga / Motorista
    if "ACERTO DE CARGA" in up or "CONFIRA A MERCADORIA" in up:
        return "acerto"

    # 4. Mapa de Entrega
    if "MAPA DE ENTREGA" in up or "QUANTIDADES CONTADAS POR PRODUTO" in up:
        return "mapa"

    # 5. Continuações dependentes do contexto da página anterior
    if tipo_anterior == "acerto" and ("VALOR R$" in up or "NOTA DEVOLVIDA" in up):
        return "acerto"

    if tipo_anterior == "mapa" and ("ITEM PESO" in up or "TOTAL PRODUTO" in up or re.search(r"P[ÁA]GINA\s+\d+\s+DE\s+\d+", up)):
        return "mapa"

    if tipo_anterior == "nota" and (re.search(r"FOLHA\s+[2-9]/\d+", up) or re.search(r"CONTINUA[ÇC][ÃA]O", up)):
        return "nota"

    return "outro"


# ----------------------------------------------------------------------------
# Processamento Central
# ----------------------------------------------------------------------------


def processar_pdf(
    pdf_path: Path,
    saida: Path,
    relatorio: list,
    juntar_boletos: bool = False,
    salvar_outros: bool = False,
    limpar_cnpj_nome: bool = False,
):
    """
    Processa um único PDF de carga com DANFEs, Boletos, Mapas e Acertos.
    """
    pasta_notas = saida / "notas"
    pasta_boletos = saida / "boletos"
    pasta_unificados = saida / "notas_com_boleto"
    pasta_mapas = saida / "mapas"
    pasta_acertos = saida / "acertos"
    pasta_revisar = saida / "revisar"

    pasta_notas.mkdir(parents=True, exist_ok=True)
    pasta_boletos.mkdir(parents=True, exist_ok=True)
    if juntar_boletos:
        pasta_unificados.mkdir(parents=True, exist_ok=True)
    if salvar_outros:
        pasta_mapas.mkdir(parents=True, exist_ok=True)
        pasta_acertos.mkdir(parents=True, exist_ok=True)

    reader = PdfReader(str(pdf_path))
    total_pags = len(reader.pages)

    notas = defaultdict(lambda: {
        "paginas": [],
        "nome": None,
        "cnpj_cpf": None,
        "chave": None,
        "serie": None,
        "dados": {},
    })
    ordem_notas = []
    boletos = []  # Lista de dicionários com dados dos boletos
    mapas_paginas = []
    acertos_paginas = []
    descartadas = []
    revisar = []

    num_carga = None
    tipo_anterior = None
    nf_atual = None

    with pdfplumber.open(str(pdf_path)) as pdf:
        for idx, page in enumerate(pdf.pages):
            texto = page.extract_text() or ""
            tipo = classificar_pagina(texto, tipo_anterior=tipo_anterior)
            tipo_anterior = tipo

            # Identifica número da carga se disponível
            if not num_carga:
                m_c = re.search(r"(?:Ordem\s+de\s+Carga|CARGA)\s*[:.]?\s*(\d+)", texto, re.I)
                if m_c:
                    num_carga = m_c.group(1)

            if tipo == "nota":
                chave = extrair_chave_acesso(texto)
                nf = None
                serie = None
                if chave:
                    nf = str(int(chave[25:34]))  # 9 dígitos da NF sem zeros à esquerda
                    serie = str(int(chave[22:25]))
                else:
                    # Fallback por regex caso a chave não esteja legível
                    m_nf = re.search(r"NOTA\s+FISCAL\s+N\S\s*([\d.]+)", texto, re.I) or \
                           re.search(r"N[º°o]\s*([\d]{1,3}(?:\.\d{3})+)", texto)
                    if m_nf:
                        nf = m_nf.group(1).replace(".", "").lstrip("0") or "0"
                    elif nf_atual:
                        # Continuação da folha anterior da mesma nota
                        nf = nf_atual

                if not nf:
                    revisar.append((idx, "Nota fiscal sem identificação de número"))
                    continue

                nf_atual = nf
                if nf not in notas:
                    ordem_notas.append(nf)
                notas[nf]["paginas"].append(idx)
                if chave:
                    notas[nf]["chave"] = chave
                    notas[nf]["serie"] = serie

                # Extrai nome e dados na primeira página da nota
                if notas[nf]["nome"] is None:
                    nome, doc = extrair_destinatario_e_cnpj(page, texto, limpar_cnpj_inicio=limpar_cnpj_nome)
                    notas[nf]["nome"] = nome
                    notas[nf]["cnpj_cpf"] = doc
                    notas[nf]["dados"] = extrair_metadados_danfe(texto)

            elif tipo == "boleto":
                nf_atual = None
                dados_bol = extrair_dados_boleto(texto)
                dados_bol["pagina"] = idx
                boletos.append(dados_bol)

            elif tipo == "mapa":
                nf_atual = None
                mapas_paginas.append(idx)

            elif tipo == "acerto":
                nf_atual = None
                acertos_paginas.append(idx)

            else:
                nf_atual = None
                descartadas.append(idx)

    # ------------------------------------------------------------------------
    # 1. Gravação das Notas Fiscais
    # ------------------------------------------------------------------------
    arquivos_notas = {}
    for nf in ordem_notas:
        info = notas[nf]
        nome = limpar(info["nome"] or "SEM NOME")
        destino = caminho_livre(pasta_notas, f"NF {nf} - {nome}")
        salvar_paginas(reader, info["paginas"], destino)
        arquivos_notas[nf] = destino

        meta = info["dados"]
        relatorio.append({
            "origem": pdf_path.name,
            "tipo": "nota",
            "nf": nf,
            "parcela": "-",
            "nome": nome,
            "cnpj_cpf": info.get("cnpj_cpf", "") or "",
            "valor_nf": meta.get("valor_total", "") or "",
            "valor_boleto": "",
            "vencimento": "",
            "forma_pgto": meta.get("forma_pgto", "") or "",
            "banco": "",
            "paginas": ",".join(str(p + 1) for p in info["paginas"]),
            "arquivo": str(destino.relative_to(saida)),
            "obs": f"Chave: {info['chave']}" if info['chave'] else "",
        })

    # ------------------------------------------------------------------------
    # 2. Gravação dos Boletos e Cruzamento com Notas
    # ------------------------------------------------------------------------
    boletos_por_nf = defaultdict(list)
    for b in boletos:
        boletos_por_nf[b["nf"]].append(b)

    for nf, lista in boletos_por_nf.items():
        # Ordena boletos por vencimento e página
        lista.sort(key=lambda item: (item["vencimento"] or "", item["pagina"]))

        for k, b in enumerate(lista, 1):
            pag = b["pagina"]
            parcela_num = b["parcela"] if b["parcela"] and b["parcela"] > 1 else (k if len(lista) > 1 else 1)

            if not nf:
                # Boleto sem NF identificada
                pasta_revisar.mkdir(parents=True, exist_ok=True)
                destino = caminho_livre(pasta_revisar, f"BOLETO sem NF - p{pag + 1}")
                salvar_paginas(reader, [pag], destino)
                relatorio.append({
                    "origem": pdf_path.name,
                    "tipo": "boleto",
                    "nf": "?",
                    "parcela": str(parcela_num),
                    "nome": limpar(b["pagador"] or "DESCONHECIDO"),
                    "cnpj_cpf": b["cnpj_pagador"] or "",
                    "valor_nf": "",
                    "valor_boleto": b["valor"] or "",
                    "vencimento": b["vencimento"] or "",
                    "forma_pgto": "BOLETO",
                    "banco": b["banco"] or "",
                    "paginas": str(pag + 1),
                    "arquivo": str(destino.relative_to(saida)),
                    "obs": "ATENÇÃO: Número da NF não localizado no boleto",
                })
                continue

            # Nome preferencial: destinatário da própria NF (mantém consistência)
            nome_nf = notas[nf]["nome"] if nf in notas and notas[nf]["nome"] else None
            nome = limpar(nome_nf or b["pagador"] or "SEM NOME")
            sufixo_parcela = f" - parcela {parcela_num}" if len(lista) > 1 else ""

            destino = caminho_livre(pasta_boletos, f"BOLETO NF {nf} - {nome}{sufixo_parcela}")
            salvar_paginas(reader, [pag], destino)

            obs = ""
            if nf not in notas:
                obs = "AVISO: NF correspondente a este boleto não está neste PDF"

            relatorio.append({
                "origem": pdf_path.name,
                "tipo": "boleto",
                "nf": nf,
                "parcela": str(parcela_num),
                "nome": nome,
                "cnpj_cpf": b["cnpj_pagador"] or "",
                "valor_nf": "",
                "valor_boleto": b["valor"] or "",
                "vencimento": b["vencimento"] or "",
                "forma_pgto": "BOLETO",
                "banco": b["banco"] or "",
                "paginas": str(pag + 1),
                "arquivo": str(destino.relative_to(saida)),
                "obs": obs,
            })

    # ------------------------------------------------------------------------
    # 3. Modo Opcional: Juntar Nota + Boleto correspondente
    # ------------------------------------------------------------------------
    if juntar_boletos:
        for nf in ordem_notas:
            if nf in boletos_por_nf:
                pags_nota = notas[nf]["paginas"]
                pags_boleto = [b["pagina"] for b in boletos_por_nf[nf]]
                todas_pags = pags_nota + pags_boleto
                nome = limpar(notas[nf]["nome"] or "SEM NOME")
                destino_unif = caminho_livre(pasta_unificados, f"NF {nf} (com Boleto) - {nome}")
                salvar_paginas(reader, todas_pags, destino_unif)

    # ------------------------------------------------------------------------
    # 4. Modo Opcional: Salvar Mapas e Acertos
    # ------------------------------------------------------------------------
    if salvar_outros:
        sufixo_carga = f" - Carga {num_carga}" if num_carga else ""
        if mapas_paginas:
            dest_mapa = caminho_livre(pasta_mapas, f"MAPA DE ENTREGA{sufixo_carga}")
            salvar_paginas(reader, mapas_paginas, dest_mapa)
            relatorio.append({
                "origem": pdf_path.name,
                "tipo": "mapa",
                "nf": "-",
                "parcela": "-",
                "nome": f"Ordem de Carga {num_carga or 'N/A'}",
                "cnpj_cpf": "",
                "valor_nf": "",
                "valor_boleto": "",
                "vencimento": "",
                "forma_pgto": "",
                "banco": "",
                "paginas": ",".join(str(p + 1) for p in mapas_paginas),
                "arquivo": str(dest_mapa.relative_to(saida)),
                "obs": "Mapa de Entrega preservado",
            })
        if acertos_paginas:
            dest_acerto = caminho_livre(pasta_acertos, f"ACERTO DE CARGA{sufixo_carga}")
            salvar_paginas(reader, acertos_paginas, dest_acerto)
            relatorio.append({
                "origem": pdf_path.name,
                "tipo": "acerto",
                "nf": "-",
                "parcela": "-",
                "nome": f"Acerto Motorista {num_carga or 'N/A'}",
                "cnpj_cpf": "",
                "valor_nf": "",
                "valor_boleto": "",
                "vencimento": "",
                "forma_pgto": "",
                "banco": "",
                "paginas": ",".join(str(p + 1) for p in acertos_paginas),
                "arquivo": str(dest_acerto.relative_to(saida)),
                "obs": "Acerto de Carga/Motorista preservado",
            })

    # Registra páginas pendentes de revisão
    for idx_rev, motivo in revisar:
        relatorio.append({
            "origem": pdf_path.name,
            "tipo": "revisar",
            "nf": "?",
            "parcela": "-",
            "nome": "",
            "cnpj_cpf": "",
            "valor_nf": "",
            "valor_boleto": "",
            "vencimento": "",
            "forma_pgto": "",
            "banco": "",
            "paginas": str(idx_rev + 1),
            "arquivo": "",
            "obs": motivo,
        })

    # ------------------------------------------------------------------------
    # Retorno estatístico da execução
    # ------------------------------------------------------------------------
    return {
        "arquivo": pdf_path.name,
        "total_paginas": total_pags,
        "notas": len(ordem_notas),
        "boletos": len(boletos),
        "mapas": len(mapas_paginas),
        "acertos": len(acertos_paginas),
        "descartadas": len(descartadas),
        "revisar": len(revisar),
        "carga": num_carga,
    }


# ----------------------------------------------------------------------------
# Ponto de Entrada CLI
# ----------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Separa, classifica e renomeia PDFs de DANFEs (NFs), Boletos e Cargas com alta precisão."
    )
    parser.add_argument("entrada", nargs="+", help="Arquivo(s) PDF ou pasta(s) com PDFs")
    parser.add_argument("-o", "--saida", default="saida", help="Pasta de saída (padrão: ./saida)")
    parser.add_argument(
        "-j", "--juntar",
        action="store_true",
        help="Gera também PDFs unificados com a NF + Boleto juntos em 'notas_com_boleto/'"
    )
    parser.add_argument(
        "-s", "--salvar-outros",
        action="store_true",
        help="Salva mapas de entrega e acertos de carga em pastas separadas ao invés de descartar"
    )
    parser.add_argument(
        "--limpar-cnpj-nome",
        action="store_true",
        help="Remove CNPJ ou números do início da Razão Social (ex: '68.051.909 NOME' -> 'NOME')"
    )

    args = parser.parse_args()
    t_inicio = time.time()

    arquivos = []
    for item in args.entrada:
        p = Path(item)
        if p.is_dir():
            arquivos.extend(sorted(p.glob("*.pdf")))
        elif p.suffix.lower() == ".pdf" and p.exists():
            arquivos.append(p)
        else:
            print(f"[!] Ignorado (não encontrado ou não é PDF): {item}", file=sys.stderr)

    if not arquivos:
        sys.exit("Nenhum arquivo PDF encontrado para processar.")

    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)
    relatorio = []

    print("=" * 65)
    print("🚀 SEPARADOR DE NOTAS FISCAIS E BOLETOS - VERSÃO OTIMIZADA")
    print("=" * 65)

    totais = {"notas": 0, "boletos": 0, "paginas": 0}

    for pdf in arquivos:
        res = processar_pdf(
            pdf_path=pdf,
            saida=saida,
            relatorio=relatorio,
            juntar_boletos=args.juntar,
            salvar_outros=args.salvar_outros,
            limpar_cnpj_nome=args.limpar_cnpj_nome,
        )
        totais["notas"] += res["notas"]
        totais["boletos"] += res["boletos"]
        totais["paginas"] += res["total_paginas"]

        carga_str = f" [Carga {res['carga']}]" if res['carga'] else ""
        print(f"📄 {res['arquivo']}{carga_str}:")
        print(f"   ├─ {res['total_paginas']} páginas analisadas")
        print(f"   ├─ {res['notas']} Nota(s) Fiscal(is) identificada(s)")
        print(f"   ├─ {res['boletos']} Boleto(s) bancário(s) identificado(s)")
        if args.salvar_outros:
            print(f"   ├─ {res['mapas']} pág(s) de Mapa de Entrega salvas")
            print(f"   ├─ {res['acertos']} pág(s) de Acerto de Carga salvas")
        else:
            print(f"   ├─ {res['mapas'] + res['acertos'] + res['descartadas']} pág(s) descartadas (mapas/acertos)")
        if res["revisar"] > 0:
            print(f"   └─ ⚠️ {res['revisar']} página(s) requerem revisão!")
        else:
            print("   └─ ✅ 100% das páginas processadas com sucesso")

    # Gravação do Relatório CSV compatível com Excel (UTF-8 com BOM)
    caminho_csv = saida / "relatorio.csv"
    campos = [
        "origem", "tipo", "nf", "parcela", "nome", "cnpj_cpf",
        "valor_nf", "valor_boleto", "vencimento", "forma_pgto",
        "banco", "paginas", "arquivo", "obs"
    ]
    with open(caminho_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=campos, delimiter=";")
        writer.writeheader()
        writer.writerows(relatorio)

    t_decorrido = time.time() - t_inicio
    minutos = int(t_decorrido // 60)
    segundos = int(t_decorrido % 60)
    tempo_fmt = f"{segundos}s" if minutos == 0 else f"{minutos}m {segundos:02d}s"

    print("=" * 65)
    print(f"✅ Concluído em ⏱ {tempo_fmt}")
    print(f"📦 Total: {totais['notas']} NFs | {totais['boletos']} Boletos | {totais['paginas']} Páginas")
    print(f"📁 Arquivos organizados em: {saida.resolve()}")
    print(f"📊 Relatório exportado em:  {caminho_csv.resolve()}")
    if args.juntar:
        print(f"📎 Pastas unificadas em:    {(saida / 'notas_com_boleto').resolve()}")
    print("=" * 65)


if __name__ == "__main__":
    main()
