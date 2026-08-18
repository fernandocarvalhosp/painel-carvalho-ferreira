# -*- coding: utf-8 -*-
"""
gerador_pdf.py
Gera o dossie em memoria (bytes). Sem upload no Drive. Sem interface.
"""
import base64
import io
import re
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from jinja2 import Template
import weasyprint

SCRIPT_DIR = Path(__file__).resolve().parent

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]

ID_RAIZ = "1NaZ7kv_jHVCTlLV8vqxCzBwbTX5y3fR7"
SPREADSHEET_ID = "1nVEpOZFYFKcq0MXtOwxn22nqxafmJBHnf6zhHQlyT8w"
NOME_ABA = "Imoveis"

PASTA_MARCA = SCRIPT_DIR / "marca"
PASTA_ICONES = PASTA_MARCA / "icones"
PASTA_LOGO = PASTA_MARCA / "logo"
PASTA_FONTES = PASTA_MARCA / "fontes"


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
    if not service or not id_pasta_pai:
        return None
    query = (
        f"'{id_pasta_pai}' in parents "
        f"and name = '{nome_item}' "
        f"and trashed = false"
    )
    try:
        results = service.files().list(
            q=query,
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()
        files = results.get("files", [])
        return files[0]["id"] if files else None
    except Exception as e:
        print(f"Erro ao buscar '{nome_item}': {e}", flush=True)
        return None


def buscar_pasta_imovel_por_codigo(service, codigo_imovel, id_pasta_imoveis):
    if not service or not id_pasta_imoveis:
        return None
    codigo = codigo_imovel.strip().upper()
    query = (
        f"'{id_pasta_imoveis}' in parents "
        f"and mimeType = 'application/vnd.google-apps.folder' "
        f"and name contains '{codigo}' "
        f"and trashed = false"
    )
    try:
        results = service.files().list(
            q=query,
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()
        files = results.get("files", [])
        if not files:
            return None
        for f in files:
            nome = f["name"].strip().upper()
            if (
                nome == codigo
                or nome.startswith(codigo + " ")
                or nome.startswith(codigo + "-")
            ):
                return f["id"]
        return files[0]["id"]
    except Exception as e:
        print(f"Erro ao buscar pasta do imovel '{codigo_imovel}': {e}", flush=True)
        return None


def obter_id_pasta_imovel(service, codigo_imovel):
    id_portfolio = buscar_id_por_nome(service, "PORTFOLIO", ID_RAIZ)
    if not id_portfolio:
        print("Pasta PORTFOLIO nao encontrada.", flush=True)
        return None
    id_imoveis = buscar_id_por_nome(service, "IMOVEIS", id_portfolio)
    if not id_imoveis:
        print("Pasta IMOVEIS nao encontrada.", flush=True)
        return None
    id_imovel = buscar_pasta_imovel_por_codigo(service, codigo_imovel, id_imoveis)
    if not id_imovel:
        print(f"Pasta do imovel '{codigo_imovel}' nao encontrada.", flush=True)
        return None
    return id_imovel


def baixar_bytes(service, id_arquivo):
    """Baixa arquivo do Drive direto para bytes (RAM)."""
    try:
        request = service.files().get_media(fileId=id_arquivo)
        memoria = io.BytesIO()
        downloader = MediaIoBaseDownload(memoria, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return memoria.getvalue()
    except Exception as e:
        print(f"Erro ao baixar arquivo {id_arquivo}: {e}", flush=True)
        return None


def bytes_para_data_uri(data, mime_type):
    if not data:
        return ""
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime_type};base64,{b64}"


def carregar_icone_local(nome_arquivo, cor=None):
    caminho = PASTA_ICONES / nome_arquivo
    if not caminho.exists():
        return ""
    svg = caminho.read_text(encoding="utf-8")
    if cor:
        for antigo in ("currentColor", "#000000", "#000", "black"):
            svg = svg.replace(antigo, cor)
    return svg


def buscar_logo_local():
    if not PASTA_LOGO.exists():
        return None
    extensoes = {".png", ".jpg", ".jpeg", ".svg", ".webp"}
    for arquivo in PASTA_LOGO.iterdir():
        if arquivo.is_file() and arquivo.suffix.lower() in extensoes:
            return arquivo.as_uri()
    return None


def fonte_local(subpasta, nome_arquivo):
    caminho = PASTA_FONTES / subpasta / nome_arquivo
    if caminho.exists():
        return caminho.as_uri()
    if PASTA_FONTES.exists():
        for encontrado in PASTA_FONTES.rglob(nome_arquivo):
            if encontrado.is_file():
                return encontrado.as_uri()
    return ""


def normalizar(texto):
    if not texto:
        return ""
    return " ".join(str(texto).strip().upper().split())


def ler_dados_sheets(sheets, codigo_imovel):
    try:
        result = sheets.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"'{NOME_ABA}'!A:Z",
        ).execute()
        rows = result.get("values", [])
        if not rows:
            return {}
        cabecalho = [normalizar(h) for h in rows[0]]
        codigo_busca = normalizar(codigo_imovel)
        for row in rows[1:]:
            if not row:
                continue
            while len(row) < len(cabecalho):
                row.append("")
            if normalizar(row[0]) == codigo_busca:
                return {cabecalho[i]: row[i] for i in range(len(cabecalho))}
        return {}
    except Exception as e:
        print(f"Erro ao ler Google Sheets: {e}", flush=True)
        return {}


def get_dado(dados, *chaves, default="-"):
    for chave in chaves:
        valor = dados.get(normalizar(chave), "")
        if valor not in ("", None):
            return valor
    return default


HTML_LAYOUT = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <style>
        @font-face {
            font-family: 'Cormorant Garamond';
            src: url('{{ fonte_cormorant_medium }}');
            font-weight: 500;
        }
        @font-face {
            font-family: 'Cormorant Garamond';
            src: url('{{ fonte_cormorant_semibold }}');
            font-weight: 600;
        }
        @font-face {
            font-family: 'Manrope';
            src: url('{{ fonte_manrope_regular }}');
            font-weight: 400;
        }
        @font-face {
            font-family: 'Manrope';
            src: url('{{ fonte_manrope_medium }}');
            font-weight: 500;
        }
        @font-face {
            font-family: 'Manrope';
            src: url('{{ fonte_manrope_semibold }}');
            font-weight: 600;
        }
        @page { size: A4; margin: 0; }
        * { box-sizing: border-box; }
        body { margin: 0; padding: 0; font-family: 'Manrope', sans-serif; background: #f4f1ea; color: #1a1a1a; }
        .page { width: 210mm; height: 297mm; position: relative; overflow: hidden; background: #f4f1ea; }
        .sidebar-bg { position: absolute; top: 0; left: 0; width: 37%; height: 100%; background: #06192a; z-index: 1; }
        .photo-bg { position: absolute; top: 0; right: 0; width: 64%; height: 62%; overflow: hidden; z-index: 1; }
        .photo-bg img { width: 100%; height: 100%; object-fit: cover; display: block; }
        .sidebar-content { position: absolute; top: 0; left: 0; width: 36%; height: 60%; padding: 42px 24px 20px 24px; z-index: 2; overflow: hidden; }
        .logo-container { width: 100%; text-align: center; margin-bottom: 28px; }
        .logo-img { max-width: 151.8px; max-height: 79.2px; object-fit: contain; display: block; margin: 0 auto 14px auto; }
        .logo-symbol { font-size: 28pt; font-weight: 300; color: #e2e8f0; letter-spacing: -2px; margin-bottom: 2px; }
        .logo-title { font-family: 'Cormorant Garamond', serif; font-size: 15.5pt; letter-spacing: 2.8px; font-weight: 500; line-height: 1.18; color: #F7F5F0; text-transform: uppercase; }
        .logo-divider { width: 45px; height: 1px; background: #F7F5F0; margin: 8px auto 7px auto; }
        .logo-subtitle { font-size: 8pt; letter-spacing: 1.8px; color: #94a3b8; margin-top: 6px; text-transform: uppercase; }
        .header-info { width: 100%; margin-top: 4px; }
        .tipo-imovel { font-family: 'Cormorant Garamond', serif; width: 100%; font-size: 16pt; font-weight: 500; letter-spacing: 1.3px; color: #94a3b8; margin: 0; line-height: 1; }
        .destaque-imovel { font-family: 'Cormorant Garamond', serif; width: 100%; font-size: 21pt; font-weight: 600; letter-spacing: 1.1px; margin-top: 3px; margin: 0; color: #F7F5F0; line-height: 1; overflow-wrap: anywhere; }
        .nome-imovel { width: 100%; font-size: 13pt; color: #F7F5F0; font-weight: 300; margin-top: 8px; letter-spacing: 0.8px; overflow-wrap: anywhere; }
        .valor-imovel { position: fixed; top: 400px; left: 0px; font-size: 24pt; font-weight: 600; color: #F7F5F0; letter-spacing: 0.8px; text-align: center; width: 100%; }
        .location-container { width: 100%; display: flex; align-items: flex-end; position: fixed; top: 580px; left: 45px; }
        .location-icon-box { width: 35px; height: 35px; margin-right: 8px; flex-shrink: 0; margin-top: 1px; }
        .location-icon-box svg { width: 100%; height: 100%; }
        .localizacao-topo { min-width: 0; font-size: 8.5pt; letter-spacing: 0.8px; color: #94a3b8; text-transform: uppercase; line-height: 1.4; overflow-wrap: anywhere; }
        .specs-card { position: absolute; top: 56.5%; left: 5.5%; width: 33.5%; height: 35.5%; background: #06192a; border: 1px solid #1e2d3d; border-radius: 2px; padding: 24px 18px; color: white; box-shadow: -4px -4px 14px rgba(0, 0, 0, 0.18); z-index: 10; display: flex; flex-direction: column; justify-content: space-around; }
        .spec-row { display: flex; align-items: center; min-width: 0; width: 100%; }
        .spec-icon-box { width: 32px; height: 32px; margin-right: 12px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; }
        .spec-icon-box svg { width: 25px !important; height: 25px !important; }
        .spec-text-box { min-width: 0; display: flex; flex-direction: column; }
        .spec-label { font-size: 10pt; letter-spacing: 1px; color: #94a3b8; text-transform: uppercase; font-weight: 500; line-height: 1.15; }
        .spec-value { font-size: 13.5pt; font-weight: 400; margin-top: 3px; color: #ffffff; letter-spacing: 0.3px; line-height: 1.1; overflow-wrap: anywhere; }
        .spec-divider { height: 1px; background: #1a2b3c; width: 100%; flex-shrink: 0; }
        .details-area { position: absolute; top: 62%; right: 0; width: 62%; height: 31%; padding: 20px 40px 10px 45px; z-index: 2; display: flex; flex-direction: column; justify-content: space-between; }
        .description-wrapper { border-left: 2px solid #06192a; padding-left: 16px; margin-top: 5px; }
        .diferencial-destaque { font-size: 10pt; font-weight: 600; color: #06192a; letter-spacing: 1.1px; text-transform: uppercase; margin-bottom: 10px; display: block; line-height: 1.25; }
        .description { font-size: 10pt; line-height: 1.45; color: #2d3748; font-weight: 400; }
        .features-grid { width: 100%; display: flex; justify-content: space-between; align-items: flex-start; padding: 5px 6px 0 6px; }
        .feature-item { width: 25%; min-width: 0; text-align: center; display: flex; flex-direction: column; align-items: center; }
        .feature-icon-box { width: 28px; height: 28px; margin-bottom: 7px; flex-shrink: 0; }
        .feature-icon-box svg { width: 100%; height: 100%; }
        .feature-value { font-size: 14pt; font-weight: bold; color: #06192a; line-height: 1; min-height: 14pt; }
        .feature-label { font-size: 9pt; letter-spacing: 0.8px; color: #94a3b8; margin-top: 5px; text-transform: uppercase; font-weight: 700; line-height: 1.15; }
        .footer-line { position: absolute; bottom: 45px; left: 5%; width: 90%; border-top: 1px solid #94a3b8; z-index: 2; }
        .footer-content { position: absolute; bottom: 15px; left: 5%; width: 90%; display: flex; justify-content: space-between; align-items: flex-end; font-size: 8pt; color: #94a3b8; letter-spacing: 0.5px; z-index: 2; }
        .footer-brand { font-weight: bold; color: #06192a; font-size: 9pt; letter-spacing: 1px; }
        .page-break { page-break-before: always; height: 297mm; width: 210mm; box-sizing: border-box; padding: 20mm; background: #f4f1ea; display: flex; flex-direction: column; justify-content: space-between; }
        .full-photo { width: 100%; height: 230mm; object-fit: contain; display: block; }
        .page-footer { border-top: 1px solid #06192a; padding-top: 12px; display: flex; justify-content: space-between; font-size: 11pt; font-weight: bold; color: #06192a; }
    </style>
</head>
<body>
    <div class="page">
        <div class="sidebar-bg"></div>
        <div class="photo-bg"><img src="{{ foto_capa }}" alt="Capa"></div>
        <div class="sidebar-content">
            <div class="logo-container">
                {% if logo_uri %}
                    <img class="logo-img" src="{{ logo_uri }}" alt="Carvalho Ferreira">
                {% else %}
                    <div class="logo-symbol">| •</div>
                {% endif %}
                <div class="logo-title">CARVALHO<br>FERREIRA</div>
                <div class="logo-divider"></div>
                <div class="logo-subtitle">CONSULTORIA IMOBILIARIA</div>
            </div>
            <div class="header-info">
                <h1 class="tipo-imovel">{{ titulo_1 }}</h1>
                <h1 class="destaque-imovel">{{ titulo_2 }}</h1>
                <div class="nome-imovel">{{ titulo_3 }}</div>
                {% if valor and valor != '-' %}
                <div class="valor-imovel">{{ valor }}</div>
                {% endif %}
                <div class="location-container">
                    <div class="location-icon-box">{{ svg_localizacao | safe }}</div>
                    <div class="localizacao-topo">{{ bairro }}<br>{{ cidade_uf }}</div>
                </div>
            </div>
        </div>
        <div class="specs-card">
            <div class="spec-row">
                <div class="spec-icon-box">{{ svg_campo1 | safe }}</div>
                <div class="spec-text-box">
                    <span class="spec-label">{{ label_campo1 }}</span>
                    <span class="spec-value">{{ valor_campo1 }}</span>
                </div>
            </div>
            <div class="spec-divider"></div>
            <div class="spec-row">
                <div class="spec-icon-box">{{ svg_campo2 | safe }}</div>
                <div class="spec-text-box">
                    <span class="spec-label">{{ label_campo2 }}</span>
                    <span class="spec-value">{{ valor_campo2 }}</span>
                </div>
            </div>
            <div class="spec-divider"></div>
            <div class="spec-row">
                <div class="spec-icon-box">{{ svg_campo3 | safe }}</div>
                <div class="spec-text-box">
                    <span class="spec-label">{{ label_campo3 }}</span>
                    <span class="spec-value">{{ valor_campo3 }}</span>
                </div>
            </div>
        </div>
        <div class="details-area">
            <div class="description-wrapper">
                {% if observacao and observacao != '-' %}
                    <span class="diferencial-destaque">DESTAQUES: {{ observacao }}</span>
                {% endif %}
                <div class="description">{{ descricao }}</div>
            </div>
            <div class="features-grid">
                <div class="feature-item">
                    <div class="feature-icon-box">{{ svg_dormitorios | safe }}</div>
                    <div class="feature-value">{{ dormitorios }}</div>
                    <div class="feature-label">Dormitorios</div>
                </div>
                <div class="feature-item">
                    <div class="feature-icon-box">{{ svg_suites | safe }}</div>
                    <div class="feature-value">{{ suites }}</div>
                    <div class="feature-label">Suites</div>
                </div>
                <div class="feature-item">
                    <div class="feature-icon-box">{{ svg_banheiros | safe }}</div>
                    <div class="feature-value">{{ banheiros }}</div>
                    <div class="feature-label">Banheiros</div>
                </div>
                <div class="feature-item">
                    <div class="feature-icon-box">{{ svg_vagas | safe }}</div>
                    <div class="feature-value">{{ vagas }}</div>
                    <div class="feature-label">Vagas</div>
                </div>
            </div>
        </div>
        <div class="footer-line"></div>
        <div class="footer-content">
            <div>
                <div class="footer-brand">CARVALHO FERREIRA</div>
                <div style="font-size: 7.5pt; color: #718096; margin-top: 2px;">CARVALHO FERREIRA</div>
            </div>
            <div style="text-align: right;">
                <div style="font-weight: bold; color: #06192a;">CONSULTORIA IMOBILIARIA</div>
            </div>
        </div>
    </div>
    {% for foto in fotos_galeria %}
    <div class="page-break">
        <img class="full-photo" src="{{ foto }}" alt="Foto">
        <div class="page-footer">
            <div>CARVALHO FERREIRA</div>
            <div>CONSULTORIA IMOBILIARIA</div>
        </div>
    </div>
    {% endfor %}
</body>
</html>
"""


def sanitizar_nome_arquivo(nome):
    return re.sub(r'[\\/*?:"<>|]', "", str(nome)).strip()


def gerar_pdf(codigo_imovel):
    """
    Retorna bytes do PDF, ou None.
    Nao grava no Google Drive. Nao abre interface.
    """
    drive, sheets = conectar_google()
    if not drive or not sheets:
        return None

    codigo_imovel = str(codigo_imovel).strip().upper()
    if not codigo_imovel:
        return None

    dados = ler_dados_sheets(sheets, codigo_imovel)
    if not dados:
        print(f"Imovel '{codigo_imovel}' nao encontrado no Sheets.", flush=True)
        return None

    id_pasta_imovel = obter_id_pasta_imovel(drive, codigo_imovel)
    if not id_pasta_imovel:
        return None

    id_pasta_fotos = buscar_id_por_nome(drive, "FOTOS SELECIONADAS", id_pasta_imovel)
    if not id_pasta_fotos:
        print("Pasta FOTOS SELECIONADAS nao encontrada.", flush=True)
        return None

    try:
        arquivos_fotos = []
        page_token = None
        while True:
            resposta = drive.files().list(
                q=f"'{id_pasta_fotos}' in parents and trashed = false",
                fields="nextPageToken, files(id, name, mimeType)",
                orderBy="name",
                pageSize=1000,
                pageToken=page_token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            ).execute()
            arquivos_fotos.extend(resposta.get("files", []))
            page_token = resposta.get("nextPageToken")
            if not page_token:
                break

        fotos = []
        for arquivo in sorted(arquivos_fotos, key=lambda x: x.get("name", "").lower()):
            mime_type = arquivo.get("mimeType", "")
            if not mime_type.startswith("image/"):
                continue
            data = baixar_bytes(drive, arquivo["id"])
            if not data:
                continue
            fotos.append(bytes_para_data_uri(data, mime_type))

    except Exception as e:
        print(f"Erro ao listar/baixar fotos: {e}", flush=True)
        return None

    if not fotos:
        print("Nenhuma foto valida encontrada.", flush=True)
        return None

    foto_capa = fotos[0]
    fotos_galeria = fotos[1:] if len(fotos) > 1 else []

    tipo_imovel = get_dado(dados, "TIPO", default="IMOVEL")
    tipo_lower = tipo_imovel.lower()

    if "apartamento" in tipo_lower:
        label_campo1, valor_campo1, icone_campo1 = (
            "Area Util",
            get_dado(dados, "AREA UTIL"),
            "area.svg",
        )
        label_campo2, valor_campo2, icone_campo2 = (
            "Andar",
            get_dado(dados, "ANDAR"),
            "andar.svg",
        )
        label_campo3, valor_campo3, icone_campo3 = (
            "IPTU",
            get_dado(dados, "IPTU"),
            "iptu.svg",
        )
    else:
        label_campo1, valor_campo1, icone_campo1 = (
            "Area Util",
            get_dado(dados, "AREA UTIL"),
            "area.svg",
        )
        label_campo2, valor_campo2, icone_campo2 = (
            "Area do Terreno",
            get_dado(dados, "AREA TOTAL"),
            "terreno.svg",
        )
        label_campo3, valor_campo3, icone_campo3 = (
            "IPTU",
            get_dado(dados, "IPTU"),
            "iptu.svg",
        )

    html_rendered = Template(HTML_LAYOUT).render(
        foto_capa=foto_capa,
        fotos_galeria=fotos_galeria,
        logo_uri=buscar_logo_local(),
        fonte_cormorant_medium=fonte_local(
            "CORMORANT GARAMOND", "CormorantGaramond-Medium.ttf"
        ),
        fonte_cormorant_semibold=fonte_local(
            "CORMORANT GARAMOND", "CormorantGaramond-SemiBold.ttf"
        ),
        fonte_manrope_regular=fonte_local("MANROPE", "Manrope-Regular.ttf"),
        fonte_manrope_medium=fonte_local("MANROPE", "Manrope-Medium.ttf"),
        fonte_manrope_semibold=fonte_local("MANROPE", "Manrope-SemiBold.ttf"),
        svg_localizacao=carregar_icone_local("localizacao.svg", "#f4f1ea"),
        svg_dormitorios=carregar_icone_local("dormitorios.svg", "#06192a"),
        svg_suites=carregar_icone_local("suites.svg", "#06192a"),
        svg_banheiros=carregar_icone_local("banheiros.svg", "#06192a"),
        svg_vagas=carregar_icone_local("vagas.svg", "#06192a"),
        svg_campo1=carregar_icone_local(icone_campo1, "#f4f1ea"),
        svg_campo2=carregar_icone_local(icone_campo2, "#f4f1ea"),
        svg_campo3=carregar_icone_local(icone_campo3, "#f4f1ea"),
        label_campo1=label_campo1,
        valor_campo1=valor_campo1,
        label_campo2=label_campo2,
        valor_campo2=valor_campo2,
        label_campo3=label_campo3,
        valor_campo3=valor_campo3,
        titulo_1=get_dado(dados, "TITULO 1", default=""),
        titulo_2=get_dado(dados, "TITULO 2", default=""),
        titulo_3=get_dado(dados, "TITULO 3", default=""),
        valor=get_dado(dados, "VALOR"),
        bairro=get_dado(dados, "BAIRRO", default=""),
        cidade_uf=get_dado(dados, "CIDADE", default=""),
        observacao=get_dado(dados, "OBS EXTRAS", default=""),
        descricao=get_dado(dados, "DESCRICAO", default=""),
        dormitorios=get_dado(dados, "DORMITORIOS"),
        suites=get_dado(dados, "SUITES", default="-"),
        banheiros=get_dado(dados, "BANHEIROS"),
        vagas=get_dado(dados, "VAGAS"),
    )

    pdf_buffer = io.BytesIO()
    weasyprint.HTML(string=html_rendered, base_url=str(SCRIPT_DIR)).write_pdf(
        pdf_buffer
    )
    pdf_bytes = pdf_buffer.getvalue()

    if len(pdf_bytes) < 10000:
        print("PDF gerado parece vazio ou incompleto.", flush=True)
        return None

    return pdf_bytes
