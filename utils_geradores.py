# -*- coding: utf-8 -*-

import io
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

# Intervalo amplo para acompanhar o crescimento da planilha.
RANGE_PLANILHA = "A:AZ"

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
            range=f"'{NOME_ABA}'!{RANGE_PLANILHA}",
        )
        .execute()
    )

    rows = result.get(
        "values",
        [],
    )

    if not rows:
        return {}

    # A posição da coluna não importa.
    # O cabeçalho vira a chave usada para localizar cada informação.
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

    for c in chaves:

        chave = normalizar(c)

        v = dados.get(
            chave,
            "",
        )

        if v not in (
            "",
            None,
        ):

            valor = str(v).strip()

            if valor:
                return valor

    return default


def tem_dado(
    dados,
    *chaves,
):

    valor = get_dado(
        dados,
        *chaves,
        default="",
    )

    return bool(
        str(valor).strip()
    )


# =============================================================================
# TÍTULOS
# =============================================================================

def montar_titulo_completo(
    dados,
):

    partes = []

    for chave in [
        "TITULO 1",
        "TITULO 2",
        "TITULO 3",
    ]:

        valor = get_dado(
            dados,
            chave,
            default="",
        )

        if valor:
            partes.append(
                valor.strip()
            )

    return " ".join(partes)


# =============================================================================
# FICHA TÉCNICA INTELIGENTE
# =============================================================================

def montar_ficha_tecnica(
    dados,
):

    itens = []

    usados = set()

    def adicionar(
        label,
        valor,
        chave=None,
    ):

        if not valor:
            return False

        valor = str(valor).strip()

        if not valor:
            return False

        identificador = (
            chave or label
        )

        if identificador in usados:
            return False

        itens.append(
            {
                "label": label,
                "valor": valor,
                "chave": identificador,
            }
        )

        usados.add(
            identificador
        )

        return True

    # -------------------------------------------------------------------------
    # 1. Dormitórios
    # -------------------------------------------------------------------------

    adicionar(
        "Dormitorios",
        get_dado(
            dados,
            "DORMITORIOS",
        ),
        "DORMITORIOS",
    )

    # -------------------------------------------------------------------------
    # 2. Suítes
    #
    # Se não houver suíte, usa ANDAR.
    # Isso evita que um apartamento fique com um card vazio.
    # -------------------------------------------------------------------------

    suites = get_dado(
        dados,
        "SUITES",
        default="",
    )

    if suites:

        adicionar(
            "Suites",
            suites,
            "SUITES",
        )

    else:

        andar = get_dado(
            dados,
            "ANDAR",
            default="",
        )

        if andar:

            adicionar(
                "Andar",
                andar,
                "ANDAR",
            )

    # -------------------------------------------------------------------------
    # 3. Banheiros
    # -------------------------------------------------------------------------

    adicionar(
        "Banheiros",
        get_dado(
            dados,
            "BANHEIROS",
        ),
        "BANHEIROS",
    )

    # -------------------------------------------------------------------------
    # 4. Vagas
    # -------------------------------------------------------------------------

    adicionar(
        "Vagas",
        get_dado(
            dados,
            "VAGAS",
        ),
        "VAGAS",
    )

    # -------------------------------------------------------------------------
    # 5. Área
    #
    # Prioridade:
    # Área útil
    # Área total
    # -------------------------------------------------------------------------

    area_util = get_dado(
        dados,
        "AREA UTIL",
        default="",
    )

    area_total = get_dado(
        dados,
        "AREA TOTAL",
        default="",
    )

    if area_util:

        adicionar(
            "Area util",
            area_util,
            "AREA UTIL",
        )

    elif area_total:

        adicionar(
            "Area total",
            area_total,
            "AREA TOTAL",
        )

    # -------------------------------------------------------------------------
    # 6. Condomínio
    #
    # Se não existir condomínio, usa IPTU.
    # -------------------------------------------------------------------------

    condominio = get_dado(
        dados,
        "CONDOMINIO",
        default="",
    )

    if condominio:

        adicionar(
            "Condominio",
            condominio,
            "CONDOMINIO",
        )

    else:

        iptu = get_dado(
            dados,
            "IPTU",
            default="",
        )

        if iptu:

            adicionar(
                "IPTU",
                iptu,
                "IPTU",
            )

    # -------------------------------------------------------------------------
    # Caso algum dos seis espaços ainda esteja disponível, procura outras
    # informações úteis antes de permitir que apareça um "-".
    # -------------------------------------------------------------------------

    alternativas = [
        (
            "Andar",
            "ANDAR",
            "ANDAR",
        ),
        (
            "Condominio",
            "CONDOMINIO",
            "CONDOMINIO",
        ),
        (
            "IPTU",
            "IPTU",
            "IPTU",
        ),
        (
            "Area total",
            "AREA TOTAL",
            "AREA TOTAL",
        ),
    ]

    for label, chave, identificador in alternativas:

        if len(itens) >= 6:
            break

        valor = get_dado(
            dados,
            chave,
            default="",
        )

        if valor:

            adicionar(
                label,
                valor,
                identificador,
            )

    return itens[:6]


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
# CONTEXTO COMUM (usado pelos dois geradores)
# =============================================================================

def montar_contexto(
    drive,
    sheets,
    codigo,
):
    """
    Monta o contexto completo do imóvel.
    Retorna (ctx, fotos) ou (None, None) em caso de erro.
    """

    codigo = codigo.strip().upper()

    dados = ler_dados_sheets(sheets, codigo)

    if not dados:
        print(f"Imóvel '{codigo}' não encontrado.", flush=True)
        return None, None

    fotos = carregar_fotos(drive, codigo)

    if not fotos:
        print("Nenhuma foto encontrada.", flush=True)
        return None, None

    logo_bytes = buscar_logo_bytes(drive)

    titulo_1 = get_dado(dados, "TITULO 1", default="")
    titulo_2 = get_dado(dados, "TITULO 2", default="")
    titulo_3 = get_dado(dados, "TITULO 3", default="")

    ficha = montar_ficha_tecnica(dados)

    mapa_icones = {
        "DORMITORIOS": carregar_icone_bytes(drive, "dormitorios.svg", COR_OFF_WHITE),
        "SUITES": carregar_icone_bytes(drive, "suites.svg", COR_OFF_WHITE),
        "BANHEIROS": carregar_icone_bytes(drive, "banheiros.svg", COR_OFF_WHITE),
        "VAGAS": carregar_icone_bytes(drive, "vagas.svg", COR_OFF_WHITE),
        "AREA UTIL": carregar_icone_bytes(drive, "area.svg", COR_OFF_WHITE),
        "AREA TOTAL": carregar_icone_bytes(drive, "area.svg", COR_OFF_WHITE),
        "CONDOMINIO": carregar_icone_bytes(drive, "condominio.svg", COR_OFF_WHITE),
        "IPTU": carregar_icone_bytes(drive, "condominio.svg", COR_OFF_WHITE),
        "ANDAR": carregar_icone_bytes(drive, "area.svg", COR_OFF_WHITE),
    }

    for item in ficha:
        chave = item["chave"]
        item["icone"] = mapa_icones.get(chave, "")

    ctx = {
        "codigo": codigo,
        "css_fontes": montar_css_fontes(drive),
        "logo_uri": logo_uri(logo_bytes),
        "pin": icone_pin(drive, COR_OFF_WHITE),
        "titulo_1": titulo_1,
        "titulo_2": titulo_2,
        "titulo_3": titulo_3,
        "titulo_completo": montar_titulo_completo(dados),
        "valor": get_dado(dados, "VALOR"),
        "condominio": get_dado(dados, "CONDOMINIO", default=""),
        "iptu": get_dado(dados, "IPTU", default=""),
        "bairro": get_dado(dados, "BAIRRO", default=""),
        "cidade": get_dado(dados, "CIDADE", default=""),
        "dormitorios": get_dado(dados, "DORMITORIOS", default="-"),
        "suites": get_dado(dados, "SUITES", default=""),
        "banheiros": get_dado(dados, "BANHEIROS", default="-"),
        "vagas": get_dado(dados, "VAGAS", default="-"),
        "area": get_dado(dados, "AREA UTIL", "AREA TOTAL", default="-"),
        "terreno": get_dado(dados, "AREA TOTAL", default=""),
        "ficha_tecnica": ficha,
    }

    return ctx, fotos
