# -*- coding: utf-8 -*-
"""
gerador_dossie.py
Gera Capa + Documentos do Drive (PDF/Imagens) + Encerramento com LGPD
em um único PDF mantido em memória RAM.
"""

import io
from datetime import datetime
from PIL import Image
from pypdf import PdfWriter, PdfReader

# ReportLab para geração das páginas de Capa e Encerramento
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
ID_RAIZ = "1NaZ7kv_jHVCTlLV8vqxCzBwbTX5y3fR7"

# Cores da Identidade Visual
COR_DOURADO = colors.HexColor("#d4af37")
COR_FUNDO_ESCURO = colors.HexColor("#0e1117")
COR_TEXTO_CLARO = colors.HexColor("#f7f5ef")
COR_CINZA_TEXTO = colors.HexColor("#8b949e")


# =============================================================================
# GERADORES DE CAPA E ENCERRAMENTO (REPORTLAB)
# =============================================================================

def gerar_capa_pdf_bytes(codigo_imovel, dados_imovel=None):
    """Cria a página de Capa do Dossiê com Aviso LGPD em memória RAM."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    style_titulo_empresa = ParagraphStyle(
        'EmpresaStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=COR_DOURADO,
        alignment=1, # Centralizado
        spaceAfter=5
    )
    
    style_sub_empresa = ParagraphStyle(
        'SubEmpresaStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        textColor=COR_CINZA_TEXTO,
        alignment=1,
        spaceAfter=30
    )

    style_titulo_dossie = ParagraphStyle(
        'DossieStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#161b22"),
        alignment=1,
        spaceAfter=15
    )

    style_info = ParagraphStyle(
        'InfoStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=16,
        textColor=colors.HexColor("#333333"),
        alignment=1,
        spaceAfter=20
    )

    style_lgpd_titulo = ParagraphStyle(
        'LgpdTitulo',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=colors.HexColor("#da3633"),
        spaceAfter=4
    )

    style_lgpd_texto = ParagraphStyle(
        'LgpdTexto',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#444444")
    )

    bairro = dados_imovel.get("bairro", "") if dados_imovel else ""
    cidade = dados_imovel.get("cidade", "") if dados_imovel else ""
    tipo = dados_imovel.get("tipo", "Imóvel") if dados_imovel else "Imóvel"
    data_hoje = datetime.now().strftime("%d/%m/%Y")

    elements = [
        Spacer(1, 40),
        Paragraph("CARVALHO FERREIRA", style_titulo_empresa),
        Paragraph("SOLUÇÕES IMOBILIÁRIAS", style_sub_empresa),
        HRFlowable(width="100%", thickness=2, color=COR_DOURADO, spaceAfter=50),
        
        Paragraph("DOSSIÊ DOCUMENTAL DO IMÓVEL", style_titulo_dossie),
        Paragraph(f"<b>CÓDIGO DO IMÓVEL:</b> {codigo_imovel.upper()}", style_info),
        Paragraph(f"<b>TIPO:</b> {tipo} | <b>LOCALIZAÇÃO:</b> {bairro} - {cidade}", style_info),
        Paragraph(f"<b>DATA DE EMISSÃO:</b> {data_hoje}", style_info),
        
        Spacer(1, 100),
        HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=15),
        
        # AVISO DE ATENÇÃO / LGPD
        Paragraph("⚠️ AVISO DE CONFIDENCIALIDADE E LGPD (Lei nº 13.709/2018)", style_lgpd_titulo),
        Paragraph(
            "Este documento contém informações estritamente confidenciais e dados pessoais protegidos "
            "pela Lei Geral de Proteção de Dados (LGPD). O acesso, cópia, distribuição ou uso não autorizado "
            "destes documentos é expressamente proibido. Este dossiê destina-se exclusivamente à análise "
            "imobiliária e jurídica entre as partes interessadas na transação comercial.",
            style_lgpd_texto
        )
    ]

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def gerar_encerramento_pdf_bytes():
    """Cria a página de Encerramento com contatos dos corretores."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    styles = getSampleStyleSheet()

    style_titulo = ParagraphStyle(
        'TituloEnd',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=COR_DOURADO,
        alignment=1,
        spaceAfter=20
    )

    style_corretor = ParagraphStyle(
        'CorretorStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1f2937"),
        alignment=1,
        spaceAfter=5
    )

    style_texto = ParagraphStyle(
        'TextoEnd',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#555555"),
        alignment=1,
        spaceAfter=15
    )

    elements = [
        Spacer(1, 150),
        Paragraph("ATENDIMENTO E CONSULTORIA", style_titulo),
        HRFlowable(width="60%", thickness=1, color=COR_DOURADO, spaceAfter=30),
        
        Paragraph("<b>Fernando</b>", style_corretor),
        Paragraph("WhatsApp: (12) 98816-2626", style_texto),
        
        Spacer(1, 10),
        
        Paragraph("<b>Valdir</b>", style_corretor),
        Paragraph("WhatsApp: (12) 99215-7474", style_texto),
        
        Spacer(1, 40),
        HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=20),
        Paragraph("Carvalho Ferreira Soluções Imobiliárias • Todos os direitos reservados", style_texto)
    ]

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


# =============================================================================
# INTEGRATION & GOOGLE DRIVE
# =============================================================================

def buscar_id_por_nome(service, nome_item, id_pasta_pai):
    if not service or not id_pasta_pai:
        return None
    query = f"'{id_pasta_pai}' in parents and name = '{nome_item}' and trashed = false"
    try:
        results = service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get("files", [])
        return files[0]["id"] if files else None
    except Exception:
        return None

def buscar_pasta_imovel(service, codigo_imovel, id_pasta_imoveis):
    if not service or not id_pasta_imoveis:
        return None
    codigo = codigo_imovel.strip().upper()
    query = f"'{id_pasta_imoveis}' in parents and mimeType = 'application/vnd.google-apps.folder' and name contains '{codigo}' and trashed = false"
    try:
        results = service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get("files", [])
        if not files:
            return None
        return files[0]["id"]
    except Exception:
        return None

def localizar_pasta_documentacao(service, codigo_imovel):
    id_portfolio = buscar_id_por_nome(service, "PORTFOLIO", ID_RAIZ)
    if not id_portfolio:
        return None
    id_imoveis = buscar_id_por_nome(service, "IMOVEIS", id_portfolio)
    if not id_imoveis:
        return None
    id_imovel = buscar_pasta_imovel(service, codigo_imovel, id_imoveis)
    if not id_imovel:
        return None

    id_doc = buscar_id_por_nome(service, "DOCUMENTOS", id_imovel)
    if not id_doc:
        id_doc = buscar_id_por_nome(service, "DOCUMENTAÇÃO", id_imovel)
    return id_doc if id_doc else id_imovel

def listar_arquivos(service, id_pasta):
    query = f"'{id_pasta}' in parents and trashed = false and (mimeType = 'application/pdf' or mimeType = 'image/jpeg' or mimeType = 'image/png')"
    try:
        results = service.files().list(q=query, fields="files(id, name, mimeType)", orderBy="name").execute()
        return results.get("files", [])
    except Exception:
        return []

def baixar_bytes(service, file_id):
    try:
        request = service.files().get_media(fileId=file_id)
        memoria = io.BytesIO()
        downloader = MediaIoBaseDownload(memoria, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        memoria.seek(0)
        return memoria.getvalue()
    except Exception:
        return None

def imagem_para_pdf_bytes(conteudo_imagem):
    img = Image.open(io.BytesIO(conteudo_imagem))
    if img.mode != "RGB":
        img = img.convert("RGB")
    out = io.BytesIO()
    img.save(out, format="PDF")
    out.seek(0)
    return out.getvalue()


# =============================================================================
# FUNÇÃO PRINCIPAL DE GERAR O DOSSIÊ
# =============================================================================

def criar_dossie_consolidado(creds_dict, codigo_imovel, dados_imovel=None):
    creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    drive_service = build("drive", "v3", credentials=creds)

    id_pasta = localizar_pasta_documentacao(drive_service, codigo_imovel)
    if not id_pasta:
        return None, "Pasta do imóvel não localizada no Google Drive."

    arquivos = listar_arquivos(drive_service, id_pasta)
    if not arquivos:
        return None, "Nenhum arquivo (PDF/Imagem) encontrado na pasta de documentos."

    merger = PdfWriter()

    # 1. ANEXAR A CAPA COM LGPD
    capa_bytes = gerar_capa_pdf_bytes(codigo_imovel, dados_imovel)
    capa_reader = PdfReader(io.BytesIO(capa_bytes))
    for page in capa_reader.pages:
        merger.add_page(page)

    # 2. ANEXAR DOCUMENTOS DO GOOGLE DRIVE
    processados = 0
    for arq in arquivos:
        conteudo = baixar_bytes(drive_service, arq["id"])
        if not conteudo:
            continue
        try:
            if arq["mimeType"] == "application/pdf":
                reader = PdfReader(io.BytesIO(conteudo))
                for page in reader.pages:
                    merger.add_page(page)
                processados += 1
            elif arq["mimeType"] in ["image/jpeg", "image/png"]:
                img_pdf = imagem_para_pdf_bytes(conteudo)
                reader = PdfReader(io.BytesIO(img_pdf))
                for page in reader.pages:
                    merger.add_page(page)
                processados += 1
        except Exception as e:
            print(f"Erro ao anexar {arq['name']}: {e}")

    # 3. ANEXAR PÁGINA FINAL DE ENCERRAMENTO
    encerramento_bytes = gerar_encerramento_pdf_bytes()
    enc_reader = PdfReader(io.BytesIO(encerramento_bytes))
    for page in enc_reader.pages:
        merger.add_page(page)

    # EXPORTAR EM MEMÓRIA RAM
    pdf_final = io.BytesIO()
    merger.write(pdf_final)
    merger.close()
    pdf_final.seek(0)

    return pdf_final.getvalue(), f"Dossiê gerado com sucesso! ({processados} arquivos unificados)"
