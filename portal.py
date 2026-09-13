# portal.py
# Carvalho Ferreira | Portal Público
#
# Aplicação pública separada do sistema interno (app.py).
# O portal lê a mesma planilha e o Google Drive, mas não expõe
# materiais internos, documentos ou controles do backoffice.

import io
import os
import re
from pathlib import Path

import streamlit as st
from PIL import Image
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


# ============================================================
# CONFIGURAÇÕES
# ============================================================

st.set_page_config(
    page_title="Carvalho Ferreira | Consultoria Imobiliária",
    page_icon="CF",
    layout="wide",
    initial_sidebar_state="collapsed",
)

SPREADSHEET_ID = "1nVEpOZFYFKcq0MXtOwxn22nqxafmJBHnf6zhHQlyT8w"
ABA_IMOVEIS = "Imoveis"

# Estrutura principal do Drive
NOME_PASTA_RAIZ = "PORTFOLIO"
NOME_PASTA_IMOVEIS = "IMOVEIS"

# Fotos públicas do imóvel.
# Primeiro procura FOTOS SELECIONADAS. Se não existir,
# tenta FOTOS TRATADAS.
PASTAS_FOTOS = ["FOTOS SELECIONADAS", "FOTOS TRATADAS"]

WHATSAPP_FERNANDO = "5512988162626"
WHATSAPP_VALDIR = "5512992157474"

ITENS_POR_PAGINA = 6


# ============================================================
# ESTILO
# ============================================================

st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Manrope:wght@400;500;600;700&display=swap');

    :root {
        --cf-bg: #F7F5F0;
        --cf-dark: #0A1F2E;
        --cf-dark-2: #102B3D;
        --cf-gold: #B8943D;
        --cf-text: #18232C;
        --cf-muted: #69747D;
        --cf-line: #DCD8D0;
        --cf-white: #FFFFFF;
    }

    .stApp {
        background: var(--cf-bg);
        color: var(--cf-text);
        font-family: 'Manrope', sans-serif;
    }

    #MainMenu, footer, header {
        visibility: hidden;
    }

    [data-testid="stSidebar"] {
        display: none;
    }

    .block-container {
        max-width: 1240px;
        padding-top: 1.2rem;
        padding-bottom: 3rem;
    }

    .cf-header {
        padding: 10px 0 4px;
        border-bottom: 1px solid var(--cf-line);
        margin-bottom: 8px;
    }

    .cf-brand {
        display: flex;
        align-items: center;
        gap: 18px;
    }

    .cf-logo {
        height: 68px;
        width: auto;
        object-fit: contain;
    }

    .cf-brand-name {
        font-family: 'Cormorant Garamond', serif;
        font-size: 31px;
        font-weight: 600;
        line-height: 1;
        color: var(--cf-dark);
    }

    .cf-subtitle {
        margin-top: 5px;
        font-size: 12px;
        letter-spacing: 2.4px;
        text-transform: uppercase;
        color: var(--cf-muted);
    }

    .cf-gold-line {
        width: 42px;
        height: 2px;
        background: var(--cf-gold);
        margin-top: 10px;
    }

    .cf-nav {
        margin: 18px 0 25px;
        color: var(--cf-muted);
        font-size: 12px;
        letter-spacing: 1.25px;
        text-transform: uppercase;
    }

    .cf-nav-sep {
        color: var(--cf-gold);
        padding: 0 12px;
    }

    .section-kicker {
        color: var(--cf-gold);
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-bottom: 5px;
    }

    .section-title {
        font-family: 'Cormorant Garamond', serif;
        font-size: 43px;
        line-height: 1.05;
        color: var(--cf-dark);
        margin: 0 0 8px;
    }

    .section-description {
        color: var(--cf-muted);
        font-size: 14px;
        margin-bottom: 25px;
    }

    .hero {
        background: var(--cf-dark);
        border-radius: 3px;
        overflow: hidden;
        margin: 10px 0 28px;
    }

    .hero-image {
        width: 100%;
        max-height: 570px;
        object-fit: cover;
        display: block;
    }

    .hero-info {
        padding: 22px 25px 25px;
        color: white;
    }

    .hero-kicker {
        color: #D8BC72;
        font-size: 10px;
        letter-spacing: 2px;
        text-transform: uppercase;
        font-weight: 700;
    }

    .hero-title {
        font-family: 'Cormorant Garamond', serif;
        font-size: 34px;
        line-height: 1.05;
        margin: 6px 0;
    }

    .hero-location {
        color: #C7D0D5;
        font-size: 13px;
    }

    .hero-price {
        font-size: 22px;
        font-weight: 700;
        margin-top: 14px;
    }

    .hero-meta {
        color: #C7D0D5;
        font-size: 12px;
        margin-top: 6px;
    }

    .carousel-dots {
        text-align: center;
        color: var(--cf-gold);
        letter-spacing: 5px;
        margin: 2px 0 22px;
    }

    .property-card {
        background: white;
        border: 1px solid var(--cf-line);
        border-radius: 3px;
        overflow: hidden;
        height: 100%;
        transition: transform .15s ease, box-shadow .15s ease;
    }

    .property-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(10,31,46,.08);
    }

    .card-image {
        width: 100%;
        height: 225px;
        object-fit: cover;
        display: block;
        background: #EAE7E0;
    }

    .card-body {
        padding: 17px 18px 18px;
    }

    .card-type {
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        color: var(--cf-gold);
    }

    .card-title {
        font-family: 'Cormorant Garamond', serif;
        font-size: 26px;
        color: var(--cf-dark);
        line-height: 1.05;
        margin: 5px 0 4px;
    }

    .card-location {
        color: var(--cf-muted);
        font-size: 12px;
        min-height: 18px;
    }

    .card-price {
        color: var(--cf-dark);
        font-size: 18px;
        font-weight: 700;
        margin-top: 13px;
    }

    .card-meta {
        color: var(--cf-muted);
        font-size: 11px;
        margin-top: 6px;
        min-height: 18px;
    }

    .card-code {
        color: #8B9297;
        font-size: 10px;
        letter-spacing: 1px;
        margin-top: 10px;
    }

    .detail-top {
        margin-bottom: 18px;
    }

    .detail-kicker {
        color: var(--cf-gold);
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 1.7px;
        text-transform: uppercase;
    }

    .detail-title {
        font-family: 'Cormorant Garamond', serif;
        color: var(--cf-dark);
        font-size: 48px;
        line-height: 1;
        margin: 5px 0;
    }

    .detail-location {
        color: var(--cf-muted);
        font-size: 14px;
    }

    .detail-price {
        color: var(--cf-dark);
        font-size: 27px;
        font-weight: 700;
        margin: 13px 0 18px;
    }

    .stat-box {
        background: white;
        border: 1px solid var(--cf-line);
        padding: 15px;
        min-height: 76px;
    }

    .stat-label {
        color: #899198;
        font-size: 9px;
        letter-spacing: 1.4px;
        text-transform: uppercase;
    }

    .stat-value {
        color: var(--cf-dark);
        font-size: 16px;
        font-weight: 700;
        margin-top: 4px;
    }

    .detail-section {
        margin-top: 34px;
    }

    .detail-section-title {
        font-family: 'Cormorant Garamond', serif;
        color: var(--cf-dark);
        font-size: 31px;
        border-bottom: 1px solid var(--cf-line);
        padding-bottom: 7px;
        margin-bottom: 14px;
    }

    .contact-box {
        background: var(--cf-dark);
        color: white;
        padding: 25px;
        margin-top: 35px;
        border-radius: 3px;
    }

    .contact-title {
        font-family: 'Cormorant Garamond', serif;
        font-size: 31px;
        margin-bottom: 4px;
    }

    .contact-text {
        color: #CBD3D8;
        font-size: 13px;
        margin-bottom: 18px;
    }

    .cf-footer {
        border-top: 1px solid var(--cf-line);
        margin-top: 55px;
        padding-top: 20px;
        color: var(--cf-muted);
        font-size: 11px;
        text-align: center;
    }

    .empty-state {
        background: white;
        border: 1px solid var(--cf-line);
        padding: 35px;
        text-align: center;
        color: var(--cf-muted);
    }

    @media (max-width: 700px) {
        .block-container {
            padding: .6rem .8rem 2rem;
        }

        .cf-logo {
            height: 53px;
        }

        .cf-brand-name {
            font-size: 25px;
        }

        .cf-subtitle {
            font-size: 9px;
            letter-spacing: 1.7px;
        }

        .cf-nav {
            white-space: nowrap;
            overflow-x: auto;
            padding-bottom: 4px;
            font-size: 10px;
        }

        .cf-nav-sep {
            padding: 0 6px;
        }

        .section-title {
            font-size: 35px;
        }

        .hero-image {
            max-height: 430px;
        }

        .hero-title {
            font-size: 29px;
        }

        .detail-title {
            font-size: 38px;
        }

        .card-image {
            height: 205px;
        }
    }
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# AUTENTICAÇÃO GOOGLE
# ============================================================

@st.cache_resource
def obter_credenciais():
    """
    Aceita o formato padrão:
    [gcp_service_account] no secrets.toml.
    """
    if "gcp_service_account" not in st.secrets:
        raise RuntimeError(
            "Credenciais Google não encontradas em st.secrets['gcp_service_account']."
        )

    info = dict(st.secrets["gcp_service_account"])
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]

    return service_account.Credentials.from_service_account_info(
        info,
        scopes=scopes,
    )


@st.cache_resource
def obter_services():
    credenciais = obter_credenciais()

    sheets = build(
        "sheets",
        "v4",
        credentials=credenciais,
        cache_discovery=False,
    )

    drive = build(
        "drive",
        "v3",
        credentials=credenciais,
        cache_discovery=False,
    )

    return sheets, drive


# ============================================================
# UTILITÁRIOS
# ============================================================

def normalizar_chave(valor):
    texto = str(valor or "").strip().upper()
    texto = (
        texto.replace("Á", "A")
        .replace("À", "A")
        .replace("Ã", "A")
        .replace("Â", "A")
        .replace("É", "E")
        .replace("Ê", "E")
        .replace("Í", "I")
        .replace("Ó", "O")
        .replace("Ô", "O")
        .replace("Õ", "O")
        .replace("Ú", "U")
        .replace("Ç", "C")
    )
    texto = re.sub(r"[^A-Z0-9]+", "_", texto)
    return texto.strip("_")


def valor_sinalizado(valor):
    return str(valor or "").strip().upper() in {
        "SIM",
        "S",
        "YES",
        "Y",
        "TRUE",
        "1",
        "X",
    }


def primeiro_valor(item, *chaves):
    for chave in chaves:
        valor = item.get(chave)
        if valor is not None and str(valor).strip():
            return str(valor).strip()
    return ""


def formatar_moeda(valor):
    texto = str(valor or "").strip()

    if not texto:
        return "Consultar"

    if "R$" in texto:
        return texto

    # Tenta interpretar números simples vindos da planilha.
    bruto = texto.replace(" ", "").replace("R$", "")

    try:
        if "," in bruto and "." in bruto:
            numero = float(bruto.replace(".", "").replace(",", "."))
        elif "," in bruto:
            numero = float(bruto.replace(",", "."))
        else:
            numero = float(bruto)

        if numero <= 0:
            return "Consultar"

        return f"R$ {numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return texto


def formatar_area(valor):
    texto = str(valor or "").strip()
    if not texto:
        return ""
    if "m²" in texto.lower() or "m2" in texto.lower():
        return texto.replace("m2", "m²")
    return f"{texto} m²"


def url_whatsapp(numero, codigo, origem="portal"):
    mensagem = (
        f"Olá! Vi o imóvel {codigo} no portal da Carvalho Ferreira "
        f"e gostaria de receber mais informações."
    )
    from urllib.parse import quote

    return f"https://wa.me/{numero}?text={quote(mensagem)}"


def descobrir_logo():
    candidatos = [
        Path("marca/logo/logo.png"),
        Path("marca/logo.png"),
        Path("marca/logo/logo.jpg"),
        Path("marca/logo.jpg"),
        Path("assets/logo.png"),
        Path("assets/logo.jpg"),
    ]

    for caminho in candidatos:
        if caminho.exists():
            return str(caminho)

    return None


def mostrar_logo():
    caminho = descobrir_logo()

    if caminho:
        try:
            st.image(caminho, width=190)
            return
        except Exception:
            pass

    st.markdown(
        """
        <div class="cf-brand">
            <div>
                <div class="cf-brand-name">Carvalho Ferreira</div>
                <div class="cf-subtitle">Consultoria Imobiliária</div>
                <div class="cf-gold-line"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# GOOGLE SHEETS
# ============================================================

@st.cache_data(ttl=120)
def carregar_imoveis_sheets():
    sheets, _ = obter_services()

    resposta = (
        sheets.spreadsheets()
        .values()
        .get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{ABA_IMOVEIS}!A:AF",
        )
        .execute()
    )

    valores = resposta.get("values", [])

    if not valores:
        return []

    cabecalho_original = valores[0]
    cabecalho = [normalizar_chave(c) for c in cabecalho_original]

    imoveis = []

    for linha in valores[1:]:
        if not any(str(x).strip() for x in linha):
            continue

        linha = list(linha) + [""] * max(0, len(cabecalho) - len(linha))
        item = {}

        for indice, chave in enumerate(cabecalho):
            if chave:
                item[chave] = str(linha[indice]).strip()

        codigo = primeiro_valor(item, "CODIGO", "CF", "CODIGO_IMOVEL")
        if not codigo:
            continue

        item["CODIGO"] = codigo.upper()
        imoveis.append(item)

    return imoveis


def imoveis_publicados(imoveis):
    publicados = []

    for imovel in imoveis:
        publicar = primeiro_valor(
            imovel,
            "PUBLICAR_NO_PORTAL",
            "PUBLICAR_PORTAL",
            "PUBLICAR",
        )

        if valor_sinalizado(publicar):
            publicados.append(imovel)

    return publicados


def imoveis_destaques(imoveis):
    destaques = []

    for imovel in imoveis:
        if not valor_sinalizado(
            primeiro_valor(
                imovel,
                "PUBLICAR_NO_PORTAL",
                "PUBLICAR_PORTAL",
                "PUBLICAR",
            )
        ):
            continue

        if valor_sinalizado(
            primeiro_valor(
                imovel,
                "DESTAQUE",
                "EM_DESTAQUE",
            )
        ):
            destaques.append(imovel)

    def ordem(item):
        valor = primeiro_valor(item, "ORDEM_DE_DESTAQUE", "ORDEM_DESTAQUE")
        try:
            return int(valor)
        except Exception:
            return 999999

    return sorted(destaques, key=ordem)


# ============================================================
# GOOGLE DRIVE
# ============================================================

@st.cache_data(ttl=600)
def buscar_pasta_por_nome(drive, nome, parent_id):
    query = (
        "mimeType = 'application/vnd.google-apps.folder' "
        f"and name = '{nome.replace(chr(39), chr(92) + chr(39))}' "
        f"and '{parent_id}' in parents "
        "and trashed = false"
    )

    resposta = (
        drive.files()
        .list(
            q=query,
            spaces="drive",
            fields="files(id,name)",
            pageSize=10,
        )
        .execute()
    )

    arquivos = resposta.get("files", [])
    return arquivos[0]["id"] if arquivos else None


@st.cache_data(ttl=600)
def listar_pastas_imoveis(drive, parent_id):
    resposta = (
        drive.files()
        .list(
            q=(
                "mimeType = 'application/vnd.google-apps.folder' "
                f"and '{parent_id}' in parents "
                "and trashed = false"
            ),
            spaces="drive",
            fields="files(id,name)",
            pageSize=1000,
        )
        .execute()
    )

    return resposta.get("files", [])


@st.cache_data(ttl=600)
def localizar_pasta_imovel(drive, codigo):
    raiz = buscar_pasta_por_nome(drive, NOME_PASTA_RAIZ, "root")

    if not raiz:
        return None

    pasta_imoveis = buscar_pasta_por_nome(
        drive,
        NOME_PASTA_IMOVEIS,
        raiz,
    )

    if not pasta_imoveis:
        return None

    pastas = listar_pastas_imoveis(drive, pasta_imoveis)
    codigo_upper = str(codigo).strip().upper()

    for pasta in pastas:
        if pasta["name"].strip().upper() == codigo_upper:
            return pasta["id"]

    # Fallback: alguns nomes de pasta podem conter descrição além do código.
    for pasta in pastas:
        if codigo_upper in pasta["name"].upper():
            return pasta["id"]

    return None


@st.cache_data(ttl=600)
def localizar_pasta_fotos(drive, codigo):
    pasta_imovel = localizar_pasta_imovel(drive, codigo)

    if not pasta_imovel:
        return None

    for nome in PASTAS_FOTOS:
        pasta = buscar_pasta_por_nome(drive, nome, pasta_imovel)
        if pasta:
            return pasta

    return None


@st.cache_data(ttl=600)
def listar_fotos_imovel(codigo):
    _, drive = obter_services()

    pasta_fotos = localizar_pasta_fotos(drive, codigo)

    if not pasta_fotos:
        return []

    resposta = (
        drive.files()
        .list(
            q=(
                f"'{pasta_fotos}' in parents "
                "and trashed = false"
            ),
            spaces="drive",
            fields="files(id,name,mimeType,size)",
            pageSize=1000,
        )
        .execute()
    )

    imagens = []

    extensoes = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".gif",
    }

    for arquivo in resposta.get("files", []):
        mime = arquivo.get("mimeType", "")
        nome = arquivo.get("name", "")
        extensao = Path(nome).suffix.lower()

        if mime.startswith("image/") or extensao in extensoes:
            imagens.append(arquivo)

    def ordem_foto(item):
        nome = item.get("name", "").lower()

        # Fotos com prefixo numérico ficam na ordem natural.
        numeros = re.findall(r"\d+", nome)
        if numeros:
            try:
                return (0, int(numeros[0]), nome)
            except Exception:
                pass

        return (1, 0, nome)

    return sorted(imagens, key=ordem_foto)


@st.cache_data(ttl=1800)
def baixar_arquivo_drive(file_id):
    _, drive = obter_services()

    requisicao = drive.files().get(
        fileId=file_id,
        alt="media",
    )

    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, requisicao)

    concluido = False

    while not concluido:
        _, concluido = downloader.next_chunk()

    buffer.seek(0)
    return buffer.getvalue()


@st.cache_data(ttl=1800)
def obter_foto_miniatura_por_id(file_id):
    if not file_id:
        return None

    try:
        dados = baixar_arquivo_drive(file_id)
        return dados
    except Exception:
        return None


# ============================================================
# CAMPOS DO IMÓVEL
# ============================================================

def obter_miniatura_id(imovel):
    return primeiro_valor(
        imovel,
        "MINIATURA",
        "MINIATURA_ID",
        "FOTO",
        "FOTO_PRINCIPAL",
        "FOTO_ID",
    )


def obter_tipo(imovel):
    return primeiro_valor(
        imovel,
        "TIPO",
        "CATEGORIA",
        "TIPO_IMOVEL",
    ) or "Imóvel"


def obter_bairro(imovel):
    return primeiro_valor(imovel, "BAIRRO", "LOCALIZACAO", "LOCAL") or ""


def obter_cidade(imovel):
    return primeiro_valor(imovel, "CIDADE", "MUNICIPIO") or ""


def obter_valor(imovel):
    return formatar_moeda(
        primeiro_valor(
            imovel,
            "VALOR",
            "VALOR_VENDA",
            "PRECO",
            "PRECO_VENDA",
        )
    )


def obter_quartos(imovel):
    return primeiro_valor(
        imovel,
        "QUARTOS",
        "DORMS",
        "DORMITORIOS",
        "DORMITORIOS",
    )


def obter_suites(imovel):
    return primeiro_valor(imovel, "SUITES", "SUITE")


def obter_banheiros(imovel):
    return primeiro_valor(imovel, "BANHEIROS", "BANHEIRO")


def obter_vagas(imovel):
    return primeiro_valor(
        imovel,
        "VAGAS",
        "GARAGEM",
        "VAGAS_GARAGEM",
    )


def obter_area(imovel):
    return primeiro_valor(
        imovel,
        "AREA_UTIL",
        "AREA",
        "AREA_CONSTRUIDA",
    )


def obter_area_terreno(imovel):
    return primeiro_valor(
        imovel,
        "AREA_TERRENO",
        "TERRENO",
    )


def obter_condominio(imovel):
    return primeiro_valor(
        imovel,
        "CONDOMINIO",
        "VALOR_CONDOMINIO",
    )


def obter_descricao(imovel):
    return primeiro_valor(
        imovel,
        "DESCRICAO",
        "OBSERVACOES",
        "OBSERVACOES_EXTRAS",
        "COMPLEMENTO",
    )


def titulo_imovel(imovel):
    tipo = obter_tipo(imovel).strip()
    bairro = obter_bairro(imovel).strip()

    if bairro:
        return f"{tipo} em {bairro}"

    return tipo


def meta_imovel(imovel):
    partes = []

    quartos = obter_quartos(imovel)
    if quartos:
        partes.append(f"{quartos} quarto{'s' if quartos != '1' else ''}")

    suites = obter_suites(imovel)
    if suites:
        partes.append(f"{suites} suíte{'s' if suites != '1' else ''}")

    vagas = obter_vagas(imovel)
    if vagas:
        partes.append(f"{vagas} vaga{'s' if vagas != '1' else ''}")

    area = obter_area(imovel)
    if area:
        partes.append(formatar_area(area))

    return " · ".join(partes)


def texto_localizacao(imovel):
    bairro = obter_bairro(imovel)
    cidade = obter_cidade(imovel)

    if bairro and cidade:
        return f"{bairro} · {cidade}"

    return bairro or cidade or "Localização sob consulta"


# ============================================================
# NAVEGAÇÃO / ESTADO
# ============================================================

def selecionar_imovel(codigo):
    st.session_state["imovel_selecionado"] = codigo
    st.session_state["pagina"] = 1
    st.rerun()


def voltar_portal():
    st.session_state["imovel_selecionado"] = None
    st.rerun()


def definir_categoria(categoria):
    st.session_state["categoria"] = categoria
    st.session_state["pagina"] = 1
    st.session_state["imovel_selecionado"] = None
    st.rerun()


# ============================================================
# HEADER
# ============================================================

st.markdown('<div class="cf-header">', unsafe_allow_html=True)

col_logo, col_spacer = st.columns([3, 7])

with col_logo:
    mostrar_logo()

st.markdown("</div>", unsafe_allow_html=True)

categorias = [
    ("DESTAQUES", "DESTAQUES"),
    ("CASAS", "CASAS"),
    ("APARTAMENTOS", "APARTAMENTOS"),
    ("TERRENOS", "TERRENOS"),
    ("COMERCIAIS", "COMERCIAIS"),
]

# Barra de navegação com botões discretos.
cols_nav = st.columns(len(categorias))

for col, (rotulo, valor) in zip(cols_nav, categorias):
    with col:
        if st.button(
            rotulo,
            key=f"nav_{valor}",
            use_container_width=True,
        ):
            definir_categoria(valor)


# ============================================================
# DADOS
# ============================================================

try:
    todos_imoveis = carregar_imoveis_sheets()
    publicados = imoveis_publicados(todos_imoveis)
except Exception as erro:
    st.error(
        "Não foi possível carregar os imóveis neste momento. "
        "Verifique as credenciais do Google e a conexão com a planilha."
    )
    st.stop()


# ============================================================
# DETALHE DO IMÓVEL
# ============================================================

codigo_selecionado = st.session_state.get("imovel_selecionado")

if codigo_selecionado:
    selecionado = next(
        (
            item
            for item in publicados
            if item.get("CODIGO", "").upper() == str(codigo_selecionado).upper()
        ),
        None,
    )

    if not selecionado:
        st.session_state["imovel_selecionado"] = None
        st.warning("Este imóvel não está disponível no portal.")
        st.stop()

    if st.button("← VOLTAR PARA OS IMÓVEIS"):
        voltar_portal()

    st.markdown('<div class="detail-top">', unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="detail-kicker">{selecionado.get("CODIGO", "")} · {obter_tipo(selecionado)}</div>
        <div class="detail-title">{titulo_imovel(selecionado)}</div>
        <div class="detail-location">{texto_localizacao(selecionado)}</div>
        <div class="detail-price">{obter_valor(selecionado)}</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)

    # Galeria completa só é carregada quando o usuário abre o imóvel.
    try:
        fotos = listar_fotos_imovel(selecionado["CODIGO"])
    except Exception:
        fotos = []

    if fotos:
        principal = baixar_arquivo_drive(fotos[0]["id"])

        st.image(
            principal,
            use_container_width=True,
        )

        if len(fotos) > 1:
            st.markdown(
                '<div class="detail-section-title">Fotos</div>',
                unsafe_allow_html=True,
            )

            # Até 12 fotos na primeira renderização. O restante continua
            # disponível se a pasta tiver mais arquivos.
            fotos_galeria = fotos[1:]

            for inicio in range(0, len(fotos_galeria), 4):
                grupo = fotos_galeria[inicio:inicio + 4]
                colunas = st.columns(len(grupo))

                for coluna, foto in zip(colunas, grupo):
                    with coluna:
                        try:
                            dados = baixar_arquivo_drive(foto["id"])
                            st.image(dados, use_container_width=True)
                        except Exception:
                            st.empty()
    else:
        miniatura_id = obter_miniatura_id(selecionado)
        miniatura = obter_foto_miniatura_por_id(miniatura_id)

        if miniatura:
            st.image(miniatura, use_container_width=True)
        else:
            st.info("Fotos deste imóvel ainda não estão disponíveis.")

    # Características
    st.markdown(
        '<div class="detail-section"><div class="detail-section-title">Características</div></div>',
        unsafe_allow_html=True,
    )

    estatisticas = []

    area = obter_area(selecionado)
    if area:
        estatisticas.append(("Área", formatar_area(area)))

    terreno = obter_area_terreno(selecionado)
    if terreno:
        estatisticas.append(("Terreno", formatar_area(terreno)))

    quartos = obter_quartos(selecionado)
    if quartos:
        estatisticas.append(("Quartos", quartos))

    suites = obter_suites(selecionado)
    if suites:
        estatisticas.append(("Suítes", suites))

    banheiros = obter_banheiros(selecionado)
    if banheiros:
        estatisticas.append(("Banheiros", banheiros))

    vagas = obter_vagas(selecionado)
    if vagas:
        estatisticas.append(("Vagas", vagas))

    condominio = obter_condominio(selecionado)
    if condominio:
        estatisticas.append(("Condomínio", formatar_moeda(condominio)))

    if estatisticas:
        colunas = st.columns(min(4, len(estatisticas)))

        for indice, (rotulo, valor) in enumerate(estatisticas):
            with colunas[indice % len(colunas)]:
                st.markdown(
                    f"""
                    <div class="stat-box">
                        <div class="stat-label">{rotulo}</div>
                        <div class="stat-value">{valor}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    descricao = obter_descricao(selecionado)

    if descricao:
        st.markdown(
            f"""
            <div class="detail-section">
                <div class="detail-section-title">Sobre este imóvel</div>
                <div style="font-size:14px; line-height:1.8; color:#4F5A62;">
                    {descricao}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        f"""
        <div class="contact-box">
            <div class="contact-title">Quer conhecer este imóvel?</div>
            <div class="contact-text">
                Fale com a Carvalho Ferreira para receber mais informações ou agendar uma visita.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)

    with c1:
        st.link_button(
            "FALAR COM FERNANDO",
            url_whatsapp(WHATSAPP_FERNANDO, selecionado["CODIGO"]),
            use_container_width=True,
        )

    with c2:
        st.link_button(
            "FALAR COM VALDIR",
            url_whatsapp(WHATSAPP_VALDIR, selecionado["CODIGO"]),
            use_container_width=True,
        )

    st.markdown(
        f"""
        <div class="cf-footer">
            Carvalho Ferreira · Consultoria Imobiliária · {selecionado.get("CODIGO", "")}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.stop()


# ============================================================
# PÁGINA PRINCIPAL
# ============================================================

categoria = st.session_state.get("categoria", "DESTAQUES")

# Busca pública
busca = st.text_input(
    "Buscar imóvel",
    placeholder="Buscar imóvel, bairro ou código",
    label_visibility="collapsed",
)

busca_normalizada = str(busca or "").strip().lower()

if categoria == "DESTAQUES":
    st.markdown(
        """
        <div class="section-kicker">Carvalho Ferreira</div>
        <div class="section-title">Imóveis selecionados</div>
        <div class="section-description">
            Uma seleção de imóveis disponíveis para você conhecer.
        </div>
        """,
        unsafe_allow_html=True,
    )

    destaques = imoveis_destaques(publicados)

    if busca_normalizada:
        destaques = [
            item for item in destaques
            if busca_normalizada in " ".join(
                [
                    item.get("CODIGO", ""),
                    obter_tipo(item),
                    obter_bairro(item),
                    obter_cidade(item),
                ]
            ).lower()
        ]

    if destaques:
        if "carousel_indice" not in st.session_state:
            st.session_state["carousel_indice"] = 0

        indice = st.session_state["carousel_indice"] % len(destaques)
        destaque = destaques[indice]

        miniatura_id = obter_miniatura_id(destaque)
        imagem = obter_foto_miniatura_por_id(miniatura_id)

        if imagem:
            st.markdown('<div class="hero">', unsafe_allow_html=True)
            st.image(imagem, use_container_width=True)

            st.markdown(
                f"""
                <div class="hero-info">
                    <div class="hero-kicker">{destaque.get("CODIGO", "")} · {obter_tipo(destaque)}</div>
                    <div class="hero-title">{titulo_imovel(destaque)}</div>
                    <div class="hero-location">{texto_localizacao(destaque)}</div>
                    <div class="hero-price">{obter_valor(destaque)}</div>
                    <div class="hero-meta">{meta_imovel(destaque)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown("</div>", unsafe_allow_html=True)

            if st.button(
                "VER IMÓVEL",
                key=f"hero_ver_{destaque['CODIGO']}",
                use_container_width=True,
            ):
                selecionar_imovel(destaque["CODIGO"])

            n = len(destaques)

            c_prev, c_dots, c_next = st.columns([1, 4, 1])

            with c_prev:
                if st.button("←", key="carousel_prev", use_container_width=True):
                    st.session_state["carousel_indice"] = (indice - 1) % n
                    st.rerun()

            with c_dots:
                st.markdown(
                    f'<div class="carousel-dots">{"·" * (indice + 1)} · {"·" * (n - indice - 1)}</div>',
                    unsafe_allow_html=True,
                )

            with c_next:
                if st.button("→", key="carousel_next", use_container_width=True):
                    st.session_state["carousel_indice"] = (indice + 1) % n
                    st.rerun()
        else:
            st.info("As fotos dos imóveis em destaque ainda não estão disponíveis.")
    else:
        st.markdown(
            '<div class="empty-state">Nenhum imóvel em destaque disponível no momento.</div>',
            unsafe_allow_html=True,
        )

else:
    filtrados = [
        item for item in publicados
        if normalizar_chave(obter_tipo(item)) == normalizar_chave(categoria[:-1])
        or (
            categoria == "COMERCIAIS"
            and any(
                termo in normalizar_chave(obter_tipo(item))
                for termo in ["COMERCIAL", "SALA", "PONTO", "GALPAO", "LOJA"]
            )
        )
    ]

    if categoria == "CASAS":
        filtrados = [
            item for item in publicados
            if any(
                termo in normalizar_chave(obter_tipo(item))
                for termo in ["CASA", "SOBRADO", "ASSOBRADADA"]
            )
        ]

    elif categoria == "APARTAMENTOS":
        filtrados = [
            item for item in publicados
            if "APART" in normalizar_chave(obter_tipo(item))
        ]

    elif categoria == "TERRENOS":
        filtrados = [
            item for item in publicados
            if any(
                termo in normalizar_chave(obter_tipo(item))
                for termo in ["TERRENO", "LOTE"]
            )
        ]

    elif categoria == "COMERCIAIS":
        filtrados = [
            item for item in publicados
            if any(
                termo in normalizar_chave(obter_tipo(item))
                for termo in [
                    "COMERCIAL",
                    "SALA",
                    "PONTO",
                    "GALPAO",
                    "LOJA",
                    "PRÉDIO",
                    "PREDIO",
                ]
            )
        ]

    if busca_normalizada:
        filtrados = [
            item for item in filtrados
            if busca_normalizada in " ".join(
                [
                    item.get("CODIGO", ""),
                    obter_tipo(item),
                    obter_bairro(item),
                    obter_cidade(item),
                ]
            ).lower()
        ]

    st.markdown(
        f"""
        <div class="section-kicker">Carvalho Ferreira</div>
        <div class="section-title">{categoria.title()}</div>
        <div class="section-description">
            {len(filtrados)} imóvel{' disponível' if len(filtrados) == 1 else 's disponíveis'}.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not filtrados:
        st.markdown(
            '<div class="empty-state">Nenhum imóvel encontrado com esses critérios.</div>',
            unsafe_allow_html=True,
        )
    else:
        pagina = st.session_state.get("pagina", 1)

        total_paginas = max(
            1,
            (len(filtrados) + ITENS_POR_PAGINA - 1) // ITENS_POR_PAGINA,
        )

        pagina = min(max(pagina, 1), total_paginas)

        inicio = (pagina - 1) * ITENS_POR_PAGINA
        fim = inicio + ITENS_POR_PAGINA
        pagina_imoveis = filtrados[inicio:fim]

        for inicio_grupo in range(0, len(pagina_imoveis), 3):
            grupo = pagina_imoveis[inicio_grupo:inicio_grupo + 3]
            colunas = st.columns(3)

            for coluna, imovel in zip(colunas, grupo):
                with coluna:
                    miniatura_id = obter_miniatura_id(imovel)
                    imagem = obter_foto_miniatura_por_id(miniatura_id)

                    st.markdown('<div class="property-card">', unsafe_allow_html=True)

                    if imagem:
                        st.image(
                            imagem,
                            use_container_width=True,
                        )

                    st.markdown(
                        f"""
                        <div class="card-body">
                            <div class="card-type">{obter_tipo(imovel)}</div>
                            <div class="card-title">{titulo_imovel(imovel)}</div>
                            <div class="card-location">{texto_localizacao(imovel)}</div>
                            <div class="card-price">{obter_valor(imovel)}</div>
                            <div class="card-meta">{meta_imovel(imovel)}</div>
                            <div class="card-code">{imovel.get("CODIGO", "")}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    st.markdown("</div>", unsafe_allow_html=True)

                    if st.button(
                        "VER IMÓVEL",
                        key=f"ver_{imovel['CODIGO']}",
                        use_container_width=True,
                    ):
                        selecionar_imovel(imovel["CODIGO"])

        if total_paginas > 1:
            st.markdown("<br>", unsafe_allow_html=True)

            p1, p2, p3 = st.columns([1, 2, 1])

            with p1:
                if pagina > 1:
                    if st.button("← ANTERIOR", use_container_width=True):
                        st.session_state["pagina"] = pagina - 1
                        st.rerun()

            with p2:
                st.markdown(
                    f"<div style='text-align:center;color:#69747D;font-size:12px;padding-top:8px;'>"
                    f"Página {pagina} de {total_paginas}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            with p3:
                if pagina < total_paginas:
                    if st.button("PRÓXIMA →", use_container_width=True):
                        st.session_state["pagina"] = pagina + 1
                        st.rerun()


# ============================================================
# RODAPÉ
# ============================================================

st.markdown(
    """
    <div class="cf-footer">
        Carvalho Ferreira · Consultoria Imobiliária<br>
        Análise precisa + transparência + cliente certo.
    </div>
    """,
    unsafe_allow_html=True,
)
