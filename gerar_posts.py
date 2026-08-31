# -*- coding: utf-8 -*-

import io
import zipfile
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from weasyprint import HTML
import fitz


SCRIPT_DIR = Path(__file__).resolve().parent


# =============================================================================
# CONFIGURAÇÃO
# =============================================================================

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]

ID_RAIZ = "1NaZ7kv_jHVCTlLV8vqxCzBwbTX5y3fR7"
ID_PASTA_MARCA = "19b_7n4ER-hmFyhvMmFIO1pBmPlRu85aA"

SPREADSHEET_ID = "1nVEpOZFYFKcq0MXtOwxn22nqxafmJBHnf6zhHQlyT8w"
NOME_ABA = "Imoveis"

COR_AZUL_ESCURO = "#0A1F2E"
COR_AZUL_BLOCO = "#0D2538"
COR_OFF_WHITE = "#F7F5F0"
COR_AZUL_SUAVE = "#94A3B8"
COR_LINHA = "#26384A"


# =============================================================================
# CONEXÃO GOOGLE
# =============================================================================

def conectar_google():

    try:

        import streamlit as st

        creds_dict = dict(
            st.secrets["google_credentials"]
        )

        creds = (
            service_account
            .Credentials
            .from_service_account_info(
                creds_dict,
                scopes=SCOPES,
            )
        )

        drive = build(
            "drive",
            "v3",
            credentials=creds,
        )

        sheets = build(
            "sheets",
            "v4",
            credentials=creds,
        )

        return drive, sheets

    except Exception as e:

        print(
            f"Erro ao autenticar Google: {e}",
            flush=True,
        )

        return None, None


# =============================================================================
# DRIVE
# =============================================================================

def buscar_id_por_nome(
    service,
    nome_item,
    id_pasta_pai,
):

    if not service or not id_pasta_pai:
        return None

    try:

        results = service.files().list(
            q=(
                f"'{id_pasta_pai}' in parents "
                f"and name = '{nome_item}' "
                f"and trashed = false"
            ),
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()

        files = results.get(
            "files",
            [],
        )

        return (
            files[0]["id"]
            if files
            else None
        )

    except Exception as e:

        print(
            f"Erro ao buscar '{nome_item}': {e}",
            flush=True,
        )

        return None


def buscar_pasta_imovel_por_codigo(
    service,
    codigo,
    id_imoveis,
):

    codigo = (
        codigo
        .strip()
        .upper()
    )

    try:

        results = service.files().list(
            q=(
                f"'{id_imoveis}' in parents "
                f"and mimeType = "
                f"'application/vnd.google-apps.folder' "
                f"and name contains '{codigo}' "
                f"and trashed = false"
            ),
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()

        files = results.get(
            "files",
            [],
        )

        for f in files:

            nome = (
                f["name"]
                .strip()
                .upper()
            )

            if (
                nome == codigo
                or nome.startswith(
                    codigo + " "
                )
                or nome.startswith(
                    codigo + "-"
                )
            ):

                return f["id"]

        return (
            files[0]["id"]
            if files
            else None
        )

    except Exception as e:

        print(
            f"Erro ao buscar pasta do imóvel: {e}",
            flush=True,
        )

        return None


def obter_id_pasta_imovel(
    service,
    codigo,
):

    id_portfolio = buscar_id_por_nome(
        service,
        "PORTFOLIO",
        ID_RAIZ,
    )

    if not id_portfolio:
        return None

    id_imoveis = buscar_id_por_nome(
        service,
        "IMOVEIS",
        id_portfolio,
    )

    if not id_imoveis:
        return None

    return buscar_pasta_imovel_por_codigo(
        service,
        codigo,
        id_imoveis,
    )


def baixar_arquivo_bytes(
    service,
    id_arquivo,
):

    try:

        request = service.files().get_media(
            fileId=id_arquivo
        )

        buffer = io.BytesIO()

        downloader = MediaIoBaseDownload(
            buffer,
            request,
        )

        done = False

        while not done:

            _, done = downloader.next_chunk()

        buffer.seek(0)

        return buffer.getvalue()

    except Exception as e:

        print(
            f"Erro ao baixar arquivo: {e}",
            flush=True,
        )

        return None


# =============================================================================
# ATIVOS DA MARCA
# =============================================================================

def baixar_ativo_marca_bytes(
    service,
    subpasta,
    nome_arquivo,
):

    id_sub = buscar_id_por_nome(
        service,
        subpasta,
        ID_PASTA_MARCA,
    )

    if not id_sub:
        return None

    id_arq = buscar_id_por_nome(
        service,
        nome_arquivo,
        id_sub,
    )

    if not id_arq:
        return None

    return baixar_arquivo_bytes(
        service,
        id_arq,
    )


def fonte_uri(
    service,
    nome,
):

    dados = baixar_ativo_marca_bytes(
        service,
        "FONTES",
        nome,
    )

    if not dados:
        return ""

    import base64

    encoded = base64.b64encode(
        dados
    ).decode("ascii")

    return (
        "data:font/ttf;base64,"
        + encoded
    )


def montar_css_fontes(
    service,
):

    itens = [
        (
            "CormorantGaramond-Medium.ttf",
            "Cormorant Garamond",
            500,
        ),
        (
            "CormorantGaramond-SemiBold.ttf",
            "Cormorant Garamond",
            600,
        ),
        (
            "Manrope-Regular.ttf",
            "Manrope",
            400,
        ),
        (
            "Manrope-Medium.ttf",
            "Manrope",
            500,
        ),
        (
            "Manrope-SemiBold.ttf",
            "Manrope",
            600,
        ),
    ]

    blocos = []

    for arq, fam, peso in itens:

        uri = fonte_uri(
            service,
            arq,
        )

        if uri:

            blocos.append(
                f"""
                @font-face {{
                    font-family: '{fam}';
                    src: url('{uri}') format('truetype');
                    font-weight: {peso};
                    font-style: normal;
                }}
                """
            )

    return "\n".join(blocos)


def buscar_logo_bytes(
    service,
):

    id_logo = buscar_id_por_nome(
        service,
        "LOGO",
        ID_PASTA_MARCA,
    )

    if not id_logo:
        return None

    results = service.files().list(
        q=(
            f"'{id_logo}' in parents "
            f"and trashed = false"
        ),
        fields="files(id, name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()

    for f in results.get(
        "files",
        [],
    ):

        extensao = (
            Path(
                f["name"]
            )
            .suffix
            .lower()
        )

        if extensao in {
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
        }:

            return baixar_arquivo_bytes(
                service,
                f["id"],
            )

    return None


def carregar_icone_bytes(
    service,
    nome_arquivo,
    cor=None,
):

    dados = baixar_ativo_marca_bytes(
        service,
        "ICONES",
        nome_arquivo,
    )

    if not dados:
        return ""

    try:

        svg = dados.decode(
            "utf-8"
        )

    except Exception:

        return ""

    if cor:

        for antigo in [
            "currentColor",
            "#000000",
            "#000",
            "black",
            "#111111",
            "#1a1a1a",
        ]:

            svg = svg.replace(
                antigo,
                cor,
            )

    return svg


def icone_pin(
    service,
    cor,
):

    svg = carregar_icone_bytes(
        service,
        "localizacao.svg",
        cor,
    )

    if svg:
        return svg

    return f"""
    <svg width="20" height="20"
         viewBox="0 0 24 24"
         fill="none"
         stroke="{cor}"
         stroke-width="2"
         stroke-linecap="round"
         stroke-linejoin="round">

        <path d="M21 10c0 7-9 13-9 13S3 17 3 10a9 9 0 1 1 18 0z"></path>

        <circle cx="12" cy="10" r="3"></circle>

    </svg>
    """


# =============================================================================
# PLANILHA
# =============================================================================

def normalizar(
    texto,
):

    if not texto:
        return ""

    return " ".join(
        str(texto)
        .strip()
        .upper()
        .split()
    )


def ler_dados_sheets(
    sheets,
    codigo,
):

    result = (
        sheets
        .spreadsheets()
        .values()
        .get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"'{NOME_ABA}'!A:Z",
        )
        .execute()
    )

    rows = result.get(
        "values",
        [],
    )

    if not rows:
        return {}

    cab = [
        normalizar(h)
        for h in rows[0]
    ]

    cod = normalizar(
        codigo
    )

    for row in rows[1:]:

        if not row:
            continue

        while len(row) < len(cab):
            row.append("")

        if normalizar(
            row[0]
        ) == cod:

            return {
                cab[i]: row[i]
                for i in range(
                    len(cab)
                )
            }

    return {}


def get_dado(
    dados,
    *chaves,
    default="-",
):

    for c in chaves:

        v = dados.get(
            normalizar(c),
            "",
        )

        if v not in (
            "",
            None,
        ):

            return v

    return default


# =============================================================================
# FOTOS
# =============================================================================

def carregar_fotos(
    drive,
    codigo,
):

    id_imovel = obter_id_pasta_imovel(
        drive,
        codigo,
    )

    if not id_imovel:
        return []

    id_fotos = buscar_id_por_nome(
        drive,
        "FOTOS TRATADAS",
        id_imovel,
    )

    if not id_fotos:

        id_fotos = buscar_id_por_nome(
            drive,
            "FOTOS SELECIONADAS",
            id_imovel,
        )

    if not id_fotos:
        id_fotos = id_imovel

    files = []

    token = None

    while True:

        resp = drive.files().list(
            q=(
                f"'{id_fotos}' in parents "
                f"and trashed = false"
            ),
            fields=(
                "nextPageToken, "
                "files(id, name, mimeType)"
            ),
            orderBy="name",
            pageToken=token,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()

        files.extend(
            resp.get(
                "files",
                [],
            )
        )

        token = resp.get(
            "nextPageToken"
        )

        if not token:
            break

    fotos = []

    for f in sorted(
        files,
        key=lambda x: x[
            "name"
        ].lower(),
    ):

        if not f.get(
            "mimeType",
            "",
        ).startswith(
            "image/"
        ):

            continue

        dados = baixar_arquivo_bytes(
            drive,
            f["id"],
        )

        if dados:

            fotos.append(
                {
                    "nome": f[
                        "name"
                    ],
                    "bytes": dados,
                }
            )

    return fotos


# =============================================================================
# IMAGENS EM MEMÓRIA
# =============================================================================

def imagem_uri(
    dados,
    nome,
):

    import base64

    extensao = (
        Path(nome)
        .suffix
        .lower()
    )

    mime = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(
        extensao,
        "image/jpeg",
    )

    encoded = base64.b64encode(
        dados
    ).decode("ascii")

    return (
        f"data:{mime};base64,"
        f"{encoded}"
    )


def logo_uri(
    dados,
):

    if not dados:
        return ""

    import base64

    encoded = base64.b64encode(
        dados
    ).decode("ascii")

    return (
        "data:image/png;base64,"
        + encoded
    )


# =============================================================================
# RENDERIZAÇÃO
# =============================================================================

def renderizar_png(
    html_string,
    largura,
    altura,
):

    pdf_buffer = io.BytesIO()

    HTML(
        string=html_string,
        base_url=str(SCRIPT_DIR),
    ).write_pdf(
        pdf_buffer
    )

    pdf_buffer.seek(0)

    doc = fitz.open(
        stream=pdf_buffer.getvalue(),
        filetype="pdf",
    )

    page = doc[0]

    matriz = fitz.Matrix(
        largura / page.rect.width,
        altura / page.rect.height,
    )

    pix = page.get_pixmap(
        matrix=matriz,
        alpha=False,
    )

    png_bytes = pix.tobytes(
        "png"
    )

    doc.close()

    pdf_buffer.close()

    return png_bytes


# =============================================================================
# CSS CARD
# =============================================================================

def css_card_principal():

    return f"""
    .card-fundo {{
        position: absolute;
        left: 0;
        bottom: 0px;
        width: 775px;
        height: 397px;
        background: {COR_OFF_WHITE};
        z-index: 2;
    }}

    .card-azul {{
        position: absolute;
        left: 0;
        bottom: 36px;
        width: 875px;
        height: 341px;
        background: {COR_AZUL_ESCURO};
        z-index: 3;
        padding: 48px 55px 38px 55px;
        color: {COR_OFF_WHITE};
    }}

    .card-conteudo {{
        position: relative;
        z-index: 5;
    }}
    """


# =============================================================================
# LÂMINAS
# =============================================================================

def gerar_lamina_capa(
    ctx,
    foto,
):

    nome_html = (
        f"<span class='nome'>{ctx['titulo_3']}</span>"
        if ctx["titulo_3"]
        else ""
    )

    foto_uri = imagem_uri(
        foto["bytes"],
        foto["nome"],
    )

    condominio_html = (
        f"<div class='condominio-texto'>Condomínio: {ctx['condominio']}</div>"
        if ctx["condominio"] and ctx["condominio"] != "-"
        else ""
    )

    html = f"""
    <html>
    <head>
    <meta charset="UTF-8">

    <style>

    {ctx['css_fontes']}

    @page {{
        size: 1080px 1350px;
        margin: 0;
    }}

    * {{
        box-sizing: border-box;
    }}

    body {{
        margin: 0;
        width: 1080px;
        height: 1350px;
        background: {COR_OFF_WHITE};
        overflow: hidden;
        font-family: 'Manrope', Arial, sans-serif;
    }}

    .foto {{
        position: absolute;
        top: 0;
        left: 0;
        width: 1080px;
        height: 1350px;
        padding: 20px;
        box-sizing: border-box;
        object-fit: contain;
        display: block;
    }}

    {css_card_principal()}

    .titulo {{
        font-size: 39px;
        line-height: 1.15;
        margin: 0;
    }}

    .tipo {{
        font-family: 'Cormorant Garamond', Georgia, serif;
        font-size: 38px;
        font-weight: 500;
        letter-spacing: 2px;
        text-transform: uppercase;
        color: {COR_OFF_WHITE};
    }}

    .destaque {{
        font-family: 'Cormorant Garamond', Georgia, serif;
        font-size: 45px;
        font-weight: 500;
        letter-spacing: 2px;
        text-transform: uppercase;
        color: {COR_OFF_WHITE};
    }}

    .nome {{
        display: block;
        margin-top: 4px;
        font-size: 28px;
        color: {COR_OFF_WHITE};
    }}

    .local {{
        margin-top: 24px;
        font-size: 18px;
        letter-spacing: 1px;
        text-transform: uppercase;
        color: {COR_AZUL_SUAVE};
        display: flex;
        align-items: center;
        gap: 9px;
    }}

    .valor {{
        margin-top: 23px;
        font-size: 43px;
        font-weight: 600;
        color: {COR_OFF_WHITE};
    }}

    .condominio-texto {{
        margin-top: 4px;
        font-size: 16px;
        color: {COR_AZUL_SUAVE};
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}

    .linha {{
        width: 100%;
        height: 1px;
        background: {COR_LINHA};
        margin-top: 27px;
        margin-bottom: 19px;
    }}

    .rodape {{
        font-size: 13px;
        letter-spacing: 1.8px;
    }}

    .marca {{
        float: left;
        color: {COR_OFF_WHITE};
        font-weight: 600;
    }}

    .deslize {{
        float: right;
        color: {COR_AZUL_SUAVE};
        font-weight: 500;
    }}

    </style>
    </head>

    <body>

        <img class="foto" src="{foto_uri}">

        <div class="card-fundo"></div>

        <div class="card-azul">

            <div class="card-conteudo">

                <div class="titulo">

                    <span class="tipo">
                        {ctx['titulo_1']}
                    </span>

                    <span class="destaque">
                        {ctx['titulo_2']}
                    </span>

                    {nome_html}

                </div>

                <div class="local">

                    {ctx['pin']}

                    <span>
                        {ctx['bairro']} • {ctx['cidade']}
                    </span>

                </div>

                <div class="valor">
                    {ctx['valor']}
                </div>

                {condominio_html}

                <div class="linha"></div>

                <div class="rodape">

                    <span class="marca">
                        CARVALHO FERREIRA
                    </span>

                    <span class="deslize">
                        DESLIZE PARA CONHECER
                    </span>

                </div>

            </div>

        </div>

    </body>
    </html>
    """

    return renderizar_png(
        html,
        1080,
        1350,
    )


def gerar_lamina_foto(
    ctx,
    foto,
):

    foto_uri = imagem_uri(
        foto["bytes"],
        foto["nome"],
    )

    html = f"""
    <html>
    <head>
    <meta charset="UTF-8">

    <style>

    {ctx['css_fontes']}

    @page {{
        size: 1080px 1350px;
        margin: 0;
    }}

    * {{
        box-sizing: border-box;
    }}

    body {{
        margin: 0;
        width: 1080px;
        height: 1350px;
        background: {COR_OFF_WHITE};
        overflow: hidden;
        font-family: 'Manrope', Arial, sans-serif;
    }}

    .foto {{
        position: absolute;
        top: 0;
        left: 0;
        width: 1080px;
        height: 1350px;
        object-fit: cover;
    }}

    .barra-inferior {{
        position: absolute;
        bottom: 0;
        left: 0;
        width: 100%;
        height: 90px;
        background: {COR_AZUL_ESCURO};
        color: {COR_OFF_WHITE};
        padding: 31px 55px;
    }}

    .marca {{
        font-size: 13px;
        font-weight: 600;
        letter-spacing: 2px;
    }}

    </style>
    </head>

    <body>

        <img class="foto" src="{foto_uri}">

        <div class="barra-inferior">
            <div class="marca">
                CARVALHO FERREIRA
            </div>
        </div>

    </body>
    </html>
    """

    return renderizar_png(
        html,
        1080,
        1350,
    )


def gerar_lamina_ficha(
    ctx,
):

    html = f"""
    <html>
    <head>
    <meta charset="UTF-8">

    <style>

    {ctx['css_fontes']}

    @page {{
        size: 1080px 1350px;
        margin: 0;
    }}

    * {{
        box-sizing: border-box;
    }}

    body {{
        margin: 0;
        width: 1080px;
        height: 1350px;
        padding: 70px 65px;
        background: {COR_AZUL_ESCURO};
        color: {COR_OFF_WHITE};
        font-family: 'Manrope', Arial, sans-serif;
        overflow: hidden;
    }}

    .titulo {{
        font-size: 39px;
        font-weight: 500;
        letter-spacing: 2px;
        margin-bottom: 55px;
    }}

    .grid {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 22px;
        width: 100%;
    }}

    .card {{
        height: 245px;
        background: {COR_AZUL_BLOCO};
        padding: 30px 32px;
        color: {COR_OFF_WHITE};
        position: relative;
        overflow: hidden;
    }}

    .icone {{
        height: 34px;
        margin-bottom: 26px;
    }}

    .icone svg {{
        width: 31px;
        height: 31px;
    }}

    .label {{
        font-size: 15px;
        letter-spacing: 2px;
        text-transform: uppercase;
        color: {COR_AZUL_SUAVE};
        font-weight: 500;
    }}

    .valor {{
        margin-top: 9px;
        font-size: 37px;
        font-weight: 600;
        color: {COR_OFF_WHITE};
        line-height: 1;
    }}

    .rodape {{
        position: absolute;
        left: 65px;
        right: 65px;
        bottom: 50px;
        padding-top: 22px;
        border-top: 1px solid #D8DDE2;
        font-size: 13px;
        letter-spacing: 2px;
        color: {COR_AZUL_SUAVE};
        text-transform: uppercase;
    }}

    </style>
    </head>

    <body>

        <div class="titulo">
            ESPECIFICACOES
        </div>

        <div class="grid">

            <div class="card">
                <div class="icone">{ctx['svg_dorm']}</div>
                <div class="label">Dormitorios</div>
                <div class="valor">{ctx['dormitorios']}</div>
            </div>

            <div class="card">
                <div class="icone">{ctx['svg_suites']}</div>
                <div class="label">Suites</div>
                <div class="valor">{ctx['suites']}</div>
            </div>

            <div class="card">
                <div class="icone">{ctx['svg_banheiros']}</div>
                <div class="label">Banheiros</div>
                <div class="valor">{ctx['banheiros']}</div>
            </div>

            <div class="card">
                <div class="icone">{ctx['svg_vagas']}</div>
                <div class="label">Vagas</div>
                <div class="valor">{ctx['vagas']}</div>
            </div>

            <div class="card">
                <div class="icone">{ctx['svg_area']}</div>
                <div class="label">Area util</div>
                <div class="valor">{ctx['area']}</div>
            </div>

            <div class="card">
                <div class="icone">{ctx['svg_condominio']}</div>
                <div class="label">Condominio</div>
                <div class="valor">{ctx['condominio']}</div>
            </div>

        </div>

        <div class="rodape">
            CARVALHO FERREIRA • CONSULTORIA IMOBILIARIA
        </div>

    </body>
    </html>
    """

    return renderizar_png(
        html,
        1080,
        1350,
    )


def gerar_lamina_final(
    ctx,
):

    logo_html = ""

    if ctx.get(
        "logo_uri"
    ):

        logo_html = (
            '<img class="logo" '
            f'src="{ctx["logo_uri"]}">'
        )

    html = f"""
    <html>
    <head>
    <meta charset="UTF-8">

    <style>

    {ctx['css_fontes']}

    @page {{
        size: 1080px 1350px;
        margin: 0;
    }}

    * {{
        box-sizing: border-box;
    }}

    body {{
        margin: 0;
        width: 1080px;
        height: 1350px;
        background: {COR_AZUL_ESCURO};
        font-family: 'Manrope', Arial, sans-serif;
        text-align: center;
        position: relative;
        overflow: hidden;
    }}

    .topo {{
        position: absolute;
        top: 100px;
        left: 80px;
        right: 80px;
    }}

    .logo {{
        max-width: 300px;
        max-height: 125px;
        display: block;
        margin: 0 auto 22px;
    }}

    .submarca {{
        font-size: 15px;
        letter-spacing: 3px;
        color: {COR_OFF_WHITE};
        text-transform: uppercase;
        font-weight: 600;
    }}

    .centro {{
        position: absolute;
        top: 50%;
        left: 80px;
        right: 80px;
        transform: translateY(-35%);
    }}

    .titulo {{
        font-family: 'Cormorant Garamond', Georgia, serif;
        font-size: 55px;
        line-height: 1.2;
        color: {COR_OFF_WHITE};
        font-weight: 600;
        letter-spacing: 1px;
    }}

    .linha {{
        width: 75px;
        height: 2px;
        background: {COR_OFF_WHITE};
        margin: 30px auto 0;
    }}

    </style>
    </head>

    <body>

        <div class="topo">

            {logo_html}

            <div class="submarca">
                CARVALHO FERREIRA • CONSULTORIA IMOBILIARIA
            </div>

        </div>

        <div class="centro">

            <div class="titulo">
                TALVEZ ESTE SEJA O IMOVEL.<br>
                QUE VOCE ESTAVA PROCURANDO.
            </div>

            <div class="linha"></div>

        </div>

    </body>
    </html>
    """

    return renderizar_png(
        html,
        1080,
        1350,
    )


def gerar_thumbnail(
    ctx,
    foto,
):

    nome_html = (
        f"<span class='nome'>{ctx['titulo_3']}</span>"
        if ctx["titulo_3"]
        else ""
    )

    foto_uri = imagem_uri(
        foto["bytes"],
        foto["nome"],
    )

    condominio_html = (
        f"<div class='condominio-texto'>Condomínio: {ctx['condominio']}</div>"
        if ctx["condominio"] and ctx["condominio"] != "-"
        else ""
    )

    html = f"""
    <html>
    <head>
    <meta charset="UTF-8">

    <style>

    {ctx['css_fontes']}

    @page {{
        size: 1080px 1350px;
        margin: 0;
    }}

    * {{
        box-sizing: border-box;
    }}

    body {{
        margin: 0;
        width: 1080px;
        height: 1350px;
        background: {COR_OFF_WHITE};
        overflow: hidden;
        font-family: 'Manrope', Arial, sans-serif;
    }}

    .foto {{
        position: absolute;
        top: 0;
        left: 0;
        width: 1080px;
        height: 1350px;
        padding: 20px;
        object-fit: contain;
    }}

    {css_card_principal()}

    .titulo {{
        font-size: 38px;
        line-height: 1.15;
    }}

    .tipo {{
        font-family: 'Cormorant Garamond', Georgia, serif;
        font-size: 36px;
        font-weight: 500;
        letter-spacing: 2px;
        text-transform: uppercase;
        color: {COR_OFF_WHITE};
    }}

    .destaque {{
        font-family: 'Cormorant Garamond', Georgia, serif;
        font-size: 45px;
        font-weight: 500;
        letter-spacing: 2px;
        text-transform: uppercase;
        color: {COR_OFF_WHITE};
    }}

    .nome {{
        display: block;
        margin-top: 3px;
        font-size: 27px;
        font-weight: 400;
        color: {COR_OFF_WHITE};
    }}

    .local {{
        margin-top: 20px;
        font-size: 17px;
        letter-spacing: 1px;
        text-transform: uppercase;
        color: {COR_AZUL_SUAVE};
        display: flex;
        align-items: center;
        gap: 8px;
    }}

    .valor {{
        margin-top: 19px;
        font-size: 42px;
        font-weight: 600;
        color: {COR_OFF_WHITE};
    }}

    .condominio-texto {{
        margin-top: 3px;
        font-size: 15px;
        color: {COR_AZUL_SUAVE};
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}

    .marca {{
        margin-top: 20px;
        padding-top: 14px;
        border-top: 1px solid rgba(255,255,255,.3);
        font-size: 13px;
        letter-spacing: 2px;
        font-weight: 600;
        color: {COR_OFF_WHITE};
    }}

    </style>
    </head>

    <body>

        <img class="foto" src="{foto_uri}">

        <div class="card-fundo"></div>

        <div class="card-azul">

            <div class="card-conteudo">

                <div class="titulo">

                    <span class="tipo">
                        {ctx['titulo_1']}
                    </span>

                    <span class="destaque">
                        {ctx['titulo_2']}
                    </span>

                    {nome_html}

                </div>

                <div class="local">

                    {ctx['pin']}

                    <span>
                        {ctx['bairro']} • {ctx['cidade']}
                    </span>

                </div>

                <div class="valor">
                    {ctx['valor']}
                </div>

                {condominio_html}

                <div class="marca">
                    CARVALHO FERREIRA
                </div>

            </div>

        </div>

    </body>
    </html>
    """

    return renderizar_png(
        html,
        1080,
        1350,
    )


# =============================================================================
# STORIES
# =============================================================================

def gerar_stories(
    ctx,
    fotos,
):

    gerados = []

    for indice, foto in enumerate(
        fotos[:4],
        start=1,
    ):

        nome_html = (
            f"<span class='nome'>{ctx['titulo_3']}</span>"
            if ctx["titulo_3"]
            else ""
        )

        foto_uri = imagem_uri(
            foto["bytes"],
            foto["nome"],
        )

        condominio_story_html = (
            f"<div>Cond. {ctx['condominio']}</div>"
            if ctx["condominio"] and ctx["condominio"] != "-"
            else ""
        )

        html = f"""
        <html>
        <head>
        <meta charset="UTF-8">

        <style>

        {ctx['css_fontes']}

        @page {{
            size: 1080px 1920px;
            margin: 0;
        }}

        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            width: 1080px;
            height: 1920px;
            background: {COR_OFF_WHITE};
            overflow: hidden;
            font-family: 'Manrope', Arial, sans-serif;
        }}

        .foto {{
            position: absolute;
            top: 0;
            left: 0;
            width: 1080px;
            height: 1920px;
            object-fit: cover;
        }}

        .card-fundo {{
            position: absolute;
            left: 0;
            bottom: 70px;
            width: 780px;
            height: 450px;
            background: {COR_OFF_WHITE};
            z-index: 2;
        }}

        .card-azul {{
            position: absolute;
            left: 0;
            bottom: 51px;
            width: 900px;
            height: 431px;
            background: {COR_AZUL_ESCURO};
            z-index: 3;
            padding: 60px 62px 45px 62px;
            color: {COR_OFF_WHITE};
        }}

        .titulo {{
            font-size: 43px;
            line-height: 1.15;
        }}

        .tipo {{
            font-family: 'Cormorant Garamond', Georgia, serif;
            font-size: 36px;
            font-weight: 500;
            letter-spacing: 2px;
            text-transform: uppercase;
        }}

        .destaque {{
            font-family: 'Cormorant Garamond', Georgia, serif;
            font-size: 45px;
            font-weight: 500;
            letter-spacing: 2px;
            text-transform: uppercase;
            color: {COR_OFF_WHITE};
        }}

        .nome {{
            display: block;
            margin-top: 5px;
            font-size: 30px;
            color: {COR_OFF_WHITE};
            font-weight: 400;
        }}

        .local {{
            margin-top: 25px;
            font-size: 20px;
            letter-spacing: 1px;
            text-transform: uppercase;
            color: {COR_AZUL_SUAVE};
            display: flex;
            align-items: center;
            gap: 9px;
        }}

        .valor {{
            margin-top: 23px;
            font-size: 52px;
            font-weight: 600;
            color: {COR_OFF_WHITE};
        }}

        .info {{
            margin-top: 25px;
            font-size: 20px;
            font-weight: 500;
            color: #E2E8F0;
            display: flex;
            gap: 28px;
            flex-wrap: wrap;
        }}

        .marca {{
            margin-top: 30px;
            padding-top: 18px;
            border-top: 1px solid rgba(255,255,255,.3);
            font-size: 14px;
            letter-spacing: 2px;
            font-weight: 600;
        }}

        </style>
        </head>

        <body>

            <img class="foto" src="{foto_uri}">

            <div class="card-fundo"></div>

            <div class="card-azul">

                <div class="titulo">

                    <span class="tipo">
                        {ctx['titulo_1']}
                    </span>

                    <span class="destaque">
                        {ctx['titulo_2']}
                    </span>

                    {nome_html}

                </div>

                <div class="local">

                    {ctx['pin']}

                    <span>
                        {ctx['bairro']} • {ctx['cidade']}
                    </span>

                </div>

                <div class="valor">
                    {ctx['valor']}
                </div>

                <div class="info">

                    <div>
                        {ctx['dormitorios']} dorm.
                    </div>

                    <div>
                        {ctx['vagas']} vagas
                    </div>

                    <div>
                        {ctx['area']} const.
                    </div>

                    {condominio_story_html}

                </div>

                <div class="marca">
                    CARVALHO FERREIRA
                </div>

            </div>

        </body>
        </html>
        """

        png = renderizar_png(
            html,
            1080,
            1920,
        )

        gerados.append(
            (
                f"story_{ctx['codigo']}_{indice:02d}.png",
                png,
            )
        )

    return gerados


# =============================================================================
# GERADOR PRINCIPAL
# =============================================================================

def gerar_posts(
    codigo_imovel,
):

    drive, sheets = conectar_google()

    if not drive or not sheets:
        return None

    codigo = (
        codigo_imovel
        .strip()
        .upper()
    )

    dados = ler_dados_sheets(
        sheets,
        codigo,
    )

    if not dados:

        print(
            f"Imóvel '{codigo}' não encontrado.",
            flush=True,
        )

        return None

    fotos = carregar_fotos(
        drive,
        codigo,
    )

    if not fotos:

        print(
            "Nenhuma foto encontrada.",
            flush=True,
        )

        return None

    # ---------------------------------------------------------
    # ATIVOS DA MARCA
    # ---------------------------------------------------------

    logo_bytes = buscar_logo_bytes(
        drive
    )

    ctx = {
        "codigo": codigo,

        "css_fontes":
            montar_css_fontes(
                drive
            ),

        "logo_uri":
            logo_uri(
                logo_bytes
            ),

        "pin":
            icone_pin(
                drive,
                COR_OFF_WHITE,
            ),

        "titulo_1":
            get_dado(
                dados,
                "TITULO 1",
                default="",
            ),

        "titulo_2":
            get_dado(
                dados,
                "TITULO 2",
                default="",
            ),

        "titulo_3":
            get_dado(
                dados,
                "TITULO 3",
                default="",
            ),

        "valor":
            get_dado(
                dados,
                "VALOR",
            ),

        "condominio":
            get_dado(
                dados,
                "CONDOMINIO",
                default="",
            ),

        "bairro":
            get_dado(
                dados,
                "BAIRRO",
                default="",
            ),

        "cidade":
            get_dado(
                dados,
                "CIDADE",
                default="",
            ),

        "dormitorios":
            get_dado(
                dados,
                "DORMITORIOS",
            ),

        "suites":
            get_dado(
                dados,
                "SUITES",
                default="-",
            ),

        "banheiros":
            get_dado(
                dados,
                "BANHEIROS",
            ),

        "vagas":
            get_dado(
                dados,
                "VAGAS",
            ),

        "area":
            get_dado(
                dados,
                "AREA UTIL",
            ),

        "terreno":
            get_dado(
                dados,
                "AREA TOTAL",
            ),

        "svg_dorm":
            carregar_icone_bytes(
                drive,
                "dormitorios.svg",
                COR_OFF_WHITE,
            ),

        "svg_suites":
            carregar_icone_bytes(
                drive,
                "suites.svg",
                COR_OFF_WHITE,
            ),

        "svg_banheiros":
            carregar_icone_bytes(
                drive,
                "banheiros.svg",
                COR_OFF_WHITE,
            ),

        "svg_vagas":
            carregar_icone_bytes(
                drive,
                "vagas.svg",
                COR_OFF_WHITE,
            ),

        "svg_area":
            carregar_icone_bytes(
                drive,
                "area.svg",
                COR_OFF_WHITE,
            ),

        "svg_condominio":
            carregar_icone_bytes(
                drive,
                "condominio.svg",
                COR_OFF_WHITE,
            ),
    }

    # ---------------------------------------------------------
    # GERAÇÃO EM MEMÓRIA
    # ---------------------------------------------------------

    arquivos = []

    # Thumbnail

    arquivos.append(
        (
            f"thumbnail_{codigo}.png",
            gerar_thumbnail(
                ctx,
                fotos[0],
            ),
        )
    )

    # Capa

    arquivos.append(
        (
            f"carrossel_{codigo}_01.png",
            gerar_lamina_capa(
                ctx,
                fotos[0],
            ),
        )
    )

    # Fotos do carrossel

    numero = 2

    for foto in fotos[1:4]:

        arquivos.append(
            (
                f"carrossel_{codigo}_{numero:02d}.png",
                gerar_lamina_foto(
                    ctx,
                    foto,
                ),
            )
        )

        numero += 1

    # Ficha técnica

    arquivos.append(
        (
            f"carrossel_{codigo}_{numero:02d}.png",
            gerar_lamina_ficha(
                ctx
            ),
        )
    )

    numero += 1

    # Final

    arquivos.append(
        (
            f"carrossel_{codigo}_{numero:02d}.png",
            gerar_lamina_final(
                ctx
            ),
        )
    )

    # Stories

    arquivos.extend(
        gerar_stories(
            ctx,
            fotos,
        )
    )

    # ---------------------------------------------------------
    # ZIP TOTALMENTE EM MEMÓRIA
    # ---------------------------------------------------------

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(
        zip_buffer,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as zf:

        for nome, dados_arquivo in arquivos:

            zf.writestr(
                nome,
                dados_arquivo,
            )

    zip_buffer.seek(0)

    print(
        "SUCESSO: Posts gerados com sucesso.",
        flush=True,
    )

    return zip_buffer.getvalue()
