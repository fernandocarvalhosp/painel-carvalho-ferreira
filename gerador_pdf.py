# -*- coding: utf-8 -*-
import io
import os
import re
import sys
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from jinja2 import Template
import streamlit as st
import weasyprint

SCRIPT_DIR = Path(__file__).resolve().parent

# -------------------------------------------------
# CONFIGURACOES
# -------------------------------------------------
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]

ID_RAIZ = "1NaZ7kv_jHVCTlLV8vqxCzBwbTX5y3fR7"
ID_PASTA_MARCA = "19b_7n4ER-hmFyhvMmFIO1pBmPlRu85aA"

SPREADSHEET_ID = "1nVEpOZFYFKcq0MXtOwxn22nqxafmJBHnf6zhHQlyT8w"
NOME_ABA = "Imoveis"


# -------------------------------------------------
# CONEXAO GOOGLE (ADAPTADA PARA NUVEM)
# -------------------------------------------------
@st.cache_resource
def conectar_google_v2():
    try:
        creds_dict = dict(st.secrets["google_credentials"])
        creds = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=SCOPES
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


def baixar_arquivo_por_id(service, id_arquivo, caminho_local):
    try:
        request = service.files().get_media(fileId=id_arquivo)
        fh = io.FileIO(str(caminho_local), "wb")
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        return True
    except Exception as e:
        print(f"Erro ao baixar arquivo {id_arquivo}: {e}", flush=True)
        return False


def baixar_ativo_marca(service, nome_subpasta, nome_arquivo, pasta_local="temp_ativos"):
    id_subpasta = buscar_id_por_nome(service, nome_subpasta, ID_PASTA_MARCA)
    if not id_subpasta:
        return ""

    id_arquivo = buscar_id_por_nome(service, nome_arquivo, id_subpasta)
    if not id_arquivo:
        return ""

    destino_dir = SCRIPT_DIR / pasta_local
    destino_dir.mkdir(parents=True, exist_ok=True)
    caminho_local = destino_dir / nome_arquivo

    if not caminho_local.exists():
        if not baixar_arquivo_por_id(service, id_arquivo, caminho_local):
            return ""

    return str(caminho_local)


def carregar_icone(service, nome_arquivo, cor=None):
    caminho = baixar_ativo_marca(service, "ICONES", nome_arquivo)
    if not caminho or not os.path.exists(caminho):
        return ""
    with open(caminho, "r", encoding="utf-8") as f:
        svg = f.read()
    if cor:
        svg = svg.replace("currentColor", cor)
    return svg


def buscar_logo_uri(service):
    id_logo = buscar_id_por_nome(service, "LOGO", ID_PASTA_MARCA)
    if not id_logo:
        return None

    try:
        results = service.files().list(
            q=f"'{id_logo}' in parents and trashed = false",
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()
        files = results.get("files", [])
        extensoes = {".png", ".jpg", ".jpeg", ".svg", ".webp"}
        for f in files:
            nome = f["name"]
            if any(nome.lower().endswith(ext) for ext in extensoes):
                caminho = baixar_ativo_marca(service, "LOGO", nome)
                if caminho:
                    return Path(caminho).as_uri()
    except Exception as e:
        print(f"Erro ao buscar logo: {e}", flush=True)
    return None


def fonte_uri(service, nome_arquivo):
    caminho = baixar_ativo_marca(service, "FONTES", nome_arquivo)
    if caminho and os.path.exists(caminho):
        return Path(caminho).as_uri()
    return ""


# -------------------------------------------------
# GOOGLE SHEETS
# -------------------------------------------------
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
                dados = {}
                for i, chave in enumerate(cabecalho):
                    dados[chave] = row[i] if i < len(row) else ""
                return dados
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


# -------------------------------------------------
# TEMPLATE HTML
# -------------------------------------------------
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
        .tipo-imovel { font-family: 'Cormorant Garamond', serif; width: 100%; font-size: 17pt; font-weight: 500; letter-spacing: 1.3px; color: #94a3b8; margin: 0; line-height: 1; }
        .destaque-imovel { font-family: 'Cormorant Garamond', serif; width: 100%; font-size: 25pt; font-weight: 600; letter-spacing: 1.2px; margin-top: 3px; color: #F7F5F0; line-height: 1; overflow-wrap: anywhere; }
        .nome-imovel { width: 100%; font-size: 13pt; color: #F7F5F0; font-weight: 300; margin-top: 8px; letter-spacing: 0.8px; overflow-wrap: anywhere; }
        .valor-imovel { font-size: 24pt; font-weight: 600; color: #F7F5F0; letter-spacing: 0.8px; margin-top: 50px; margin-bottom: 4px; text-align: center; width: 100%; }
        .location-container { width: 100%; display: flex; align-items: flex-end; margin-top: 150px; margin-bottom: 6px; }
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
                    <span class="diferencial-destaque">OBS: {{ observacao }}</span>
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
                    <div class="feature-icon-box">{{ svg_banheiros | safe }}</div>
                    <div class="feature-value">{{ banheiros }}</div>
                    <div class="feature-label">Banheiros</div>
                </div>
                <div class="feature-item">
                    <div class="feature-icon-box">{{ svg_suites | safe }}</div>
                    <div class="feature-value">{{ suites }}</div>
                    <div class="feature-label">Suites</div>
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
                <div style="font-size: 7.5pt; color: #718096; margin-top: 2px;">TRANSFORMA NEGOCIOS EM CONQUISTAS.</div>
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
    drive, sheets = conectar_google()
    if not drive or not sheets:
        return None

    codigo_imovel = codigo_imovel.strip().upper()
    if not codigo_imovel:
        print("Codigo invalido.", flush=True)
        return None

    dados = ler_dados_sheets(sheets, codigo_imovel)
    if not dados:
        print(f"Imovel '{codigo_imovel}' nao encontrado no Google Sheets.", flush=True)
        return None

    id_pasta_imovel = obter_id_pasta_imovel(drive, codigo_imovel)
    if not id_pasta_imovel:
        return None

    id_pasta_fotos = buscar_id_por_nome(drive, "FOTOS SELECIONADAS", id_pasta_imovel)
    fotos = []

    if not id_pasta_fotos:
        print(
            f"Pasta FOTOS SELECIONADAS nao encontrada dentro do imovel {codigo_imovel}.",
            flush=True,
        )
        return None

    try:
        arquivos_fotos = []
        page_token = None

        while True:
            resposta = drive.files().list(
                q=f"'{id_pasta_fotos}' in parents and trashed = false",
                fields="nextPageToken, files(id, name, mimeType, size)",
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

        temp_fotos_dir = SCRIPT_DIR / "temp_fotos" / codigo_imovel
        temp_fotos_dir.mkdir(parents=True, exist_ok=True)

        for arquivo in sorted(arquivos_fotos, key=lambda x: x.get("name", "").lower()):
            nome_f = arquivo.get("name", "")
            mime_type = arquivo.get("mimeType", "")

            if not mime_type.startswith("image/"):
                continue

            caminho_local = temp_fotos_dir / nome_f

            if not caminho_local.exists():
                sucesso_download = baixar_arquivo_por_id(
                    drive, arquivo["id"], caminho_local
                )
                if not sucesso_download:
                    continue

            if caminho_local.exists():
                fotos.append(caminho_local.as_uri())

    except Exception as e:
        print(f"Erro ao listar as fotos de FOTOS SELECIONADAS: {e}", flush=True)
        return None

    if not fotos:
        print("ERRO: Nenhuma imagem valida foi encontrada em FOTOS SELECIONADAS.", flush=True)
        return None

    foto_capa = fotos[0]
    fotos_galeria = fotos[1:] if len(fotos) > 1 else []

    logo_uri = buscar_logo_uri(drive)
    fonte_cormorant_medium = fonte_uri(drive, "CormorantGaramond-Medium.ttf")
    fonte_cormorant_semibold = fonte_uri(drive, "CormorantGaramond-SemiBold.ttf")
    fonte_manrope_regular = fonte_uri(drive, "Manrope-Regular.ttf")
    fonte_manrope_medium = fonte_uri(drive, "Manrope-Medium.ttf")
    fonte_manrope_semibold = fonte_uri(drive, "Manrope-SemiBold.ttf")

    tipo_imovel = get_dado(dados, "TIPO", default="IMOVEL")
    tipo_lower = tipo_imovel.lower()

    if "apartamento" in tipo_lower:
        label_campo1 = "Area Util"
        valor_campo1 = get_dado(dados, "AREA UTIL")
        icone_campo1 = "area.svg"
        label_campo2 = "Andar"
        valor_campo2 = get_dado(dados, "ANDAR")
        icone_campo2 = "andar.svg"
        label_campo3 = "IPTU"
        valor_campo3 = get_dado(dados, "IPTU")
        icone_campo3 = "iptu.svg"
    else:
        label_campo1 = "Area Util"
        valor_campo1 = get_dado(dados, "AREA UTIL")
        icone_campo1 = "area.svg"
        label_campo2 = "Area do Terreno"
        valor_campo2 = get_dado(dados, "AREA TOTAL")
        icone_campo2 = "terreno.svg"
        label_campo3 = "IPTU"
        valor_campo3 = get_dado(dados, "IPTU")
        icone_campo3 = "iptu.svg"

    titulo_1 = get_dado(dados, "TITULO 1", default="")
    titulo_2 = get_dado(dados, "TITULO 2", default="")
    titulo_3 = get_dado(dados, "TITULO 3", default="")

    template = Template(HTML_LAYOUT)
    html_rendered = template.render(
        foto_capa=foto_capa,
        fotos_galeria=fotos_galeria,
        logo_uri=logo_uri,
        fonte_cormorant_medium=fonte_cormorant_medium,
        fonte_cormorant_semibold=fonte_cormorant_semibold,
        fonte_manrope_regular=fonte_manrope_regular,
        fonte_manrope_medium=fonte_manrope_medium,
        fonte_manrope_semibold=fonte_manrope_semibold,
        svg_localizacao=carregar_icone(drive, "localizacao.svg", "#f4f1ea"),
        svg_dormitorios=carregar_icone(drive, "dormitorios.svg", "#06192a"),
        svg_banheiros=carregar_icone(drive, "banheiros.svg", "#06192a"),
        svg_suites=carregar_icone(drive, "suites.svg", "#06192a"),
        svg_vagas=carregar_icone(drive, "vagas.svg", "#06192a"),
        svg_campo1=carregar_icone(drive, icone_campo1, "#f4f1ea"),
        svg_campo2=carregar_icone(drive, icone_campo2, "#f4f1ea"),
        svg_campo3=carregar_icone(drive, icone_campo3, "#f4f1ea"),
        label_campo1=label_campo1,
        valor_campo1=valor_campo1,
        label_campo2=label_campo2,
        valor_campo2=valor_campo2,
        label_campo3=label_campo3,
        valor_campo3=valor_campo3,
        titulo_1=titulo_1,
        titulo_2=titulo_2,
        titulo_3=titulo_3,
        valor=get_dado(dados, "VALOR"),
        bairro=get_dado(dados, "BAIRRO", default=""),
        cidade_uf=get_dado(dados, "CIDADE", default=""),
        observacao=get_dado(dados, "OBS EXTRAS", default=""),
        descricao=get_dado(dados, "DESCRICAO", default=""),
        dormitorios=get_dado(dados, "DORMITORIOS"),
        banheiros=get_dado(dados, "BANHEIROS"),
        suites=get_dado(dados, "SUITES", default="-"),
        vagas=get_dado(dados, "VAGAS"),
    )

    nome_pdf = f"{sanitizar_nome_arquivo(codigo_imovel)}.pdf"
    pdf_local_path = SCRIPT_DIR / "temp_pdf" / nome_pdf
    pdf_local_path.parent.mkdir(parents=True, exist_ok=True)

    weasyprint.HTML(
        string=html_rendered,
        base_url=str(SCRIPT_DIR),
    ).write_pdf(str(pdf_local_path))

    tamanho = pdf_local_path.stat().st_size if pdf_local_path.exists() else 0
    if tamanho < 10000:
        return None

    # -------------------------------------------------
    # SALVAR O PDF GERADO NO GOOGLE DRIVE (NA PASTA DO IMÓVEL)
    # -------------------------------------------------
    try:
        from googleapiclient.http import MediaFileUpload
       
        # Nome do arquivo PDF final
        nome_pdf = f"{sanitizar_nome_arquivo(codigo_imovel)}.pdf"
       
        # Verifica se já existe um PDF antigo na pasta do imóvel para atualizar ou criar novo
        query_pdf = f"'{id_pasta_imovel}' in parents and name = '{nome_pdf}' and trashed = false"
        res_pdf = drive.files().list(q=query_pdf, fields="files(id)").execute()
        arquivos_existentes = res_pdf.get("files", [])

        media = MediaFileUpload(str(pdf_local_path), mimetype="application/pdf")

        if arquivos_existentes:
            # Atualiza o arquivo existente no Drive
            file_id = arquivos_existentes[0]["id"]
            drive.files().update(fileId=file_id, media_body=media).execute()
        else:
            # Cria um novo arquivo PDF na pasta do imóvel
            metadata = {
                "name": nome_pdf,
                "parents": [id_pasta_imovel]
            }
            drive.files().create(body=metadata, media_body=media, fields="id").execute()
           
    except Exception as e:
        print(f"Erro ao salvar o PDF no Google Drive: {e}", flush=True)

    return str(pdf_local_path)
