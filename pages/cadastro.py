# -*- coding: utf-8 -*-

import sys
import os
from pathlib import Path

# =========================================================
# RAIZ DO PROJETO
# =========================================================

raiz_projeto = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

if raiz_projeto not in sys.path:
    sys.path.insert(0, raiz_projeto)

import importlib
import streamlit as st

from google.oauth2 import service_account
from googleapiclient.discovery import build

import gerador_pdf


# =========================================================
# IMPORTAÇÃO DOS MÓDULOS
# =========================================================

erro_import_dossie = None

try:
    import gerador_dossie
except Exception as e:
    gerador_dossie = None
    erro_import_dossie = str(e)


try:
    import gerar_posts
except Exception:
    gerar_posts = None


try:
    import tratador_nuvem
except Exception:
    tratador_nuvem = None


# =========================================================
# CONFIGURAÇÃO STREAMLIT
# =========================================================

st.set_page_config(
    page_title="Carvalho Ferreira | Painel",
    layout="wide"
)


# =========================================================
# SENHA
# =========================================================

def verificar_senha():

    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    if st.session_state["autenticado"]:
        return True

    st.subheader("🔒 Acesso Restrito - Painel Carvalho Ferreira")

    senha_digitada = st.text_input(
        "Digite a senha de acesso:",
        type="password"
    )

    if st.button("Entrar"):

        if senha_digitada == st.secrets["passwords"]["senha_acesso"]:

            st.session_state["autenticado"] = True
            st.rerun()

        else:

            st.error("Senha incorreta. Tente novamente.")

    return False


if not verificar_senha():
    st.stop()


# =========================================================
# CONFIGURAÇÕES GOOGLE
# =========================================================

SCOPES_SHEETS = [
    "https://www.googleapis.com/auth/spreadsheets"
]

SPREADSHEET_ID = (
    "1nVEpOZFYFKcq0MXtOwxn22nqxafmJBHnf6zhHQlyT8w"
)

NOME_ABA = "Imoveis"


SCOPES_DRIVE = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]


# =========================================================
# CONEXÃO SHEETS
# =========================================================

@st.cache_resource
def conectar_sheets():

    creds_dict = dict(
        st.secrets["google_credentials"]
    )

    creds = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=SCOPES_SHEETS
    )

    return build(
        "sheets",
        "v4",
        credentials=creds
    )


# =========================================================
# CONEXÃO DRIVE
# =========================================================

@st.cache_resource
def conectar_drive():

    try:

        creds_dict = dict(
            st.secrets["google_credentials"]
        )

        creds = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=SCOPES_DRIVE
        )

        return build(
            "drive",
            "v3",
            credentials=creds
        )

    except Exception:

        return None


# =========================================================
# NORMALIZAÇÃO
# =========================================================

def normalizar(texto):

    if not texto:
        return ""

    return " ".join(
        str(texto)
        .strip()
        .upper()
        .split()
    )


# =========================================================
# LEITURA DE UM IMÓVEL
# =========================================================

def buscar_imovel(codigo):

    try:

        service = conectar_sheets()

        result = (
            service.spreadsheets()
            .values()
            .get(
                spreadsheetId=SPREADSHEET_ID,
                range=f"'{NOME_ABA}'!A:ZZ"
            )
            .execute()
        )

        rows = result.get("values", [])

        if not rows:
            return None

        cabecalho = [
            normalizar(h)
            for h in rows[0]
        ]

        codigo_busca = normalizar(codigo)

        for row in rows[1:]:

            if not row:
                continue

            while len(row) < len(cabecalho):
                row.append("")

            if normalizar(row[0]) == codigo_busca:

                return {
                    cabecalho[i]: row[i]
                    for i in range(len(cabecalho))
                }

        return None

    except Exception as e:

        st.error(
            f"Erro ao conectar na planilha: {e}"
        )

        return None


# =========================================================
# CONVERTE NÚMERO DA COLUNA
# =========================================================

def numero_para_coluna(numero):

    coluna = ""

    while numero > 0:

        numero, resto = divmod(
            numero - 1,
            26
        )

        coluna = chr(
            65 + resto
        ) + coluna

    return coluna


# =========================================================
# SALVAR DADOS
#
# IMPORTANTE:
# Agora salva por NOME DO CABEÇALHO.
# Não depende mais da posição fixa das colunas.
# =========================================================

def salvar_dados(codigo, novos_dados):

    try:

        service = conectar_sheets()

        result = (
            service.spreadsheets()
            .values()
            .get(
                spreadsheetId=SPREADSHEET_ID,
                range=f"'{NOME_ABA}'!A:ZZ"
            )
            .execute()
        )

        rows = result.get("values", [])

        if not rows:
            return False

        cabecalho_original = rows[0]

        cabecalho_normalizado = [
            normalizar(h)
            for h in cabecalho_original
        ]

        codigo_normalizado = normalizar(codigo)

        linha_encontrada = None

        for indice, row in enumerate(rows[1:], start=2):

            if not row:
                continue

            if normalizar(row[0]) == codigo_normalizado:

                linha_encontrada = indice
                break

        if linha_encontrada is None:
            return False

        # -------------------------------------------------
        # Dicionário:
        # nome da coluna -> novo valor
        # -------------------------------------------------

        dados_por_coluna = {}

        for chave, valor in novos_dados.items():

            chave_normalizada = normalizar(chave)

            if chave_normalizada in cabecalho_normalizado:

                indice = cabecalho_normalizado.index(
                    chave_normalizada
                )

                dados_por_coluna[indice] = (
                    "" if valor is None else str(valor)
                )

        if not dados_por_coluna:
            return False

        # -------------------------------------------------
        # Fazemos apenas atualizações pontuais.
        #
        # Isso é fundamental:
        # colunas novas que o cadastro não conhece
        # permanecem intactas.
        # -------------------------------------------------

        data = []

        for indice, valor in dados_por_coluna.items():

            coluna = numero_para_coluna(
                indice + 1
            )

            data.append(
                {
                    "range": (
                        f"'{NOME_ABA}'!"
                        f"{coluna}{linha_encontrada}"
                    ),
                    "values": [[valor]],
                }
            )

        service.spreadsheets().values().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={
                "valueInputOption": "RAW",
                "data": data,
            }
        ).execute()

        return True

    except Exception as e:

        st.error(
            f"Erro ao salvar na planilha: {e}"
        )

        return False


# =========================================================
# OBTER VALOR
# =========================================================

def obter_valor(dados_imovel, chave):

    if not dados_imovel:
        return ""

    valor = dados_imovel.get(
        normalizar(chave),
        ""
    )

    if valor is None:
        return ""

    return str(valor)


# =========================================================
# CARREGAR DADOS NA INTERFACE
# =========================================================

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

        "f_condominio": "CONDOMINIO",

        "f_dormitorios": "DORMITORIOS",

        "f_banheiros": "BANHEIROS",

        "f_suites": "SUITES",

        "f_vagas": "VAGAS",

        "f_titulo1": "TITULO 1",

        "f_titulo2": "TITULO 2",

        "f_titulo3": "TITULO 3",

        "f_descricao": "DESCRICAO",

        "f_obs": "OBS EXTRAS",

        "f_legenda1": "LEGENDA 01",

        "f_legenda2": "LEGENDA 02",

        # NOVOS CAMPOS DO PORTAL
        "f_publicar_portal": "PUBLICAR NO PORTAL",

        "f_destaque": "DESTAQUE",
    }

    for campo, chave in campos.items():

        valor = obter_valor(
            dados,
            chave
        )

        st.session_state[campo] = valor


# =========================================================
# GERADOR PDF
# =========================================================

def executar_gerador_pdf(codigo_imovel):

    try:

        importlib.reload(
            gerador_pdf
        )

        pdf_bytes = gerador_pdf.gerar_pdf(
            codigo_imovel
        )

        if (
            pdf_bytes
            and isinstance(
                pdf_bytes,
                (bytes, bytearray)
            )
            and len(pdf_bytes) > 10000
        ):

            return True, pdf_bytes

        return False, "Falha ao gerar o PDF."

    except Exception as e:

        return False, (
            f"Erro ao gerar PDF: {e}"
        )


# =========================================================
# GERADOR DOSSIÊ
# =========================================================

def executar_gerador_dossie(
    codigo_imovel,
    dados_imovel
):

    if gerador_dossie is None:

        detalhe = (
            f" ({erro_import_dossie})"
            if erro_import_dossie
            else ""
        )

        return (
            False,
            None,
            {
                "mensagem":
                "Módulo gerador_dossie "
                f"não pôde ser carregado{detalhe}."
            }
        )

    try:

        importlib.reload(
            gerador_dossie
        )

        pdf_bytes, resultado = (
            gerador_dossie.gerar_dossie_bytes(
                codigo_imovel=codigo_imovel,
                dados_imovel=dados_imovel
            )
        )

        if (
            pdf_bytes
            and isinstance(
                pdf_bytes,
                (bytes, bytearray)
            )
            and len(pdf_bytes) > 100
        ):

            return True, pdf_bytes, resultado

        return (
            False,
            None,
            resultado
            if isinstance(resultado, dict)
            else {
                "mensagem":
                "Falha ao gerar o Dossiê."
            }
        )

    except Exception as e:

        return (
            False,
            None,
            {
                "mensagem":
                f"Erro ao gerar Dossiê Documental: {e}"
            }
        )


# =========================================================
# GERADOR DE POSTS
# =========================================================

def executar_gerador_posts(codigo_imovel):

    if gerar_posts is None:

        return (
            False,
            "Modulo gerar_posts nao encontrado."
        )

    try:

        importlib.reload(
            gerar_posts
        )

        resultado = (
            gerar_posts.gerar_posts(
                codigo_imovel
            )
        )

        if (
            isinstance(
                resultado,
                (bytes, bytearray)
            )
            and len(resultado) > 1000
        ):

            return True, resultado

        if (
            isinstance(resultado, str)
            and Path(resultado).exists()
        ):

            return True, resultado

        return (
            False,
            "Falha ao gerar os posts."
        )

    except Exception as e:

        return (
            False,
            f"Erro ao gerar posts: {e}"
        )


# =========================================================
# TRATAMENTO DE FOTOS
# =========================================================

def executar_tratador_fotos(
    codigo_imovel
):

    if tratador_nuvem is None:

        return (
            False,
            "Modulo tratador_nuvem nao encontrado."
        )

    try:

        importlib.reload(
            tratador_nuvem
        )

        service_drive = conectar_drive()

        if service_drive is None:

            return (
                False,
                "Não foi possível conectar ao Google Drive."
            )

        logo_bytes = None

        logo_path = Path(
            "marca/logo.png"
        )

        if logo_path.exists():

            with open(
                logo_path,
                "rb"
            ) as f:

                logo_bytes = f.read()

        with st.spinner(
            f"Processando fotos do imóvel "
            f"{codigo_imovel}..."
        ):

            if hasattr(
                tratador_nuvem,
                "tratar"
            ):

                resultado = (
                    tratador_nuvem.tratar(
                        codigo_imovel,
                        service=service_drive,
                        logo_bytes=logo_bytes
                    )
                )

            elif hasattr(
                tratador_nuvem,
                "tratar_fotos"
            ):

                resultado = (
                    tratador_nuvem.tratar_fotos(
                        codigo_imovel,
                        service=service_drive,
                        logo_bytes=logo_bytes
                    )
                )

            else:

                return (
                    False,
                    "Função de tratamento não encontrada."
                )

        if not resultado:

            return (
                False,
                "Nenhuma foto foi tratada "
                "(pasta vazia ou não localizada)."
            )

        if isinstance(
            resultado,
            bytes
        ):

            zip_bytes = resultado

        elif isinstance(
            resultado,
            bytearray
        ):

            zip_bytes = bytes(
                resultado
            )

        elif hasattr(
            resultado,
            "getvalue"
        ):

            zip_bytes = resultado.getvalue()

        elif hasattr(
            resultado,
            "read"
        ):

            resultado.seek(0)
            zip_bytes = resultado.read()

        else:

            return (
                False,
                "O tratamento não retornou "
                "um ZIP válido."
            )

        if not zip_bytes:

            return (
                False,
                "O ZIP gerado está vazio."
            )

        return True, zip_bytes

    except Exception as e:

        return (
            False,
            f"Erro no tratamento: {e}"
        )


# =========================================================
# SESSION STATE
# =========================================================

for var, val in [

    ("codigo_busca", ""),

    ("dados_imovel", None),

    ("confirmar_tratamento", False),

    ("fotos_tratadas_zip", None),

    (
        "fotos_tratadas_nome",
        "fotos_tratadas.zip"
    ),

    ("dossie_bytes", None),

    ("dossie_nome", "dossie.pdf"),

    ("pdf_bytes", None),

    ("pdf_nome", "imovel.pdf"),

]:

    if var not in st.session_state:

        st.session_state[var] = val


# =========================================================
# TÍTULO
# =========================================================

st.title(
    "Carvalho Ferreira"
)

st.caption(
    "Painel de gestão e geração de materiais"
)


# =========================================================
# BUSCA DO IMÓVEL
# =========================================================

st.markdown(
    "### Seleção de Imóvel"
)

col_busca1, col_busca2 = st.columns(
    [3, 1]
)


with col_busca1:

    codigo_input = st.text_input(
        "Código do Imóvel",
        value=st.session_state[
            "codigo_busca"
        ],
        placeholder="Ex: CF003",
        label_visibility="collapsed",
        key="campo_codigo_principal",
    )


with col_busca2:

    buscar = st.button(
        "Buscar",
        use_container_width=True,
        type="primary",
        key="btn_buscar_principal"
    )


codigo_digitado = (
    codigo_input or ""
).strip().upper()


if (
    buscar
    and codigo_digitado
) or (
    codigo_digitado
    and codigo_digitado
    != st.session_state["codigo_busca"]
):

    st.session_state[
        "codigo_busca"
    ] = codigo_digitado

    if codigo_digitado:

        with st.spinner(
            "Buscando dados na planilha..."
        ):

            dados_encontrados = (
                buscar_imovel(
                    codigo_digitado
                )
            )

        if dados_encontrados is None:

            st.session_state[
                "dados_imovel"
            ] = None

            st.warning(
                f"Registro {codigo_digitado} "
                "nao localizado."
            )

        else:

            st.session_state[
                "dados_imovel"
            ] = dados_encontrados

            carregar_dados_na_interface(
                dados_encontrados
            )

    st.rerun()


codigo_busca = (
    st.session_state
    .get("codigo_busca", "")
    .strip()
    .upper()
)

dados_imovel = (
    st.session_state
    .get("dados_imovel", None)
)


if (
    codigo_busca
    and dados_imovel
):

    st.success(
        f"Imóvel **{codigo_busca}** "
        "carregado com sucesso!"
    )


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.markdown(
    "### Materiais & Ações"
)

st.sidebar.markdown("---")


# =========================================================
# MATERIAIS
# =========================================================

if codigo_busca:

    if st.sidebar.button(
        "📂 Materiais / Compartilhar",
        use_container_width=True,
        key="btn_materiais_atalho"
    ):

        st.switch_page(
            "pages/materiais.py"
        )

else:

    st.sidebar.button(
        "📂 Materiais / Compartilhar",
        use_container_width=True,
        disabled=True,
        help="Busque um imóvel primeiro"
    )


# =========================================================
# PDF
# =========================================================

if st.sidebar.button(
    "Gerar PDF",
    use_container_width=True,
    key="btn_pdf"
):

    if not codigo_busca:

        st.sidebar.error(
            "Informe o codigo."
        )

    else:

        with st.spinner(
            "Gerando PDF..."
        ):

            ok, res = (
                executar_gerador_pdf(
                    codigo_busca
                )
            )

        if ok:

            st.session_state[
                "pdf_bytes"
            ] = res

            st.session_state[
                "pdf_nome"
            ] = f"{codigo_busca}.pdf"

            st.sidebar.success(
                "PDF gerado."
            )

        else:

            st.sidebar.error(
                res
            )


if st.session_state.get(
    "pdf_bytes"
):

    st.sidebar.download_button(

        "Baixar PDF",

        data=st.session_state[
            "pdf_bytes"
        ],

        file_name=st.session_state.get(
            "pdf_nome",
            "dossie.pdf"
        ),

        mime="application/pdf",

        use_container_width=True,

        key="dl_pdf_sidebar",
    )


# =========================================================
# POSTS
# =========================================================

if st.sidebar.button(
    "Gerar Posts",
    use_container_width=True,
    key="btn_posts"
):

    if not codigo_busca:

        st.sidebar.error(
            "Informe o codigo."
        )

    else:

        with st.spinner(
            "Gerando posts..."
        ):

            ok, res = (
                executar_gerador_posts(
                    codigo_busca
                )
            )

        if ok:

            st.session_state[
                "posts_resultado"
            ] = res

            st.sidebar.success(
                "Posts gerados."
            )

        else:

            st.sidebar.error(
                res
            )


if (
    st.session_state.get(
        "posts_resultado"
    )
    is not None
):

    posts_res = (
        st.session_state[
            "posts_resultado"
        ]
    )

    if isinstance(
        posts_res,
        (bytes, bytearray)
    ):

        st.sidebar.download_button(

            "Baixar Posts (ZIP)",

            data=posts_res,

            file_name=(
                f"posts_{codigo_busca}.zip"
            ),

            mime="application/zip",

            use_container_width=True,

            key="dl_posts_bytes",
        )

    else:

        caminho = Path(
            str(posts_res)
        )

        if caminho.exists():

            with open(
                caminho,
                "rb"
            ) as f:

                st.sidebar.download_button(

                    "Baixar Posts (ZIP)",

                    data=f.read(),

                    file_name=caminho.name,

                    mime="application/zip",

                    use_container_width=True,

                    key="dl_posts_path",
                )


# =========================================================
# TRATAR FOTOS
# =========================================================

if st.sidebar.button(
    "Tratar fotos",
    use_container_width=True,
    key="btn_tratar"
):

    if not codigo_busca:

        st.sidebar.error(
            "Informe o codigo."
        )

    else:

        st.session_state[
            "confirmar_tratamento"
        ] = True


if st.session_state.get(
    "confirmar_tratamento"
):

    st.sidebar.warning(
        "O tratamento pode demorar "
        "alguns minutos."
    )

    a1, a2 = st.sidebar.columns(2)

    with a1:

        if st.button(
            "Sim",
            use_container_width=True,
            key="trat_sim"
        ):

            st.session_state[
                "confirmar_tratamento"
            ] = False

            ok, resultado = (
                executar_tratador_fotos(
                    codigo_busca
                )
            )

            if ok:

                st.session_state[
                    "fotos_tratadas_zip"
                ] = resultado

                st.session_state[
                    "fotos_tratadas_nome"
                ] = (
                    f"{codigo_busca}"
                    "_fotos_tratadas.zip"
                )

                st.sidebar.success(
                    "Fotos tratadas com sucesso."
                )

            else:

                st.session_state[
                    "fotos_tratadas_zip"
                ] = None

                st.sidebar.warning(
                    str(resultado)
                )

    with a2:

        if st.button(
            "Nao",
            use_container_width=True,
            key="trat_nao"
        ):

            st.session_state[
                "confirmar_tratamento"
            ] = False


if st.session_state.get(
    "fotos_tratadas_zip"
):

    st.sidebar.markdown(
        "### Fotos tratadas"
    )

    st.sidebar.download_button(

        "Baixar Fotos Tratadas",

        data=st.session_state[
            "fotos_tratadas_zip"
        ],

        file_name=st.session_state.get(
            "fotos_tratadas_nome",
            f"{codigo_busca}_fotos_tratadas.zip"
        ),

        mime="application/zip",

        use_container_width=True,

        type="primary",

        key="dl_fotos_tratadas",
    )


# =========================================================
# DOSSIÊ DOCUMENTAL
# =========================================================

st.sidebar.markdown("---")


if st.sidebar.button(
    "📄 Gerar Dossiê Documental",
    use_container_width=True,
    key="btn_dossie"
):

    if not codigo_busca:

        st.sidebar.error(
            "Informe o código do imóvel primeiro."
        )

    else:

        with st.spinner(
            "Consolidando Dossiê Documental PDF..."
        ):

            ok, pdf_bytes, info_res = (
                executar_gerador_dossie(
                    codigo_busca,
                    dados_imovel
                )
            )

        if ok:

            st.session_state[
                "dossie_bytes"
            ] = pdf_bytes

            st.session_state[
                "dossie_nome"
            ] = (
                info_res.get(
                    "nome_arquivo",
                    f"Dossie_{codigo_busca}.pdf"
                )
            )

            st.sidebar.success(
                info_res.get(
                    "mensagem",
                    "Dossiê gerado com sucesso!"
                )
            )

        else:

            st.sidebar.error(
                info_res.get(
                    "mensagem",
                    "Erro ao gerar Dossiê."
                )
                if isinstance(
                    info_res,
                    dict
                )
                else str(info_res)
            )


if st.session_state.get(
    "dossie_bytes"
):

    st.sidebar.download_button(

        "📥 Baixar Dossiê (PDF)",

        data=st.session_state[
            "dossie_bytes"
        ],

        file_name=st.session_state.get(
            "dossie_nome",
            f"Dossie_{codigo_busca}.pdf"
        ),

        mime="application/pdf",

        use_container_width=True,

        type="primary",

        key="dl_dossie_sidebar",
    )


# =========================================================
# ABAS DO CADASTRO
# =========================================================

tab1, tab2, tab3 = st.tabs(
    [
        "Identificação",
        "Dados Técnicos",
        "Divulgação"
    ]
)


# =========================================================
# IDENTIFICAÇÃO
# =========================================================

with tab1:

    col_a, col_b = st.columns(2)

    with col_a:

        novo_codigo = st.text_input(
            "Código",
            key="f_codigo"
        )

        novo_tipo = st.text_input(
            "Tipo",
            key="f_tipo"
        )

        novo_cidade = st.text_input(
            "Cidade",
            key="f_cidade"
        )

        novo_bairro = st.text_input(
            "Bairro",
            key="f_bairro"
        )

        novo_endereco = st.text_input(
            "Endereço",
            key="f_endereco"
        )

    with col_b:

        novo_proprietario = st.text_input(
            "Proprietário",
            key="f_proprietario"
        )

        novo_contato = st.text_input(
            "Contato",
            key="f_contato"
        )

        novo_status = st.text_input(
            "Status",
            key="f_status"
        )

        novo_exclus = st.text_input(
            "Exclusividade",
            key="f_exclus"
        )

        novo_data = st.text_input(
            "Data",
            key="f_data"
        )


# =========================================================
# DADOS TÉCNICOS
# =========================================================

with tab2:

    col_d, col_e = st.columns(2)

    with col_d:

        novo_valor = st.text_input(
            "Valor",
            key="f_valor"
        )

        novo_area_util = st.text_input(
            "Área Útil",
            key="f_area_util"
        )

        novo_area_total = st.text_input(
            "Área Total",
            key="f_area_total"
        )

        novo_andar = st.text_input(
            "Andar",
            key="f_andar"
        )

        novo_iptu = st.text_input(
            "IPTU",
            key="f_iptu"
        )

        novo_condominio = st.text_input(
            "Condomínio",
            key="f_condominio"
        )

    with col_e:

        novo_dormitorios = st.text_input(
            "Dormitórios",
            key="f_dormitorios"
        )

        novo_banheiros = st.text_input(
            "Banheiros",
            key="f_banheiros"
        )

        novo_suites = st.text_input(
            "Suítes",
            key="f_suites"
        )

        novo_vagas = st.text_input(
            "Vagas",
            key="f_vagas"
        )


# =========================================================
# DIVULGAÇÃO
# =========================================================

with tab3:

    novo_titulo_1 = st.text_input(
        "Título 1",
        key="f_titulo1"
    )

    novo_titulo_2 = st.text_input(
        "Título 2",
        key="f_titulo2"
    )

    novo_titulo_3 = st.text_input(
        "Título 3",
        key="f_titulo3"
    )

    novo_descricao = st.text_area(
        "Descrição",
        height=150,
        key="f_descricao"
    )

    novo_obs_extras = st.text_area(
        "Obs Extras",
        height=100,
        key="f_obs"
    )

    st.markdown("---")

    st.markdown(
        "### 📝 Legendas para Redes Sociais"
    )

    nova_legenda_1 = st.text_area(
        "Legenda 1",
        height=130,
        key="f_legenda1"
    )

    nova_legenda_2 = st.text_area(
        "Legenda 2",
        height=130,
        key="f_legenda2"
    )

    # -----------------------------------------------------
    # CONTROLES DO PORTAL PÚBLICO
    # -----------------------------------------------------

    st.markdown("---")

    st.markdown(
        "### 🌐 Portal Público"
    )

    publicar_portal_atual = (
        obter_valor(
            dados_imovel,
            "PUBLICAR NO PORTAL"
        )
    )

    destaque_atual = (
        obter_valor(
            dados_imovel,
            "DESTAQUE"
        )
    )

    opcoes_publicacao = [
        "",
        "SIM",
        "NAO",
    ]

    if (
        publicar_portal_atual
        and publicar_portal_atual
        not in opcoes_publicacao
    ):

        opcoes_publicacao.insert(
            0,
            publicar_portal_atual
        )

    indice_publicacao = 0

    if publicar_portal_atual:

        try:

            indice_publicacao = (
                opcoes_publicacao.index(
                    publicar_portal_atual.upper()
                )
            )

        except ValueError:

            indice_publicacao = 0


    novo_publicar_portal = st.selectbox(
        "Publicar no Portal",
        options=opcoes_publicacao,
        index=indice_publicacao,
        key="f_publicar_portal"
    )


    opcoes_destaque = [
        "",
        "SIM",
        "NAO",
    ]

    if (
        destaque_atual
        and destaque_atual
        not in opcoes_destaque
    ):

        opcoes_destaque.insert(
            0,
            destaque_atual
        )

    indice_destaque = 0

    if destaque_atual:

        try:

            indice_destaque = (
                opcoes_destaque.index(
                    destaque_atual.upper()
                )
            )

        except ValueError:

            indice_destaque = 0


    novo_destaque = st.selectbox(
        "Destaque",
        options=opcoes_destaque,
        index=indice_destaque,
        key="f_destaque"
    )

    st.caption(
        "O destaque só deve ser considerado quando "
        "o imóvel estiver marcado para publicação no portal."
    )


# =========================================================
# CAMPOS AUXILIARES
# =========================================================

novo_link = obter_valor(
    dados_imovel,
    "LINK"
)

novo_foto = obter_valor(
    dados_imovel,
    "FOTO"
)


# =========================================================
# SALVAR
# =========================================================

st.markdown("---")


if st.button(
    "Salvar atualizações",
    type="primary",
    use_container_width=True,
    key="btn_salvar"
):

    if not codigo_busca:

        st.warning(
            "Busque um imóvel primeiro."
        )

    else:

        # -------------------------------------------------
        # IMPORTANTE:
        #
        # Não montamos mais uma lista fixa.
        # Agora cada valor é associado ao nome da coluna.
        #
        # Isso protege as novas colunas da planilha.
        # -------------------------------------------------

        dados_para_salvar = {

            "CODIGO":
                novo_codigo,

            "TIPO":
                novo_tipo,

            "CIDADE":
                novo_cidade,

            "BAIRRO":
                novo_bairro,

            "ENDERECO":
                novo_endereco,

            "PROPRIETARIO":
                novo_proprietario,

            "CONTATO":
                novo_contato,

            "VALOR":
                novo_valor,

            "STATUS":
                novo_status,

            "EXCLUS":
                novo_exclus,

            "DATA":
                novo_data,

            "LINK":
                novo_link,

            "FOTO":
                novo_foto,

            "DORMITORIOS":
                novo_dormitorios,

            "BANHEIROS":
                novo_banheiros,

            "SUITES":
                novo_suites,

            "VAGAS":
                novo_vagas,

            "AREA UTIL":
                novo_area_util,

            "AREA TOTAL":
                novo_area_total,

            "ANDAR":
                novo_andar,

            "IPTU":
                novo_iptu,

            "CONDOMINIO":
                novo_condominio,

            "TITULO 1":
                novo_titulo_1,

            "TITULO 2":
                novo_titulo_2,

            "TITULO 3":
                novo_titulo_3,

            "DESCRICAO":
                novo_descricao,

            "OBS EXTRAS":
                novo_obs_extras,

            "LEGENDA 01":
                nova_legenda_1,

            "LEGENDA 02":
                nova_legenda_2,

            # NOVOS CAMPOS
            "PUBLICAR NO PORTAL":
                novo_publicar_portal,

            "DESTAQUE":
                novo_destaque,
        }


        with st.spinner(
            "Salvando..."
        ):

            sucesso = salvar_dados(
                codigo_busca,
                dados_para_salvar
            )


        if sucesso:

            st.success(
                "Dados atualizados com sucesso!"
            )

            # Atualiza imediatamente os dados
            # em memória para a interface.

            dados_atualizados = (
                buscar_imovel(
                    codigo_busca
                )
            )

            if dados_atualizados:

                st.session_state[
                    "dados_imovel"
                ] = dados_atualizados

                carregar_dados_na_interface(
                    dados_atualizados
                )

        else:

            st.error(
                "Nao foi possivel salvar."
            )