# app.py
# -*- coding: utf-8 -*-

import importlib
from pathlib import Path

import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build

import gerador_pdf

try:
  import gerar_posts
except Exception:
  gerar_posts = None

try:
  import tratador_nuvem
except Exception:
  tratador_nuvem = None


st.set_page_config(
    page_title="Carvalho Ferreira | Painel",
    layout="wide",
)


# =============================================================================
# AUTENTICAÇÃO (SENHA DE ACESSO COM SESSÃO PERSISTENTE)
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
# CONFIGURAÇÕES
# =============================================================================

SCOPES_SHEETS = ["https://www.googleapis.com/auth/spreadsheets"]

SPREADSHEET_ID = "1nVEpOZFYFKcq0MXtOwxn22nqxafmJBHnf6zhHQlyT8w"

NOME_ABA = "Imoveis"


SCOPES_DRIVE = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]


# =============================================================================
# CONEXÃO COM GOOGLE SHEETS
# =============================================================================


@st.cache_resource
def conectar_sheets():
  creds_dict = dict(st.secrets["google_credentials"])

  creds = service_account.Credentials.from_service_account_info(
      creds_dict,
      scopes=SCOPES_SHEETS,
  )

  return build(
      "sheets",
      "v4",
      credentials=creds,
  )


# =============================================================================
# CONEXÃO COM GOOGLE DRIVE
# =============================================================================


@st.cache_resource
def conectar_drive():
  try:
    creds_dict = dict(st.secrets["google_credentials"])
    creds = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=SCOPES_DRIVE,
    )
    return build(
        "drive",
        "v3",
        credentials=creds,
    )
  except Exception:
    return None


# =============================================================================
# PLANILHA
# =============================================================================


def normalizar(texto):
  if not texto:
    return ""

  return " ".join(str(texto).strip().upper().split())


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

    rows = result.get(
        "values",
        [],
    )

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


def salvar_dados(
    codigo,
    novos_dados,
):
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

    rows = result.get(
        "values",
        [],
    )

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


def obter_valor(
    dados_imovel,
    chave,
):
  if not dados_imovel:
    return ""

  return str(
      dados_imovel.get(
          normalizar(chave),
          "",
      )
  )


def carregar_dados_na_interface(
    dados,
):
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
    st.session_state[campo] = obter_valor(
        dados,
        chave,
    )


# =============================================================================
# GERADOR PDF
# =============================================================================


def executar_gerador_pdf(
    codigo_imovel,
):
  try:
    importlib.reload(gerador_pdf)

    pdf_bytes = gerador_pdf.gerar_pdf(codigo_imovel)

    if (
        pdf_bytes
        and isinstance(
            pdf_bytes,
            (bytes, bytearray),
        )
        and len(pdf_bytes) > 10000
    ):
      return True, pdf_bytes

    return False, "Falha ao gerar o PDF."

  except Exception as e:
    return False, f"Erro ao gerar PDF: {e}"


# =============================================================================
# GERADOR POSTS
# =============================================================================


def executar_gerador_posts(
    codigo_imovel,
):
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


# =============================================================================
# TRATADOR DE FOTOS
# =============================================================================


def executar_tratador_fotos(
    codigo_imovel,
):
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
      with open(
          logo_path,
          "rb",
      ) as f:
        logo_bytes = f.read()

    with st.spinner(f"Processando fotos do imóvel {codigo_imovel}..."):
      if hasattr(
          tratador_nuvem,
          "tratar",
      ):
        resultado = tratador_nuvem.tratar(
            codigo_imovel,
            service=service_drive,
            logo_bytes=logo_bytes,
        )

      elif hasattr(
          tratador_nuvem,
          "tratar_fotos",
      ):
        resultado = tratador_nuvem.tratar_fotos(
            codigo_imovel,
            service=service_drive,
            logo_bytes=logo_bytes,
        )

      else:
        return False, "Função de tratamento não encontrada."

    if not resultado:
      return False, "Nenhuma foto foi tratada (pasta vazia ou não localizada)."

    if isinstance(
        resultado,
        bytes,
    ):
      zip_bytes = resultado

    elif isinstance(
        resultado,
        bytearray,
    ):
      zip_bytes = bytes(resultado)

    elif hasattr(
        resultado,
        "getvalue",
    ):
      zip_bytes = resultado.getvalue()

    elif hasattr(
        resultado,
        "read",
    ):
      resultado.seek(0)

      zip_bytes = resultado.read()

    else:
      return False, "O tratamento não retornou um ZIP válido."

    if not zip_bytes:
      return False, "O ZIP gerado está vazio."

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
# CABEÇALHO
# =============================================================================

st.title("Carvalho Ferreira")

st.caption("Painel de gestao e geracao de materiais")


# =============================================================================
# BUSCA DO IMÓVEL
# =============================================================================

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


codigo_busca = st.session_state.get(
    "codigo_busca",
    "",
).strip().upper()

dados_imovel = st.session_state.get(
    "dados_imovel",
    None,
)


if codigo_busca and dados_imovel:
  st.success(f"Imóvel **{codigo_busca}** carregado com sucesso!")


# =============================================================================
# SIDEBAR
# =============================================================================

st.sidebar.markdown("### Materiais & Ações")


# =============================================================================
# BOTÃO MATERIAIS
# =============================================================================

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


# =============================================================================
# PDF
# =============================================================================

if st.sidebar.button(
    "Gerar PDF",
    use_container_width=True,
    key="btn_pdf",
):
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
      file_name=st.session_state.get(
          "pdf_nome",
          "dossie.pdf",
      ),
      mime="application/pdf",
      use_container_width=True,
      key="dl_pdf_sidebar",
  )


# =============================================================================
# POSTS
# =============================================================================

if st.sidebar.button(
    "Gerar Posts",
    use_container_width=True,
    key="btn_posts",
):
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

  if isinstance(
      posts_res,
      (bytes, bytearray),
  ):
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
      with open(
          caminho,
          "rb",
      ) as f:
        st.sidebar.download_button(
            "Baixar Posts (ZIP)",
            data=f.read(),
            file_name=caminho.name,
            mime="application/zip",
            use_container_width=True,
            key="dl_posts_path",
        )


# =============================================================================
# TRATAR FOTOS
# =============================================================================

if st.sidebar.button(
    "Tratar fotos",
    use_container_width=True,
    key="btn_tratar",
):
  if not codigo_busca:
    st.sidebar.error("Informe o codigo.")

  else:
    st.session_state["confirmar_tratamento"] = True


if st.session_state.get("confirmar_tratamento"):
  st.sidebar.warning("O tratamento pode demorar alguns minutos.")

  a1, a2 = st.sidebar.columns(2)

  with a1:
    if st.button(
        "Sim",
        use_container_width=True,
        key="trat_sim",
    ):
      st.session_state["confirmar_tratamento"] = False

      ok, resultado = executar_tratador_fotos(codigo_busca)

      if ok:
        st.session_state["fotos_tratadas_zip"] = resultado

        st.session_state["fotos_tratadas_nome"] = (
            f"{codigo_busca}_fotos_tratadas.zip"
        )

        st.sidebar.success("Fotos tratadas com sucesso.")

      else:
        st.session_state["fotos_tratadas_zip"] = None
        st.sidebar.warning(str(resultado))

  with a2:
    if st.button(
        "Nao",
        use_container_width=True,
        key="trat_nao",
    ):
      st.session_state["confirmar_tratamento"] = False


# =============================================================================
# DOWNLOAD DAS FOTOS TRATADAS
# =============================================================================

if st.session_state.get("fotos_tratadas_zip"):
  st.sidebar.markdown("### Fotos tratadas")

  st.sidebar.download_button(
      "Baixar Fotos Tratadas",
      data=st.session_state["fotos_tratadas_zip"],
      file_name=st.session_state.get(
          "fotos_tratadas_nome",
          f"{codigo_busca}_fotos_tratadas.zip",
      ),
      mime="application/zip",
      use_container_width=True,
      type="primary",
      key="dl_fotos_tratadas",
  )


# =============================================================================
# ABAS DE CONTEÚDO
# =============================================================================

tab1, tab2, tab3 = st.tabs(
    [
        "Identificacao",
        "Dados Tecnicos",
        "Divulgacao",
    ]
)


# =============================================================================
# IDENTIFICAÇÃO
# =============================================================================

with tab1:
  col_a, col_b = st.columns(2)

  with col_a:
    novo_codigo = st.text_input(
        "Codigo",
        key="f_codigo",
    )

    novo_tipo = st.text_input(
        "Tipo",
        key="f_tipo",
    )

    novo_cidade = st.text_input(
        "Cidade",
        key="f_cidade",
    )

    novo_bairro = st.text_input(
        "Bairro",
        key="f_bairro",
    )

    novo_endereco = st.text_input(
        "Endereco",
        key="f_endereco",
    )

  with col_b:
    novo_proprietario = st.text_input(
        "Proprietario",
        key="f_proprietario",
    )

    novo_contato = st.text_input(
        "Contato",
        key="f_contato",
    )

    novo_status = st.text_input(
        "Status",
        key="f_status",
    )

    novo_exclus = st.text_input(
        "Exclusividade",
        key="f_exclus",
    )

    novo_data = st.text_input(
        "Data",
        key="f_data",
    )


# =============================================================================
# DADOS TÉCNICOS
# =============================================================================

with tab2:
  col_d, col_e = st.columns(2)

  with col_d:
    novo_valor = st.text_input(
        "Valor",
        key="f_valor",
    )

    novo_area_util = st.text_input(
        "Area Util",
        key="f_area_util",
    )

    novo_area_total = st.text_input(
        "Area Total",
        key="f_area_total",
    )

    novo_andar = st.text_input(
        "Andar",
        key="f_andar",
    )

    novo_iptu = st.text_input(
        "IPTU",
        key="f_iptu",
    )

  with col_e:
    novo_dormitorios = st.text_input(
        "Dormitorios",
        key="f_dormitorios",
    )

    novo_banheiros = st.text_input(
        "Banheiros",
        key="f_banheiros",
    )

    novo_suites = st.text_input(
        "Suites",
        key="f_suites",
    )

    novo_vagas = st.text_input(
        "Vagas",
        key="f_vagas",
    )


# =============================================================================
# DIVULGAÇÃO (COM LEGENDAS 1 E 2)
# =============================================================================

with tab3:
  novo_titulo_1 = st.text_input(
      "Titulo 1",
      key="f_titulo1",
  )

  novo_titulo_2 = st.text_input(
      "Titulo 2",
      key="f_titulo2",
  )

  novo_titulo_3 = st.text_input(
      "Titulo 3",
      key="f_titulo3",
  )

  novo_descricao = st.text_area(
      "Descricao",
      height=150,
      key="f_descricao",
  )

  st.markdown("---")
  st.markdown("### 📝 Legendas para Redes Sociais")

  nova_legenda_1 = st.text_area(
      "Legenda 1",
      height=130,
      key="f_legenda1",
  )

  nova_legenda_2 = st.text_area(
      "Legenda 2",
      height=130,
      key="f_legenda2",
  )

  novo_obs_extras = st.text_area(
      "Obs Extras",
      height=100,
      key="f_obs",
  )


# =============================================================================
# LINKS
# =============================================================================

novo_link = obter_valor(
    dados_imovel,
    "LINK",
)

novo_foto = obter_valor(
    dados_imovel,
    "FOTO",
)


# =============================================================================
# SALVAR
# =============================================================================

st.markdown("---")


if st.button(
    "Salvar atualizacoes",
    type="primary",
    use_container_width=True,
    key="btn_salvar",
):
  if not codigo_busca:
    st.warning("Busque um imovel primeiro.")

  else:
    # A ordem exata reflete as colunas padrão da planilha (incluindo LEGENDA 1 e LEGENDA 2)
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
        nova_legenda_1,  # LEGENDA 1
        nova_legenda_2,  # LEGENDA 2
        novo_obs_extras,
    ]

    with st.spinner("Salvando..."):
      if salvar_dados(
          codigo_busca,
          dados_para_salvar,
      ):
        st.success("Dados atualizados com sucesso (incluindo as legendas)!")

      else:
        st.error("Nao foi possivel salvar.")
