# app.py
# -*- coding: utf-8 -*-

import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build


# =============================================================================
# CONFIGURAÇÕES DA PÁGINA
# =============================================================================

st.set_page_config(
    page_title="Vitrine de Imóveis | Carvalho Ferreira",
    page_icon="CF",
    layout="wide",
    initial_sidebar_state="expanded",
)

SCOPES_SHEETS = [
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
        margin-bottom: 0.5rem;
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
# CONEXÃO GOOGLE SHEETS
# =============================================================================

@st.cache_resource
def conectar_sheets():
    creds_dict = dict(st.secrets["google_credentials"])
    creds = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=SCOPES_SHEETS
    )
    return build("sheets", "v4", credentials=creds)


def normalizar(texto):
    if not texto:
        return ""
    return " ".join(str(texto).strip().upper().split())


@st.cache_data(ttl=300)
def carregar_imoveis_sheets():
    try:
        service = conectar_sheets()
        result = (
            service.spreadsheets()
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
            
            # Mapeamento flexível de colunas comuns
            codigo = dados.get("CODIGO") or dados.get("CÓDIGO") or row[0]
            titulo = dados.get("TITULO 1") or dados.get("TITULO") or dados.get("TITULAÇÃO") or ""
            bairro = dados.get("BAIRRO") or ""
            cidade = dados.get("CIDADE") or ""
            valor = dados.get("VALOR") or "Sob consulta"
            quartos = dados.get("QUARTOS") or dados.get("DORMS") or dados.get("DORMITORIOS") or ""
            foto = dados.get("FOTO") or dados.get("FOTOS") or dados.get("FOTO PRINCIPAL") or ""
            
            imoveis.append({
                "codigo": codigo,
                "titulo": titulo,
                "bairro": bairro,
                "cidade": cidade,
                "valor": valor,
                "quartos": quartos,
                "foto": foto,
                "dados_completos": dados
            })
            
        return imoveis
    except Exception as e:
        st.error(f"Erro ao carregar dados da planilha: {e}")
        return []


# =============================================================================
# INTERFACE PRINCIPAL (VITRINE DE BUSCA)
# =============================================================================

# Cabeçalho da página
col_titulo, col_link = st.columns([4, 1])
with col_titulo:
    st.title("Carvalho Ferreira")
    st.markdown("### Vitrine de Imóveis & Atendimento")
with col_link:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("⚙️ Ir para Cadastro", use_container_width=True):
        st.switch_page("pages/cadastro.py")

st.markdown("---")

# Carrega os dados
with st.spinner("Buscando imóveis disponíveis..."):
    lista_imoveis = carregar_imoveis_sheets()

if not lista_imoveis:
    st.warning("Nenhum imóvel encontrado na planilha.")
    st.stop()


# =============================================================================
# FILTROS NA BARRA LATERAL (SIDEBAR)
# =============================================================================

st.sidebar.markdown("## 🔍 Filtrar Imóveis")
st.sidebar.markdown("Use os filtros abaixo para encontrar o imóvel ideal para o lead.")

# Extrair lista única de bairros para o filtro
bairros_disponiveis = sorted(list(set([i["bairro"] for i in lista_imoveis if i["bairro"]])))
filtro_bairro = st.sidebar.selectbox("Bairro / Região", ["Todos"] + bairros_disponiveis)

# Busca por texto livre (código ou título)
busca_texto = st.sidebar.text_input("Buscar por Código ou Título", placeholder="Ex: AP0018 ou Jardins")

# Filtro de Quartos
filtro_quartos = st.sidebar.selectbox("Dormitórios Mínimos", ["Todos", "1", "2", "3", "4+"])

st.sidebar.markdown("---")
st.sidebar.markdown("💡 *Dica: Selecione o imóvel nos cards para abrir a Central de Materiais.*")


# =============================================================================
# APLICAR FILTROS
# =============================================================================

imoveis_filtrados = []
for item in lista_imoveis:
    # Filtro por bairro
    if filtro_bairro != "Todos" and normalizar(item["bairro"]) != normalizar(filtro_bairro):
        continue
    
    # Filtro por texto livre
    if busca_texto:
        termo = normalizar(busca_texto)
        texto_alvo = normalizar(f"{item['codigo']} {item['titulo']} {item['bairro']} {item['cidade']}")
        if termo not in texto_alvo:
            continue
            
    # Filtro por quartos
    if filtro_quartos != "Todos":
        q_str = "".join(filter(str.isdigit, str(item["quartos"])))
        if q_str:
            q_num = int(q_str)
            min_q = 4 if filtro_quartos == "4+" else int(filtro_quartos)
            if q_num < min_q:
                continue

    imoveis_filtrados.append(item)


# =============================================================================
# EXIBIÇÃO DOS RESULTADOS (GRID DE CARDS)
# =============================================================================

st.markdown(f"### Imóveis Encontrados ({len(imoveis_filtrados)})")

if not imoveis_filtrados:
    st.info("Nenhum imóvel corresponde aos filtros selecionados.")
else:
    # Organiza em 3 colunas por linha
    colunas = st.columns(3)
    
    for indice, imovel in enumerate(imoveis_filtrados):
        coluna_atual = colunas[indice % 3]
        
        with coluna_atual:
            with st.container():
                st.markdown('<div class="imovel-card">', unsafe_allow_html=True)
                
                # Exibe a foto se houver link válido na planilha
                if imovel["foto"] and imovel["foto"].startswith("http"):
                    try:
                        st.image(imovel["foto"], use_container_width=True)
                    except Exception:
                        st.markdown("🖼️ *Foto indisponível*")
                else:
                    st.markdown("🖼️ *Sem imagem cadastrada*")
                
                # Código e Valores
                st.markdown(f'<div class="codigo-tag">🏷️ {imovel["codigo"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="info-sub">{imovel["bairro"]} • {imovel["cidade"]}</div>', unsafe_allow_html=True)
                
                if imovel["titulo"]:
                    st.markdown(f"**{imovel['titulo']}**")
                    
                st.markdown(f'<div class="preco-imovel">{imovel["valor"]}</div>', unsafe_allow_html=True)
                
                # Botão de Ação para ir aos Materiais
                if st.button("📂 Acessar Materiais", key=f"btn_mat_{imovel['codigo']}_{indice}", use_container_width=True):
                    st.session_state["codigo_materiais"] = imovel["codigo"]
                    st.switch_page("pages/materiais.py")
                
                st.markdown('</div>', unsafe_allow_html=True)
