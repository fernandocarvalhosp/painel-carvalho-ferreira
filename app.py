# app.py
# -*- coding: utf-8 -*-

import importlib
from pathlib import Path

import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

import gerador_pdf

try:
  import gerar_posts
except Exception:
  gerar_posts = None

try:
  import tratador_nuvem
except Exception:
  tratador_nuvem = None


# =============================================================================
# CONFIGURAÇÕES DA PÁGINA
# =============================================================================

st.set_page_config(
    page_title="Vitrine de Imóveis | Carvalho Ferreira",
    page_icon="CF",
    layout="wide",
    initial_sidebar_state="expanded",
)

SCOPES_SHEETS = ["https://www.googleapis.com/auth/spreadsheets"]

SPREADSHEET_ID = "1nVEpOZFYFKcq0MXtOwxn22nqxafmJBHnf6zhHQlyT8w"
NOME_ABA = "Imoveis"

SCOPES_DRIVE = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]


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
        max-height: 220px !important;
    }


    /* =========================================================
       PREÇO (DESTAQUE MAIOR)
       ========================================================= */

    .preco-imovel {
        font-size: 1.3rem;
        font-weight: 700;
        color: #d4af37;
        margin-top: 10px;
        margin-bottom: 4px;
    }


    /* =========================================================
       TIPO E DETALHES
       ========================================================= */

    .tipo-detalhe {
        font-size: 1rem;
        font-weight: 600;
        color: #f7f5ef;
        margin-bottom: 2px;
    }


    /* =========================================================
       INFORMAÇÕES SECUNDÁRIAS (ÁREA, BAIRRO)
       ========================================================= */

    .info-sub {
        font-size: 0.9rem;
        color: #8b949e;
        margin-bottom: 4px;
    }


    /* =========================================================
       CÓDIGO DO IMÓVEL
       ========================================================= */

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
def conectar_sheets():
  creds_dict = dict(st.secrets["google_credentials"])
  creds = service_account.Credentials.from_service_account_info(
      creds_dict,
      scopes=SCOPES_SHEETS,
  )
  return build("sheets", "v4", credentials=creds)


@st.cache_resource
def conectar_drive():
  try:
    creds_dict = dict(st.secrets["google_credentials"])
    creds = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=SCOPES_DRIVE,
    )
    return build("drive", "v3", credentials=creds)
  except Exception:
    return None


# =============================================================================
# AUTENTICAÇÃO (SESSÃO PERSISTENTE)
# =============================================================================

def verificar_senha():
  if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

  if st.session_state["autenticado"]:
    return True

  st.subheader("🔒 Acesso Restrito - Painel Carvalho Ferreira")
  senha_digitada = st.text_input("Digite a senha de acesso:", type="password")

  if st.button("Entrar"):
    if senha_digitada == st.secrets["passwords"]["senha_acesso"]:
      st.session_state["autenticado"] = True
      st.rerun()
    else:
      st.error("Senha incorreta. Tente novamente.")

  return False


if not verificar_senha():
  st.stop()


# =============================================================================
# FUNÇÃO DE NORMALIZAÇÃO E LEITURA DA PLANILHA
# =============================================================================

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
      quartos = dados.get("DORMITORIOS") or dados.get("QUARTOS") or ""
      area_util = dados.get("AREA UTIL") or ""
      
      # ID da miniatura salvo na coluna correspondente
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
              "miniatura_id": miniatura_id.strip(),
          }
      )

    return imoveis
  except Exception as e:
    st.error(f"Erro ao carregar dados da planilha: {e}")
    return []


def buscar_imovel(codigo):
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
      return None

    cabecalho = [normalizar(h) for h in rows[0]]
    codigo_busca = normalizar(codigo)

    for row in rows[1:]:
      if not row:
        continue
      while len(row) < len(cabecalho):
        row.append("")
      if normalizar(row[0]) == codigo_busca:
        return {cabecalho[i]: row[i] for i in range(len(cabecalho))}

    return None
  except Exception as e:
    st.error(f"Erro ao conectar na planilha: {e}")
    return None


def salvar_dados(codigo, novos_dados):
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

    for i, row in enumerate(rows):
      if row and normalizar(row[0]) == normalizar(codigo):
        range_to_update = f"'{NOME_ABA}'!A{i + 1}:AZ{i + 1}"
        body = {"values": [novos_dados]}
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_to_update,
            valueInputOption="RAW",
            body=body,
        ).execute()
        return True
    return False
  except Exception as e:
    st.error(f"Erro ao salvar na planilha: {e}")
    return False


def obter_valor(dados_imovel, chave):
  if not dados_imovel:
    return ""
  return str(dados_imovel.get(normalizar(chave), ""))


def carregar_dados_na_interface(dados):
  campos = {
      "f_codigo": "CODIGO",
      "f_tipo": "TIPO",
      "f_cidade": "CIDADE",
      "f_bairro": "BAIRRO",
      "f_endereco": "ENDERECO",
      "f_proprietario": "PROPRIETARIO",
      "f_contato": "CONTATO",
      "f_status": "STATUS",
      "f_exclus": "EXCLUS",
      "f_data": "DATA",
      "f_valor": "VALOR",
      "f_area_util": "AREA UTIL",
      "f_area_total": "AREA TOTAL",
      "f_andar": "ANDAR",
      "f_iptu": "IPTU",
      "f_dormitorios": "DORMITORIOS",
      "f_banheiros": "BANHEIROS",
      "f_suites": "SUITES",
      "f_vagas": "VAGAS",
      "f_titulo1": "TITULO 1",
      "f_titulo2": "TITULO 2",
      "f_titulo3": "TITULO 3",
      "f_descricao": "DESCRICAO",
      "f_legenda1": "LEGENDA 1",
      "f_legenda2": "LEGENDA 2",
      "f_obs": "OBS EXTRAS",
  }

  for campo, chave in campos.items():
    st.session_state[campo] = obter_valor(dados, chave)


# =============================================================================
# BUSCA DA MINIATURA PELO ID DA PLANILHA
# =============================================================================

@st.cache_data(ttl=600)
def obter_foto_miniatura_por_id(file_id):
  if not file_id or len(str(file_id).strip()) < 10:
    return None
  try:
    drive = conectar_drive()
    if not drive:
      return None

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
# EXECUÇÃO DE MÓDULOS (PDF, POSTS, TRATADOR)
# =============================================================================

def executar_gerador_pdf(codigo_imovel):
  try:
    importlib.reload(gerador_pdf)
    pdf_bytes = gerador_pdf.gerar_pdf(codigo_imovel)
    if pdf_bytes and isinstance(pdf_bytes, (bytes, bytearray)) and len(pdf_bytes) > 10000:
      return True, pdf_bytes
    return False, "Falha ao gerar o PDF."
  except Exception as e:
    return False, f"Erro ao gerar PDF: {e}"


def executar_gerador_posts(codigo_imovel):
  if gerar_posts is None:
    return False, "Modulo gerar_posts nao encontrado."
  try:
    importlib.reload(gerar_posts)
    resultado = gerar_posts.gerar_posts(codigo_imovel)
    if isinstance(resultado, (bytes, bytearray)) and len(resultado) > 1000:
      return True, resultado
    if isinstance(resultado, str) and Path(resultado).exists():
      return True, resultado
    return False, "Falha ao gerar os posts."
  except Exception as e:
    return False, f"Erro ao gerar posts: {e}"


def executar_tratador_fotos(codigo_imovel):
  if tratador_nuvem is None:
    return False, "Modulo tratador_nuvem nao encontrado."
  try:
    importlib.reload(tratador_nuvem)
    service_drive = conectar_drive()
    if service_drive is None:
      return False, "Não foi possível conectar ao Google Drive."

    logo_bytes = None
    logo_path = Path("marca/logo.png")
    if logo_path.exists():
      with open(logo_path, "rb") as f:
        logo_bytes = f.read()

    with st.spinner(f"Processando fotos do imóvel {codigo_imovel}..."):
      if hasattr(tratador_nuvem, "tratar"):
        resultado = tratador_nuvem.tratar(codigo_imovel, service=service_drive, logo_bytes=logo_bytes)
      elif hasattr(tratador_nuvem, "tratar_fotos"):
        resultado = tratador_nuvem.tratar_fotos(codigo_imovel, service=service_drive, logo_bytes=logo_bytes)
      else:
        return False, "Função de tratamento não encontrada."

    if not resultado:
      return False, "Nenhuma foto foi tratada."

    if isinstance(resultado, bytes):
      zip_bytes = resultado
    elif isinstance(resultado, bytearray):
      zip_bytes = bytes(resultado)
    elif hasattr(resultado, "getvalue"):
      zip_bytes = resultado.getvalue()
    elif hasattr(resultado, "read"):
      resultado.seek(0)
      zip_bytes = resultado.read()
    else:
      return False, "O tratamento não retornou um ZIP válido."

    return True, zip_bytes
  except Exception as e:
    return False, f"Erro no tratamento: {e}"


# =============================================================================
# ESTADO DA APLICAÇÃO
# =============================================================================

if "codigo_busca" not in st.session_state:
  st.session_state["codigo_busca"] = ""

if "dados_imovel" not in st.session_state:
  st.session_state["dados_imovel"] = None

if "confirmar_tratamento" not in st.session_state:
  st.session_state["confirmar_tratamento"] = False

if "fotos_tratadas_zip" not in st.session_state:
  st.session_state["fotos_tratadas_zip"] = None

if "fotos_tratadas_nome" not in st.session_state:
  st.session_state["fotos_tratadas_nome"] = "fotos_tratadas.zip"


# =============================================================================
# CABEÇALHO E BUSCA PRINCIPAL
# =============================================================================

st.title("Carvalho Ferreira")
st.caption("Painel de gestao e geracao de materiais")

st.markdown("### Seleção de Imóvel")

col_busca1, col_busca2 = st.columns([3, 1])

with col_busca1:
  codigo_input = st.text_input(
      "Código do Imóvel",
      value=st.session_state["codigo_busca"],
      placeholder="Ex: CF003",
      label_visibility="collapsed",
      key="campo_codigo_principal",
  )

with col_busca2:
  buscar = st.button(
      "Buscar",
      use_container_width=True,
      type="primary",
      key="btn_buscar_principal",
  )

codigo_digitado = (codigo_input or "").strip().upper()

if (buscar and codigo_digitado) or (
    codigo_digitado and codigo_digitado != st.session_state["codigo_busca"]
):
  st.session_state["codigo_busca"] = codigo_digitado
  if codigo_digitado:
    with st.spinner("Buscando dados na planilha..."):
      dados_encontrados = buscar_imovel(codigo_digitado)

    if dados_encontrados is None:
      st.session_state["dados_imovel"] = None
      st.warning(f"Registro {codigo_digitado} nao localizado.")
    else:
      st.session_state["dados_imovel"] = dados_encontrados
      carregar_dados_na_interface(dados_encontrados)
  st.rerun()

codigo_busca = st.session_state.get("codigo_busca", "").strip().upper()
dados_imovel = st.session_state.get("dados_imovel", None)

if codigo_busca and dados_imovel:
  st.success(f"Imóvel **{codigo_busca}** carregado com sucesso!")


# =============================================================================
# SIDEBAR (AÇÕES E FILTROS)
# =============================================================================

st.sidebar.markdown("### Materiais & Ações")

st.sidebar.markdown("---")

if codigo_busca:
  if st.sidebar.button(
      "📂 Materiais / Compartilhar",
      use_container_width=True,
      key="btn_materiais_atalho",
  ):
    st.switch_page("pages/materiais.py")
else:
  st.sidebar.button(
      "📂 Materiais / Compartilhar",
      use_container_width=True,
      disabled=True,
      help="Busque um imóvel primeiro",
  )

# PDF
if st.sidebar.button("Gerar PDF", use_container_width=True, key="btn_pdf"):
  if not codigo_busca:
    st.sidebar.error("Informe o codigo.")
  else:
    with st.spinner("Gerando PDF..."):
      ok, res = executar_gerador_pdf(codigo_busca)
    if ok:
      st.session_state["pdf_bytes"] = res
      st.session_state["pdf_nome"] = f"{codigo_busca}.pdf"
      st.sidebar.success("PDF gerado.")
    else:
      st.sidebar.error(res)

if st.session_state.get("pdf_bytes"):
  st.sidebar.download_button(
      "Baixar PDF",
      data=st.session_state["pdf_bytes"],
      file_name=st.session_state.get("pdf_nome", "dossie.pdf"),
      mime="application/pdf",
      use_container_width=True,
      key="dl_pdf_sidebar",
  )

# POSTS
if st.sidebar.button("Gerar Posts", use_container_width=True, key="btn_posts"):
  if not codigo_busca:
    st.sidebar.error("Informe o codigo.")
  else:
    with st.spinner("Gerando posts..."):
      ok, res = executar_gerador_posts(codigo_busca)
    if ok:
      st.session_state["posts_resultado"] = res
      st.sidebar.success("Posts gerados.")
    else:
      st.sidebar.error(res)

if st.session_state.get("posts_resultado") is not None:
  posts_res = st.session_state["posts_resultado"]
  if isinstance(posts_res, (bytes, bytearray)):
    st.sidebar.download_button(
        "Baixar Posts (ZIP)",
        data=posts_res,
        file_name=f"posts_{codigo_busca}.zip",
        mime="application/zip",
        use_container_width=True,
        key="dl_posts_bytes",
    )
  else:
    caminho = Path(str(posts_res))
    if caminho.exists():
      with open(caminho, "rb") as f:
        st.sidebar.download_button(
            "Baixar Posts (ZIP)",
            data=f.read(),
            file_name=caminho.name,
            mime="application/zip",
            use_container_width=True,
            key="dl_posts_path",
        )

# TRATAR FOTOS
if st.sidebar.button("Tratar fotos", use_container_width=True, key="btn_tratar"):
  if not codigo_busca:
    st.sidebar.error("Informe o codigo.")
  else:
    st.session_state["confirmar_tratamento"] = True

if st.session_state.get("confirmar_tratamento"):
  st.sidebar.warning("O tratamento pode demorar alguns minutos.")
  a1, a2 = st.sidebar.columns(2)
  with a1:
    if st.button("Sim", use_container_width=True, key="trat_sim"):
      st.session_state["confirmar_tratamento"] = False
      ok, resultado = executar_tratador_fotos(codigo_busca)
      if ok:
        st.session_state["fotos_tratadas_zip"] = resultado
        st.session_state["fotos_tratadas_nome"] = f"{codigo_busca}_fotos_tratadas.zip"
        st.sidebar.success("Fotos tratadas com sucesso.")
      else:
        st.session_state["fotos_tratadas_zip"] = None
        st.sidebar.warning(str(resultado))
  with a2:
    if st.button("Nao", use_container_width=True, key="trat_nao"):
      st.session_state["confirmar_tratamento"] = False

if st.session_state.get("fotos_tratadas_zip"):
  st.sidebar.markdown("### Fotos tratadas")
  st.sidebar.download_button(
      "Baixar Fotos Tratadas",
      data=st.session_state["fotos_tratadas_zip"],
      file_name=st.session_state.get("fotos_tratadas_nome", f"{codigo_busca}_fotos_tratadas.zip"),
      mime="application/zip",
      use_container_width=True,
      type="primary",
      key="dl_fotos_tratadas",
  )


# =============================================================================
# CARREGAMENTO DOS IMÓVEIS PARA A VITRINE
# =============================================================================

with st.spinner("Buscando imóveis disponíveis..."):
  lista_imoveis = carregar_imoveis_sheets()

if not lista_imoveis:
  st.warning("Nenhum imóvel encontrado na planilha.")
  st.stop()


# =============================================================================
# FILTROS NA SIDEBAR
# =============================================================================

st.sidebar.markdown("---")
st.sidebar.markdown("## 🔍 Filtrar Imóveis")

if st.sidebar.button("🧹 Limpar Pesquisa", use_container_width=True):
  st.session_state["filtro_bairro"] = "Todos"
  st.session_state["busca_texto"] = ""
  st.session_state["filtro_quartos"] = "Todos"
  st.rerun()

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
# RESULTADOS DA VITRINE COM LAYOUT REESTRUTURADO
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

          # 1. MINIATURA (Carregada via ID do Google Sheets)
          foto_bytes = obter_foto_miniatura_por_id(imovel["miniatura_id"])
          if foto_bytes:
            st.image(foto_bytes, use_container_width=True)
          else:
            st.markdown("🖼️ *Miniatura não configurada*")

          # 2. PREÇO (Destaque Maior no Topo)
          st.markdown(
              f'''
              <div class="preco-imovel">
                  {imovel["valor"]}
              </div>
              ''',
              unsafe_allow_html=True,
          )

          # 3. TIPO + DORMITÓRIOS (Lado a lado)
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
          area_texto = f"📐 {imovel['area_util']} úteis" if imovel["area_util"] else ""
          if area_texto:
            st.markdown(
                f'''
                <div class="info-sub">
                    {area_texto}
                </div>
                ''',
                unsafe_allow_html=True,
            )

          # 5. LOCALIZAÇÃO (Bairro • Cidade)
          st.markdown(
              f'''
              <div class="info-sub">
                  📍 {imovel["bairro"]} • {imovel["cidade"]}
              </div>
              ''',
              unsafe_allow_html=True,
          )

          # 6. CÓDIGO DO IMÓVEL (Tag menor)
          st.markdown(
              f'''
              <div class="codigo-tag">
                  🏷️ {imovel["codigo"]}
              </div>
              ''',
              unsafe_allow_html=True,
          )

          # 7. BOTÃO DE ACESSAR MATERIAIS
          if st.button(
              "📂 Acessar Materiais",
              key=f"btn_mat_{imovel['codigo']}_{inicio}_{posicao}",
              use_container_width=True,
          ):
            st.session_state["codigo_materiais"] = imovel["codigo"]
            st.switch_page("pages/materiais.py")

          st.markdown("</div>", unsafe_allow_html=True)


# =============================================================================
# ABAS DE EDIÇÃO (FICHA TÉCNICA E DIVULGAÇÃO)
# =============================================================================

st.markdown("---")
st.markdown("### ⚙️ Gerenciamento e Ficha Técnica do Imóvel")

tab1, tab2, tab3 = st.tabs(["Identificação", "Dados Tecnicos", "Divulgacao"])

with tab1:
  col_a, col_b = st.columns(2)
  with col_a:
    novo_codigo = st.text_input("Codigo", key="f_codigo")
    novo_tipo = st.text_input("Tipo", key="f_tipo")
    novo_cidade = st.text_input("Cidade", key="f_cidade")
    novo_bairro = st.text_input("Bairro", key="f_bairro")
    novo_endereco = st.text_input("Endereco", key="f_endereco")
  with col_b:
    novo_proprietario = st.text_input("Proprietario", key="f_proprietario")
    novo_contato = st.text_input("Contato", key="f_contato")
    novo_status = st.text_input("Status", key="f_status")
    novo_exclus = st.text_input("Exclusividade", key="f_exclus")
    novo_data = st.text_input("Data", key="f_data")

with tab2:
  col_d, col_e = st.columns(2)
  with col_d:
    novo_valor = st.text_input("Valor", key="f_valor")
    novo_area_util = st.text_input("Area Util", key="f_area_util")
    novo_area_total = st.text_input("Area Total", key="f_area_total")
    novo_andar = st.text_input("Andar", key="f_andar")
    novo_iptu = st.text_input("IPTU", key="f_iptu")
  with col_e:
    novo_dormitorios = st.text_input("Dormitorios", key="f_dormitorios")
    novo_banheiros = st.text_input("Banheiros", key="f_banheiros")
    novo_suites = st.text_input("Suites", key="f_suites")
    novo_vagas = st.text_input("Vagas", key="f_vagas")

with tab3:
  novo_titulo_1 = st.text_input("Titulo 1", key="f_titulo1")
  novo_titulo_2 = st.text_input("Titulo 2", key="f_titulo2")
  novo_titulo_3 = st.text_input("Titulo 3", key="f_titulo3")
  novo_descricao = st.text_area("Descricao", height=150, key="f_descricao")

  st.markdown("---")
  st.markdown("### 📝 Legendas para Redes Sociais")
  nova_legenda_1 = st.text_area("Legenda 1", height=130, key="f_legenda1")
  nova_legenda_2 = st.text_area("Legenda 2", height=130, key="f_legenda2")
  novo_obs_extras = st.text_area("Obs Extras", height=100, key="f_obs")

# Manter links e fotos já existentes salvos na planilha
novo_link = obter_valor(dados_imovel, "LINK")
novo_foto = obter_valor(dados_imovel, "FOTO")

st.markdown("---")

if st.button("Salvar atualizacoes", type="primary", use_container_width=True, key="btn_salvar"):
  if not codigo_busca:
    st.warning("Busque um imovel primeiro.")
  else:
    dados_para_salvar = [
        novo_codigo,
        novo_tipo,
        novo_cidade,
        novo_bairro,
        novo_endereco,
        novo_proprietario,
        novo_contato,
        novo_valor,
        novo_status,
        novo_exclus,
        novo_data,
        novo_link,
        novo_foto,
        novo_dormitorios,
        novo_banheiros,
        novo_suites,
        novo_vagas,
        novo_area_util,
        novo_area_total,
        novo_andar,
        novo_iptu,
        novo_titulo_1,
        novo_titulo_2,
        novo_titulo_3,
        novo_descricao,
        nova_legenda_1,
        nova_legenda_2,
        novo_obs_extras,
    ]

    with st.spinner("Salvando..."):
      if salvar_dados(codigo_busca, dados_para_salvar):
        st.success("Dados atualizados com sucesso!")
      else:
        st.error("Nao foi possivel salvar.")
