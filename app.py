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


# =============================================================================
# ESTILO VISUAL
# =============================================================================

st.markdown(
    """
    <style>

    /* =========================================================
       OCULTA A LISTAGEM AUTOMÁTICA DE PÁGINAS
       ========================================================= */

    [data-testid="stSidebarNav"] {
        display: none;
    }


    /* =========================================================
       FUNDO GERAL
       ========================================================= */

    .stApp {
        background-color: #0e1117;
        color: #f0f2f6;
    }


    /* =========================================================
       CONTAINER PRINCIPAL
       ========================================================= */

    .block-container {
        padding-top: 2rem;
        padding-bottom: 4rem;
        max-width: 1200px;
    }


    /* =========================================================
       TÍTULOS
       ========================================================= */

    h1 {
        font-size: 2rem !important;
        color: #f7f5ef !important;
        margin-bottom: 0.2rem;
    }

    h2,
    h3 {
        color: #f7f5ef !important;
    }


    /* =========================================================
       CARD DO IMÓVEL
       ========================================================= */

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


    /* =========================================================
       IMAGENS
       ========================================================= */

    [data-testid="stImage"] img {
        border-radius: 8px;
        width: 100% !important;
        object-fit: cover !important;
        max-height: 240px !important;
    }


    /* =========================================================
       CÓDIGO DO IMÓVEL
       ========================================================= */

    .codigo-tag {
        font-size: 0.9rem;
        font-weight: 700;
        color: #d4af37;
        background: #1a1f2c;
        padding: 4px 10px;
        border-radius: 6px;
        border: 1px solid #30363d;
        display: inline-block;
        margin-bottom: 8px;
        margin-top: 8px;
    }


    /* =========================================================
       PREÇO
       ========================================================= */

    .preco-imovel {
        font-size: 1.2rem;
        font-weight: 700;
        color: #f7f5ef;
        margin-top: 8px;
        margin-bottom: 12px;
    }


    /* =========================================================
       INFORMAÇÕES SECUNDÁRIAS
       ========================================================= */

    .info-sub {
        font-size: 0.9rem;
        color: #8b949e;
        margin-bottom: 4px;
    }


    /* =========================================================
       BOTÕES
       ========================================================= */

    .stButton > button,
    .stLinkButton > button {
        border-radius: 8px;
        font-weight: 600;
        background-color: #1f2937;
        color: #f7f5ef;
        border: 1px solid #374151;
        width: 100%;
        transition: all 0.2s ease-in-out;
    }

    .stButton > button:hover,
    .stLinkButton > button:hover {
        background-color: #374151;
        border-color: #d4af37;
        color: #ffffff;
    }


    /* =========================================================
       RESPONSIVIDADE PARA CELULAR
       ========================================================= */

    @media (max-width: 768px) {

        /* Cada linha criada pelo Python vira uma coluna no celular */
        [data-testid="stHorizontalBlock"] {
            flex-direction: column !important;
            gap: 1rem !important;
        }

        /* A coluna ocupa toda a largura */
        [data-testid="stHorizontalBlock"] > div {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }

        /* Imagem ocupa toda a largura disponível */
        [data-testid="stImage"] img {
            width: 100% !important;
            max-height: none !important;
            object-fit: cover !important;
        }

        /* Card ocupa toda a largura */
        .imovel-card {
            width: 100%;
            padding: 14px;
        }

        /* Título um pouco menor no celular */
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

    creds_dict = dict(
        st.secrets["google_credentials"]
    )

    creds = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=SCOPES_DRIVE,
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


# =============================================================================
# FUNÇÃO DE NORMALIZAÇÃO
# =============================================================================

def normalizar(texto):

    if not texto:
        return ""

    return " ".join(
        str(texto).strip().upper().split()
    )


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

        cabecalho = [
            normalizar(h)
            for h in rows[0]
        ]

        imoveis = []

        for row in rows[1:]:

            if not row or not row[0]:
                continue

            while len(row) < len(cabecalho):
                row.append("")

            dados = {
                cabecalho[i]: row[i]
                for i in range(len(cabecalho))
            }

            codigo = (
                dados.get("CODIGO")
                or dados.get("CÓDIGO")
                or row[0]
            )

            tipo = (
                dados.get("TIPO")
                or dados.get("CATEGORIA")
                or "Imóvel"
            )

            bairro = (
                dados.get("BAIRRO")
                or ""
            )

            cidade = (
                dados.get("CIDADE")
                or ""
            )

            valor = (
                dados.get("VALOR")
                or "Sob consulta"
            )

            quartos = (
                dados.get("QUARTOS")
                or dados.get("DORMS")
                or dados.get("DORMITORIOS")
                or ""
            )

            # Captura o ID da miniatura direto da coluna MINIATURA ou FOTO da planilha
            miniatura_id = (
                dados.get("MINIATURA")
                or dados.get("FOTO")
                or ""
            )

            imoveis.append(
                {
                    "codigo": codigo,
                    "tipo": tipo,
                    "bairro": bairro,
                    "cidade": cidade,
                    "valor": valor,
                    "quartos": quartos,
                    "miniatura_id": miniatura_id.strip(),
                }
            )

        return imoveis

    except Exception as e:

        st.error(
            f"Erro ao carregar dados da planilha: {e}"
        )

        return []


# =============================================================================
# BUSCA DA MINIATURA DIRETAMENTE PELO ID DA PLANILHA
# =============================================================================

@st.cache_data(ttl=600)
def obter_foto_miniatura_por_id(file_id):
    if not file_id or len(str(file_id).strip()) < 10:
        return None

    try:
        drive, _ = conectar_google()

        request = (
            drive.files()
            .get_media(
                fileId=file_id.strip()
            )
        )

        fh = io.BytesIO()

        downloader = MediaIoBaseDownload(
            fh,
            request
        )

        done = False

        while not done:

            _, done = (
                downloader.next_chunk()
            )

        fh.seek(0)

        return fh.read()

    except Exception:

        return None


# =============================================================================
# INTERFACE PRINCIPAL
# =============================================================================

st.title("Carvalho Ferreira")

st.markdown(
    "### Vitrine de Imóveis & Atendimento"
)

st.markdown("---")


# =============================================================================
# CARREGAMENTO DOS IMÓVEIS
# =============================================================================

with st.spinner(
    "Buscando imóveis disponíveis..."
):

    lista_imoveis = (
        carregar_imoveis_sheets()
    )


if not lista_imoveis:

    st.warning(
        "Nenhum imóvel encontrado na planilha."
    )

    st.stop()


# =============================================================================
# SIDEBAR
# =============================================================================

st.sidebar.markdown(
    "## 🧭 Navegação"
)


if st.sidebar.button(
    "⚙️ Ir para Cadastro",
    use_container_width=True,
):

    st.switch_page(
        "pages/cadastro.py"
    )


st.sidebar.markdown("---")

st.sidebar.markdown(
    "## 🔍 Filtrar Imóveis"
)


if st.sidebar.button(
    "🧹 Limpar Pesquisa",
    use_container_width=True,
):

    st.session_state[
        "filtro_bairro"
    ] = "Todos"

    st.session_state[
        "busca_texto"
    ] = ""

    st.session_state[
        "filtro_quartos"
    ] = "Todos"

    st.rerun()


st.sidebar.markdown("---")


# =============================================================================
# FILTRO DE BAIRRO
# =============================================================================

bairros_disponiveis = sorted(
    list(
        set(
            [
                i["bairro"]
                for i in lista_imoveis
                if i["bairro"]
            ]
        )
    )
)


filtro_bairro = st.sidebar.selectbox(
    "Bairro / Região",
    ["Todos"] + bairros_disponiveis,
    key="filtro_bairro",
)


# =============================================================================
# BUSCA
# =============================================================================

busca_texto = st.sidebar.text_input(
    "Buscar por Código ou Tipo",
    placeholder="Ex: AP0018 ou Casa",
    key="busca_texto",
)


# =============================================================================
# FILTRO DE QUARTOS
# =============================================================================

filtro_quartos = st.sidebar.selectbox(
    "Dormitórios Mínimos",
    [
        "Todos",
        "1",
        "2",
        "3",
        "4+",
    ],
    key="filtro_quartos",
)


st.sidebar.markdown("---")

st.sidebar.markdown(
    "💡 *Selecione o imóvel para abrir "
    "a Central de Materiais.*"
)


# =============================================================================
# APLICAR FILTROS
# =============================================================================

imoveis_filtrados = []


for item in lista_imoveis:

    # -----------------------------------------------------
    # BAIRRO
    # -----------------------------------------------------

    if (
        filtro_bairro != "Todos"
        and normalizar(
            item["bairro"]
        )
        != normalizar(
            filtro_bairro
        )
    ):

        continue


    # -----------------------------------------------------
    # BUSCA
    # -----------------------------------------------------

    if busca_texto:

        termo = normalizar(
            busca_texto
        )

        texto_alvo = normalizar(
            f"""
            {item['codigo']}
            {item['tipo']}
            {item['bairro']}
            {item['cidade']}
            """
        )

        if termo not in texto_alvo:

            continue


    # -----------------------------------------------------
    # QUARTOS
    # -----------------------------------------------------

    if filtro_quartos != "Todos":

        q_str = "".join(
            filter(
                str.isdigit,
                str(
                    item["quartos"]
                )
            )
        )

        if q_str:

            q_num = int(q_str)

            min_q = (
                4
                if filtro_quartos == "4+"
                else int(filtro_quartos)
            )

            if q_num < min_q:

                continue


    imoveis_filtrados.append(
        item
    )


# =============================================================================
# RESULTADOS
# =============================================================================

st.markdown(
    f"### Imóveis Encontrados "
    f"({len(imoveis_filtrados)})"
)


if not imoveis_filtrados:

    st.info(
        "Nenhum imóvel corresponde "
        "aos filtros selecionados."
    )


else:

    # =========================================================
    # IMPORTANTE
    #
    # Criamos uma LINHA de três colunas por vez.
    #
    # Isso mantém a ordem:
    #
    # 1  2  3
    # 4  5  6
    # 7  8  9
    #
    # Quando o celular empilhar as colunas,
    # a sequência continua:
    #
    # 1
    # 2
    # 3
    # 4
    # 5
    # 6
    # =========================================================

    for inicio in range(
        0,
        len(imoveis_filtrados),
        3
    ):

        grupo = imoveis_filtrados[
            inicio:inicio + 3
        ]

        colunas = st.columns(3)


        for posicao, imovel in enumerate(
            grupo
        ):

            with colunas[posicao]:

                with st.container():

                    st.markdown(
                        '<div class="imovel-card">',
                        unsafe_allow_html=True
                    )


                    # =====================================================
                    # MINIATURA (Carregada via ID do Google Sheets)
                    # =====================================================

                    foto_bytes = (
                        obter_foto_miniatura_por_id(
                            imovel["miniatura_id"]
                        )
                    )


                    if foto_bytes:

                        st.image(
                            foto_bytes,
                            use_container_width=True,
                        )

                    else:

                        st.markdown(
                            "🖼️ *Miniatura não configurada*"
                        )


                    # =====================================================
                    # CÓDIGO
                    # =====================================================

                    st.markdown(
                        f'''
                        <div class="codigo-tag">
                            🏷️ {imovel["codigo"]}
                        </div>
                        ''',
                        unsafe_allow_html=True,
                    )


                    # =====================================================
                    # LOCALIZAÇÃO
                    # =====================================================

                    st.markdown(
                        f'''
                        <div class="info-sub">
                            {imovel["bairro"]}
                            •
                            {imovel["cidade"]}
                        </div>
                        ''',
                        unsafe_allow_html=True,
                    )


                    # =====================================================
                    # TIPO
                    # =====================================================

                    if imovel["tipo"]:

                        st.markdown(
                            f"**{imovel['tipo']}**"
                        )


                    # =====================================================
                    # PREÇO
                    # =====================================================

                    st.markdown(
                        f'''
                        <div class="preco-imovel">
                            {imovel["valor"]}
                        </div>
                        ''',
                        unsafe_allow_html=True,
                    )


                    # =====================================================
                    # ACESSAR MATERIAIS
                    # =====================================================

                    if st.button(
                        "📂 Acessar Materiais",
                        key=(
                            f"btn_mat_"
                            f"{imovel['codigo']}_"
                            f"{inicio}_"
                            f"{posicao}"
                        ),
                        use_container_width=True,
                    ):

                        st.session_state[
                            "codigo_materiais"
                        ] = imovel["codigo"]

                        st.switch_page(
                            "pages/materiais.py"
                        )


                    st.markdown(
                        "</div>",
                        unsafe_allow_html=True,
                    )
