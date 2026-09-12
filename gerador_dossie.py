# -*- coding: utf-8 -*-
"""
gerador_dossie.py
Gera o Dossiê Documental (Gerador C / VECÃO) unificando arquivos (PDFs e Imagens) 
da subpasta DOCUMENTOS no Google Drive, adicionando capa e página de encerramento/LGPD.
"""

import io
import re
import unicodedata
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from pypdf import PdfReader, PdfWriter
from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]

ID_RAIZ = "1NaZ7kv_jHVCTlLV8vqxCzBwbTX5y3fR7"


# ==========================================
# FUNÇÕES DE NORMALIZAÇÃO E LIMPEZA DE TEXTO
# ==========================================

def normalizar_texto(texto):
    """Remove acentos, converte para maiúsculas e remove espaços extras."""
    if not texto:
        return ""
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return " ".join(texto.upper().split())


def extrair_codigo_chave(texto):
    """
    Extrai e padroniza o código do imóvel (ex: 'cf007 - casa continental' -> 'CF007').
    Funciona para formatos variados como CF007, CF 007, CF-007, C01, etc.
    """
    if not texto:
        return ""
    texto_norm = normalizar_texto(texto)
    
    # Busca padrão de 1 a 4 letras seguidas de 1 a 4 números
    match = re.search(r'([A-Z]{1,4}\s*[-_]?\s*\d{1,4})', texto_norm)
    if match:
        return re.sub(r'[^A-Z0-9]', '', match.group(1))
    
    return re.sub(r'[^A-Z0-9]', '', texto_norm)


# ==========================================
# CONEXÃO E NAVEGAÇÃO ROBUSTA NO GOOGLE DRIVE
# ==========================================

def conectar_google():
    """Autentica via st.secrets['google_credentials']."""
    try:
        import streamlit as st
        creds_dict = dict(st.secrets["google_credentials"])
        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=SCOPES
        )
        drive = build("drive", "v3", credentials=creds)
        sheets = build("sheets", "v4", credentials=creds)
        return drive, sheets
    except Exception as e:
        print(f"Erro ao autenticar no Google: {e}", flush=True)
        return None, None


def listar_subpastas(service, id_pasta_pai):
    """Retorna todas as subpastas ativas dentro de uma pasta pai."""
    if not service or not id_pasta_pai:
        return []

    query = (
        f"'{id_pasta_pai}' in parents "
        f"and mimeType = 'application/vnd.google-apps.folder' "
        f"and trashed = false"
    )

    try:
        results = service.files().list(
            q=query,
            fields="files(id, name)",
            pageSize=1000,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()

        return results.get("files", [])
    except Exception as e:
        print(f"Erro ao listar subpastas do pai '{id_pasta_pai}': {e}", flush=True)
        return []


def buscar_id_por_nome(service, nome_item, id_pasta_pai):
    """Busca uma pasta tolerando diferenças de acentuação e maiúsculas/minúsculas."""
    subpastas = listar_subpastas(service, id_pasta_pai)
    alvo = normalizar_texto(nome_item)

    for f in subpastas:
        if normalizar_texto(f["name"]) == alvo:
            return f["id"]

    for f in subpastas:
        nome_f = normalizar_texto(f["name"])
        if alvo in nome_f or nome_f in alvo:
            return f["id"]

    return None


def buscar_pasta_imovel_por_codigo(service, codigo_imovel, id_pasta_imoveis):
    """
    Localiza a pasta do imóvel no Drive isolando a sigla/código principal.
    Suporta entradas como 'cf007', 'CF007', 'cf007 - casa continental', 'CF 007'.
    """
    subpastas = listar_subpastas(service, id_pasta_imoveis)
    cod_chave = extrair_codigo_chave(codigo_imovel)

    if not cod_chave:
        return None

    # 1. Busca por código chave exato (ex: 'CF007' == 'CF007')
    for f in subpastas:
        if extrair_codigo_chave(f["name"]) == cod_chave:
            return f["id"]

    # 2. Busca por prefixo ou inclusão parcial
    for f in subpastas:
        nome_limpo = extrair_codigo_chave(f["name"])
        if nome_limpo.startswith(cod_chave) or cod_chave in nome_limpo:
            return f["id"]

    return None


def obter_id_pasta_documentos(service, codigo_imovel):
    """
    Navega na hierarquia (PORTFOLIO -> IMOVEIS -> [PASTA_IMOVEL] -> DOCUMENTOS).
    """
    id_portfolio = buscar_id_por_nome(service, "PORTFOLIO", ID_RAIZ)
    if not id_portfolio:
        print("Pasta 'PORTFOLIO' não encontrada.", flush=True)
        return None

    id_imoveis = buscar_id_por_nome(service, "IMOVEIS", id_portfolio)
    if not id_imoveis:
        print("Pasta 'IMOVEIS' não encontrada.", flush=True)
        return None

    id_imovel = buscar_pasta_imovel_por_codigo(service, codigo_imovel, id_imoveis)
    if not id_imovel:
        print(f"Pasta do imóvel para '{codigo_imovel}' não encontrada.", flush=True)
        return None

    # Tenta encontrar a subpasta 'DOCUMENTOS' ou variações comuns
    id_documentos = buscar_id_por_nome(service, "DOCUMENTOS", id_imovel)
    if not id_documentos:
        id_documentos = buscar_id_por_nome(service, "DOCUMENTO", id_imovel)
    if not id_documentos:
        id_documentos = buscar_id_por_nome(service, "DOCS", id_imovel)

    return id_documentos


def baixar_bytes(service, id_arquivo):
    """Baixa o conteúdo de um arquivo do Drive diretamente para a memória RAM."""
    try:
        request = service.files().get_media(fileId=id_arquivo)
        memoria = io.BytesIO()
        downloader = MediaIoBaseDownload(memoria, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        memoria.seek(0)
        return memoria.getvalue()
    except Exception as e:
        print(f"Erro ao baixar arquivo {id_arquivo}: {e}", flush=True)
        return None


# ==========================================
# GERADORES DE PÁGINAS REPORTLAB (MEMÓRIA)
# ==========================================

def criar_pagina_capa(codigo_imovel):
    """Gera a capa do Dossiê Documental usando ReportLab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=50, bottomMargin=50)
    story = []
    styles = getSampleStyleSheet()

    titulo_style = ParagraphStyle(
        'CapaTitulo',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        textColor=colors.HexColor("#06192A"),
        spaceAfter=15,
        alignment=1
    )

    subtitulo_style = ParagraphStyle(
        'CapaSubtitulo',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=14,
        textColor=colors.HexColor("#4A5568"),
        spaceAfter=30,
        alignment=1
    )

    story.append(Spacer(1, 150))
    story.append(Paragraph("DOSSIÊ DOCUMENTAL", titulo_style))
    story.append(Paragraph(f"IMÓVEL REF: {codigo_imovel.upper()}", subtitulo_style))
    story.append(Spacer(1, 40))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def criar_pagina_encerramento():
    """Gera a página final de encerramento com Termos e LGPD."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=50, bottomMargin=50)
    story = []
    styles = getSampleStyleSheet()

    titulo_style = ParagraphStyle(
        'EncTitulo',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        textColor=colors.HexColor("#06192A"),
        spaceAfter=15
    )

    corpo_style = ParagraphStyle(
        'EncCorpo',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor("#2D3748"),
        leading=14,
        spaceAfter=10
    )

    story.append(Spacer(1, 40))
    story.append(Paragraph("AVISO DE CONFIDENCIALIDADE E LGPD", titulo_style))
    story.append(Paragraph(
        "Este documento e seus anexos contêm informações confidenciais destinadas exclusivamente "
        "ao uso do destinatário autorizado. O tratamento dos dados aqui contidos cumpre as disposições "
        "da Lei Geral de Proteção de Dados (Lei nº 13.709/2018).", corpo_style
    ))
    story.append(Spacer(1, 20))
    story.append(Paragraph("<b>CARVALHO FERREIRA CONSULTORIA IMOBILIÁRIA</b>", corpo_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def converter_imagem_para_pdf_bytes(imagem_bytes):
    """Converte imagens (JPG, PNG) baixadas do Drive para PDF em formato A4."""
    try:
        img = Image.open(io.BytesIO(imagem_bytes))
        if img.mode != 'RGB':
            img = img.convert('RGB')

        pdf_buffer = io.BytesIO()
        img.save(pdf_buffer, format='PDF', resolution=100.0)
        pdf_buffer.seek(0)
        return pdf_buffer.getvalue()
    except Exception as e:
        print(f"Erro ao converter imagem para PDF: {e}", flush=True)
        return None


# ==========================================
# FLUXO PRINCIPAL: CONSOLIDAÇÃO DO DOSSIÊ
# ==========================================

def gerar_dossie_documental(codigo_imovel):
    """
    Função principal do Gerador C:
    Busca a pasta DOCUMENTOS, consolida PDFs e Imagens, adiciona Capa e Encerramento.
    Retorna os bytes do PDF unificado em memória RAM.
    """
    drive, _ = conectar_google()
    if not drive:
        return None

    codigo_imovel = str(codigo_imovel).strip()

    # 1. Localiza a subpasta DOCUMENTOS do imóvel
    id_pasta_docs = obter_id_pasta_documentos(drive, codigo_imovel)
    if not id_pasta_docs:
        print(f"Pasta DOCUMENTOS não encontrada para '{codigo_imovel}'.", flush=True)
        return None

    # 2. Lista os arquivos dentro da subpasta DOCUMENTOS
    try:
        resposta = drive.files().list(
            q=f"'{id_pasta_docs}' in parents and trashed = false",
            fields="files(id, name, mimeType)",
            orderBy="name",
            pageSize=1000,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        arquivos = resposta.get("files", [])
    except Exception as e:
        print(f"Erro ao listar documentos no Drive: {e}", flush=True)
        return None

    if not arquivos:
        print("Nenhum documento encontrado na pasta DOCUMENTOS.", flush=True)
        return None

    writer = PdfWriter()

    # 3. Adiciona a Capa
    bytes_capa = criar_pagina_capa(codigo_imovel)
    writer.append(PdfReader(io.BytesIO(bytes_capa)))

    # 4. Processa e unifica os arquivos da pasta DOCUMENTOS
    for arq in arquivos:
        mime = arq.get("mimeType", "")
        arq_bytes = baixar_bytes(drive, arq["id"])
        if not arq_bytes:
            continue

        if mime == "application/pdf":
            try:
                reader = PdfReader(io.BytesIO(arq_bytes))
                for page in reader.pages:
                    writer.add_page(page)
            except Exception as e:
                print(f"Erro ao anexar PDF {arq['name']}: {e}", flush=True)

        elif mime.startswith("image/"):
            img_pdf_bytes = converter_imagem_para_pdf_bytes(arq_bytes)
            if img_pdf_bytes:
                reader = PdfReader(io.BytesIO(img_pdf_bytes))
                for page in reader.pages:
                    writer.add_page(page)

    # 5. Adiciona a Página de Encerramento (LGPD)
    bytes_encerramento = criar_pagina_encerramento()
    writer.append(PdfReader(io.BytesIO(bytes_encerramento)))

    # 6. Gera o PDF final em memória (RAM)
    saida_buffer = io.BytesIO()
    writer.write(saida_buffer)
    saida_buffer.seek(0)

    return saida_buffer.getvalue()
