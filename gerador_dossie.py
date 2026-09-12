# -*- coding: utf-8 -*-
"""
gerador_dossie.py
Gera o Dossiê Documental unificando arquivos (PDFs e Imagens) da subpasta DOCUMENTOS
no Google Drive, gerando capa, resumo LGPD e encerramento em memória.
"""

import io
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
# CONEXÃO E NAVEGAÇÃO NO GOOGLE DRIVE
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


def buscar_id_por_nome(service, nome_item, id_pasta_pai):
    """Busca pasta aceitando nome exato ou termo contido (ex: IMOVEIS / IMOVEIS DISSOLUCAO)."""
    if not service or not id_pasta_pai:
        return None

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

        files = results.get("files", [])
        nome_busca = nome_item.strip().upper()

        # Match exato
        for f in files:
            if f["name"].strip().upper() == nome_busca:
                return f["id"]

        # Match parcial
        for f in files:
            if nome_busca in f["name"].strip().upper():
                return f["id"]

        return None
    except Exception as e:
        print(f"Erro ao buscar '{nome_item}': {e}", flush=True)
        return None


def buscar_pasta_imovel_por_codigo(service, codigo_imovel, id_pasta_imoveis):
    """Localiza a pasta do imóvel sem problemas de maiúsculas/minúsculas."""
    if not service or not id_pasta_imoveis:
        return None

    codigo = codigo_imovel.strip().upper()

    query = (
        f"'{id_pasta_imoveis}' in parents "
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

        files = results.get("files", [])

        for f in files:
            nome = f["name"].strip().upper()
            if (
                nome == codigo
                or nome.startswith(codigo + " ")
                or nome.startswith(codigo + "-")
                or nome.startswith(codigo + "_")
            ):
                return f["id"]

        return None
    except Exception as e:
        print(f"Erro ao buscar pasta do imovel '{codigo_imovel}': {e}", flush=True)
        return None


def obter_id_pasta_documentos(service, codigo_imovel):
    """Busca a subpasta 'DOCUMENTOS' dentro do imóvel."""
    id_portfolio = buscar_id_por_nome(service, "PORTFOLIO", ID_RAIZ)
    if not id_portfolio:
        return None

    id_imoveis = buscar_id_por_nome(service, "IMOVEIS", id_portfolio)
    if not id_imoveis:
        return None

    id_imovel = buscar_pasta_imovel_por_codigo(service, codigo_imovel, id_imoveis)
    if not id_imovel:
        return None

    id_documentos = buscar_id_por_nome(service, "DOCUMENTOS", id_imovel)
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
    Retorna os bytes do PDF unificado em memória.
    """
    drive, _ = conectar_google()
    if not drive:
        return None

    codigo_imovel = str(codigo_imovel).strip().upper()

    # 1. Localiza a subpasta DOCUMENTOS do imóvel
    id_pasta_docs = obter_id_pasta_documentos(drive, codigo_imovel)
    if not id_pasta_docs:
        print(f"Pasta DOCUMENTOS não encontrada para o código {codigo_imovel}.", flush=True)
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
                print(f"Erro ao anexa PDF {arq['name']}: {e}", flush=True)

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
