# -*- coding: utf-8 -*-

import io
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


# =============================================================================
# CONFIGURAÇÕES DA PÁGINA
# =============================================================================

st.set_page_config(
    page_title="Vitrine de Imóveis | Carvalho Ferreira",
    page_icon="CF",
    layout="wide",
    initial_sidebar_state="expanded",
)

SCOPES_DRIVE = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]

SPREADSHEET_ID = "1nVEpOZFYFKcq0MXtOwxn22nqxafmJBHnf6zhHQlyT8w"
NOME_ABA = "Imoveis"

# Número de WhatsApp padrão para atendimento (Substitua pelo seu número com DDI e DDD)
TELEFONE_WHATSAPP = "5511999999999"


# =============================================================================
# ESTILO VISUAL CORPORATIVO & MODERNO
# =============================================================================

st.markdown(
    """
    <style>

    [data-testid="stSidebarNav"] {
        display: none;
    }

    .stApp {
        background-color: #0e1117;
        color: #f0f2f6;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 4rem;
        max-width: 1200px;
    }

    h1 {
        font-size: 2rem !important;
        color: #f7f5ef !important;
        margin-bottom: 0.2rem;
    }

    h2, h3 {
        color: #f7f5ef !important;
    }

    /* CONTAINER DA FOTO COM STATUS FLUTUANTE */
    .foto-container {
        position: relative;
        width: 100%;
    }

    .status-badge {
        position: absolute;
        top: 10px;
        right: 10px;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        z-index: 2;
        box-shadow: 0 2px 6px rgba(0,0,0,0.4);
    }

    .status-disponivel {
        background-color: #238636;
        color: #ffffff;
    }

    .status-negociacao {
        background-color: #9e6a03;
        color: #ffffff;
    }

    .status-vendido {
        background-color: #da3633;
        color: #ffffff;
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

    [data-testid="stImage"] img {
        border-radius: 8px;
        width: 100% !important;
        object-fit: cover !important;
        max-height: 220px !important;
    }

    .preco-imovel {
        font-size: 1.3rem;
        font-weight: 700;
        color: #d4af37;
        margin-top: 10px;
        margin-bottom: 4px;
    }

    .tipo-detalhe {
        font-size: 1rem;
        font-weight: 600;
        color: #f7f5ef;
        margin-bottom: 2px;
    }

    .info-sub {
        font-size: 0.9rem;
        color: #8b949e;
        margin-bottom: 4px;
    }

    .codigo-tag {
        font-size: 0.85rem;
        font-weight: 600;
        color: #8b949e;
        background: #1a1f2c;
        padding: 3px 8px;
        border-radius: 6px;
        border: 1px solid #30363d;
        display: inline-block;
        margin-bottom: 10px;
        margin-top: 4px;
    }

    .stButton > button, .stLinkButton > button {
        border-radius: 8px;
        font-weight: 600;
        background-color: #1f2937;
        color: #f7f5ef;
        border: 1px solid #374151;
        width: 100%;
        transition: all 0.2s ease-in-out;
    }

    .stButton > button:hover, .stLinkButton > button:hover {
        background-color: #374151;
        border-color: #d4af37;
        color: #ffffff;
    }

    .btn-whatsapp {
        background-color: #1b4332 !important;
        border-color: #2d6a4f !important;
        color: #52b788 !important;
    }

    .btn-whatsapp:hover {
        background-color: #2d6a4f !important;
        border-color: #52b788 !important;
        color: #ffffff !important;
    }

    @media (max-width: 768px) {
        [data-testid="stHorizontalBlock"] {
            flex-direction: column !important;
            gap: 1rem !important;
        }
        [data-testid="stHorizontalBlock"] > div {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }
        [data-testid="stImage"] img {
            width: 100% !important;
            max-height: none !important;
            object-fit: cover !important;
        }
        .imovel-card {
            width: 100%;
            padding: 14px;
        }
        h1 {
            font-size: 1.7rem !important;
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
        creds_dict,
        scopes=SCOPES_DRIVE,
    )
    drive = build("drive", "v3", credentials=creds)
    sheets = build("sheets", "v4", credentials=creds)
    return drive, sheets


def normalizar(texto):
    if not texto:
        return ""
    return " ".join(str(texto).strip().upper().split())


# =============================================================================
# CARREGAR IMÓVEIS DA PLANILHA
# =============================================================================

@st.cache_data(ttl=300)
def carregar_imoveis_sheets():
    try:
        _, sheets = conectar_google()
        result = (
            sheets.spreadsheets()
            .values()
            .get(
                spreadsheetId=SPREADSHEET_ID,
                range=f"'{NOME_ABA}'!A:AZ",
            )
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
            area_util = dados.get("AREA UTIL") or dados.get("ÁREA ÚTIL") or ""
            status = dados.get("STATUS") or "Disponível"
            miniatura_id = dados.get("MINIATURA") or dados.get("FOTO") or ""

            imoveis.append(
                {
                    "codigo": codigo,
                    "tipo": tipo,
                    "bairro": bairro,
                    "cidade": cidade,
                    "valor": valor,
                    "quartos": quartos,
                    "area_util": area_util,
                    "status": status,
                    "miniatura_id": miniatura_id.strip(),
                }
            )

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
# INTERFACE PRINCIPAL
# =============================================================================

st.title("Carvalho Ferreira")
st.markdown("### Vitrine de Imóveis & Atendimento")
st.markdown("---")

with st.spinner("Buscando imóveis disponíveis..."):
    lista_imoveis = carregar_imoveis_sheets()

if not lista_imoveis:
    st.warning("Nenhum imóvel encontrado na planilha.")
    st.stop()


# =============================================================================
# SIDEBAR
# =============================================================================

st.sidebar.markdown("### Navegação")

if st.sidebar.button("Ir para Cadastro", use_container_width=True):
    st.switch_page("pages/cadastro.py")

st.sidebar.markdown("---")
st.sidebar.markdown("### Filtrar Imóveis")

if st.sidebar.button("Limpar Pesquisa", use_container_width=True):
    st.session_state["filtro_bairro"] = "Todos"
    st.session_state["busca_texto"] = ""
    st.session_state["filtro_quartos"] = "Todos"
    st.rerun()

st.sidebar.markdown("---")

bairros_disponiveis = sorted(list(set([i["bairro"] for i in lista_imoveis if i["bairro"]])))
filtro_bairro = st.sidebar.selectbox("Bairro / Região", ["Todos"] + bairros_disponiveis, key="filtro_bairro")

busca_texto = st.sidebar.text_input("Buscar por Código ou Tipo", placeholder="Ex: AP0018 ou Casa", key="busca_texto")

filtro_quartos = st.sidebar.selectbox("Dormitórios Mínimos", ["Todos", "1", "2", "3", "4+"], key="filtro_quartos")


# =============================================================================
# APLICAR FILTROS
# =============================================================================

imoveis_filtrados = []

for item in lista_imoveis:
    if filtro_bairro != "Todos" and normalizar(item["bairro"]) != normalizar(filtro_bairro):
        continue

    if busca_texto:
        termo = normalizar(busca_texto)
        texto_alvo = normalizar(f"{item['codigo']} {item['tipo']} {item['bairro']} {item['cidade']}")
        if termo not in texto_alvo:
            continue

    if filtro_quartos != "Todos":
        q_str = "".join(filter(str.isdigit, str(item["quartos"])))
        if q_str:
            q_num = int(q_str)
            min_q = 4 if filtro_quartos == "4+" else int(filtro_quartos)
            if q_num < min_q:
                continue

    imoveis_filtrados.append(item)


# =============================================================================
# RESULTADOS DA VITRINE
# =============================================================================

st.markdown(f"### Imóveis Encontrados ({len(imoveis_filtrados)})")

if not imoveis_filtrados:
    st.info("Nenhum imóvel corresponde aos filtros selecionados.")
else:
    for inicio in range(0, len(imoveis_filtrados), 3):
        grupo = imoveis_filtrados[inicio:inicio + 3]
        colunas = st.columns(3)

        for posicao, imovel in enumerate(grupo):
            with colunas[posicao]:
                with st.container():
                    st.markdown('<div class="imovel-card">', unsafe_allow_html=True)

                    # 1. FOTO COM SELO DE STATUS FLUTUANTE
                    foto_bytes = obter_foto_miniatura_por_id(imovel["miniatura_id"])
                    
                    st_normal = normalizar(imovel["status"])
                    if "NEGOCIAÇÃO" in st_normal or "NEGOCIACAO" in st_normal:
                        badge_classe = "status-negociacao"
                        badge_texto = "Em Negociação"
                    elif "VENDIDO" in st_normal or "LOCADO" in st_normal or "INDISPONÍVEL" in st_normal or "INDISPONIVEL" in st_normal:
                        badge_classe = "status-vendido"
                        badge_texto = imovel["status"]
                    else:
                        badge_classe = "status-disponivel"
                        badge_texto = "Disponível"

                    if foto_bytes:
                        # Exibição customizada com o badge flutuante de status
                        st.markdown(f'''
                            <div class="foto-container">
                                <span class="status-badge {badge_classe}">{badge_texto}</span>
                            </div>
                        ''', unsafe_allow_html=True)
                        st.image(foto_bytes, use_container_width=True)
                    else:
                        st.markdown(f'''
                            <div style="position: relative;">
                                <span class="status-badge {badge_classe}">{badge_texto}</span>
                            </div>
                        ''', unsafe_allow_html=True)
                        st.markdown("Miniatura não configurada")

                    # 2. PREÇO
                    st.markdown(
                        f'''
                        <div class="preco-imovel">
                            {imovel["valor"]}
                        </div>
                        ''',
                        unsafe_allow_html=True,
                    )

                    # 3. TIPO + DORMITÓRIOS
                    dorm_texto = f" • {imovel['quartos']} Dorm." if imovel["quartos"] else ""
                    st.markdown(
                        f'''
                        <div class="tipo-detalhe">
                            {imovel["tipo"]}{dorm_texto}
                        </div>
                        ''',
                        unsafe_allow_html=True,
                    )

                    # 4. ÁREA ÚTIL
                    if imovel["area_util"]:
                        st.markdown(
                            f'''
                            <div class="info-sub">
                                Área: {imovel["area_util"]} úteis
                            </div>
                            ''',
                            unsafe_allow_html=True,
                        )

                    # 5. LOCALIZAÇÃO
                    st.markdown(
                        f'''
                        <div class="info-sub">
                            {imovel["bairro"]} - {imovel["cidade"]}
                        </div>
                        ''',
                        unsafe_allow_html=True,
                    )

                    # 6. CÓDIGO
                    st.markdown(
                        f'''
                        <div class="codigo-tag">
                            Cód: {imovel["codigo"]}
                        </div>
                        ''',
                        unsafe_allow_html=True,
                    )

                    # 7. BOTÕES DE AÇÃO (MATERIAIS + WHATSAPP)
                    col_b1, col_b2 = st.columns(2)
                    
                    with col_b1:
                        if st.button(
                            "Materiais",
                            key=f"btn_mat_{imovel['codigo']}_{inicio}_{posicao}",
                            use_container_width=True,
                        ):
                            st.session_state["codigo_materiais"] = imovel["codigo"]
                            st.switch_page("pages/materiais.py")

                    with col_b2:
                        msg_whats = f"Olá, tenho interesse no imóvel {imovel['codigo']} ({imovel['tipo']} em {imovel['bairro']}). Poderia me passar mais informações?"
                        link_whats = f"https://wa.me/{TELEFONE_WHATSAPP}?text={urllib.parse.quote(msg_whats)}" if 'urllib' in globals() else f"https://wa.me/{TELEFONE_WHATSAPP}"
                        
                        # Botão de redirecionamento direto para o WhatsApp do imóvel
                        import urllib.parse
                        link_w = f"https://wa.me/{TELEFONE_WHATSAPP}?text={urllib.parse.quote(msg_whats)}"
                        st.link_button("WhatsApp", link_w, use_container_width=True)

                    st.markdown("</div>", unsafe_allow_html=True)
