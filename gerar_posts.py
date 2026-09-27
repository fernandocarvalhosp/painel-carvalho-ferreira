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

# Faixa ampla para não ficar limitada às primeiras colunas.
RANGE_SHEETS = f"'{NOME_ABA}'!A:ZZ"

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


def icone_generico(
    cor,
):

    return f"""
    <svg width="31" height="31"
         viewBox="0 0 24 24"
         fill="none"
         stroke="{cor}"
         stroke-width="1.8"
         stroke-linecap="round"
         stroke-linejoin="round">

        <rect x="4" y="4" width="16" height="16" rx="2"></rect>
        <path d="M8 9h8"></path>
        <path d="M8 13h8"></path>
        <path d="M8 17h5"></path>

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
            range=RANGE_SHEETS,
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
    default="",
):

    if not dados:
        return default

    for c in chaves:

        chave_normalizada = normalizar(c)

        v = dados.get(
            chave_normalizada,
            "",
        )

        if v not in (
            "",
            None,
        ):

            texto = str(v).strip()

            if texto:
                return texto

    return default


# =============================================================================
# TÍTULOS
# =============================================================================

def montar_titulo_completo(
    ctx,
):

    partes = []

    for chave in [
        "titulo_1",
        "titulo_2",
        "titulo_3",
    ]:

        valor = (
            ctx.get(chave, "")
            or ""
        ).strip()

        if valor:
            partes.append(valor)

    return " ".join(partes)


def montar_titulo_html(
    ctx,
):

    partes = []

    titulo_1 = (
        ctx.get("titulo_1", "")
        or ""
    ).strip()

    titulo_2 = (
        ctx.get("titulo_2", "")
        or ""
    ).strip()

    titulo_3 = (
        ctx.get("titulo_3", "")
        or ""
    ).strip()

    if titulo_1:
        partes.append(
            f"<span class='tipo'>{titulo_1}</span>"
        )

    if titulo_2:
        partes.append(
            f"<span class='destaque'>{titulo_2}</span>"
        )

    if titulo_3:
        partes.append(
            f"<span class='nome'>{titulo_3}</span>"
        )

    return "\n".join(partes)


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
# CSS CARD PRINCIPAL
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
# LÂMINA DE CAPA
# =============================================================================

def gerar_lamina_capa(
    ctx,
    foto,
):

    foto_uri = imagem_uri(
        foto["bytes"],
        foto["nome"],
    )

    titulo_html = montar_titulo_html(
        ctx
    )

    condominio_html = (
        f"<div class='condominio-texto'>Condomínio: {ctx['condominio']}</div>"
        if ctx["condominio"]
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
        display: block;
    }}

    {css_card_principal()}

    .titulo {{
        font-size: 39px;
        line-height: 1.15;
        margin: 0;
    }}

    .tipo {{
        display: block;
        font-family: 'Cormorant Garamond', Georgia, serif;
        font-size: 38px;
        font-weight: 500;
        letter-spacing: 2px;
        text-transform: uppercase;
        color: {COR_OFF_WHITE};
    }}

    .destaque {{
        display: block;
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

                    {titulo_html}

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


# =============================================================================
# LÂMINA DE FOTO
# =============================================================================

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


# =============================================================================
# FICHA TÉCNICA
# =============================================================================

def montar_especificacoes(
    ctx,
):

    especificacoes = []

    # 1. Dormitórios
    if ctx["dormitorios"]:
        especificacoes.append(
            {
                "label": "Dormitórios",
                "valor": ctx["dormitorios"],
                "icone": ctx["svg_dorm"],
            }
        )

    # 2. Suítes
    if ctx["suites"]:
        especificacoes.append(
            {
                "label": "Suítes",
                "valor": ctx["suites"],
                "icone": ctx["svg_suites"],
            }
        )

    # Se não houver suítes, usa andar.
    elif ctx["andar"]:
        especificacoes.append(
            {
                "label": "Andar",
                "valor": ctx["andar"],
                "icone": ctx["svg_andar"],
            }
        )

    # 3. Banheiros
    if ctx["banheiros"]:
        especificacoes.append(
            {
                "label": "Banheiros",
                "valor": ctx["banheiros"],
                "icone": ctx["svg_banheiros"],
            }
        )

    # 4. Vagas
    if ctx["vagas"]:
        especificacoes.append(
            {
                "label": "Vagas",
                "valor": ctx["vagas"],
                "icone": ctx["svg_vagas"],
            }
        )

    # 5. Área útil
    if ctx["area"]:
        especificacoes.append(
            {
                "label": "Área útil",
                "valor": ctx["area"],
                "icone": ctx["svg_area"],
            }
        )

    # 6. Condomínio
    if ctx["condominio"]:
        especificacoes.append(
            {
                "label": "Condomínio",
                "valor": ctx["condominio"],
                "icone": ctx["svg_condominio"],
            }
        )

    # Se ainda houver espaço, usa IPTU.
    if len(especificacoes) < 6 and ctx["iptu"]:
        especificacoes.append(
            {
                "label": "IPTU",
                "valor": ctx["iptu"],
                "icone": ctx["svg_iptu"],
            }
        )

    # Se ainda houver espaço, usa Área Total.
    if len(especificacoes) < 6 and ctx["area_total"]:
        especificacoes.append(
            {
                "label": "Área total",
                "valor": ctx["area_total"],
                "icone": ctx["svg_area_total"],
            }
        )

    # Limita aos 6 cards disponíveis.
    return especificacoes[:6]


def gerar_lamina_ficha(
    ctx,
):

    especificacoes = montar_especificacoes(
        ctx
    )

    cards_html = ""

    for item in especificacoes:

        cards_html += f"""
        <div class="card">

            <div class="icone">
                {item["icone"]}
            </div>

            <div class="label">
                {item["label"]}
            </div>

            <div class="valor">
                {item["valor"]}
            </div>

        </div>
        """

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
        position: relative;
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

    /*
    Marca presa no fundo do card.
    A linha continua acima da marca.
    */
    .rodape {{
        position: absolute;
        left: 65px;
        right: 65px;
        bottom: 4px;
        padding-top: 18px;
        border-top: 1px solid rgba(255,255,255,.3);
        font-size: 13px;
        line-height: 1;
        letter-spacing: 2px;
        color: {COR_AZUL_SUAVE};
        text-transform: uppercase;
    }}

    </style>
    </head>

    <body>

        <div class="titulo">
            ESPECIFICAÇÕES
        </div>

        <div class="grid">

            {cards_html}

        </div>

        <div class="rodape">
            CARVALHO FERREIRA • CONSULTORIA IMOBILIÁRIA
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
# LÂMINA FINAL
# =============================================================================

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
                CARVALHO FERREIRA • CONSULTORIA IMOBILIÁRIA
            </div>

        </div>

        <div class="centro">

            <div class="titulo">
                TALVEZ ESTE SEJA O IMÓVEL.<br>
                QUE VOCÊ ESTAVA PROCURANDO.
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

        foto_uri = imagem_uri(
            foto["bytes"],
            foto["nome"],
        )

        titulo_html = montar_titulo_html(
            ctx
        )

        condominio_story_html = (
            f"<div>Cond. {ctx['condominio']}</div>"
            if ctx["condominio"]
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
            display: block;
            font-family: 'Cormorant Garamond', Georgia, serif;
            font-size: 36px;
            font-weight: 500;
            letter-spacing: 2px;
            text-transform: uppercase;
        }}

        .destaque {{
            display: block;
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

                    {titulo_html}

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

    svg_dorm = carregar_icone_bytes(
        drive,
        "dormitorios.svg",
        COR_OFF_WHITE,
    )

    svg_suites = carregar_icone_bytes(
        drive,
        "suites.svg",
        COR_OFF_WHITE,
    )

    svg_banheiros = carregar_icone_bytes(
        drive,
        "banheiros.svg",
        COR_OFF_WHITE,
    )

    svg_vagas = carregar_icone_bytes(
        drive,
        "vagas.svg",
        COR_OFF_WHITE,
    )

    svg_area = carregar_icone_bytes(
        drive,
        "area.svg",
        COR_OFF_WHITE,
    )

    svg_condominio = carregar_icone_bytes(
        drive,
        "condominio.svg",
        COR_OFF_WHITE,
    )

    svg_andar = carregar_icone_bytes(
        drive,
        "andar.svg",
        COR_OFF_WHITE,
    )

    svg_iptu = carregar_icone_bytes(
        drive,
        "iptu.svg",
        COR_OFF_WHITE,
    )

    svg_area_total = carregar_icone_bytes(
        drive,
        "area_total.svg",
        COR_OFF_WHITE,
    )

    # Caso algum desses ícones ainda não exista na pasta da marca,
    # utiliza um ícone genérico para não quebrar a geração.
    svg_generico = icone_generico(
        COR_OFF_WHITE
    )

    if not svg_dorm:
        svg_dorm = svg_generico

    if not svg_suites:
        svg_suites = svg_generico

    if not svg_banheiros:
        svg_banheiros = svg_generico

    if not svg_vagas:
        svg_vagas = svg_generico

    if not svg_area:
        svg_area = svg_generico

    if not svg_condominio:
        svg_condominio = svg_generico

    if not svg_andar:
        svg_andar = svg_generico

    if not svg_iptu:
        svg_iptu = svg_generico

    if not svg_area_total:
        svg_area_total = svg_generico

    # ---------------------------------------------------------
    # DADOS
    # ---------------------------------------------------------

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
            ),

        "titulo_2":
            get_dado(
                dados,
                "TITULO 2",
            ),

        "titulo_3":
            get_dado(
                dados,
                "TITULO 3",
            ),

        "valor":
            get_dado(
                dados,
                "VALOR",
                "PREÇO",
                "PRECO",
            ),

        "condominio":
            get_dado(
                dados,
                "CONDOMINIO",
                "CONDOMÍNIO",
            ),

        "iptu":
            get_dado(
                dados,
                "IPTU",
            ),

        "bairro":
            get_dado(
                dados,
                "BAIRRO",
            ),

        "cidade":
            get_dado(
                dados,
                "CIDADE",
            ),

        "dormitorios":
            get_dado(
                dados,
                "DORMITORIOS",
                "DORMITÓRIOS",
            ),

        "suites":
            get_dado(
                dados,
                "SUITES",
                "SUÍTES",
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
                "ÁREA ÚTIL",
            ),

        "area_total":
            get_dado(
                dados,
                "AREA TOTAL",
                "ÁREA TOTAL",
            ),

        "andar":
            get_dado(
                dados,
                "ANDAR",
            ),

        "svg_dorm":
            svg_dorm,

        "svg_suites":
            svg_suites,

        "svg_banheiros":
            svg_banheiros,

        "svg_vagas":
            svg_vagas,

        "svg_area":
            svg_area,

        "svg_condominio":
            svg_condominio,

        "svg_andar":
            svg_andar,

        "svg_iptu":
            svg_iptu,

        "svg_area_total":
            svg_area_total,
    }

    # ---------------------------------------------------------
    # GERAÇÃO EM MEMÓRIA
    # ---------------------------------------------------------

    arquivos = []

    # ---------------------------------------------------------
    # CAPA
    # ---------------------------------------------------------

    arquivos.append(
        (
            f"carrossel_{codigo}_01.png",
            gerar_lamina_capa(
                ctx,
                fotos[0],
            ),
        )
    )

    # ---------------------------------------------------------
    # FOTOS DO CARROSSEL
    # ---------------------------------------------------------

    numero = 2

    for foto in fotos[1:4]:

        arquivos.append(
            (
                f"carrossel_{codigo}_{numero:02d}.png",
                gerar_lamina_foto(
                    ctx,
                    foto,
                )
            )
        )

        numero += 1

    # ---------------------------------------------------------
    # FICHA TÉCNICA
    # ---------------------------------------------------------

    arquivos.append(
        (
            f"carrossel_{codigo}_{numero:02d}.png",
            gerar_lamina_ficha(
                ctx
            ),
        )
    )

    numero += 1

    # ---------------------------------------------------------
    # LÂMINA FINAL
    # ---------------------------------------------------------

    arquivos.append(
        (
            f"carrossel_{codigo}_{numero:02d}.png",
            gerar_lamina_final(
                ctx
            ),
        )
    )

    # ---------------------------------------------------------
    # STORIES
    # ---------------------------------------------------------

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