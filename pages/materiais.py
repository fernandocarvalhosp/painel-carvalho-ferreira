# pages/materiais.py
# -*- coding: utf-8 -*-

import io
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


# =============================================================================
# CONFIGURAÇÕES
# =============================================================================

st.set_page_config(
    page_title="Materiais | Carvalho Ferreira",
    page_icon="CF",
    layout="wide",
    initial_sidebar_state="collapsed",
)

SCOPES_DRIVE = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]

SCOPES_SHEETS = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]

SPREADSHEET_ID = "1nVEpOZFYFKcq0MXtOwxn22nqxafmJBHnf6zhHQlyT8w"
NOME_ABA = "Imoveis"

PASTAS_MATERIAIS = [
    "POSTS",
    "FOTOS SELECIONADAS",
    "FOTOS TRATADAS",
    "PDF",
    "STATUS",
    "VIDEOS",
]


# =============================================================================
# ESTILO
# =============================================================================

st.markdown(
    """
    <style>

    /* Fundo */
    .stApp {
        background-color: #f7f5ef;
    }

    /* Remove excesso do topo */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 4rem;
        max-width: 1200px;
    }

    /* Títulos */
    h1, h2, h3 {
        color: #0b1b33;
    }

    /* Cartões */
    .material-card {
        background: #ffffff;
        border: 1px solid #e5e1d8;
        border-radius: 14px;
        padding: 22px;
        margin-bottom: 18px;
    }

    .material-title {
        color: #0b1b33;
        font-size: 1.15rem;
        font-weight: 700;
        margin-bottom: 4px;
    }

    .material-description {
        color: #666666;
        font-size: 0.9rem;
        margin-bottom: 16px;
    }

    .property-code {
        color: #9a7a38;
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 1px;
        text-transform: uppercase;
    }

    .property-title {
        color: #0b1b33;
        font-size: 2rem;
        font-weight: 700;
        margin: 4px 0 0 0;
    }

    .property-price {
        color: #0b1b33;
        font-size: 1.3rem;
        font-weight: 600;
        margin-top: 4px;
    }

    .quick-action {
        background: #0b1b33;
        color: white;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        font-weight: 600;
    }

    /* Botões */
    .stButton > button,
    .stDownloadButton > button {
        border-radius: 9px;
        font-weight: 600;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =============================================================================
# CONEXÕES
# =============================================================================

@st.cache_resource
def conectar_drive():
    creds_dict = dict(st.secrets["google_credentials"])

    creds = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=SCOPES_DRIVE,
    )

    return build("drive", "v3", credentials=creds)


@st.cache_resource
def conectar_sheets():
    creds_dict = dict(st.secrets["google_credentials"])

    creds = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=SCOPES_SHEETS,
    )

    return build("sheets", "v4", credentials=creds)


# =============================================================================
# AUXILIARES
# =============================================================================

def normalizar(texto):
    if not texto:
        return ""

    return " ".join(str(texto).strip().upper().split())


@st.cache_data(ttl=300)
def buscar_legendas(codigo):
    try:
        service = conectar_sheets()

        result = (
            service.spreadsheets()
            .values()
            .get(
                spreadsheetId=SPREADSHEET_ID,
                range=f"'{NOME_ABA}'!A:AZ",
            )
            .execute()
        )

        rows = result.get("values", [])

        if not rows:
            return "", ""

        cabecalho = [normalizar(h) for h in rows[0]]
        codigo_busca = normalizar(codigo)

        for row in rows[1:]:

            if not row:
                continue

            while len(row) < len(cabecalho):
                row.append("")

            if normalizar(row[0]) == codigo_busca:

                dados = {
                    cabecalho[i]: row[i]
                    for i in range(len(cabecalho))
                }

                legenda1 = (
                    dados.get("LEGENDA 1", "")
                    or dados.get("LEGENDA1", "")
                )

                legenda2 = (
                    dados.get("LEGENDA 2", "")
                    or dados.get("LEGENDA2", "")
                )

                return legenda1, legenda2

        return "", ""

    except Exception as e:
        st.error(f"Erro ao buscar legendas: {e}")
        return "", ""


@st.cache_data(ttl=300)
def encontrar_pasta_imovel(codigo):
    service = conectar_drive()

    query = (
        f"name = '{codigo}' "
        f"and mimeType = 'application/vnd.google-apps.folder' "
        f"and trashed = false"
    )

    resultados = (
        service.files()
        .list(
            q=query,
            spaces="drive",
            fields="files(id,name)",
            pageSize=10,
        )
        .execute()
    )

    pastas = resultados.get("files", [])

    if pastas:
        return pastas[0]["id"]

    return None


@st.cache_data(ttl=300)
def listar_subpastas(pasta_pai_id):

    service = conectar_drive()

    query = (
        f"'{pasta_pai_id}' in parents "
        f"and mimeType = 'application/vnd.google-apps.folder' "
        f"and trashed = false"
    )

    resultados = (
        service.files()
        .list(
            q=query,
            spaces="drive",
            fields="files(id,name)",
            pageSize=50,
        )
        .execute()
    )

    return resultados.get("files", [])


@st.cache_data(ttl=300)
def listar_arquivos(pasta_id):

    service = conectar_drive()

    query = (
        f"'{pasta_id}' in parents "
        f"and mimeType != 'application/vnd.google-apps.folder' "
        f"and trashed = false"
    )

    resultados = (
        service.files()
        .list(
            q=query,
            spaces="drive",
            fields="files(id,name,mimeType,webViewLink)",
            pageSize=100,
            orderBy="name",
        )
        .execute()
    )

    return resultados.get("files", [])


def baixar_arquivo(file_id):

    service = conectar_drive()

    try:

        request = service.files().get_media(
            fileId=file_id
        )

        fh = io.BytesIO()

        downloader = MediaIoBaseDownload(
            fh,
            request
        )

        done = False

        while not done:

            status, done = downloader.next_chunk()

        fh.seek(0)

        return fh.read()

    except Exception as e:

        st.error(f"Erro ao carregar arquivo: {e}")

        return None


def encontrar_pasta(subpastas, nome):

    nome_normalizado = normalizar(nome)

    for pasta in subpastas:

        if normalizar(pasta["name"]) == nome_normalizado:

            return pasta

    return None


def arquivos_da_pasta(subpastas, nome):

    pasta = encontrar_pasta(subpastas, nome)

    if not pasta:
        return []

    return listar_arquivos(pasta["id"])


def arquivo_e_imagem(arquivo):

    mime = arquivo.get("mimeType", "")

    return mime.startswith("image/")


def arquivo_e_pdf(arquivo):

    return arquivo.get("mimeType") == "application/pdf"


# =============================================================================
# IMÓVEL SELECIONADO
# =============================================================================

codigo = (
    st.session_state.get("codigo_materiais")
    or st.session_state.get("codigo_busca", "")
)

if not codigo:

    st.warning(
        "Nenhum imóvel selecionado. "
        "Volte para o painel e escolha um imóvel."
    )

    if st.button("← Voltar para o painel"):

        st.switch_page("app.py")

    st.stop()


# =============================================================================
# CABEÇALHO
# =============================================================================

col_voltar, col_vazio = st.columns([1, 5])

with col_voltar:

    if st.button("← Voltar"):

        st.switch_page("app.py")


st.markdown(
    f"""
    <div class="material-card">

        <div class="property-code">
            {codigo}
        </div>

        <div class="property-title">
            Materiais do imóvel
        </div>

        <div class="property-price">
            Tudo pronto para usar
        </div>

    </div>
    """,
    unsafe_allow_html=True,
)


# =============================================================================
# DRIVE
# =============================================================================

with st.spinner("Carregando materiais..."):

    pasta_imovel_id = encontrar_pasta_imovel(codigo)

if not pasta_imovel_id:

    st.error(
        f"Não encontrei a pasta do imóvel {codigo} no Google Drive."
    )

    st.stop()


subpastas = listar_subpastas(pasta_imovel_id)


# =============================================================================
# AÇÕES RÁPIDAS
# =============================================================================

st.markdown("### Ações rápidas")

col1, col2, col3, col4 = st.columns(4)

with col1:

    if st.button(
        "📝 COPY",
        use_container_width=True
    ):

        st.session_state["material_aba"] = "COPY"


with col2:

    if st.button(
        "📱 STATUS",
        use_container_width=True
    ):

        st.session_state["material_aba"] = "STATUS"


with col3:

    if st.button(
        "📲 POSTS",
        use_container_width=True
    ):

        st.session_state["material_aba"] = "POSTS"


with col4:

    if st.button(
        "📄 PDF",
        use_container_width=True
    ):

        st.session_state["material_aba"] = "PDF"


st.markdown("---")


# =============================================================================
# COPY
# =============================================================================

st.markdown("### 📝 Copy")

legenda1, legenda2 = buscar_legendas(codigo)

col1, col2 = st.columns(2)

with col1:

    st.markdown(
        """
        <div class="material-card">
        <div class="material-title">Legenda 1</div>
        <div class="material-description">
        Texto principal para publicação
        </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if legenda1:

        st.text_area(
            "Legenda 1",
            value=legenda1,
            height=220,
            key=f"legenda1_{codigo}",
            label_visibility="collapsed",
        )

        st.code(
            legenda1,
            language=None,
        )

    else:

        st.info("Legenda 1 não cadastrada.")


with col2:

    st.markdown(
        """
        <div class="material-card">
        <div class="material-title">Legenda 2</div>
        <div class="material-description">
        Segunda opção de texto
        </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if legenda2:

        st.text_area(
            "Legenda 2",
            value=legenda2,
            height=220,
            key=f"legenda2_{codigo}",
            label_visibility="collapsed",
        )

        st.code(
            legenda2,
            language=None,
        )

    else:

        st.info("Legenda 2 não cadastrada.")


# =============================================================================
# STATUS
# =============================================================================

st.markdown("---")
st.markdown("### 📱 Status")

arquivos_status = arquivos_da_pasta(
    subpastas,
    "STATUS"
)

if not arquivos_status:

    st.info(
        "Nenhum material de Status encontrado."
    )

else:

    colunas = st.columns(3)

    for indice, arquivo in enumerate(arquivos_status):

        with colunas[indice % 3]:

            st.markdown(
                f"**{arquivo['name']}**"
            )

            visualizar_key = (
                f"ver_status_{codigo}_{arquivo['id']}"
            )

            if st.button(
                "Visualizar",
                key=visualizar_key,
                use_container_width=True,
            ):

                st.session_state[
                    f"preview_{arquivo['id']}"
                ] = True

            if st.session_state.get(
                f"preview_{arquivo['id']}",
                False
            ):

                dados = baixar_arquivo(
                    arquivo["id"]
                )

                if dados:

                    st.image(
                        dados,
                        use_container_width=True,
                    )

                    st.download_button(
                        "Baixar / compartilhar",
                        data=dados,
                        file_name=arquivo["name"],
                        key=f"download_status_{arquivo['id']}",
                        use_container_width=True,
                    )


# =============================================================================
# POSTS
# =============================================================================

st.markdown("---")
st.markdown("### 📲 Posts")

arquivos_posts = arquivos_da_pasta(
    subpastas,
    "POSTS"
)

if not arquivos_posts:

    st.info(
        "Nenhum post encontrado."
    )

else:

    colunas = st.columns(3)

    for indice, arquivo in enumerate(arquivos_posts):

        with colunas[indice % 3]:

            st.markdown(
                f"**{arquivo['name']}**"
            )

            preview_key = (
                f"preview_post_{arquivo['id']}"
            )

            if st.button(
                "Visualizar",
                key=preview_key,
                use_container_width=True,
            ):

                st.session_state[
                    f"post_preview_{arquivo['id']}"
                ] = True

            if st.session_state.get(
                f"post_preview_{arquivo['id']}",
                False
            ):

                dados = baixar_arquivo(
                    arquivo["id"]
                )

                if dados:

                    st.image(
                        dados,
                        use_container_width=True,
                    )

                    st.download_button(
                        "Baixar / compartilhar",
                        data=dados,
                        file_name=arquivo["name"],
                        key=f"download_post_{arquivo['id']}",
                        use_container_width=True,
                    )


# =============================================================================
# FOTOS
# =============================================================================

st.markdown("---")
st.markdown("### 📸 Fotos tratadas")

arquivos_fotos = arquivos_da_pasta(
    subpastas,
    "FOTOS TRATADAS"
)

if not arquivos_fotos:

    st.info(
        "Nenhuma foto tratada encontrada."
    )

else:

    colunas = st.columns(4)

    for indice, arquivo in enumerate(arquivos_fotos):

        with colunas[indice % 4]:

            if arquivo_e_imagem(arquivo):

                preview_key = (
                    f"foto_preview_{arquivo['id']}"
                )

                if st.button(
                    arquivo["name"],
                    key=preview_key,
                    use_container_width=True,
                ):

                    st.session_state[
                        f"foto_aberta_{arquivo['id']}"
                    ] = True

                if st.session_state.get(
                    f"foto_aberta_{arquivo['id']}",
                    False,
                ):

                    dados = baixar_arquivo(
                        arquivo["id"]
                    )

                    if dados:

                        st.image(
                            dados,
                            use_container_width=True,
                        )

                        st.download_button(
                            "Baixar",
                            data=dados,
                            file_name=arquivo["name"],
                            key=f"download_foto_{arquivo['id']}",
                            use_container_width=True,
                        )


# =============================================================================
# PDF
# =============================================================================

st.markdown("---")
st.markdown("### 📄 Apresentação")

arquivos_pdf = arquivos_da_pasta(
    subpastas,
    "PDF"
)

if not arquivos_pdf:

    st.info(
        "Nenhum PDF encontrado."
    )

else:

    for arquivo in arquivos_pdf:

        st.markdown(
            f"""
            <div class="material-card">

            <div class="material-title">
                {arquivo["name"]}
            </div>

            <div class="material-description">
                Apresentação completa do imóvel
            </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

        dados_pdf = baixar_arquivo(
            arquivo["id"]
        )

        if dados_pdf:

            col1, col2 = st.columns(2)

            with col1:

                st.download_button(
                    "📥 Baixar PDF",
                    data=dados_pdf,
                    file_name=arquivo["name"],
                    mime="application/pdf",
                    key=f"download_pdf_{arquivo['id']}",
                    use_container_width=True,
                )

            with col2:

                if arquivo.get("webViewLink"):

                    st.link_button(
                        "↗ Abrir apresentação",
                        url=arquivo["webViewLink"],
                        use_container_width=True,
                    )


# =============================================================================
# VÍDEOS
# =============================================================================

st.markdown("---")
st.markdown("### 🎥 Vídeos")

arquivos_videos = arquivos_da_pasta(
    subpastas,
    "VIDEOS"
)

if not arquivos_videos:

    st.info(
        "Nenhum vídeo encontrado."
    )

else:

    for arquivo in arquivos_videos:

        st.markdown(
            f"**{arquivo['name']}**"
        )

        if arquivo.get("webViewLink"):

            st.link_button(
                "Abrir vídeo",
                url=arquivo["webViewLink"],
                use_container_width=True,
            )


# =============================================================================
# FINAL
# =============================================================================

st.markdown("---")

st.markdown(
    """
    <div style="
        text-align:center;
        color:#777;
        padding:20px;
    ">
        Carvalho Ferreira · Central de Materiais
    </div>
    """,
    unsafe_allow_html=True,
)