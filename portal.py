# portal.py
# -*- coding: utf-8 -*-
"""
Carvalho Ferreira | Portal Público
Versão focada em experiência premium e conversão de leads.
"""

import io
import urllib.parse
from pathlib import Path
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import base64
import math

# =============================================================================
# CONFIGURAÇÃO DA PÁGINA
# =============================================================================

st.set_page_config(
    page_title="Carvalho Ferreira | Consultoria Imobiliária",
    page_icon="CF",
    layout="wide",
    initial_sidebar_state="collapsed",
)

SCOPES_DRIVE = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]

SPREADSHEET_ID = "1nVEpOZFYFKcq0MXtOwxn22nqxafmJBHnf6zhHQlyT8w"
NOME_ABA = "Imoveis"

TELEFONE_FERNANDO = "5512988162626"
TELEFONE_VALDIR = "5512992157474"

ITENS_POR_PAGINA = 6

# =============================================================================
# ESTILO VISUAL – IDENTIDADE CARVALHO FERREIRA
# Fundo bem fechado (quase preto) + dourado + off-white
# =============================================================================

st.markdown(
    """
    <style>
    /* ===== RESET E BASE ===== */
    [data-testid="stSidebarNav"] { display: none !important; }
    header { visibility: hidden !important; }
    #MainMenu { visibility: hidden !important; }
    footer { visibility: hidden !important; }

    .stApp {
        background-color: #0B0F14;
        color: #F7F5F0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 4rem;
        max-width: 1180px;
        padding-left: 1.5rem;
        padding-right: 1.5rem;
    }

    /* Remove espaços extras que parecem botões vazios */
    div[data-testid="stVerticalBlock"] > div {
        gap: 0.4rem !important;
    }

    .element-container {
        margin-bottom: 0 !important;
    }

    /* ===== CABEÇALHO DE MARCA ===== */
    .brand-header {
        text-align: center;
        padding: 0.4rem 0 0.6rem 0;
    }

    .brand-title {
        font-size: 1.85rem !important;
        font-weight: 600 !important;
        letter-spacing: 5px;
        color: #F7F5F0 !important;
        margin: 0;
        text-transform: uppercase;
        line-height: 1.2;
    }

    .brand-subtitle {
        font-size: 0.72rem;
        font-weight: 500;
        letter-spacing: 3.5px;
        color: #6B7280;
        margin-top: 6px;
        text-transform: uppercase;
    }

    .brand-line {
        width: 48px;
        height: 1px;
        background: #D4AF37;
        margin: 12px auto 0 auto;
        opacity: 0.9;
    }

    /* ===== MENU DE NAVEGAÇÃO FINO ===== */
    div[data-testid="stHorizontalBlock"] button {
        background: transparent !important;
        border: none !important;
        color: #6B7280 !important;
        font-size: 0.78rem !important;
        font-weight: 500 !important;
        letter-spacing: 1.8px !important;
        text-transform: uppercase !important;
        padding: 4px 2px 8px 2px !important;
        border-radius: 0 !important;
        border-bottom: 1.5px solid transparent !important;
        box-shadow: none !important;
        min-height: unset !important;
    }

    div[data-testid="stHorizontalBlock"] button:hover {
        color: #F7F5F0 !important;
        border-bottom: 1.5px solid rgba(212, 175, 55, 0.5) !important;
        background: transparent !important;
    }

    /* ===== DIVISÓRIA FINA ===== */
    .thin-divider {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, #1F2937 15%, #1F2937 85%, transparent);
        margin: 0.3rem 0 1.4rem 0;
    }

    /* ===== BUSCA ===== */
    .stTextInput > div > div > input {
        background-color: #111827 !important;
        border: 1px solid #1F2937 !important;
        border-radius: 6px !important;
        color: #F7F5F0 !important;
        font-size: 0.9rem !important;
        padding: 0.55rem 0.9rem !important;
    }

    .stTextInput > div > div > input:focus {
        border-color: #D4AF37 !important;
        box-shadow: 0 0 0 1px rgba(212, 175, 55, 0.25) !important;
    }

    .stTextInput label {
        color: #6B7280 !important;
        font-size: 0.8rem !important;
    }

    /* ===== TÍTULOS DE SEÇÃO ===== */
    .section-title {
        font-size: 1.05rem !important;
        font-weight: 600 !important;
        color: #F7F5F0 !important;
        letter-spacing: 1px;
        margin: 0.3rem 0 1rem 0;
        text-transform: uppercase;
    }

    .section-count {
        font-size: 0.85rem;
        color: #6B7280;
        font-weight: 400;
        letter-spacing: 0.5px;
    }

    /* ===== CARDS DE IMÓVEIS ===== */
    .imovel-card {
        background-color: #111827;
        border: 1px solid #1F2937;
        border-radius: 10px;
        padding: 14px;
        margin-bottom: 8px;
        transition: border-color 0.2s ease;
        height: 100%;
    }

    .imovel-card:hover {
        border-color: #D4AF37;
    }

    .foto-container-relativo {
        position: relative;
        width: 100%;
        margin-bottom: 10px;
        overflow: hidden;
        border-radius: 7px;
    }

    .foto-container-relativo img {
        border-radius: 7px;
        width: 100% !important;
        object-fit: cover !important;
        height: 200px !important;
        display: block;
        transition: transform 0.3s ease;
    }

    .imovel-card:hover .foto-container-relativo img {
        transform: scale(1.03);
    }

    .status-badge {
        position: absolute;
        top: 10px;
        right: 10px;
        padding: 4px 9px;
        border-radius: 4px;
        font-size: 0.65rem;
        font-weight: 700;
        letter-spacing: 0.7px;
        z-index: 10;
        backdrop-filter: blur(4px);
    }

    .status-disponivel {
        background-color: rgba(35, 134, 54, 0.92);
        color: #ffffff;
        border: 1px solid rgba(255, 255, 255, 0.15);
    }

    .status-negociacao {
        background-color: rgba(158, 106, 3, 0.92);
        color: #ffffff;
        border: 1px solid rgba(255, 255, 255, 0.15);
    }

    .status-vendido {
        background-color: rgba(218, 54, 51, 0.92);
        color: #ffffff;
        border: 1px solid rgba(255, 255, 255, 0.15);
    }

    .preco-imovel {
        font-size: 1.22rem;
        font-weight: 700;
        color: #D4AF37;
        margin-bottom: 5px;
        letter-spacing: 0.3px;
    }

    .codigo-tag {
        font-size: 0.72rem;
        font-weight: 600;
        color: #6B7280;
        background: #0B0F14;
        padding: 2px 7px;
        border-radius: 4px;
        border: 1px solid #1F2937;
        display: inline-block;
        margin-bottom: 7px;
        letter-spacing: 0.4px;
    }

    .info-sub {
        font-size: 0.82rem;
        color: #6B7280;
        margin-bottom: 2px;
        line-height: 1.35;
    }

    .tipo-detalhe {
        font-size: 0.88rem;
        font-weight: 560;
        color: #F7F5F0;
        margin-top: 5px;
        margin-bottom: 10px;
        line-height: 1.4;
    }

    /* ===== BOTÕES WHATSAPP ===== */
    .stLinkButton > button {
        border-radius: 6px !important;
        font-weight: 600 !important;
        background-color: #0B0F14 !important;
        color: #F7F5F0 !important;
        border: 1px solid #1F2937 !important;
        width: 100% !important;
        font-size: 0.78rem !important;
        padding: 0.42rem 0.4rem !important;
        letter-spacing: 0.3px;
        transition: all 0.2s ease !important;
    }

    .stLinkButton > button:hover {
        background-color: #111827 !important;
        border-color: #D4AF37 !important;
        color: #ffffff !important;
    }

    /* ===== PAGINAÇÃO ===== */
    .paginacao-info {
        text-align: center;
        font-size: 0.82rem;
        color: #6B7280;
        margin: 1.2rem 0 0.6rem 0;
        letter-spacing: 0.4px;
    }

    /* ===== RODAPÉ ===== */
    .footer-cf {
        text-align: center;
        margin-top: 2.8rem;
        padding-top: 1.3rem;
        border-top: 1px solid #1F2937;
    }

    .footer-text {
        font-size: 0.72rem;
        color: #6B7280;
        letter-spacing: 1.5px;
        text-transform: uppercase;
    }

    .footer-line {
        width: 36px;
        height: 1px;
        background: #D4AF37;
        margin: 10px auto 12px auto;
        opacity: 0.75;
    }

    /* ===== RESPONSIVO ===== */
    @media (max-width: 768px) {
        .brand-title {
            font-size: 1.45rem !important;
            letter-spacing: 3px;
        }
        div[data-testid="stHorizontalBlock"] button {
            font-size: 0.68rem !important;
            letter-spacing: 1.2px !important;
        }
        .imovel-card {
            padding: 12px;
        }
        .foto-container-relativo img {
            height: 180px !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =============================================================================
# CONEXÕES GOOGLE
# =============================================================================

@st.cache_resource
def conectar_google():
    creds_dict = dict(st.secrets["google_credentials"])
    creds = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=SCOPES_DRIVE
    )
    drive = build("drive", "v3", credentials=creds)
    sheets = build("sheets", "v4", credentials=creds)
    return drive, sheets


def normalizar(texto):
    if not texto:
        return ""
    return " ".join(str(texto).strip().upper().split())


@st.cache_data(ttl=300)
def carregar_imoveis_sheets():
    try:
        _, sheets = conectar_google()
        result = (
            sheets.spreadsheets()
            .values()
            .get(spreadsheetId=SPREADSHEET_ID, range=f"'{NOME_ABA}'!A:AZ")
            .execute()
        )
        rows = result.get("values", [])
        if not rows or len(rows) < 2:
            return []

        cabecalho = [normalizar(h) for h in rows[0]]
        imoveis = []

        for row in rows[1:]:
            if not row or not row[0]:
                continue
            while len(row) < len(cabecalho):
                row.append("")

            dados = {cabecalho[i]: row[i] for i in range(len(cabecalho))}

            codigo = dados.get("CODIGO") or dados.get("CÓDIGO") or row[0]
            tipo = dados.get("TIPO") or dados.get("CATEGORIA") or "Imóvel"
            bairro = dados.get("BAIRRO") or ""
            cidade = dados.get("CIDADE") or ""
            valor = dados.get("VALOR") or "Sob consulta"
            quartos = dados.get("QUARTOS") or dados.get("DORMS") or dados.get("DORMITORIOS") or ""
            vagas = dados.get("VAGAS") or dados.get("GARAGEM") or ""
            area_util = dados.get("AREA UTIL") or dados.get("ÁREA ÚTIL") or ""
            status = dados.get("STATUS") or "Disponível"
            miniatura_id = dados.get("MINIATURA") or dados.get("FOTO") or ""

            imoveis.append({
                "codigo": codigo,
                "tipo": tipo,
                "bairro": bairro,
                "cidade": cidade,
                "valor": valor,
                "quartos": quartos,
                "vagas": vagas,
                "area_util": area_util,
                "status": status,
                "miniatura_id": miniatura_id.strip(),
            })

        return imoveis
    except Exception as e:
        st.error(f"Erro ao carregar dados da planilha: {e}")
        return []


@st.cache_data(ttl=600)
def obter_foto_miniatura_por_id(file_id):
    if not file_id or len(str(file_id).strip()) < 10:
        return None
    try:
        drive, _ = conectar_google()
        request = drive.files().get_media(fileId=file_id.strip())
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        fh.seek(0)
        return fh.read()
    except Exception:
        return None


# =============================================================================
# ESTADO
# =============================================================================

if "cat" not in st.session_state:
    st.session_state["cat"] = "DESTAQUES"

if "pagina" not in st.session_state:
    st.session_state["pagina"] = 1

# =============================================================================
# CABEÇALHO DE MARCA
# =============================================================================

def encontrar_logo():
    """Procura o logo nos caminhos mais comuns da pasta marca."""
    candidatos = [
        Path("marca/logo/logo.png"),
        Path("marca/Logo/logo.png"),
        Path("marca/logo.png"),
        Path("marca/Logo.png"),
        Path("marca/logo/Logo.png"),
        Path("marca/Logo/Logo.png"),
    ]
    # Também procura qualquer PNG dentro de marca/logo ou marca/Logo
    for pasta in [Path("marca/logo"), Path("marca/Logo")]:
        if pasta.exists() and pasta.is_dir():
            for arq in pasta.glob("*.png"):
                candidatos.append(arq)
            for arq in pasta.glob("*.PNG"):
                candidatos.append(arq)

    for caminho in candidatos:
        if caminho.exists() and caminho.is_file():
            return caminho
    return None


# Cabeçalho com logo em tamanho controlado + nome da marca
logo_encontrado = encontrar_logo()

if logo_encontrado:
    # Centraliza o logo com largura fixa em pixels (ajuste esse número se quiser)
    col_l, col_c, col_r = st.columns([1, 0.5, 1.5])
    with col_c:
        st.image(str(logo_encontrado), width=120)  # ← mude 140 para aumentar ou diminuir

    st.markdown(
        """
        <div class="brand-header" style="padding-top: 0.15rem; padding-bottom: 0.25rem;">
            <div class="brand-title" style="font-size: 1.3rem !important; letter-spacing: 4px;">Carvalho Ferreira</div>
            <div class="brand-subtitle">Consultoria Imobiliária</div>
            <div class="brand-line"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        """
        <div class="brand-header">
            <div class="brand-title">Carvalho Ferreira</div>
            <div class="brand-subtitle">Consultoria Imobiliária</div>
            <div class="brand-line"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )



# =============================================================================
# MENU DE NAVEGAÇÃO FINO
# =============================================================================

categorias = ["DESTAQUES", "CASAS", "APARTAMENTOS", "TERRENOS", "COMERCIAIS"]
cols_nav = st.columns(len(categorias))

for i, cat_nome in enumerate(categorias):
    with cols_nav[i]:
        if st.button(cat_nome, key=f"nav_{cat_nome}", use_container_width=True):
            st.session_state["cat"] = cat_nome
            st.session_state["pagina"] = 1  # volta para a primeira página ao trocar categoria
            st.rerun()

st.markdown('<hr class="thin-divider">', unsafe_allow_html=True)

# =============================================================================
# BUSCA RÁPIDA
# =============================================================================

busca_codigo = st.text_input(
    "Busca rápida por código",
    placeholder="Ex: CF024",
    label_visibility="collapsed",
)

# =============================================================================
# CARREGAMENTO E FILTRAGEM
# =============================================================================

lista_imoveis = carregar_imoveis_sheets()

if not lista_imoveis:
    st.warning("Nenhum imóvel encontrado no momento.")
    st.stop()

imoveis_exibidos = []
cat_ativa = st.session_state["cat"]

if busca_codigo and busca_codigo.strip():
    termo = normalizar(busca_codigo)
    imoveis_exibidos = [i for i in lista_imoveis if termo in normalizar(i["codigo"])]
    titulo_secao = "Resultado da busca"
    st.session_state["pagina"] = 1
else:
    if cat_ativa == "DESTAQUES":
        imoveis_exibidos = [
            i for i in lista_imoveis
            if "DISPONÍVEL" in normalizar(i["status"]) or "DISPONIVEL" in normalizar(i["status"])
        ]
        titulo_secao = "Destaques"
    elif cat_ativa == "CASAS":
        imoveis_exibidos = [i for i in lista_imoveis if "CASA" in normalizar(i["tipo"])]
        titulo_secao = "Casas"
    elif cat_ativa == "APARTAMENTOS":
        imoveis_exibidos = [
            i for i in lista_imoveis
            if "APARTAMENTO" in normalizar(i["tipo"]) or "APTO" in normalizar(i["tipo"])
        ]
        titulo_secao = "Apartamentos"
    elif cat_ativa == "TERRENOS":
        imoveis_exibidos = [
            i for i in lista_imoveis
            if "TERRENO" in normalizar(i["tipo"]) or "LOTE" in normalizar(i["tipo"])
        ]
        titulo_secao = "Terrenos e Lotes"
    elif cat_ativa == "COMERCIAIS":
        imoveis_exibidos = [
            i for i in lista_imoveis
            if "COMERCIAL" in normalizar(i["tipo"])
            or "SALA" in normalizar(i["tipo"])
            or "GALPÃO" in normalizar(i["tipo"])
            or "GALPAO" in normalizar(i["tipo"])
        ]
        titulo_secao = "Comerciais"

# Título da seção
total = len(imoveis_exibidos)
st.markdown(
    f"""
    <div class="section-title">
        {titulo_secao}
        <span class="section-count"> · {total} imóveis</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# =============================================================================
# PAGINAÇÃO (6 por página)
# =============================================================================

if not imoveis_exibidos:
    st.info("Nenhum imóvel encontrado nesta categoria ou busca.")
else:
    total_paginas = max(1, math.ceil(total / ITENS_POR_PAGINA))
    pagina_atual = st.session_state["pagina"]

    # Garante que a página atual é válida
    if pagina_atual > total_paginas:
        pagina_atual = 1
        st.session_state["pagina"] = 1

    inicio = (pagina_atual - 1) * ITENS_POR_PAGINA
    fim = inicio + ITENS_POR_PAGINA
    pagina_imoveis = imoveis_exibidos[inicio:fim]

    # Grid de cards (3 colunas)
    for i in range(0, len(pagina_imoveis), 3):
        grupo = pagina_imoveis[i : i + 3]
        colunas = st.columns(3, gap="medium")

        for posicao, imovel in enumerate(grupo):
            with colunas[posicao]:
                st.markdown('<div class="imovel-card">', unsafe_allow_html=True)

                # Status
                st_normal = normalizar(imovel["status"])
                if "NEGOCIAÇÃO" in st_normal or "NEGOCIACAO" in st_normal:
                    badge_classe = "status-negociacao"
                    badge_texto = "EM NEGOCIAÇÃO"
                elif any(x in st_normal for x in ["VENDIDO", "LOCADO", "INDISPONÍVEL", "INDISPONIVEL"]):
                    badge_classe = "status-vendido"
                    badge_texto = imovel["status"].upper()
                else:
                    badge_classe = "status-disponivel"
                    badge_texto = "DISPONÍVEL"

                # Foto
                foto_bytes = obter_foto_miniatura_por_id(imovel["miniatura_id"])

                if foto_bytes:
                    encoded_img = base64.b64encode(foto_bytes).decode("utf-8")
                    st.markdown(
                        f"""
                        <div class="foto-container-relativo">
                            <span class="status-badge {badge_classe}">{badge_texto}</span>
                            <img src="data:image/jpeg;base64,{encoded_img}" />
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f"""
                        <div class="foto-container-relativo" style="background:#0B0F14;height:200px;display:flex;align-items:center;justify-content:center;color:#6B7280;border-radius:7px;">
                            <span class="status-badge {badge_classe}">{badge_texto}</span>
                            <span style="font-size:0.8rem;">Foto em breve</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                # Preço
                st.markdown(
                    f'<div class="preco-imovel">{imovel["valor"]}</div>',
                    unsafe_allow_html=True,
                )

                # Código
                st.markdown(
                    f'<div class="codigo-tag">Cód: {imovel["codigo"]}</div>',
                    unsafe_allow_html=True,
                )

                # Localização
                local = f"{imovel['bairro']}"
                if imovel["cidade"]:
                    local += f" · {imovel['cidade']}"
                st.markdown(
                    f'<div class="info-sub">{local}</div>',
                    unsafe_allow_html=True,
                )

                # Tipo + detalhes
                partes = [imovel["tipo"]]
                if imovel["quartos"]:
                    partes.append(f"{imovel['quartos']} Dorm.")
                if imovel["vagas"]:
                    partes.append(f"{imovel['vagas']} Vaga(s)")
                if imovel["area_util"]:
                    partes.append(f"{imovel['area_util']} úteis")

                st.markdown(
                    f'<div class="tipo-detalhe">{" · ".join(partes)}</div>',
                    unsafe_allow_html=True,
                )

                # WhatsApp
                msg_whats = (
                    f"Olá, tenho interesse no imóvel {imovel['codigo']} "
                    f"({imovel['tipo']} em {imovel['bairro']}). "
                    f"Gostaria de mais informações."
                )
                link_wf = f"https://wa.me/{TELEFONE_FERNANDO}?text={urllib.parse.quote(msg_whats)}"
                link_wv = f"https://wa.me/{TELEFONE_VALDIR}?text={urllib.parse.quote(msg_whats)}"

                col_w1, col_w2 = st.columns(2)
                with col_w1:
                    st.link_button("Fernando", link_wf, use_container_width=True)
                with col_w2:
                    st.link_button("Valdir", link_wv, use_container_width=True)

                st.markdown("</div>", unsafe_allow_html=True)

    # Controles de paginação
    if total_paginas > 1:
        st.markdown(
            f'<div class="paginacao-info">Página {pagina_atual} de {total_paginas}</div>',
            unsafe_allow_html=True,
        )

        col_prev, col_info, col_next = st.columns([1, 2, 1])

        with col_prev:
            if pagina_atual > 1:
                if st.button("← Anterior", use_container_width=True, key="btn_prev"):
                    st.session_state["pagina"] = pagina_atual - 1
                    st.rerun()

        with col_next:
            if pagina_atual < total_paginas:
                if st.button("Próxima →", use_container_width=True, key="btn_next"):
                    st.session_state["pagina"] = pagina_atual + 1
                    st.rerun()

# =============================================================================
# RODAPÉ
# =============================================================================

st.markdown(
    """
    <div class="footer-cf">
        <div class="footer-line"></div>
        <div class="footer-text">Carvalho Ferreira · Consultoria Imobiliária</div>
    </div>
    """,
    unsafe_allow_html=True,
)
