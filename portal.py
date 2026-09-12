# portal.py
# -*- coding: utf-8 -*-

import io
import urllib.parse
from pathlib import Path
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import base64

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
TELEFONE_VALDIR = "5512999999999"

st.markdown(
    """
    <style>
    [data-testid="stSidebarNav"] { display: none; }
    header { visibility: hidden; }
    
    .stApp {
        background-color: #0e1117;
        color: #f0f2f6;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 4rem;
        max-width: 1200px;
    }

    .brand-container {
        text-align: center;
        margin-bottom: 1rem;
    }

    .brand-title {
        font-size: 2rem !important;
        font-weight: 700 !important;
        letter-spacing: 4px;
        color: #f7f5ef !important;
        margin: 0;
        text-transform: uppercase;
    }

    .brand-subtitle {
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 3px;
        color: #8b949e;
        margin-top: 6px;
        text-transform: uppercase;
        text-align: center;
        margin-bottom: 25px;
    }

    /* BOTÕES DA BARRA SUPERIOR MAIS ESTREITOS E PRÓXIMOS */
    div.stButton > button {
        background-color: #1f2937 !important;
        color: #f7f5ef !important;
        border: 1px solid #374151 !important;
        border-radius: 6px !important;
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        letter-spacing: 1px !important;
        padding: 4px 8px !important;
        transition: all 0.2s ease !important;
    }
    
    div.stButton > button:hover {
        background-color: #374151 !important;
        border-color: #d4af37 !important;
        color: #ffffff !important;
    }

    .foto-container-relativo {
        position: relative;
        width: 100%;
        margin-bottom: 10px;
    }

    .foto-container-relativo img {
        border-radius: 8px;
        width: 100% !important;
        object-fit: cover !important;
        height: 220px !important;
        display: block;
    }

    .status-badge {
        position: absolute;
        top: 10px;
        right: 10px;
        padding: 5px 10px;
        border-radius: 6px;
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.8px;
        z-index: 10;
        backdrop-filter: blur(4px);
    }

    .status-disponivel {
        background-color: rgba(35, 134, 54, 0.9);
        color: #ffffff;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }

    .status-negociacao {
        background-color: rgba(158, 106, 3, 0.9);
        color: #ffffff;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }

    .status-vendido {
        background-color: rgba(218, 54, 51, 0.9);
        color: #ffffff;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }

    .imovel-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 20px;
        transition: border-color 0.2s ease-in-out;
    }

    .imovel-card:hover {
        border-color: #d4af37;
    }

    .preco-imovel {
        font-size: 1.3rem;
        font-weight: 700;
        color: #d4af37;
        margin-bottom: 6px;
    }

    .tipo-detalhe {
        font-size: 0.95rem;
        font-weight: 600;
        color: #f7f5ef;
        margin-bottom: 4px;
    }

    .info-sub {
        font-size: 0.85rem;
        color: #8b949e;
        margin-bottom: 4px;
    }

    .codigo-tag {
        font-size: 0.8rem;
        font-weight: 600;
        color: #8b949e;
        background: #1a1f2c;
        padding: 3px 8px;
        border-radius: 6px;
        border: 1px solid #30363d;
        display: inline-block;
        margin-bottom: 8px;
    }

    .stLinkButton > button {
        border-radius: 6px;
        font-weight: 600;
        background-color: #1f2937;
        color: #f7f5ef;
        border: 1px solid #374151;
        width: 100%;
        font-size: 0.8rem !important;
        padding: 4px 8px !important;
    }
    
    .stLinkButton > button:hover {
        background-color: #374151;
        border-color: #d4af37;
        color: #ffffff;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

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

if "cat" not in st.session_state:
    st.session_state["cat"] = "DESTAQUES"

# CABEÇALHO CENTRALIZADO
col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
with col_l2:
    logo_path = Path("marca/logo.png")
    if logo_path.exists():
        st.image(str(logo_path), use_container_width=True)
    else:
        st.markdown(
            """
            <div class="brand-container">
                <h1 class="brand-title">Carvalho Ferreira</h1>
            </div>
            """,
            unsafe_allow_html=True
        )
    st.markdown('<div class="brand-subtitle">Consultoria Imobiliária</div>', unsafe_allow_html=True)

# BARRA DE NAVEGAÇÃO SUPERIOR (BOTÕES ESTREITOS E PRÓXIMOS)
categorias = ["DESTAQUES", "CASAS", "APARTAMENTOS", "TERRENOS", "COMERCIAIS"]
cols_nav = st.columns(len(categorias))

for i, cat_nome in enumerate(categorias):
    with cols_nav[i]:
        if st.button(cat_nome, key=f"nav_{cat_nome}", use_container_width=True):
            st.session_state["cat"] = cat_nome

st.markdown("---")

# BUSCA RÁPIDA POR CÓDIGO (TEXTO PURO, SEM EMOJIS)
busca_codigo = st.text_input("Busca rápida por código do imóvel", placeholder="Digite o código (ex: CF001)")
st.markdown("<br>", unsafe_allow_html=True)

lista_imoveis = carregar_imoveis_sheets()

if not lista_imoveis:
    st.warning("Nenhum imóvel encontrado na planilha.")
    st.stop()

imoveis_exibidos = []
cat_ativa = st.session_state["cat"]

if busca_codigo:
    termo = normalizar(busca_codigo)
    imoveis_exibidos = [i for i in lista_imoveis if termo in normalizar(i["codigo"])]
    st.markdown(f"### Resultado da busca: {busca_codigo}")
else:
    if cat_ativa == "DESTAQUES":
        imoveis_exibidos = [i for i in lista_imoveis if "DISPONÍVEL" in normalizar(i["status"]) or "DISPONIVEL" in normalizar(i["status"])]
        st.markdown("### Destaques Selecionados")
    elif cat_ativa == "CASAS":
        imoveis_exibidos = [i for i in lista_imoveis if "CASA" in normalizar(i["tipo"])]
        st.markdown("### Casas Disponíveis")
    elif cat_ativa == "APARTAMENTOS":
        imoveis_exibidos = [i for i in lista_imoveis if "APARTAMENTO" in normalizar(i["tipo"]) or "APTO" in normalizar(i["tipo"])]
        st.markdown("### Apartamentos Disponíveis")
    elif cat_ativa == "TERRENOS":
        imoveis_exibidos = [i for i in lista_imoveis if "TERRENO" in normalizar(i["tipo"]) or "LOTE" in normalizar(i["tipo"])]
        st.markdown("### Terrenos e Lotes")
    elif cat_ativa == "COMERCIAIS":
        imoveis_exibidos = [i for i in lista_imoveis if "COMERCIAL" in normalizar(i["tipo"]) or "SALA" in normalizar(i["tipo"]) or "GALPÃO" in normalizar(i["tipo"])]
        st.markdown("### Imóveis Comerciais")

st.markdown("---")

if not imoveis_exibidos:
    st.info("Nenhum imóvel encontrado nesta categoria ou busca.")
else:
    for inicio in range(0, len(imoveis_exibidos), 3):
        grupo = imoveis_exibidos[inicio:inicio + 3]
        colunas = st.columns(3)

        for posicao, imovel in enumerate(grupo):
            with colunas[posicao]:
                with st.container():
                    st.markdown('<div class="imovel-card">', unsafe_allow_html=True)

                    st_normal = normalizar(imovel["status"])
                    if "NEGOCIAÇÃO" in st_normal or "NEGOCIACAO" in st_normal:
                        badge_classe = "status-negociacao"
                        badge_texto = "EM NEGOCIAÇÃO"
                    elif "VENDIDO" in st_normal or "LOCADO" in st_normal or "INDISPONÍVEL" in st_normal or "INDISPONIVEL" in st_normal:
                        badge_classe = "status-vendido"
                        badge_texto = imovel["status"].upper()
                    else:
                        badge_classe = "status-disponivel"
                        badge_texto = "DISPONÍVEL"

                    foto_bytes = obter_foto_miniatura_por_id(imovel["miniatura_id"])
                    
                    if foto_bytes:
                        encoded_img = base64.b64encode(foto_bytes).decode("utf-8")
                        st.markdown(f'''
                            <div class="foto-container-relativo">
                                <span class="status-badge {badge_classe}">{badge_texto}</span>
                                <img src="data:image/jpeg;base64,{encoded_img}" />
                            </div>
                        ''', unsafe_allow_html=True)
                    else:
                        st.markdown(f'''
                            <div class="foto-container-relativo" style="background: #21262d; height: 220px; display: flex; align-items: center; justify-content: center; color: #8b949e; border-radius: 8px;">
                                <span class="status-badge {badge_classe}">{badge_texto}</span>
                                <span>Miniatura não configurada</span>
                            </div>
                        ''', unsafe_allow_html=True)

                    # 1. PREÇO EM DESTAQUE NO TOPO DO CARD
                    st.markdown(
                        f'''
                        <div class="preco-imovel">
                            {imovel["valor"]}
                        </div>
                        ''',
                        unsafe_allow_html=True,
                    )

                    # 2. CÓDIGO LOGO ABAIXO (SEM EMOJI)
                    st.markdown(
                        f'''
                        <div class="codigo-tag">
                            Cód: {imovel["codigo"]}
                        </div>
                        ''',
                        unsafe_allow_html=True,
                    )

                    # 3. LOCALIZAÇÃO
                    st.markdown(
                        f'''
                        <div class="info-sub">
                            {imovel["bairro"]} - {imovel["cidade"]}
                        </div>
                        ''',
                        unsafe_allow_html=True,
                    )

                    # 4. TIPO E DETALHES
                    partes_info = [imovel["tipo"]]
                    if imovel["quartos"]:
                        partes_info.append(f"{imovel['quartos']} Dorm.")
                    if imovel["vagas"]:
                        partes_info.append(f"{imovel['vagas']} Vaga(s)")
                    elif imovel["area_util"]:
                        partes_info.append(f"{imovel['area_util']} úteis")

                    st.markdown(
                        f'''
                        <div class="tipo-detalhe">
                            {" • ".join(partes_info)}
                        </div>
                        ''',
                        unsafe_allow_html=True,
                    )

                    st.markdown("<br>", unsafe_allow_html=True)

                    # BOTÕES DE WHATSAPP PARA OS CLIENTES FALAREM COM OS CONSULTORES
                    col_w1, col_w2 = st.columns(2)
                    msg_whats = f"Olá, tenho interesse no imóvel {imovel['codigo']} ({imovel['tipo']} em {imovel['bairro']}). Poderia me passar mais informações?"
                    
                    with col_w1:
                        link_wf = f"https://wa.me/{TELEFONE_FERNANDO}?text={urllib.parse.quote(msg_whats)}"
                        st.link_button("WPP Fernando", link_wf, use_container_width=True)

                    with col_w2:
                        link_wv = f"https://wa.me/{TELEFONE_VALDIR}?text={urllib.parse.quote(msg_whats)}"
                        st.link_button("WPP Valdir", link_wv, use_container_width=True)

                    st.markdown("</div>", unsafe_allow_html=True)
