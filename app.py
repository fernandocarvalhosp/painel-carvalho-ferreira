import streamlit as st

def verificar_senha():
    # Verifica se a senha já foi digitada corretamente nesta sessão
    if "senha_correta" not in st.session_state:
        st.session_state["senha_correta"] = False

    if st.session_state["senha_correta"]:
        return True

    # Tela de Login simples na interface
    st.subheader("🔒 Acesso Restrito - Painel Carvalho Ferreira")
    senha_digitada = st.text_input("Digite a senha de acesso:", type="password")
    
    if st.button("Entrar"):
        # Compara com a senha salva nos segredos da nuvem (ou uma fixa)
        if senha_digitada == st.secrets["passwords"]["senha_acesso"]:
            st.session_state["senha_correta"] = True
            st.rerun()
        else:
            st.error("Senha incorreta. Tente novamente.")
            
    return False

# Trava principal: Se não autenticar, o código para aqui
if not verificar_senha():
    st.stop()

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

# App so precisa gravar/ler planilha
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = "1nVEpOZFYFKcq0MXtOwxn22nqxafmJBHnf6zhHQlyT8w"
NOME_ABA = "Imoveis"


@st.cache_resource
def conectar_sheets():
    creds_dict = dict(st.secrets["google_credentials"])
    creds = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=SCOPES
    )
    return build("sheets", "v4", credentials=creds)


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
                range=f"'{NOME_ABA}'!A:Z",
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
                range=f"'{NOME_ABA}'!A:Z",
            )
            .execute()
        )
        rows = result.get("values", [])

        for i, row in enumerate(rows):
            if row and normalizar(row[0]) == normalizar(codigo):
                range_to_update = f"'{NOME_ABA}'!A{i + 1}:Z{i + 1}"
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


def executar_gerador_pdf(codigo_imovel):
    """Retorna (ok, pdf_bytes_ou_mensagem)."""
    try:
        importlib.reload(gerador_pdf)
        pdf_bytes = gerador_pdf.gerar_pdf(codigo_imovel)
        if pdf_bytes and isinstance(pdf_bytes, (bytes, bytearray)) and len(pdf_bytes) > 10000:
            return True, pdf_bytes
        return False, "Falha ao gerar o PDF."
    except Exception as e:
        return False, f"Erro ao gerar PDF: {e}"


def executar_gerador_posts(codigo_imovel):
    """Retorna (ok, caminho_ou_bytes_ou_mensagem)."""
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

# -------------------------------------------------
# INICIALIZAÇÃO DE ESTADO
# -------------------------------------------------
if "codigo_busca" not in st.session_state:
    st.session_state["codigo_busca"] = ""

if "dados_imovel" not in st.session_state:
    st.session_state["dados_imovel"] = None

# -------------------------------------------------
# SIDEBAR
# -------------------------------------------------
st.sidebar.markdown("### Selecao de Imovel")

c1, c2 = st.sidebar.columns([3, 1])
with c1:
    codigo_input = st.text_input(
        "codigo",
        value=st.session_state["codigo_busca"],
        placeholder="CODIGO",
        label_visibility="collapsed",
        key="campo_codigo_sidebar",
    )
with c2:
    buscar = st.button("Buscar", use_container_width=True, key="btn_buscar")

codigo_digitado = (codigo_input or "").strip().upper()

# Dispara a busca quando clica no botão ou altera o código e aperta Enter
if (buscar and codigo_digitado) or (codigo_digitado and codigo_digitado != st.session_state["codigo_busca"]):
    st.session_state["codigo_busca"] = codigo_digitado
    if codigo_digitado:
        with st.spinner("Buscando dados na planilha..."):
            st.session_state["dados_imovel"] = buscar_imovel(codigo_digitado)
        if st.session_state["dados_imovel"] is None:
            st.sidebar.warning(f"Registro {codigo_digitado} nao localizado.")
    st.rerun()

codigo_busca = st.session_state.get("codigo_busca", "").strip().upper()
dados_imovel = st.session_state.get("dados_imovel", None)

if codigo_busca:
    st.sidebar.caption(codigo_busca)

st.sidebar.markdown("### Materiais")

# PDF
if st.sidebar.button("Gerar PDF", use_container_width=True, type="primary", key="btn_pdf"):
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

# Posts
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

# Tratar fotos (opcional)
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
            if tratador_nuvem is None:
                st.sidebar.error("Modulo tratador_nuvem nao encontrado.")
            else:
                try:
                    importlib.reload(tratador_nuvem)
                    if hasattr(tratador_nuvem, "tratar"):
                        msg = tratador_nuvem.tratar(codigo_busca)
                    elif hasattr(tratador_nuvem, "tratar_fotos"):
                        msg = tratador_nuvem.tratar_fotos(codigo_busca)
                    else:
                        msg = "Funcao de tratamento nao encontrada."
                    st.sidebar.success(str(msg) if msg else "Concluido.")
                except Exception as e:
                    st.sidebar.error(str(e))
    with a2:
        if st.button("Nao", use_container_width=True, key="trat_nao"):
            st.session_state["confirmar_tratamento"] = False


# -------------------------------------------------
# AREA PRINCIPAL
# -------------------------------------------------
st.title("Carvalho Ferreira")
st.caption("Painel de gestao e geracao de materiais")

tab1, tab2, tab3 = st.tabs(["Identificacao", "Dados Tecnicos", "Divulgacao"])

with tab1:
    col_a, col_b = st.columns(2)
    with col_a:
        novo_codigo = st.text_input(
            "Codigo", value=obter_valor(dados_imovel, "CODIGO"), key="f_codigo"
        )
        novo_tipo = st.text_input(
            "Tipo", value=obter_valor(dados_imovel, "TIPO"), key="f_tipo"
        )
        novo_cidade = st.text_input(
            "Cidade", value=obter_valor(dados_imovel, "CIDADE"), key="f_cidade"
        )
        novo_bairro = st.text_input(
            "Bairro", value=obter_valor(dados_imovel, "BAIRRO"), key="f_bairro"
        )
        novo_endereco = st.text_input(
            "Endereco", value=obter_valor(dados_imovel, "ENDERECO"), key="f_endereco"
        )
    with col_b:
        novo_proprietario = st.text_input(
            "Proprietario",
            value=obter_valor(dados_imovel, "PROPRIETARIO"),
            key="f_proprietario",
        )
        novo_contato = st.text_input(
            "Contato", value=obter_valor(dados_imovel, "CONTATO"), key="f_contato"
        )
        novo_status = st.text_input(
            "Status", value=obter_valor(dados_imovel, "STATUS"), key="f_status"
        )
        novo_exclus = st.text_input(
            "Exclusividade", value=obter_valor(dados_imovel, "EXCLUS"), key="f_exclus"
        )
        novo_data = st.text_input(
            "Data", value=obter_valor(dados_imovel, "DATA"), key="f_data"
        )

with tab2:
    col_d, col_e = st.columns(2)
    with col_d:
        novo_valor = st.text_input(
            "Valor", value=obter_valor(dados_imovel, "VALOR"), key="f_valor"
        )
        novo_area_util = st.text_input(
            "Area Util", value=obter_valor(dados_imovel, "AREA UTIL"), key="f_area_util"
        )
        novo_area_total = st.text_input(
            "Area Total",
            value=obter_valor(dados_imovel, "AREA TOTAL"),
            key="f_area_total",
        )
        novo_andar = st.text_input(
            "Andar", value=obter_valor(dados_imovel, "ANDAR"), key="f_andar"
        )
        novo_iptu = st.text_input(
            "IPTU", value=obter_valor(dados_imovel, "IPTU"), key="f_iptu"
        )
    with col_e:
        novo_dormitorios = st.text_input(
            "Dormitorios",
            value=obter_valor(dados_imovel, "DORMITORIOS"),
            key="f_dormitorios",
        )
        novo_banheiros = st.text_input(
            "Banheiros", value=obter_valor(dados_imovel, "BANHEIROS"), key="f_banheiros"
        )
        novo_suites = st.text_input(
            "Suites", value=obter_valor(dados_imovel, "SUITES"), key="f_suites"
        )
        novo_vagas = st.text_input(
            "Vagas", value=obter_valor(dados_imovel, "VAGAS"), key="f_vagas"
        )

with tab3:
    novo_titulo_1 = st.text_input(
        "Titulo 1", value=obter_valor(dados_imovel, "TITULO 1"), key="f_titulo1"
    )
    novo_titulo_2 = st.text_input(
        "Titulo 2", value=obter_valor(dados_imovel, "TITULO 2"), key="f_titulo2"
    )
    novo_titulo_3 = st.text_input(
        "Titulo 3", value=obter_valor(dados_imovel, "TITULO 3"), key="f_titulo3"
    )
    novo_descricao = st.text_area(
        "Descricao",
        value=obter_valor(dados_imovel, "DESCRICAO"),
        height=150,
        key="f_descricao",
    )
    novo_obs_extras = st.text_area(
        "Obs Extras",
        value=obter_valor(dados_imovel, "OBS EXTRAS"),
        height=100,
        key="f_obs",
    )

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
            novo_obs_extras,
        ]
        with st.spinner("Salvando..."):
            if salvar_dados(codigo_busca, dados_para_salvar):
                st.success("Dados atualizados.")
            else:
                st.error("Nao foi possivel salvar.")
