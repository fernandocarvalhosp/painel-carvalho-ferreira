# -*- coding: utf-8 -*-
import streamlit as st
import json
from google.oauth2 import service_account
import gerador_pdf
import gerar_posts.py
import tratador_nuvem.py
# Defina os escopos que seu aplicativo usa (ajuste se precisar de mais algum)
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Leitura segura das credenciais do Streamlit Secrets
creds_dict = dict(st.secrets["google_credentials"])
creds = service_account.Credentials.from_service_account_info(
    creds_dict, scopes=SCOPES
)
# -------------------------------------------------
# CONFIGURACAO DA PAGINA
# -------------------------------------------------
st.set_page_config(
    page_title="Carvalho Ferreira | Painel Operacional",
    layout="wide",
)

SCRIPT_DIR = Path(__file__).resolve().parent
CREDENCIAIS_FILE = SCRIPT_DIR / "config" / "credentials.json"

SPREADSHEET_ID = "1nVEpOZFYFKcq0MXtOwxn22nqxafmJBHnf6zhHQlyT8w"
NOME_ABA = "Imoveis"

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


# -------------------------------------------------
# CONEXAO GOOGLE SHEETS (ADAPTADA PARA NUVEM)
# -------------------------------------------------
@st.cache_resource
def conectar_sheets():
    # Valida credenciais locais ou via st.secrets se aplicável
    if CREDENCIAIS_FILE.exists():
        creds = service_account.Credentials.from_service_account_file(
            str(CREDENCIAIS_FILE),
            scopes=SCOPES,
        )
    else:
        # Fallback caso utilize secrets do Streamlit Cloud no futuro
        if "gcp_service_account" in st.secrets:
            creds = service_account.Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]),
                scopes=SCOPES,
            )
        else:
            raise FileNotFoundError(f"Arquivo de credenciais não encontrado em {CREDENCIAIS_FILE}")
           
    service = build("sheets", "v4", credentials=creds)
    return service


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
                dados = {}
                for i, chave in enumerate(cabecalho):
                    dados[chave] = row[i] if i < len(row) else ""
                return dados
        return None
    except Exception as e:
        st.error(f"Erro ao conectar na planilha: {e}")
        return None


def salvar_dados(codigo, novos_dados):
    """
    novos_dados: lista na ordem das colunas A:Z
    """
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
    try:
        importlib.reload(gerador_pdf)
        caminho = gerador_pdf.gerar_pdf(codigo_imovel)
        if caminho and Path(caminho).exists():
            return True, caminho
        return False, "Falha ao gerar o PDF."
    except Exception as e:
        return False, f"Erro ao gerar PDF: {e}"

def executar_gerador_posts(codigo_imovel):
    try:
        importlib.reload(gerar_posts)
        caminho = gerar_posts.gerar_posts(codigo_imovel)
        if caminho and Path(caminho).exists():
            return True, caminho
        return False, "Falha ao gerar os posts."
    except Exception as e:
        return False, f"Erro ao gerar posts: {e}"


# -------------------------------------------------
# INTERFACE
# -------------------------------------------------
st.title("Carvalho Ferreira")
st.subheader("Painel de Gestao e Geracao de Materiais")
st.markdown("---")

st.sidebar.header("Selecao de Imovel")
codigo_busca = st.sidebar.text_input(
    "Codigo do Imovel (Ex: CF003)"
).strip().upper()

dados_imovel = None

if codigo_busca:
    with st.spinner("Buscando dados na planilha..."):
        dados_imovel = buscar_imovel(codigo_busca)

    if dados_imovel:
        st.sidebar.success(f"Cadastro {codigo_busca} carregado.")
    else:
        st.sidebar.warning(f"Registro {codigo_busca} nao localizado.")


tab1, tab2, tab3, tab4 = st.tabs(
    [
        "Identificacao e Controle",
        "Dados Tecnicos",
        "Divulgacao",
        "Geracao de PDF",
    ]
)

with tab1:
    col_a, col_b = st.columns(2)
    with col_a:
        novo_codigo = st.text_input("Codigo", value=obter_valor(dados_imovel, "CODIGO"))
        novo_tipo = st.text_input("Tipo", value=obter_valor(dados_imovel, "TIPO"))
        novo_cidade = st.text_input("Cidade", value=obter_valor(dados_imovel, "CIDADE"))
        novo_bairro = st.text_input("Bairro", value=obter_valor(dados_imovel, "BAIRRO"))
        novo_endereco = st.text_input("Endereco", value=obter_valor(dados_imovel, "ENDERECO"))
    with col_b:
        novo_proprietario = st.text_input(
            "Proprietario", value=obter_valor(dados_imovel, "PROPRIETARIO")
        )
        novo_contato = st.text_input("Contato", value=obter_valor(dados_imovel, "CONTATO"))
        novo_status = st.text_input("Status", value=obter_valor(dados_imovel, "STATUS"))
        novo_exclus = st.text_input("Exclusividade", value=obter_valor(dados_imovel, "EXCLUS"))
        novo_data = st.text_input("Data", value=obter_valor(dados_imovel, "DATA"))

with tab2:
    col_d, col_e = st.columns(2)
    with col_d:
        novo_valor = st.text_input("Valor", value=obter_valor(dados_imovel, "VALOR"))
        novo_area_util = st.text_input(
            "Area Util", value=obter_valor(dados_imovel, "AREA UTIL")
        )
        novo_area_total = st.text_input(
            "Area Total", value=obter_valor(dados_imovel, "AREA TOTAL")
        )
        novo_andar = st.text_input("Andar", value=obter_valor(dados_imovel, "ANDAR"))
        novo_iptu = st.text_input("IPTU", value=obter_valor(dados_imovel, "IPTU"))
    with col_e:
        novo_dormitorios = st.text_input(
            "Dormitorios", value=obter_valor(dados_imovel, "DORMITORIOS")
        )
        novo_banheiros = st.text_input(
            "Banheiros", value=obter_valor(dados_imovel, "BANHEIROS")
        )
        novo_suites = st.text_input("Suites", value=obter_valor(dados_imovel, "SUITES"))
        novo_vagas = st.text_input("Vagas", value=obter_valor(dados_imovel, "VAGAS"))

with tab3:
    novo_titulo_1 = st.text_input("Titulo 1", value=obter_valor(dados_imovel, "TITULO 1"))
    novo_titulo_2 = st.text_input("Titulo 2", value=obter_valor(dados_imovel, "TITULO 2"))
    novo_titulo_3 = st.text_input("Titulo 3", value=obter_valor(dados_imovel, "TITULO 3"))
    novo_descricao = st.text_area(
        "Descricao", value=obter_valor(dados_imovel, "DESCRICAO"), height=150
    )
    novo_obs_extras = st.text_area(
        "Obs Extras", value=obter_valor(dados_imovel, "OBS EXTRAS"), height=100
    )

# Campos preservados da planilha
novo_link = obter_valor(dados_imovel, "LINK")
novo_foto = obter_valor(dados_imovel, "FOTO")

with tab4:
    st.markdown("### Geracao do Dossie PDF")
    st.write(
        "O sistema le os dados do Google Sheets e as fotos de "
        "FOTOS SELECIONADAS no Drive, gera o PDF "
        "e libera o download."
    )

    if st.button("Gerar Dossie PDF", type="primary", use_container_width=True):
        if not codigo_busca:
            st.warning("Informe o codigo do imovel na barra lateral.")
        else:
            with st.spinner("Gerando PDF..."):
                ok, resultado = executar_gerador_pdf(codigo_busca)

            if ok:
                st.success("PDF gerado com sucesso.")
                with open(resultado, "rb") as f:
                    st.download_button(
                        label="Baixar PDF",
                        data=f.read(),
                        file_name=Path(resultado).name,
                        mime="application/pdf",
                        use_container_width=True,
                    )
                st.caption(f"Arquivo gerado: {resultado}")
            else:
                st.error(resultado)

    if st.button("Gerar Posts", use_container_width=True):
        if not codigo_busca:
            st.warning("Informe o codigo do imovel.")
        else:
            with st.spinner("Gerando posts..."):
                ok, resultado = executar_gerador_posts(codigo_busca)
              
            if ok:
                st.success("Posts gerados com sucesso.")
                with open(resultado, "rb") as f:
                    st.download_button(
                        label="Baixar Posts (ZIP)",
                        data=f.read(),
                        file_name=Path(resultado).name,
                        mime="application/zip",
                        use_container_width=True,
                    )
            else:
                st.error(resultado)

st.markdown("---")

if st.button("Salvar Atualizacoes no Banco de Dados", type="primary", use_container_width=True):
    if not codigo_busca:
        st.warning("Busque um imovel primeiro antes de tentar salvar.")
    else:
        dados_para_salvar = [
            novo_codigo,        # A CODIGO
            novo_tipo,          # B TIPO
            novo_cidade,        # C CIDADE
            novo_bairro,        # D BAIRRO
            novo_endereco,      # E ENDERECO
            novo_proprietario,  # F PROPRIETARIO
            novo_contato,       # G CONTATO
            novo_valor,         # H VALOR
            novo_status,        # I STATUS
            novo_exclus,        # J EXCLUS
            novo_data,          # K DATA
            novo_link,          # L LINK
            novo_foto,          # M FOTO
            novo_dormitorios,   # N DORMITORIOS
            novo_banheiros,     # O BANHEIROS
            novo_suites,        # P SUITES
            novo_vagas,         # Q VAGAS
            novo_area_util,     # R AREA UTIL
            novo_area_total,    # S AREA TOTAL
            novo_andar,         # T ANDAR
            novo_iptu,          # U IPTU
            novo_titulo_1,      # V TITULO 1
            novo_titulo_2,      # W TITULO 2
            novo_titulo_3,      # X TITULO 3
            novo_descricao,     # Y DESCRICAO
            novo_obs_extras,    # Z OBS EXTRAS
        ]

        with st.spinner("Salvando alteracoes na planilha..."):
            if salvar_dados(codigo_busca, dados_para_salvar):
                st.success("Dados atualizados com sucesso na planilha.")
            else:
                st.error("Nao foi possivel encontrar a linha correspondente para atualizar.")
