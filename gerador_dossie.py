# -*- coding: utf-8 -*-

"""
gerador_dossie.py

Gera um Dossiê Documental do Imóvel em um único PDF, mantido em memória,
com padronização estrita de tamanho de página A4 Vertical (Portrait).

ORDEM FINAL:

1. Capa institucional
2. Documentos encontrados diretamente na pasta DOCUMENTOS / DOCUMENTAÇÃO
3. Se existir: separador + documentos da subpasta DOCUMENTOS DO COMPRADOR
4. Página de encerramento com contatos + LGPD

CORREÇÕES APLICADAS (2026-09):
- Texto da barra lateral da capa e da página de encerramento não corta mais.
- Páginas de documentos (PDF e imagem): fundo BRANCO + cabeçalho padronizado.
- Capas institucionais mantêm o visual off-white + barra navy.
- Lógica de subpasta do comprador mantida (só inclui se a pasta existir).
"""

import base64
import io
import re
import unicodedata
from pathlib import Path

import streamlit as st
from PIL import Image, ImageOps
from pypdf import PdfReader, PdfWriter, PageObject, Transformation
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import Color, HexColor

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
    Normaliza textos para comparação removendo acentos
    e espaços extras.
    """

    if valor is None:
        return ""

    texto = str(valor).strip()

    texto = unicodedata.normalize(
        "NFD",
        texto,
    )

    texto = "".join(
        c
        for c in texto
        if unicodedata.category(c) != "Mn"
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto,
    )

    return texto.upper().strip()


def extrair_codigo_chave(texto):
    """
    Extrai o código principal.
    Exemplos:
    CF007
    CR007
    C001
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

    valores = resultado.get(
        "values",
        [],
    )

    if not valores:
        return []

    cabecalhos = valores[0]
    dados = []

    for linha in valores[1:]:
        registro = {}

        for indice, cabecalho in enumerate(
            cabecalhos
        ):
            chave = normalizar(
                cabecalho
            )

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
    codigo_alvo = extrair_codigo_chave(
        codigo_imovel
    )

    dados = ler_dados_sheets()

    for imovel in dados:

        codigo_planilha = extrair_codigo_chave(
            imovel.get(
                "CODIGO",
                "",
            )
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
    nome_normalizado = normalizar(
        nome_item
    )

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
                    "nextPageToken, "
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

        # Correspondência exata.
        for arquivo in arquivos:

            if (
                normalizar(
                    arquivo.get("name")
                )
                == nome_normalizado
            ):
                return arquivo["id"]

        # Correspondência parcial.
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
                    "nextPageToken, "
                    "files(id,name)"
                ),
                pageToken=page_token,
                pageSize=1000,
            )
            .execute()
        )

        todas_pastas.extend(
            resposta.get(
                "files",
                [],
            )
        )

        page_token = resposta.get(
            "nextPageToken"
        )

        if not page_token:
            break

    # Correspondência exata pelo código.
    for pasta in todas_pastas:

        if (
            extrair_codigo_chave(
                pasta.get("name")
            )
            == cod_chave
        ):
            return pasta["id"]

    # Segunda tentativa.
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
    Localiza a pasta PRINCIPAL de documentos.

    Importante:
    esta função sempre retorna DOCUMENTOS,
    e nunca DOCUMENTOS DO COMPRADOR.
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
            "Pasta IMOVEIS não encontrada "
            "dentro de PORTFOLIO."
        )

    id_imovel = buscar_pasta_imovel(
        service,
        codigo_imovel,
        id_imoveis,
    )

    if not id_imovel:
        raise FileNotFoundError(
            f"Pasta do imóvel {codigo_imovel} "
            f"não encontrada."
        )

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
# LISTAGEM DOS DOCUMENTOS PRINCIPAIS
# =========================================================

EXTENSOES_PERMITIDAS = {
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}


def listar_arquivos_documentacao(
    service,
    id_pasta,
):
    """
    Lista SOMENTE os arquivos diretamente dentro
    da pasta DOCUMENTOS.

    Subpastas não entram aqui.
    """

    arquivos = []
    page_token = None

    while True:

        resposta = (
            service.files()
            .list(
                q=(
                    f"'{id_pasta}' in parents "
                    f"and trashed = false"
                ),
                spaces="drive",
                fields=(
                    "nextPageToken, "
                    "files(id,name,mimeType,size)"
                ),
                pageToken=page_token,
                pageSize=1000,
            )
            .execute()
        )

        for arquivo in resposta.get(
            "files",
            [],
        ):

            nome = arquivo.get(
                "name",
                "",
            )

            extensao = Path(
                nome
            ).suffix.lower()

            mime = arquivo.get(
                "mimeType",
                "",
            )

            # Não tratar subpastas como documentos.
            if (
                mime
                == "application/vnd.google-apps.folder"
            ):
                continue

            compativel = (
                mime == "application/pdf"
                or extensao
                in EXTENSOES_PERMITIDAS
            )

            if not compativel:
                continue

            arquivos.append(
                {
                    "id": arquivo["id"],
                    "nome": nome,
                    "mimeType": mime,
                    "extensao": extensao,
                    "secao": "DOCUMENTOS PRINCIPAIS",
                }
            )

        page_token = resposta.get(
            "nextPageToken"
        )

        if not page_token:
            break

    arquivos.sort(
        key=lambda item: normalizar(
            item["nome"]
        )
    )

    return arquivos


# =========================================================
# LOCALIZAÇÃO DA SUBPASTA DO COMPRADOR
# =========================================================

def localizar_pasta_comprador(
    service,
    id_pasta_documentos,
):
    """
    Procura uma subpasta de comprador
    diretamente dentro da pasta DOCUMENTOS.

    A pasta DOCUMENTOS continua sendo a pasta principal.
    """

    page_token = None

    nomes_comprador = {
        "COMPRADOR",
        "COMPRADORA",
        "DOCUMENTOS DO COMPRADOR",
        "DOCUMENTOS DA COMPRADORA",
        "DOCUMENTACAO DO COMPRADOR",
        "DOCUMENTACAO DA COMPRADORA",
    }

    while True:

        resposta = (
            service.files()
            .list(
                q=(
                    f"'{id_pasta_documentos}' in parents "
                    f"and mimeType = "
                    f"'application/vnd.google-apps.folder' "
                    f"and trashed = false"
                ),
                spaces="drive",
                fields=(
                    "nextPageToken, "
                    "files(id,name,mimeType)"
                ),
                pageToken=page_token,
                pageSize=1000,
            )
            .execute()
        )

        pastas = resposta.get(
            "files",
            [],
        )

        # Primeiro: nomes exatos.
        for pasta in pastas:

            nome = normalizar(
                pasta.get(
                    "name",
                    "",
                )
            )

            if nome in nomes_comprador:

                return (
                    pasta["id"],
                    pasta["name"],
                )

        # Segunda tentativa:
        # nome contendo COMPRADOR ou COMPRADORA.
        for pasta in pastas:

            nome = normalizar(
                pasta.get(
                    "name",
                    "",
                )
            )

            if (
                "COMPRADOR" in nome
                or "COMPRADORA" in nome
            ):

                return (
                    pasta["id"],
                    pasta["name"],
                )

        page_token = resposta.get(
            "nextPageToken"
        )

        if not page_token:
            break

    return None, None


def listar_arquivos_comprador(
    service,
    id_pasta_comprador,
):
    """
    Lista os documentos diretamente dentro
    da subpasta do comprador.
    """

    if not id_pasta_comprador:
        return []

    arquivos = []
    page_token = None

    while True:

        resposta = (
            service.files()
            .list(
                q=(
                    f"'{id_pasta_comprador}' in parents "
                    f"and trashed = false"
                ),
                spaces="drive",
                fields=(
                    "nextPageToken, "
                    "files(id,name,mimeType,size)"
                ),
                pageToken=page_token,
                pageSize=1000,
            )
            .execute()
        )

        for arquivo in resposta.get(
            "files",
            [],
        ):

            nome = arquivo.get(
                "name",
                "",
            )

            extensao = Path(
                nome
            ).suffix.lower()

            mime = arquivo.get(
                "mimeType",
                "",
            )

            if (
                mime
                == "application/vnd.google-apps.folder"
            ):
                continue

            compativel = (
                mime == "application/pdf"
                or extensao
                in EXTENSOES_PERMITIDAS
            )

            if not compativel:
                continue

            arquivos.append(
                {
                    "id": arquivo["id"],
                    "nome": nome,
                    "mimeType": mime,
                    "extensao": extensao,
                    "secao": "DOCUMENTOS DO COMPRADOR",
                }
            )

        page_token = resposta.get(
            "nextPageToken"
        )

        if not page_token:
            break

    arquivos.sort(
        key=lambda item: normalizar(
            item["nome"]
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
        f"data:{mime_type};base64,{encoded}"
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
# HTML — CAPA (texto lateral corrigido)
# =========================================================

HTML_CAPA = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">

<style>

@page {
    size: A4 portrait;
    margin: 0;
}

html, body {
    width: 210mm;
    height: 297mm;
    margin: 0;
    padding: 0;
}

body {
    background: {{ cor_fundo }};
}

.pagina {
    width: 210mm;
    height: 297mm;
    box-sizing: border-box;
    position: relative;
    background: {{ cor_fundo }};
    page-break-after: always;
}

.lateral {
    position: absolute;
    left: 0;
    top: 0;
    width: 58mm;
    height: 297mm;
    background: {{ cor_navy }};
}

.conteudo {
    position: absolute;
    left: 75mm;
    right: 25mm;
    top: 30mm;
}

.mini {
    font-family: Manrope, sans-serif;
    font-size: 7pt;
    letter-spacing: 3px;
    color: {{ cor_dourado }};
    margin-bottom: 8mm;
}

h1 {
    font-family: Cormorant, Georgia, serif;
    font-size: 31pt;
    line-height: 0.98;
    font-weight: 500;
    color: {{ cor_navy }};
    margin: 0;
}

.linha {
    width: 25mm;
    height: 0.5mm;
    background: {{ cor_dourado }};
    margin-top: 10mm;
}

.codigo {
    margin-top: 10mm;
    font-family: Manrope, sans-serif;
    font-size: 8pt;
    letter-spacing: 2px;
    color: {{ cor_dourado }};
}

.endereco {
    margin-top: 6mm;
    font-family: Cormorant, Georgia, serif;
    font-size: 16pt;
    line-height: 1.1;
    color: {{ cor_navy }};
}

.descricao {
    margin-top: 19mm;
    font-family: Manrope, sans-serif;
    font-size: 8pt;
    line-height: 1.65;
    color: #666;
    max-width: 105mm;
}

/* === CORREÇÃO: texto lateral cabe inteiro dentro da barra navy === */
.rodape_esquerdo {
    position: absolute;
    left: 7mm;
    bottom: 28mm;
    color: {{ cor_claro }};
    font-family: Manrope, sans-serif;
    font-size: 5.8pt;
    letter-spacing: 1.2px;
    line-height: 1.55;
    width: 44mm;
    text-align: left;
}

.rodape_esquerdo_linha {
    width: 28mm;
    height: 0.3mm;
    background: rgba(255,255,255,0.28);
    margin-bottom: 5mm;
}

.rodape_direito {
    position: absolute;
    right: 25mm;
    bottom: 34mm;
    font-family: Manrope, sans-serif;
    font-size: 6pt;
    letter-spacing: 2px;
    color: {{ cor_dourado }};
}

</style>
</head>

<body>

<div class="pagina">

    <div class="lateral"></div>

    <div class="conteudo">

        <div class="mini">
            CONSULTORIA IMOBILIÁRIA
        </div>

        <div class="mini">
            DOCUMENTAÇÃO
        </div>

        <h1>
            Dossiê<br>
            Documental<br>
            do Imóvel
        </h1>

        <div class="linha"></div>

        <div class="codigo">
            {{ codigo }}
        </div>

        <div class="endereco">
            {% if endereco %}
                {{ endereco }}
            {% else %}
                Imóvel identificado<br>
                pelo código {{ codigo }}
            {% endif %}
        </div>

        <div class="descricao">
            Este documento reúne a documentação disponibilizada para análise
            da operação imobiliária, organizada em um único arquivo para
            facilitar a conferência das informações e proporcionar mais
            transparência durante o processo de compra.
        </div>

    </div>

    <div class="rodape_esquerdo">

        <div class="rodape_esquerdo_linha"></div>

        MATERIAL DOCUMENTAL

        <br><br>

        Os documentos apresentados neste dossiê correspondem aos arquivos
        disponibilizados para esta operação imobiliária.

        <br><br><br>

        CARVALHO FERREIRA

    </div>

    <div class="rodape_direito">
        {{ codigo }}
    </div>

</div>

</body>
</html>
"""


# =========================================================
# HTML — DOCUMENTO EM IMAGEM (estilo padronizado)
# =========================================================

HTML_IMAGEM = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">

<style>

@page {
    size: A4 portrait;
    margin: 0;
}

html, body {
    width: 210mm;
    height: 297mm;
    margin: 0;
    padding: 0;
}

body {
    background: #ffffff;
}

.pagina {
    width: 210mm;
    height: 297mm;
    box-sizing: border-box;
    position: relative;
    background: #ffffff;
    page-break-after: always;
}

.cabecalho {
    position: absolute;
    top: 11mm;
    left: 16mm;
    right: 16mm;
    font-family: Manrope, sans-serif;
    font-size: 6pt;
    letter-spacing: 1.8px;
    color: {{ cor_slate }};
}

.imagem {
    position: absolute;
    left: 16mm;
    right: 16mm;
    top: 24mm;
    bottom: 18mm;
    display: flex;
    align-items: center;
    justify-content: center;
}

.imagem img {
    max-width: 178mm;
    max-height: 255mm;
    width: auto;
    height: auto;
    object-fit: contain;
}

</style>
</head>

<body>

<div class="pagina">

    <div class="cabecalho">
        CARVALHO FERREIRA · DOSSIÊ DOCUMENTAL
        &nbsp;&nbsp;&nbsp;
        {{ codigo }}
    </div>

    <div class="imagem">
        <img src="{{ imagem }}">
    </div>

</div>

</body>
</html>
"""


# =========================================================
# HTML — SEPARADOR DO COMPRADOR
# =========================================================

HTML_SEPARADOR_COMPRADOR = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">

<style>

@page {
    size: A4 portrait;
    margin: 0;
}

html, body {
    width: 210mm;
    height: 297mm;
    margin: 0;
    padding: 0;
}

body {
    background: {{ cor_fundo }};
}

.pagina {
    width: 210mm;
    height: 297mm;
    box-sizing: border-box;
    position: relative;
    background: {{ cor_fundo }};
    page-break-after: always;
}

.lateral {
    position: absolute;
    left: 0;
    top: 0;
    width: 58mm;
    height: 297mm;
    background: {{ cor_navy }};
}

.conteudo {
    position: absolute;
    left: 75mm;
    right: 25mm;
    top: 65mm;
}

.mini {
    font-family: Manrope, sans-serif;
    font-size: 7pt;
    letter-spacing: 3px;
    color: {{ cor_dourado }};
    margin-bottom: 10mm;
}

h1 {
    font-family: Cormorant, Georgia, serif;
    font-size: 29pt;
    line-height: 1.05;
    font-weight: 500;
    color: {{ cor_navy }};
    margin: 0;
}

.linha {
    width: 25mm;
    height: 0.5mm;
    background: {{ cor_dourado }};
    margin-top: 10mm;
}

.texto {
    margin-top: 18mm;
    font-family: Manrope, sans-serif;
    font-size: 9pt;
    line-height: 1.7;
    color: #555;
    max-width: 100mm;
}

.rodape {
    position: absolute;
    left: 75mm;
    right: 25mm;
    bottom: 22mm;
    font-family: Manrope, sans-serif;
    font-size: 7pt;
    letter-spacing: 2px;
    color: {{ cor_slate }};
}

</style>
</head>

<body>

<div class="pagina">

    <div class="lateral"></div>

    <div class="conteudo">

        <div class="mini">
            DOCUMENTAÇÃO COMPLEMENTAR
        </div>

        <h1>
            DOCUMENTOS<br>
            DO COMPRADOR
        </h1>

        <div class="linha"></div>

        <div class="texto">
            A documentação apresentada a partir desta página corresponde
            aos documentos disponibilizados pelo comprador para esta
            operação imobiliária.
        </div>

    </div>

    <div class="rodape">
        CARVALHO FERREIRA · DOSSIÊ DOCUMENTAL
    </div>

</div>

</body>
</html>
"""


# =========================================================
# HTML — ENCERRAMENTO (texto lateral corrigido)
# =========================================================

HTML_ENCERRAMENTO = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">

<style>

@page {
    size: A4 portrait;
    margin: 0;
}

html, body {
    width: 210mm;
    height: 297mm;
    margin: 0;
    padding: 0;
}

body {
    background: {{ cor_fundo }};
}

.pagina {
    width: 210mm;
    height: 297mm;
    box-sizing: border-box;
    position: relative;
    background: {{ cor_fundo }};
}

.lateral {
    position: absolute;
    left: 0;
    top: 0;
    width: 58mm;
    height: 297mm;
    background: {{ cor_navy }};
}

.conteudo {
    position: absolute;
    left: 75mm;
    right: 25mm;
    top: 38mm;
}

.mini {
    font-family: Manrope, sans-serif;
    font-size: 7pt;
    letter-spacing: 3px;
    color: {{ cor_dourado }};
    margin-bottom: 9mm;
}

h1 {
    font-family: Cormorant, Georgia, serif;
    font-size: 31pt;
    line-height: 1;
    font-weight: 500;
    color: {{ cor_navy }};
    margin: 0;
}

.subtitulo {
    margin-top: 10mm;
    font-family: Manrope, sans-serif;
    font-size: 10pt;
    color: #555;
}

.texto {
    margin-top: 15mm;
    font-family: Manrope, sans-serif;
    font-size: 8pt;
    line-height: 1.7;
    color: #666;
    max-width: 105mm;
}

.atendimento {
    display: flex;
    gap: 18mm;
    margin-top: 18mm;
}

.bloco {
    width: 48mm;
}

.rotulo {
    font-family: Manrope, sans-serif;
    font-size: 6pt;
    letter-spacing: 2px;
    color: {{ cor_dourado }};
    margin-bottom: 4mm;
}

.nome {
    font-family: Manrope, sans-serif;
    font-size: 9pt;
    color: {{ cor_navy }};
    margin-bottom: 2mm;
}

.contato {
    font-family: Manrope, sans-serif;
    font-size: 7pt;
    color: #666;
}

.lgpd {
    position: absolute;
    left: 75mm;
    right: 25mm;
    bottom: 32mm;
    font-family: Manrope, sans-serif;
    font-size: 6.5pt;
    line-height: 1.6;
    color: #777;
}

/* === CORREÇÃO: marca lateral cabe inteira === */
.marca {
    position: absolute;
    left: 7mm;
    bottom: 28mm;
    font-family: Manrope, sans-serif;
    font-size: 5.5pt;
    letter-spacing: 1.3px;
    line-height: 1.45;
    color: {{ cor_claro }};
    width: 44mm;
}

</style>
</head>

<body>

<div class="pagina">

    <div class="lateral"></div>

    <div class="conteudo">

        <div class="mini">
            CARVALHO FERREIRA
        </div>

        <h1>
            Análise e<br>
            Atendimento
        </h1>

        <div class="subtitulo">
            Transparência faz parte do nosso trabalho.
        </div>

        <div class="texto">
            Este dossiê foi organizado para facilitar a análise documental
            da operação imobiliária e reunir, em um único arquivo, os
            documentos disponibilizados para conferência.
            <br><br>
            Sempre que necessário, recomendamos que a documentação seja
            também analisada pelos profissionais de confiança das partes
            envolvidas.
        </div>

        <div class="atendimento">

            <div class="bloco">

                <div class="rotulo">
                    ATENDIMENTO
                </div>

                <div class="nome">
                    Fernando Carvalho
                </div>

                <div class="contato">
                    WhatsApp · 12 98816-2626
                </div>

            </div>

            <div class="bloco">

                <div class="rotulo">
                    CORRETOR
                </div>

                <div class="nome">
                    Valdir Ferreira
                </div>

                <div class="contato">
                    WhatsApp · 12 99215-7474
                </div>

            </div>

        </div>

    </div>

    <div class="lgpd">
        Este material pode conter dados pessoais e documentos de caráter
        privado. Seu conteúdo é disponibilizado exclusivamente para análise
        da operação imobiliária e deve ser tratado com confidencialidade,
        observando a legislação aplicável, inclusive a Lei nº 13.709/2018
        (Lei Geral de Proteção de Dados - LGPD).
    </div>

    <div class="marca">
        CARVALHO FERREIRA<br>
        CONSULTORIA IMOBILIÁRIA
    </div>

</div>

</body>
</html>
"""


# =========================================================
# PROCESSAMENTO E NORMALIZAÇÃO DE PDFS A4
# (fundo BRANCO + cabeçalho)
# =========================================================

def _criar_pagina_com_fundo_e_cabecalho(codigo_imovel):
    """
    Cria uma página A4 em branco puro com o cabeçalho
    padronizado, usando reportlab.
    Retorna os bytes do PDF de 1 página.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    largura, altura = A4

    # Fundo branco puro
    c.setFillColor(HexColor("#ffffff"))
    c.rect(0, 0, largura, altura, fill=1, stroke=0)

    # Cabeçalho
    c.setFillColor(HexColor(COR_SLATE))
    c.setFont("Helvetica", 7)
    texto_cabecalho = f"CARVALHO FERREIRA · DOSSIÊ DOCUMENTAL    {str(codigo_imovel).upper()}"
    c.drawString(45, altura - 32, texto_cabecalho)

    c.save()
    buffer.seek(0)
    return buffer.getvalue()


def normalizar_pdf_para_a4(conteudo_pdf, codigo_imovel):
    """
    Recebe os bytes de um PDF e força todas as páginas
    para A4 vertical, com fundo BRANCO + cabeçalho
    padronizado (mesmo estilo das páginas de imagem).
    """

    reader = PdfReader(io.BytesIO(conteudo_pdf))
    writer = PdfWriter()

    largura_a4 = float(A4[0])
    altura_a4 = float(A4[1])

    # Página modelo com fundo + cabeçalho
    pagina_modelo_bytes = _criar_pagina_com_fundo_e_cabecalho(codigo_imovel)
    modelo_reader = PdfReader(io.BytesIO(pagina_modelo_bytes))
    pagina_modelo = modelo_reader.pages[0]

    for pagina in reader.pages:

        largura_orig = float(pagina.mediabox.width)
        altura_orig = float(pagina.mediabox.height)

        rotacao = pagina.get("/Rotate", 0)

        if rotacao in [90, 270]:
            largura_orig, altura_orig = altura_orig, largura_orig

        # Margens um pouco maiores para ficar elegante com o cabeçalho
        margem_x = 28.0
        margem_topo = 48.0   # espaço para o cabeçalho
        margem_baixo = 28.0

        largura_util = largura_a4 - (2 * margem_x)
        altura_util = altura_a4 - margem_topo - margem_baixo

        escala_x = largura_util / largura_orig if largura_orig > 0 else 1.0
        escala_y = altura_util / altura_orig if altura_orig > 0 else 1.0
        escala = min(escala_x, escala_y)

        largura_redim = largura_orig * escala
        altura_redim = altura_orig * escala

        offset_x = (largura_a4 - largura_redim) / 2.0
        offset_y = margem_baixo + (altura_util - altura_redim) / 2.0

        # Nova página = cópia do modelo (fundo + cabeçalho)
        nova_pagina = PageObject.create_blank_page(
            width=largura_a4,
            height=altura_a4,
        )
        nova_pagina.merge_page(pagina_modelo)

        # Conteúdo original escalado e centralizado
        transformacao = (
            Transformation()
            .scale(escala, escala)
            .translate(offset_x, offset_y)
        )

        pagina_copia = PageObject.create_blank_page(
            width=largura_orig,
            height=altura_orig,
        )
        pagina_copia.merge_page(pagina)
        pagina_copia.add_transformation(transformacao)

        nova_pagina.merge_page(pagina_copia)
        writer.add_page(nova_pagina)

    saida = io.BytesIO()
    writer.write(saida)
    return saida.getvalue()


# =========================================================
# RENDERIZADORES
# =========================================================

def html_para_pdf(html):
    buffer = io.BytesIO()

    weasyprint.HTML(
        string=html,
        base_url=str(SCRIPT_DIR),
    ).write_pdf(
        buffer
    )

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

    logo = buscar_logo_local()

    contexto = {
        "codigo": codigo,
        "endereco": endereco_final,
        "logo": logo,
        "cor_fundo": COR_FUNDO,
        "cor_navy": COR_NAVY,
        "cor_claro": COR_CLARO,
        "cor_slate": COR_SLATE,
        "cor_dourado": COR_DOURADO,
        "cor_linha": COR_LINHA,

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

    return html_para_pdf(
        html
    )


def preparar_imagem_para_pdf(
    conteudo_imagem,
):
    imagem = Image.open(
        io.BytesIO(
            conteudo_imagem
        )
    )

    imagem = ImageOps.exif_transpose(
        imagem
    )

    if imagem.mode in (
        "RGBA",
        "LA",
        "P",
    ):

        fundo = Image.new(
            "RGB",
            imagem.size,
            "white",
        )

        if imagem.mode == "P":
            imagem = imagem.convert(
                "RGBA"
            )

        fundo.paste(
            imagem,
            mask=(
                imagem.getchannel("A")
                if "A"
                in imagem.getbands()
                else None
            ),
        )

        imagem = fundo

    else:

        imagem = imagem.convert(
            "RGB"
        )

    buffer = io.BytesIO()

    imagem.save(
        buffer,
        format="JPEG",
        quality=95,
        optimize=True,
    )

    return buffer.getvalue()


def gerar_pagina_imagem_pdf_bytes(
    conteudo_imagem,
    codigo_imovel,
):
    imagem_processada = (
        preparar_imagem_para_pdf(
            conteudo_imagem
        )
    )

    imagem_uri = bytes_para_data_uri(
        imagem_processada,
        "image/jpeg",
    )

    contexto = {
        "codigo": str(
            codigo_imovel
        ).upper(),

        "imagem": imagem_uri,

        "cor_fundo": COR_FUNDO,
        "cor_slate": COR_SLATE,
        "cor_dourado": COR_DOURADO,
        "cor_linha": COR_LINHA,

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

    return html_para_pdf(
        html
    )


def gerar_separador_comprador_pdf_bytes(
    codigo_imovel,
):
    contexto = {
        "codigo": str(
            codigo_imovel
        ).upper(),

        "cor_fundo": COR_FUNDO,
        "cor_navy": COR_NAVY,
        "cor_slate": COR_SLATE,
        "cor_dourado": COR_DOURADO,
        "cor_linha": COR_LINHA,
    }

    html = Template(
        HTML_SEPARADOR_COMPRADOR
    ).render(
        **contexto
    )

    return html_para_pdf(
        html
    )


def gerar_encerramento_pdf_bytes():
    contexto = {
        "cor_fundo": COR_FUNDO,
        "cor_navy": COR_NAVY,
        "cor_claro": COR_CLARO,
        "cor_slate": COR_SLATE,
        "cor_dourado": COR_DOURADO,
        "cor_linha": COR_LINHA,

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

    return html_para_pdf(
        html
    )


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

    for pagina in reader.pages:
        writer.add_page(
            pagina
        )

    return len(
        reader.pages
    )


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
# PROCESSAMENTO DE CADA DOCUMENTO
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

    conteudo = baixar_bytes(
        service,
        file_id,
    )

    if not conteudo:
        raise ValueError(
            "Arquivo baixado sem conteúdo."
        )

    # PDF
    if (
        mime == "application/pdf"
        or extensao == ".pdf"
    ):

        pdf_normalizado = (
            normalizar_pdf_para_a4(
                conteudo,
                codigo_imovel,
            )
        )

        reader = PdfReader(
            io.BytesIO(
                pdf_normalizado
            )
        )

        if len(reader.pages) == 0:
            raise ValueError(
                "PDF sem páginas."
            )

        return (
            pdf_normalizado,
            len(reader.pages),
        )

    # Imagem
    if extensao in {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
    }:

        pdf_bytes = (
            gerar_pagina_imagem_pdf_bytes(
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
        # LOCALIZA A PASTA PRINCIPAL DOCUMENTOS
        # -------------------------------------------------

        id_documentos = (
            localizar_pasta_documentacao(
                drive,
                codigo,
            )
        )

        # -------------------------------------------------
        # DOCUMENTOS PRINCIPAIS
        # -------------------------------------------------

        arquivos = (
            listar_arquivos_documentacao(
                drive,
                id_documentos,
            )
        )

        # -------------------------------------------------
        # SUBPASTA DO COMPRADOR
        # -------------------------------------------------

        (
            id_pasta_comprador,
            nome_pasta_comprador,
        ) = localizar_pasta_comprador(
            drive,
            id_documentos,
        )

        arquivos_comprador = (
            listar_arquivos_comprador(
                drive,
                id_pasta_comprador,
            )
        )

        # -------------------------------------------------
        # TOTAL
        # -------------------------------------------------

        total_documentos_encontrados = (
            len(arquivos)
            + len(arquivos_comprador)
        )

        # Se não existir nenhum documento em nenhuma
        # das duas seções, realmente não há dossiê.
        if total_documentos_encontrados == 0:

            return {
                "sucesso": False,
                "pdf": None,
                "nome_arquivo": None,
                "documentos_encontrados": 0,
                "documentos_processados": 0,
                "paginas": 0,
                "falhas": [],
                "mensagem": (
                    f"Nenhum documento PDF ou imagem "
                    f"foi encontrado na pasta "
                    f"'documentos' do {codigo}."
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
            partes.append(
                normalizar(
                    cidade
                ).title()
            )

        nome_arquivo = (
            " - ".join(partes)
            + ".pdf"
        )

        # -------------------------------------------------
        # PDF
        # -------------------------------------------------

        pdfs = []

        capa = gerar_capa_pdf_bytes(
            codigo,
            dados_imovel,
        )

        pdfs.append(
            capa
        )

        falhas = []

        documentos_processados = 0

        paginas_documentos = 0

        detalhes = []

        # =================================================
        # 1 — DOCUMENTOS PRINCIPAIS
        # =================================================

        for numero, arquivo in enumerate(
            arquivos,
            start=1,
        ):

            try:

                (
                    pdf_documento,
                    paginas,
                ) = processar_documento(
                    drive,
                    arquivo,
                    codigo,
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
                        "paginas": paginas,
                        "status": "OK",
                        "secao": (
                            "DOCUMENTOS PRINCIPAIS"
                        ),
                    }
                )

            except Exception as erro:

                falha = {
                    "nome": arquivo["nome"],
                    "erro": str(erro),
                    "secao": (
                        "DOCUMENTOS PRINCIPAIS"
                    ),
                }

                falhas.append(
                    falha
                )

                detalhes.append(
                    {
                        "numero": numero,
                        "nome": arquivo["nome"],
                        "paginas": 0,
                        "status": "ERRO",
                        "erro": str(erro),
                        "secao": (
                            "DOCUMENTOS PRINCIPAIS"
                        ),
                    }
                )

        # =================================================
        # 2 — DOCUMENTOS DO COMPRADOR
        # =================================================

        if arquivos_comprador:

            # Página separadora.
            separador = (
                gerar_separador_comprador_pdf_bytes(
                    codigo
                )
            )

            pdfs.append(
                separador
            )

            for numero, arquivo in enumerate(
                arquivos_comprador,
                start=1,
            ):

                try:

                    (
                        pdf_documento,
                        paginas,
                    ) = processar_documento(
                        drive,
                        arquivo,
                        codigo,
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
                            "paginas": paginas,
                            "status": "OK",
                            "secao": (
                                "DOCUMENTOS DO COMPRADOR"
                            ),
                        }
                    )

                except Exception as erro:

                    falha = {
                        "nome": arquivo["nome"],
                        "erro": str(erro),
                        "secao": (
                            "DOCUMENTOS DO COMPRADOR"
                        ),
                    }

                    falhas.append(
                        falha
                    )

                    detalhes.append(
                        {
                            "numero": numero,
                            "nome": arquivo["nome"],
                            "paginas": 0,
                            "status": "ERRO",
                            "erro": str(erro),
                            "secao": (
                                "DOCUMENTOS DO COMPRADOR"
                            ),
                        }
                    )

        # =================================================
        # 3 — ENCERRAMENTO
        # =================================================

        encerramento = (
            gerar_encerramento_pdf_bytes()
        )

        pdfs.append(
            encerramento
        )

        # =================================================
        # 4 — CONSOLIDAÇÃO
        # =================================================

        pdf_final, total_paginas = (
            consolidar_pdfs(
                pdfs
            )
        )

        # =================================================
        # MENSAGEM
        # =================================================

        if (
            falhas
            and documentos_processados == 0
        ):

            mensagem = (
                f"Falha ao processar os arquivos "
                f"do dossiê {codigo}."
            )

            sucesso = False

        elif falhas:

            mensagem = (
                f"Dossiê gerado parcialmente. "
                f"{documentos_processados} de "
                f"{total_documentos_encontrados} "
                f"documentos incorporados."
            )

            sucesso = True

        else:

            mensagem = (
                f"Dossiê gerado com sucesso! "
                f"{documentos_processados} "
                f"documentos incorporados em "
                f"{total_paginas} páginas."
            )

            sucesso = True

        # =================================================
        # RETORNO
        # =================================================

        return {
            "sucesso": sucesso,

            "pdf": pdf_final,

            "nome_arquivo": nome_arquivo,

            "documentos_encontrados": (
                total_documentos_encontrados
            ),

            "documentos_processados": (
                documentos_processados
            ),

            "paginas": total_paginas,

            "falhas": falhas,

            "detalhes": detalhes,

            "pasta_documentos": "DOCUMENTOS",

            "pasta_comprador": (
                nome_pasta_comprador
                or ""
            ),

            "documentos_principais": (
                len(arquivos)
            ),

            "documentos_comprador": (
                len(arquivos_comprador)
            ),

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
