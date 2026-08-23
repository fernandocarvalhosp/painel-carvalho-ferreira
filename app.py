# app.py
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
# ESTILO VISUAL SOFISTICADO (DARK & PREMIUM)
# =============================================================================

st.markdown(
    """
    <style>
    /* Fundo geral escuro / sofisticado */
    .stApp {
        background-color: #0e1117;
        color: #f0f2f6;
    }

    /* Container principal */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 4rem;
        max-width: 1200px;
    }

    /* Títulos principais */
    h1 {
        font-size: 2rem !important;
        color: #f7f5ef !important;
        margin-bottom: 0.2rem;
    }
    
    h2, h3 {
        color: #f7f5ef !important;
    }

    /* Card do Imóvel */
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

    /* Código em destaque */
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
    }

    /* Preço do imóvel */
    .preco-imovel {
        font-size: 1.2rem;
        font-weight: 700;
        color: #f7f5ef;
        margin-top: 8px;
        margin-bottom: 12px;
    }

    /* Informações secundárias */
    .info-sub {
        font-size: 0.9rem;
        color: #8b949e;
        margin-bottom: 4px;
    }

    /* Botões personalizados */
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
            titulo = dados.get("TITULO 1") or dados.get("TITULO") or ""
            bairro = dados.get("BAIRRO") or ""
            cidade = dados.get("CIDADE") or ""
            valor = dados.get("VALOR") or "Sob consulta"
            quartos = dados.get("QUARTOS") or dados.get("DORMS") or dados.get("DORMITORIOS") or ""
            
            imoveis.append({
                "codigo": codigo,
                "titulo": titulo,
                "bairro": bairro,
                "cidade": cidade,
                "valor": valor,
                "quartos": quartos,
            })
            
        return imoveis
    except Exception as e:
        st.error(f"Erro ao carregar dados da planilha: {e}")
        return []


# =============================================================================
# BUSCA DE FOTO DIRETO DO DRIVE (OTIMIZADO)
# =============================================================================

@st.cache_data(ttl=600)
def obter_primeira_foto_drive(codigo):
    try:
        drive, _ = conectar_google()
        
        # Acha a pasta do imóvel
        query_pasta = f"name contains '{codigo}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        res_pasta = drive.files().list(q=query_pasta, pageSize=5, fields="files(id, name)").execute()
        pastas = res_pasta.get("files", [])
        
        id_imovel = None
        for p in pastas:
            nome_p = p["name"].strip().upper()
            if nome_p == codigo.upper() or nome_p.startswith(codigo.upper() + " ") or nome_p.startswith(codigo.upper() + "-"):
                id_imovel = p["id"]
                break
        if not id_imovel and pastas:
            id_imovel = pastas[0]["id"]
            
        if not id_imovel:
            return None

        # Procura subpastas de fotos
        res_sub = drive.files().list(q=f"'{id_imovel}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false", fields="files(id, name)").execute()
        subpastas = res_sub.get("files", [])
        
        id_fotos = id_imovel
        for sub in subpastas:
            nome_sub = sub["name"].upper()
            if "FOTOS TRATADAS" in nome_sub or "FOTOS SELECIONADAS" in nome_sub:
                id_fotos = sub["id"]
                break

        # Pega a primeira foto da pasta
        res_arq = drive.files().list(q=f"'{id_fotos}' in parents and mimeType contains 'image/' and trashed = false", orderBy="name", pageSize=1, fields="files(id)").execute()
        arquivos = res_arq.get("files", [])
        
        if arquivos:
            file_id = arquivos[0]["id"]
            request = drive.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            fh.seek(0)
            return fh.read()
            
        return None
    except Exception:
        return None


# =============================================================================
# INTERFACE PRINCIPAL (VITRINE DE BUSCA)
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
# FILTROS NA BARRA LATERAL (SIDEBAR) COM BOTÃO DE LIMPAR
# =============================================================================

st.sidebar.markdown("## 🔍 Filtrar Imóveis")

# Gerenciador de estado para resetar filtros
if "limpar_filtros" not in st.session_state:
    st.session_state["limpar_filtros"] = False

if st.sidebar.button("🧹 Limpar Pesquisa", use_container_width=True):
    st.session_state["filtro_bairro"] = "Todos"
    st.session_state["busca_texto"] = ""
    st.session_state["filtro_quartos"] = "Todos"
    st.rerun()

st.sidebar.markdown("---")

bairros_disponiveis = sorted(list(set([i["bairro"] for i in lista_imoveis if i["bairro"]])))
filtro_bairro = st.sidebar.selectbox("Bairro / Região", ["Todos"] + bairros_disponiveis, key="filtro_bairro")

busca_texto = st.sidebar.text_input("Buscar por Código ou Título", placeholder="Ex: AP0018 ou Jardins", key="busca_texto")

filtro_quartos = st.sidebar.selectbox("Dormitórios Mínimos", ["Todos", "1", "2", "3", "4+"], key="filtro_quartos")

st.sidebar.markdown("---")
st.sidebar.markdown("💡 *Selecione o imóvel para abrir a Central de Materiais.*")


# =============================================================================
# APLICAR FILTROS
# =============================================================================

imoveis_filtrados = []
for item in lista_imoveis:
    if filtro_bairro != "Todos" and normalizar(item["bairro"]) != normalizar(filtro_bairro):
        continue
    
    if busca_texto:
        termo = normalizar(busca_texto)
        texto_alvo = normalizar(f"{item['codigo']} {item['titulo']} {item['bairro']} {item['cidade']}")
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
# EXIBIÇÃO DOS RESULTADOS (GRID DE CARDS COM FOTO DO DRIVE)
# =============================================================================

st.markdown(f"### Imóveis Encontrados ({len(imoveis_filtrados)})")

if not imoveis_filtrados:
    st.info("Nenhum imóvel corresponde aos filtros selecionados.")
else:
    colunas = st.columns(3)
    
    for indice, imovel in enumerate(imoveis_filtrados):
        coluna_atual = colunas[indice % 3]
        
        with coluna_atual:
            with st.container():
                st.markdown('<div class="imovel-card">', unsafe_allow_html=True)
                
                # Busca a primeira foto dinamicamente direto das pastas do Drive
                foto_bytes = obter_primeira_foto_drive(imovel["codigo"])
                if foto_bytes:
                    st.image(foto_bytes, use_container_width=True)
                else:
                    st.markdown("🖼️ *Sem imagem na pasta*")
                
                # Código e Informações
                st.markdown(f'<div class="codigo-tag">🏷️ {imovel["codigo"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="info-sub">{imovel["bairro"]} • {imovel["cidade"]}</div>', unsafe_allow_html=True)
                
                if imovel["titulo"]:
                    st.markdown(f"**{imovel['titulo']}**")
                    
                st.markdown(f'<div class="preco-imovel">{imovel["valor"]}</div>', unsafe_allow_html=True)
                
                # Botão para ir aos Materiais
                if st.button("📂 Acessar Materiais", key=f"btn_mat_{imovel['codigo']}_{indice}", use_container_width=True):
                    st.session_state["codigo_materiais"] = imovel["codigo"]
                    st.switch_page("pages/materiais.py")
                
                st.markdown('</div>', unsafe_allow_html=True)
