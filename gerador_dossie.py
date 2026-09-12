# -*- coding: utf-8 -*-
"""
gerador_dossie.py

Gera um Dossiê Documental do Imóvel em um único PDF, mantido em memória.

ORDEM FINAL:
1. Capa institucional
2. Documentos encontrados na pasta DOCUMENTOS / DOCUMENTAÇÃO
3. Página de encerramento com contatos + LGPD

TRATAMENTO DE DOCUMENTOS:
- PDFs são mantidos como páginas PDF.
- Imagens são convertidas para PDF.
- Imagens muito verticais são divididas automaticamente em páginas A4.
- Imagens horizontais utilizam A4 paisagem.
"""

import base64
import io
import math
import re
import unicodedata
from pathlib import Path

import streamlit as st
from PIL import Image, ImageOps
from pypdf import PdfReader, PdfWriter

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from jinja2 import Template
import weasyprint


# =========================================================
# CONFIGURAÇÃO
# =========================================================

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


# =========================================================
# IDENTIDADE VISUAL
# =========================================================

COR_FUNDO = "#f4f1ea"
COR_NAVY = "#06192a"
COR_CLARO = "#F7F5F0"
COR_SLATE = "#94a3b8"
COR_DOURADO = "#b99a5b"
COR_LINHA = "#d9d3c8"


# =========================================================
# CONFIGURAÇÃO DE IMAGENS
# =========================================================

# Área útil aproximada da página A4 para os documentos.
A4_RETRATO_LARGURA_MM = 184
A4_RETRATO_ALTURA_MM = 258

A4_PAISAGEM_LARGURA_MM = 271
A4_PAISAGEM_ALTURA_MM = 184

# Se a imagem vertical ficaria com menos que essa largura,
# ela será dividida em mais de uma página.
LARGURA_MINIMA_IMAGEM_MM = 115

# Limite para evitar que fotografias gigantes consumam memória
# desnecessariamente. 4500 px continua sendo suficiente para
# excelente leitura em A4.
MAX_DIMENSAO_IMAGEM = 4500


# =========================================================
# GOOGLE
# =========================================================

@st.cache_resource
def conectar_google():
    """
    Conecta ao Google Drive e Google Sheets usando os secrets.
    """
    credentials_info = st.secrets["google_credentials"]

    creds = service_account.Credentials.from_service_account_info(
        credentials_info,
        scopes=SCOPES,
    )

    drive = build(
        "drive",
        "v3",
        credentials=creds,
        cache_discovery=False,
    )

    sheets = build(
        "sheets",
        "v4",
        credentials=creds,
        cache_discovery=False,
    )

    return drive, sheets


# =========================================================
# NORMALIZAÇÃO E LIMPEZA
# =========================================================

def normalizar(valor):
    """
    Normaliza textos para comparação removendo acentos e espaços extras.
    """
    if valor is None:
        return ""

    texto = str(valor).strip()

    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(
        c for c in texto
        if unicodedata.category(c) != "Mn"
    )

    texto = re.sub(r"\s+", " ", texto)

    return texto.upper().strip()


def extrair_codigo_chave(texto):
    """
    Extrai o código principal.

    Exemplos:
    CF007
    CF 007
    CF-007
    cf007 - casa continental

    Resultado:
    CF007
    """
    if not texto:
        return ""

    texto_norm = normalizar(texto)

    match = re.search(
        r"([A-Z]{1,4}\s*[-_]?\s*\d{1,4})",
        texto_norm,
    )

    if match:
        return re.sub(
            r"[^A-Z0-9]",
            "",
            match.group(1),
        )

    return re.sub(
        r"[^A-Z0-9]",
        "",
        texto_norm,
    )


def valor_preenchido(valor):
    if valor is None:
        return False

    texto = str(valor).strip()

    if not texto:
        return False

    if texto.lower() in {
        "nan",
        "none",
        "null",
        "-",
        "--",
    }:
        return False

    return True


# =========================================================
# SHEETS
# =========================================================

@st.cache_data(ttl=300)
def ler_dados_sheets():
    _, sheets = conectar_google()

    resultado = (
        sheets.spreadsheets()
        .values()
        .get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{NOME_ABA}!A:AZ",
        )
        .execute()
    )

    valores = resultado.get("values", [])

    if not valores:
        return []

    cabecalhos = valores[0]
    dados = []

    for linha in valores[1:]:
        registro = {}

        for indice, cabecalho in enumerate(cabecalhos):
            chave = normalizar(cabecalho)

            if not chave:
                continue

            valor = (
                linha[indice]
                if indice < len(linha)
                else ""
            )

            registro[chave] = valor

        dados.append(registro)

    return dados


def buscar_imovel_sheets(codigo_imovel):
    codigo_alvo = extrair_codigo_chave(codigo_imovel)

    dados = ler_dados_sheets()

    for imovel in dados:
        codigo_planilha = extrair_codigo_chave(
            imovel.get("CODIGO", "")
        )

        if codigo_planilha == codigo_alvo:
            return imovel

    return None


def get_dado(dados, *chaves):
    if not dados:
        return ""

    for chave in chaves:
        valor = dados.get(
            normalizar(chave),
            "",
        )

        if valor_preenchido(valor):
            return str(valor).strip()

    return ""


# =========================================================
# DRIVE
# =========================================================

def buscar_id_por_nome(
    service,
    nome_item,
    id_pasta_pai,
):
    """
    Procura uma pasta/arquivo tolerando diferenças
    de acentuação e caixa.

    Exemplo:
    documentos
    DOCUMENTOS
    Documentos
    documentação
    """
    nome_normalizado = normalizar(nome_item)

    page_token = None

    while True:
        resposta = (
            service.files()
            .list(
                q=(
                    f"'{id_pasta_pai}' in parents "
                    f"and trashed = false"
                ),
                spaces="drive",
                fields=(
                    "nextPageToken,"
                    "files(id,name,mimeType)"
                ),
                pageToken=page_token,
                pageSize=1000,
            )
            .execute()
        )

        arquivos = resposta.get(
            "files",
            [],
        )

        # -------------------------------------------------
        # MATCH EXATO
        # -------------------------------------------------

        for arquivo in arquivos:
            if (
                normalizar(arquivo.get("name"))
                == nome_normalizado
            ):
                return arquivo["id"]

        # -------------------------------------------------
        # MATCH PARCIAL
        # -------------------------------------------------

        for arquivo in arquivos:
            nome_f = normalizar(
                arquivo.get("name")
            )

            if (
                nome_normalizado in nome_f
                or nome_f in nome_normalizado
            ):
                return arquivo["id"]

        page_token = resposta.get(
            "nextPageToken"
        )

        if not page_token:
            break

    return None


def buscar_pasta_imovel(
    service,
    codigo_imovel,
    id_pasta_imoveis,
):
    """
    Localiza a pasta do imóvel dentro de IMOVEIS
    aceitando variações no nome da pasta.
    """
    cod_chave = extrair_codigo_chave(
        codigo_imovel
    )

    if not cod_chave:
        return None

    page_token = None
    todas_pastas = []

    while True:
        resposta = (
            service.files()
            .list(
                q=(
                    f"'{id_pasta_imoveis}' in parents "
                    f"and mimeType = "
                    f"'application/vnd.google-apps.folder' "
                    f"and trashed = false"
                ),
                spaces="drive",
                fields=(
                    "nextPageToken,"
                    "files(id,name)"
                ),
                pageToken=page_token,
                pageSize=1000,
            )
            .execute()
        )

        todas_pastas.extend(
            resposta.get("files", [])
        )

        page_token = resposta.get(
            "nextPageToken"
        )

        if not page_token:
            break

    # -----------------------------------------------------
    # 1. COMPARAÇÃO EXATA
    # -----------------------------------------------------

    for pasta in todas_pastas:
        if (
            extrair_codigo_chave(
                pasta.get("name")
            )
            == cod_chave
        ):
            return pasta["id"]

    # -----------------------------------------------------
    # 2. COMPARAÇÃO POR PREFIXO / INCLUSÃO
    # -----------------------------------------------------

    for pasta in todas_pastas:
        nome_limpo = extrair_codigo_chave(
            pasta.get("name")
        )

        if (
            nome_limpo.startswith(cod_chave)
            or cod_chave in nome_limpo
        ):
            return pasta["id"]

    return None


def localizar_pasta_documentacao(
    service,
    codigo_imovel,
):
    """
    Navega na hierarquia:

    PORTFOLIO
        └── IMOVEIS
              └── [PASTA DO IMÓVEL]
                    └── documentos
                       ou documentacao
                       ou docs
    """

    id_portfolio = buscar_id_por_nome(
        service,
        "PORTFOLIO",
        ID_RAIZ,
    )

    if not id_portfolio:
        raise FileNotFoundError(
            "Pasta PORTFOLIO não encontrada no Drive."
        )

    id_imoveis = buscar_id_por_nome(
        service,
        "IMOVEIS",
        id_portfolio,
    )

    if not id_imoveis:
        raise FileNotFoundError(
            "Pasta IMOVEIS não encontrada dentro de PORTFOLIO."
        )

    id_imovel = buscar_pasta_imovel(
        service,
        codigo_imovel,
        id_imoveis,
    )

    if not id_imovel:
        raise FileNotFoundError(
            f"Pasta do imóvel {codigo_imovel} não encontrada."
        )

    # -----------------------------------------------------
    # DOCUMENTOS
    # -----------------------------------------------------

    id_documentos = buscar_id_por_nome(
        service,
        "documentos",
        id_imovel,
    )

    if not id_documentos:
        id_documentos = buscar_id_por_nome(
            service,
            "documentacao",
            id_imovel,
        )

    if not id_documentos:
        id_documentos = buscar_id_por_nome(
            service,
            "docs",
            id_imovel,
        )

    if not id_documentos:
        raise FileNotFoundError(
            f"A pasta 'documentos' não foi encontrada "
            f"dentro do imóvel {codigo_imovel}."
        )

    return id_documentos


# =========================================================
# LISTAGEM DOS DOCUMENTOS
# =========================================================

EXTENSOES_IMAGEM = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
}

MIMES_GOOGLE_EXPORTAVEIS = {
    "application/vnd.google-apps.document",
    "application/vnd.google-apps.spreadsheet",
    "application/vnd.google-apps.presentation",
    "application/vnd.google-apps.drawing",
}


def listar_arquivos_documentacao(
    service,
    id_pasta,
):
    """
    Lista todos os arquivos existentes dentro da pasta
    de documentação.

    Também procura dentro de subpastas.

    Isso evita que algum documento seja simplesmente
    ignorado sem aparecer como possível falha.
    """

    arquivos = []

    def percorrer_pasta(
        id_atual,
        caminho_relativo="",
    ):
        page_token = None

        while True:
            resposta = (
                service.files()
                .list(
                    q=(
                        f"'{id_atual}' in parents "
                        f"and trashed = false"
                    ),
                    spaces="drive",
                    fields=(
                        "nextPageToken,"
                        "files("
                        "id,"
                        "name,"
                        "mimeType,"
                        "size,"
                        "shortcutDetails"
                        ")"
                    ),
                    pageToken=page_token,
                    pageSize=1000,
                )
                .execute()
            )

            itens = resposta.get(
                "files",
                [],
            )

            for item in itens:
                nome = item.get(
                    "name",
                    "",
                )

                mime = item.get(
                    "mimeType",
                    "",
                )

                if mime == (
                    "application/vnd.google-apps.folder"
                ):
                    nova_pasta = (
                        f"{caminho_relativo}/"
                        f"{nome}"
                        if caminho_relativo
                        else nome
                    )

                    percorrer_pasta(
                        item["id"],
                        nova_pasta,
                    )

                    continue

                extensao = Path(
                    nome
                ).suffix.lower()

                # -------------------------------------------------
                # SHORTCUT
                # -------------------------------------------------

                shortcut = item.get(
                    "shortcutDetails"
                )

                id_real = item["id"]
                mime_real = mime

                if shortcut:
                    id_real = shortcut.get(
                        "targetId",
                        item["id"],
                    )

                    mime_real = shortcut.get(
                        "targetMimeType",
                        mime,
                    )

                arquivos.append(
                    {
                        "id": id_real,
                        "id_original": item["id"],
                        "nome": nome,
                        "mimeType": mime_real,
                        "mimeType_original": mime,
                        "extensao": extensao,
                        "caminho": caminho_relativo,
                    }
                )

            page_token = resposta.get(
                "nextPageToken"
            )

            if not page_token:
                break

    percorrer_pasta(id_pasta)

    arquivos.sort(
        key=lambda item: normalizar(
            f"{item.get('caminho', '')} "
            f"{item.get('nome', '')}"
        )
    )

    return arquivos


# =========================================================
# DOWNLOAD
# =========================================================

def baixar_bytes(
    service,
    file_id,
):
    request = service.files().get_media(
        fileId=file_id
    )

    buffer = io.BytesIO()

    downloader = MediaIoBaseDownload(
        buffer,
        request,
    )

    concluido = False

    while not concluido:
        _, concluido = downloader.next_chunk()

    return buffer.getvalue()


def baixar_google_exportado(
    service,
    file_id,
):
    """
    Exporta arquivos nativos do Google para PDF.
    """
    request = service.files().export_media(
        fileId=file_id,
        mimeType="application/pdf",
    )

    buffer = io.BytesIO()

    downloader = MediaIoBaseDownload(
        buffer,
        request,
    )

    concluido = False

    while not concluido:
        _, concluido = downloader.next_chunk()

    return buffer.getvalue()


# =========================================================
# ASSETS DA MARCA
# =========================================================

def bytes_para_data_uri(
    data,
    mime_type,
):
    if not data:
        return ""

    encoded = base64.b64encode(
        data
    ).decode("utf-8")

    return (
        f"data:{mime_type};"
        f"base64,{encoded}"
    )


def buscar_logo_local():
    if not PASTA_LOGO.exists():
        return ""

    extensoes = [
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".svg",
    ]

    arquivos = []

    for extensao in extensoes:
        arquivos.extend(
            PASTA_LOGO.glob(
                f"*{extensao}"
            )
        )

    if not arquivos:
        return ""

    arquivo = sorted(
        arquivos,
        key=lambda p: p.name.lower(),
    )[0]

    try:
        data = arquivo.read_bytes()

        if arquivo.suffix.lower() == ".svg":
            mime = "image/svg+xml"

        elif arquivo.suffix.lower() == ".png":
            mime = "image/png"

        elif arquivo.suffix.lower() in {
            ".jpg",
            ".jpeg",
        }:
            mime = "image/jpeg"

        else:
            mime = "image/webp"

        return bytes_para_data_uri(
            data,
            mime,
        )

    except Exception:
        return ""


def fonte_local(
    subpasta,
    nome_arquivo,
):
    caminho = (
        PASTA_FONTES
        / subpasta
        / nome_arquivo
    )

    if caminho.exists():
        return caminho.as_uri()

    encontrados = list(
        PASTA_FONTES.rglob(
            nome_arquivo
        )
    )

    if encontrados:
        return encontrados[0].as_uri()

    return ""


# =========================================================
# HTML DA CAPA
# =========================================================

HTML_CAPA = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">

<style>

@page {
    size: A4;
    margin: 0;
}

@font-face {
    font-family: "Cormorant";
    src: url("{{ fonte_cormorant }}");
    font-weight: 500;
}

@font-face {
    font-family: "Cormorant";
    src: url("{{ fonte_cormorant_semibold }}");
    font-weight: 600;
}

@font-face {
    font-family: "Manrope";
    src: url("{{ fonte_manrope }}");
    font-weight: 400;
}

@font-face {
    font-family: "Manrope";
    src: url("{{ fonte_manrope_medium }}");
    font-weight: 500;
}

@font-face {
    font-family: "Manrope";
    src: url("{{ fonte_manrope_semibold }}");
    font-weight: 600;
}

* {
    box-sizing: border-box;
}

html,
body {
    margin: 0;
    padding: 0;
    width: 210mm;
    height: 297mm;
}

body {
    background: {{ cor_fundo }};
    color: {{ cor_navy }};
    font-family: "Manrope", sans-serif;
}

.capa {
    width: 210mm;
    height: 297mm;
    position: relative;
    overflow: hidden;
    background: {{ cor_fundo }};
}

.faixa {
    position: absolute;
    top: 0;
    left: 0;
    width: 58mm;
    height: 297mm;
    background: {{ cor_navy }};
}

.conteudo {
    position: absolute;
    left: 58mm;
    top: 0;
    width: 152mm;
    height: 297mm;
    padding: 24mm 22mm 20mm 18mm;
}

.marca {
    position: relative;
    margin-bottom: 30mm;
}

.logo {
    width: 43mm;
    max-height: 22mm;
    object-fit: contain;
    object-position: left center;
}

.marca-texto {
    margin-top: 6mm;
    font-size: 8px;
    letter-spacing: 2.3px;
    color: {{ cor_dourado }};
    font-weight: 600;
}

.superior {
    font-size: 9px;
    letter-spacing: 2.8px;
    color: {{ cor_dourado }};
    font-weight: 600;
    margin-bottom: 5mm;
}

.titulo {
    font-family: "Cormorant", serif;
    font-size: 37px;
    line-height: 0.94;
    font-weight: 600;
    text-transform: uppercase;
    margin: 0;
    color: {{ cor_navy }};
}

.linha {
    width: 24mm;
    height: 0.5mm;
    background: {{ cor_dourado }};
    margin: 9mm 0 10mm 0;
}

.identificacao {
    margin-bottom: 17mm;
}

.codigo {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 2px;
    color: {{ cor_dourado }};
    margin-bottom: 4mm;
}

.endereco {
    font-family: "Cormorant", serif;
    font-size: 22px;
    line-height: 1.08;
    font-weight: 500;
    color: {{ cor_navy }};
}

.texto {
    margin-top: 15mm;
    max-width: 115mm;
    font-size: 10.5px;
    line-height: 1.75;
    color: #475569;
}

.bloco {
    position: absolute;
    left: 18mm;
    bottom: 31mm;
    width: 112mm;
    border-top: 1px solid {{ cor_linha }};
    padding-top: 7mm;
}

.bloco-label {
    font-size: 7.5px;
    letter-spacing: 2px;
    color: {{ cor_slate }};
    font-weight: 600;
    margin-bottom: 3mm;
}

.bloco-texto {
    font-size: 8.5px;
    line-height: 1.6;
    color: #64748b;
}

.rodape {
    position: absolute;
    bottom: 12mm;
    left: 18mm;
    right: 22mm;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 7px;
    letter-spacing: 1.5px;
    color: {{ cor_slate }};
}

.rodape-direita {
    color: {{ cor_dourado }};
    font-weight: 600;
}

</style>
</head>

<body>

<div class="capa">

    <div class="faixa"></div>

    <div class="conteudo">

        <div class="marca">

            {% if logo %}
                <img
                    class="logo"
                    src="{{ logo }}"
                >
            {% endif %}

            <div class="marca-texto">
                CONSULTORIA IMOBILIÁRIA
            </div>

        </div>

        <div class="superior">
            DOCUMENTAÇÃO
        </div>

        <h1 class="titulo">
            Dossiê<br>
            Documental<br>
            do Imóvel
        </h1>

        <div class="linha"></div>

        <div class="identificacao">

            <div class="codigo">
                {{ codigo }}
            </div>

            {% if endereco %}

                <div class="endereco">
                    {{ endereco }}
                </div>

            {% else %}

                <div class="endereco">
                    Imóvel identificado<br>
                    pelo código {{ codigo }}
                </div>

            {% endif %}

        </div>

        <div class="texto">

            Este documento reúne a documentação disponibilizada
            para análise da operação imobiliária, organizada em
            um único arquivo para facilitar a conferência das
            informações e proporcionar mais transparência
            durante o processo de compra.

        </div>

    </div>

    <div class="bloco">

        <div class="bloco-label">
            MATERIAL DOCUMENTAL
        </div>

        <div class="bloco-texto">

            Os documentos apresentados neste dossiê correspondem
            aos arquivos disponibilizados para esta operação imobiliária.

        </div>

    </div>

    <div class="rodape">

        <div>
            CARVALHO FERREIRA
        </div>

        <div class="rodape-direita">
            {{ codigo }}
        </div>

    </div>

</div>

</body>
</html>
"""


# =========================================================
# HTML DAS IMAGENS
# =========================================================

HTML_IMAGEM = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">

<style>

@page {
    size: {{ tamanho_pagina }};
    margin: 0;
}

@font-face {
    font-family: "Manrope";
    src: url("{{ fonte_manrope }}");
    font-weight: 400;
}

@font-face {
    font-family: "Manrope";
    src: url("{{ fonte_manrope_semibold }}");
    font-weight: 600;
}

* {
    box-sizing: border-box;
}

html,
body {
    margin: 0;
    padding: 0;
    width: {{ largura_pagina }};
    height: {{ altura_pagina }};
}

body {
    background: #ffffff;
    font-family: "Manrope", sans-serif;
}

.pagina {

    width: {{ largura_pagina }};
    height: {{ altura_pagina }};

    position: relative;

    background: #ffffff;

    display: flex;

    align-items: center;
    justify-content: center;

    padding:
        12mm
        13mm
        20mm
        13mm;

    page-break-after: always;
}

.area-documento {

    width: {{ largura_area }};
    height: {{ altura_area }};

    display: flex;

    align-items: center;
    justify-content: center;

    overflow: hidden;
}

.area-documento img {

    max-width: {{ largura_area }};
    max-height: {{ altura_area }};

    width: auto;
    height: auto;

    object-fit: contain;

    display: block;
}

.rodape {

    position: absolute;

    left: 13mm;
    right: 13mm;
    bottom: 8mm;

    height: 7mm;

    border-top:
        0.3mm solid #e5e7eb;

    padding-top: 2mm;

    display: flex;

    justify-content: space-between;

    font-size: 6.5px;

    letter-spacing: 1px;

    color: #94a3b8;
}

.rodape-direita {

    font-weight: 600;

    color: #b99a5b;
}

</style>

</head>

<body>

<div class="pagina">

    <div class="area-documento">

        <img src="{{ imagem }}">

    </div>

    <div class="rodape">

        <div>
            CARVALHO FERREIRA · DOSSIÊ DOCUMENTAL
        </div>

        <div class="rodape-direita">
            {{ codigo }}
        </div>

    </div>

</div>

</body>
</html>
"""


# =========================================================
# HTML DO ENCERRAMENTO
# =========================================================

HTML_ENCERRAMENTO = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">

<style>

@page {
    size: A4;
    margin: 0;
}

@font-face {
    font-family: "Cormorant";
    src: url("{{ fonte_cormorant }}");
    font-weight: 500;
}

@font-face {
    font-family: "Cormorant";
    src: url("{{ fonte_cormorant_semibold }}");
    font-weight: 600;
}

@font-face {
    font-family: "Manrope";
    src: url("{{ fonte_manrope }}");
    font-weight: 400;
}

@font-face {
    font-family: "Manrope";
    src: url("{{ fonte_manrope_semibold }}");
    font-weight: 600;
}

* {
    box-sizing: border-box;
}

html,
body {
    margin: 0;
    padding: 0;
    width: 210mm;
    height: 297mm;
}

body {
    background: {{ cor_fundo }};
    color: {{ cor_navy }};
    font-family: "Manrope", sans-serif;
}

.pagina {

    width: 210mm;
    height: 297mm;

    position: relative;

    overflow: hidden;

    background: {{ cor_fundo }};
}

.faixa {

    position: absolute;

    bottom: 0;
    right: 0;

    width: 58mm;
    height: 297mm;

    background: {{ cor_navy }};
}

.conteudo {

    position: absolute;

    left: 0;
    top: 0;

    width: 152mm;
    height: 297mm;

    padding:
        31mm
        18mm
        20mm
        22mm;
}

.superior {

    font-size: 8px;

    letter-spacing: 2.6px;

    color: {{ cor_dourado }};

    font-weight: 600;

    margin-bottom: 6mm;
}

.titulo {

    font-family: "Cormorant", serif;

    font-size: 37px;

    line-height: 0.95;

    font-weight: 600;

    text-transform: uppercase;

    margin: 0;

    color: {{ cor_navy }};
}

.linha {

    width: 24mm;

    height: 0.5mm;

    background: {{ cor_dourado }};

    margin:
        9mm
        0
        12mm
        0;
}

.chamada {

    font-family: "Cormorant", serif;

    font-size: 23px;

    line-height: 1.05;

    font-weight: 500;

    max-width: 105mm;

    margin-bottom: 9mm;
}

.texto {

    max-width: 112mm;

    font-size: 9px;

    line-height: 1.7;

    color: #64748b;
}

.contatos {

    position: absolute;

    left: 22mm;
    bottom: 43mm;

    width: 105mm;
}

.contato {

    border-top:
        1px solid {{ cor_linha }};

    padding: 5mm 0;
}

.contato-label {

    font-size: 7px;

    letter-spacing: 1.8px;

    color: {{ cor_slate }};

    font-weight: 600;

    margin-bottom: 2mm;
}

.contato-nome {

    font-family: "Cormorant", serif;

    font-size: 20px;

    font-weight: 600;
}

.contato-numero {

    margin-top: 1mm;

    font-size: 9px;

    color: #64748b;
}

.lgpd {

    position: absolute;

    left: 22mm;
    bottom: 17mm;

    width: 105mm;

    font-size: 6.8px;

    line-height: 1.55;

    color: #94a3b8;
}

.rodape {

    position: absolute;

    left: 22mm;
    bottom: 8mm;

    font-size: 6.5px;

    letter-spacing: 1.2px;

    color: {{ cor_slate }};
}

</style>

</head>

<body>

<div class="pagina">

    <div class="faixa"></div>

    <div class="conteudo">

        <div class="superior">
            CARVALHO FERREIRA
        </div>

        <h1 class="titulo">
            Análise e<br>
            Atendimento
        </h1>

        <div class="linha"></div>

        <div class="chamada">
            Transparência faz parte do nosso trabalho.
        </div>

        <div class="texto">

            Este dossiê foi organizado para facilitar a análise
            documental da operação imobiliária e reunir, em um
            único arquivo, os documentos disponibilizados para
            conferência.

            <br><br>

            Sempre que necessário, recomendamos que a documentação
            seja também analisada pelos profissionais de confiança
            das partes envolvidas.

        </div>

    </div>

    <div class="contatos">

        <div class="contato">

            <div class="contato-label">
                ATENDIMENTO
            </div>

            <div class="contato-nome">
                Fernando Carvalho
            </div>

            <div class="contato-numero">
                WhatsApp · 12 98816-2626
            </div>

        </div>

        <div class="contato">

            <div class="contato-label">
                CORRETOR
            </div>

            <div class="contato-nome">
                Valdir Ferreira
            </div>

            <div class="contato-numero">
                WhatsApp · 12 99215-7474
            </div>

        </div>

    </div>

    <div class="lgpd">

        Este material pode conter dados pessoais e documentos
        de caráter privado. Seu conteúdo é disponibilizado
        exclusivamente para análise da operação imobiliária
        e deve ser tratado com confidencialidade, observando
        a legislação aplicável, inclusive a Lei nº 13.709/2018
        (Lei Geral de Proteção de Dados - LGPD).

    </div>

    <div class="rodape">

        CARVALHO FERREIRA · CONSULTORIA IMOBILIÁRIA

    </div>

</div>

</body>
</html>
"""


# =========================================================
# RENDERIZADORES
# =========================================================

def html_para_pdf(html):
    buffer = io.BytesIO()

    weasyprint.HTML(
        string=html,
        base_url=str(SCRIPT_DIR),
    ).write_pdf(buffer)

    return buffer.getvalue()


def gerar_capa_pdf_bytes(
    codigo_imovel,
    dados_imovel=None,
):
    codigo = str(
        codigo_imovel
    ).strip().upper()

    endereco = get_dado(
        dados_imovel,
        "ENDERECO",
    )

    bairro = get_dado(
        dados_imovel,
        "BAIRRO",
    )

    cidade = get_dado(
        dados_imovel,
        "CIDADE",
    )

    uf = get_dado(
        dados_imovel,
        "UF",
        "ESTADO",
    )

    partes_endereco = []

    if endereco:
        partes_endereco.append(
            endereco
        )

    if bairro:
        partes_endereco.append(
            bairro
        )

    cidade_uf = ""

    if cidade:

        cidade_uf = cidade

        if uf:
            cidade_uf += (
                f" / {uf}"
            )

    if cidade_uf:
        partes_endereco.append(
            cidade_uf
        )

    endereco_final = " · ".join(
        partes_endereco
    )

    contexto = {
        "codigo": codigo,
        "endereco": endereco_final,
        "logo": buscar_logo_local(),

        "cor_fundo": COR_FUNDO,
        "cor_navy": COR_NAVY,
        "cor_claro": COR_CLARO,
        "cor_slate": COR_SLATE,
        "cor_dourado": COR_DOURADO,

        "fonte_cormorant": fonte_local(
            "Cormorant Garamond",
            "CormorantGaramond-Medium.ttf",
        ),

        "fonte_cormorant_semibold": fonte_local(
            "Cormorant Garamond",
            "CormorantGaramond-SemiBold.ttf",
        ),

        "fonte_manrope": fonte_local(
            "Manrope",
            "Manrope-Regular.ttf",
        ),

        "fonte_manrope_medium": fonte_local(
            "Manrope",
            "Manrope-Medium.ttf",
        ),

        "fonte_manrope_semibold": fonte_local(
            "Manrope",
            "Manrope-SemiBold.ttf",
        ),
    }

    html = Template(
        HTML_CAPA
    ).render(
        **contexto
    )

    return html_para_pdf(html)


# =========================================================
# PREPARAÇÃO DA IMAGEM
# =========================================================

def abrir_imagem_normalizada(
    conteudo_imagem,
):
    """
    Abre a imagem, corrige orientação EXIF,
    trata transparência e converte para RGB.
    """

    imagem = Image.open(
        io.BytesIO(
            conteudo_imagem
        )
    )

    imagem = ImageOps.exif_transpose(
        imagem
    )

    # -----------------------------------------------------
    # REDIMENSIONAMENTO CONTROLADO
    # -----------------------------------------------------

    largura, altura = imagem.size

    maior_dimensao = max(
        largura,
        altura,
    )

    if maior_dimensao > MAX_DIMENSAO_IMAGEM:

        escala = (
            MAX_DIMENSAO_IMAGEM
            / maior_dimensao
        )

        nova_largura = max(
            1,
            int(largura * escala),
        )

        nova_altura = max(
            1,
            int(altura * escala),
        )

        imagem = imagem.resize(
            (
                nova_largura,
                nova_altura,
            ),
            Image.Resampling.LANCZOS,
        )

    # -----------------------------------------------------
    # TRANSPARÊNCIA
    # -----------------------------------------------------

    if imagem.mode in (
        "RGBA",
        "LA",
        "P",
    ):

        if imagem.mode == "P":
            imagem = imagem.convert(
                "RGBA"
            )

        fundo = Image.new(
            "RGB",
            imagem.size,
            "white",
        )

        alpha = (
            imagem.getchannel("A")
            if "A" in imagem.getbands()
            else None
        )

        fundo.paste(
            imagem,
            mask=alpha,
        )

        imagem = fundo

    else:
        imagem = imagem.convert(
            "RGB"
        )

    return imagem


def imagem_para_jpeg(
    imagem,
):
    buffer = io.BytesIO()

    imagem.save(
        buffer,
        format="JPEG",
        quality=95,
        optimize=True,
    )

    return buffer.getvalue()


# =========================================================
# DIVISÃO INTELIGENTE DE IMAGENS
# =========================================================

def preparar_imagem_para_paginas(
    conteudo_imagem,
):
    """
    Decide automaticamente como tratar a imagem.

    1. Documento normal:
       uma única página A4.

    2. Documento muito vertical:
       divide em várias páginas A4.

    3. Documento horizontal:
       usa A4 paisagem.

    O objetivo é evitar que documentos compridos
    fiquem pequenos e ilegíveis.
    """

    imagem = abrir_imagem_normalizada(
        conteudo_imagem
    )

    largura, altura = imagem.size

    proporcao = (
        largura / altura
    )

    # =====================================================
    # DOCUMENTO MUITO VERTICAL
    # =====================================================

    largura_relativa = (
        A4_RETRATO_ALTURA_MM
        * proporcao
    )

    precisa_dividir = (
        proporcao < 0.60
        and largura_relativa
        < LARGURA_MINIMA_IMAGEM_MM
    )

    if precisa_dividir:

        # Altura máxima que uma página poderia
        # comportar mantendo a imagem grande.
        proporcao_a4 = (
            A4_RETRATO_LARGURA_MM
            / A4_RETRATO_ALTURA_MM
        )

        altura_maxima_segmento = (
            largura
            / proporcao_a4
        )

        quantidade_paginas = max(
            2,
            math.ceil(
                altura
                / altura_maxima_segmento
            ),
        )

        altura_segmento = math.ceil(
            altura
            / quantidade_paginas
        )

        paginas = []

        for indice in range(
            quantidade_paginas
        ):

            topo = (
                indice
                * altura_segmento
            )

            base = min(
                altura,
                (
                    indice + 1
                )
                * altura_segmento,
            )

            if base <= topo:
                continue

            recorte = imagem.crop(
                (
                    0,
                    topo,
                    largura,
                    base,
                )
            )

            paginas.append(
                {
                    "bytes": imagem_para_jpeg(
                        recorte
                    ),
                    "orientacao": "retrato",
                }
            )

        return paginas

    # =====================================================
    # IMAGEM HORIZONTAL
    # =====================================================

    if proporcao > 1.15:

        return [
            {
                "bytes": imagem_para_jpeg(
                    imagem
                ),
                "orientacao": "paisagem",
            }
        ]

    # =====================================================
    # IMAGEM NORMAL
    # =====================================================

    return [
        {
            "bytes": imagem_para_jpeg(
                imagem
            ),
            "orientacao": "retrato",
        }
    ]


# =========================================================
# GERAÇÃO DAS PÁGINAS DE IMAGEM
# =========================================================

def gerar_paginas_imagem_pdf_bytes(
    conteudo_imagem,
    codigo_imovel,
):
    """
    Recebe uma imagem e devolve um PDF com uma
    ou várias páginas, dependendo da proporção.
    """

    paginas = preparar_imagem_para_paginas(
        conteudo_imagem
    )

    pdfs = []

    for pagina in paginas:

        imagem_uri = bytes_para_data_uri(
            pagina["bytes"],
            "image/jpeg",
        )

        if pagina["orientacao"] == "paisagem":

            tamanho_pagina = (
                "A4 landscape"
            )

            largura_pagina = "297mm"
            altura_pagina = "210mm"

            largura_area = (
                "271mm"
            )

            altura_area = (
                "184mm"
            )

        else:

            tamanho_pagina = "A4"

            largura_pagina = "210mm"
            altura_pagina = "297mm"

            largura_area = "184mm"
            altura_area = "258mm"

        contexto = {
            "codigo": str(
                codigo_imovel
            ).upper(),

            "imagem": imagem_uri,

            "tamanho_pagina": tamanho_pagina,

            "largura_pagina": largura_pagina,
            "altura_pagina": altura_pagina,

            "largura_area": largura_area,
            "altura_area": altura_area,

            "fonte_manrope": fonte_local(
                "Manrope",
                "Manrope-Regular.ttf",
            ),

            "fonte_manrope_semibold": fonte_local(
                "Manrope",
                "Manrope-SemiBold.ttf",
            ),
        }

        html = Template(
            HTML_IMAGEM
        ).render(
            **contexto
        )

        pdfs.append(
            html_para_pdf(html)
        )

    # -----------------------------------------------------
    # JUNTA AS PÁGINAS DA MESMA IMAGEM
    # -----------------------------------------------------

    if len(pdfs) == 1:
        return pdfs[0]

    pdf_final, _ = consolidar_pdfs(
        pdfs
    )

    return pdf_final


# =========================================================
# ENCERRAMENTO
# =========================================================

def gerar_encerramento_pdf_bytes():

    contexto = {
        "cor_fundo": COR_FUNDO,
        "cor_navy": COR_NAVY,
        "cor_claro": COR_CLARO,
        "cor_slate": COR_SLATE,
        "cor_dourado": COR_DOURADO,

        "fonte_cormorant": fonte_local(
            "Cormorant Garamond",
            "CormorantGaramond-Medium.ttf",
        ),

        "fonte_cormorant_semibold": fonte_local(
            "Cormorant Garamond",
            "CormorantGaramond-SemiBold.ttf",
        ),

        "fonte_manrope": fonte_local(
            "Manrope",
            "Manrope-Regular.ttf",
        ),

        "fonte_manrope_semibold": fonte_local(
            "Manrope",
            "Manrope-SemiBold.ttf",
        ),
    }

    html = Template(
        HTML_ENCERRAMENTO
    ).render(
        **contexto
    )

    return html_para_pdf(html)


# =========================================================
# CONSOLIDAÇÃO
# =========================================================

def adicionar_pdf_ao_writer(
    writer,
    pdf_bytes,
):
    reader = PdfReader(
        io.BytesIO(
            pdf_bytes
        )
    )

    quantidade = 0

    for pagina in reader.pages:
        writer.add_page(
            pagina
        )
        quantidade += 1

    return quantidade


def consolidar_pdfs(
    lista_pdfs,
):
    writer = PdfWriter()

    total_paginas = 0

    for pdf_bytes in lista_pdfs:

        if not pdf_bytes:
            continue

        total_paginas += (
            adicionar_pdf_ao_writer(
                writer,
                pdf_bytes,
            )
        )

    saida = io.BytesIO()

    writer.write(
        saida
    )

    return (
        saida.getvalue(),
        total_paginas,
    )


# =========================================================
# PROCESSAMENTO INDIVIDUAL
# =========================================================

def processar_documento(
    service,
    arquivo,
    codigo_imovel,
):
    nome = arquivo["nome"]

    file_id = arquivo["id"]

    mime = arquivo.get(
        "mimeType",
        "",
    )

    extensao = arquivo.get(
        "extensao",
        "",
    ).lower()

    # =====================================================
    # GOOGLE DOCS / SHEETS / SLIDES
    # =====================================================

    if mime in MIMES_GOOGLE_EXPORTAVEIS:

        conteudo = baixar_google_exportado(
            service,
            file_id,
        )

        if not conteudo:
            raise ValueError(
                "Arquivo Google exportado sem conteúdo."
            )

        reader = PdfReader(
            io.BytesIO(
                conteudo
            )
        )

        if len(reader.pages) == 0:
            raise ValueError(
                "Documento exportado sem páginas."
            )

        return (
            conteudo,
            len(reader.pages),
        )

    # =====================================================
    # DOWNLOAD NORMAL
    # =====================================================

    conteudo = baixar_bytes(
        service,
        file_id,
    )

    if not conteudo:
        raise ValueError(
            "Arquivo baixado sem conteúdo."
        )

    # =====================================================
    # PDF
    # =====================================================

    if (
        mime == "application/pdf"
        or extensao == ".pdf"
    ):

        reader = PdfReader(
            io.BytesIO(
                conteudo
            )
        )

        if len(reader.pages) == 0:
            raise ValueError(
                "PDF sem páginas."
            )

        return (
            conteudo,
            len(reader.pages),
        )

    # =====================================================
    # IMAGEM
    # =====================================================

    if extensao in EXTENSOES_IMAGEM:

        pdf_bytes = (
            gerar_paginas_imagem_pdf_bytes(
                conteudo,
                codigo_imovel,
            )
        )

        reader = PdfReader(
            io.BytesIO(
                pdf_bytes
            )
        )

        return (
            pdf_bytes,
            len(reader.pages),
        )

    # =====================================================
    # FORMATO NÃO SUPORTADO
    # =====================================================

    raise ValueError(
        f"Formato não suportado: {nome}"
    )


# =========================================================
# GERAÇÃO PRINCIPAL
# =========================================================

def gerar_dossie(
    codigo_imovel,
    dados_imovel=None,
):
    """
    Função principal de geração do dossiê.
    """

    codigo = str(
        codigo_imovel
    ).strip().upper()

    if not codigo:

        return {
            "sucesso": False,
            "pdf": None,
            "nome_arquivo": None,
            "documentos_encontrados": 0,
            "documentos_processados": 0,
            "paginas": 0,
            "falhas": [],
            "detalhes": [],
            "mensagem": (
                "Código do imóvel não informado."
            ),
        }

    try:

        drive, _ = conectar_google()

        # -------------------------------------------------
        # DADOS DO IMÓVEL
        # -------------------------------------------------

        if dados_imovel is None:

            dados_imovel = (
                buscar_imovel_sheets(
                    codigo
                )
            )

        if dados_imovel is None:
            dados_imovel = {}

        # -------------------------------------------------
        # LOCALIZAÇÃO DA PASTA
        # -------------------------------------------------

        id_documentos = (
            localizar_pasta_documentacao(
                drive,
                codigo,
            )
        )

        # -------------------------------------------------
        # LISTAGEM
        # -------------------------------------------------

        arquivos = (
            listar_arquivos_documentacao(
                drive,
                id_documentos,
            )
        )

        if not arquivos:

            return {
                "sucesso": False,
                "pdf": None,
                "nome_arquivo": None,
                "documentos_encontrados": 0,
                "documentos_processados": 0,
                "paginas": 0,
                "falhas": [],
                "detalhes": [],
                "mensagem": (
                    f"Nenhum documento foi encontrado "
                    f"na pasta de documentação do {codigo}."
                ),
            }

        # -------------------------------------------------
        # NOME DO ARQUIVO
        # -------------------------------------------------

        partes = [
            "Dossie",
            codigo,
        ]

        cidade = get_dado(
            dados_imovel,
            "CIDADE",
        )

        if cidade:

            cidade_limpa = (
                normalizar(cidade)
                .title()
            )

            partes.append(
                cidade_limpa
            )

        nome_arquivo = (
            " - ".join(partes)
            + ".pdf"
        )

        # -------------------------------------------------
        # PARTES DO PDF
        # -------------------------------------------------

        pdfs = []

        # CAPA
        capa = gerar_capa_pdf_bytes(
            codigo,
            dados_imovel,
        )

        pdfs.append(
            capa
        )

        # -------------------------------------------------
        # DOCUMENTOS
        # -------------------------------------------------

        falhas = []

        detalhes = []

        documentos_processados = 0

        paginas_documentos = 0

        for numero, arquivo in enumerate(
            arquivos,
            start=1,
        ):

            try:

                pdf_documento, paginas = (
                    processar_documento(
                        drive,
                        arquivo,
                        codigo,
                    )
                )

                pdfs.append(
                    pdf_documento
                )

                documentos_processados += 1

                paginas_documentos += paginas

                detalhes.append(
                    {
                        "numero": numero,
                        "nome": arquivo["nome"],
                        "caminho": arquivo.get(
                            "caminho",
                            "",
                        ),
                        "paginas": paginas,
                        "status": "OK",
                    }
                )

            except Exception as erro:

                falha = {
                    "nome": arquivo["nome"],
                    "caminho": arquivo.get(
                        "caminho",
                        "",
                    ),
                    "erro": str(erro),
                }

                falhas.append(
                    falha
                )

                detalhes.append(
                    {
                        "numero": numero,
                        "nome": arquivo["nome"],
                        "caminho": arquivo.get(
                            "caminho",
                            "",
                        ),
                        "paginas": 0,
                        "status": "ERRO",
                        "erro": str(erro),
                    }
                )

        # -------------------------------------------------
        # ENCERRAMENTO
        # -------------------------------------------------

        encerramento = (
            gerar_encerramento_pdf_bytes()
        )

        pdfs.append(
            encerramento
        )

        # -------------------------------------------------
        # CONSOLIDAÇÃO
        # -------------------------------------------------

        pdf_final, total_paginas = (
            consolidar_pdfs(
                pdfs
            )
        )

        # =================================================
        # RESULTADO
        # =================================================

        if falhas:

            mensagem = (
                f"Dossiê gerado parcialmente. "
                f"{documentos_processados} de "
                f"{len(arquivos)} documentos foram "
                f"incorporados. "
                f"{len(falhas)} documento(s) "
                f"apresentaram erro."
            )

            sucesso = False

        else:

            mensagem = (
                f"Dossiê gerado com sucesso. "
                f"{documentos_processados} documentos "
                f"incorporados em "
                f"{total_paginas} páginas."
            )

            sucesso = True

        return {
            "sucesso": sucesso,
            "pdf": pdf_final,
            "nome_arquivo": nome_arquivo,
            "documentos_encontrados": len(
                arquivos
            ),
            "documentos_processados": (
                documentos_processados
            ),
            "paginas": total_paginas,
            "paginas_documentos": (
                paginas_documentos
            ),
            "falhas": falhas,
            "detalhes": detalhes,
            "mensagem": mensagem,
        }

    except Exception as erro:

        return {
            "sucesso": False,
            "pdf": None,
            "nome_arquivo": None,
            "documentos_encontrados": 0,
            "documentos_processados": 0,
            "paginas": 0,
            "falhas": [],
            "detalhes": [],
            "mensagem": (
                f"Erro ao gerar dossiê: {erro}"
            ),
        }


# =========================================================
# ALIASES DE COMPATIBILIDADE
# =========================================================

def criar_dossie_consolidado(
    codigo_imovel,
    dados_imovel=None,
):
    return gerar_dossie(
        codigo_imovel,
        dados_imovel,
    )


def gerar_dossie_documental(
    codigo_imovel,
    dados_imovel=None,
):
    return gerar_dossie(
        codigo_imovel,
        dados_imovel,
    )


def gerar_dossie_bytes(
    codigo_imovel,
    dados_imovel=None,
):
    resultado = gerar_dossie(
        codigo_imovel,
        dados_imovel,
    )

    return (
        resultado.get("pdf"),
        resultado,
    )