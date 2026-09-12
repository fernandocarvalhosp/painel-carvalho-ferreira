# portal.py
# -*- coding: utf-8 -*-

import io
import urllib.parse
from pathlib import Path
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

st.set_page_config(
    page_title="Carvalho Ferreira | Consultoria Imobiliária",
    page_icon="CF",
    layout="wide",
    initial_sidebar_state="collapsed",
)

SCOPES_DRIVE = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]

SPREADSHEET_ID = "1nVEpOZFYFKcq0MXtOwxn22nqxafmJBHnf6zhHQlyT8w"
NOME_ABA = "Imoveis"

st.markdown(
    """
    <style>
    [data-testid="stSidebarNav"] { display: none; }
    header { visibility: hidden; }
    
    .stApp {
        background-color: #0b0e14;
        color: #e6edf3;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 4rem;
        max-width: 1100px;
    }

    .brand-subtitle {
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 3px;
        color: #8b949e;
        margin-top: 6px;
        margin-bottom: 30px;
        text-transform: uppercase;
        text-align: center;
    }

    /* Transforma os botões da barra superior em texto puro elegante com linhas finas */
    div.stButton > button {
        background-color: transparent !important;
        color: #8b949e !important;
        border: none !important;
        border-radius: 0px !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        letter-spacing: 2px !important;
        box-shadow: none !important;
        transition: color 0.2s ease !important;
        padding: 0px !important;
    }
    
    div.stButton > button:hover {
        color: #f0f6fc !important;
        background-color: transparent !important;
        border: none !important;
    }

    .imovel-card {
        background-color: #11161d;
        border: 1px solid #21262d;
        border-radius: 8px;
        padding: 14px;
        margin-bottom: 24px;
        transition: border-color 0.2s ease;
    }
    .imovel-card:hover {
        border-color: #30363d;
    }

    .imovel-preco {
        font-size: 1.15rem;
        font-weight: 600;
        color: #f0f6fc;
        margin-top: 10px;
        margin-bottom: 4px;
    }

    .imovel-detalhes {
        font-size: 0.85rem;
        color: #8b949e;
        margin-bottom: 12px;
    }

    .stLinkButton > button {
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 500;
        background-color: #161b22;
        color: #c9d1d9;
        border: 1px solid #30363d;
        width: 100%;
        transition: all 0.2s ease;
    }
    .stLinkButton > button:hover {
        background-color: #21262d;
        border-color: #8b949e;
        color: #ffffff;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

@st.cache_resource
def conectar_google():
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
        else:
            creds_dict = dict(st.secrets["google_credentials"])
        
        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=SCOPES_DRIVE
        )
        drive = build("drive", "v3", credentials=creds)
        sheets = build("sheets", "v4", credentials=creds)
        return drive, sheets
    except Exception as e:
        st.error(f"Erro na conexão: {e}")
        st.stop()

def normalizar(texto):
    if not texto:
        return ""
    return " ".join(str(texto).strip().upper().split())

@st.cache_data(ttl=120)
def carregar_portal_imoveis():
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
            
            publicar = normalizar(dados.get("PUBLICAR NO PORTAL", ""))
            if publicar != "SIM":
                continue

            destaque_val = normalizar(dados.get("DESTAQUE", ""))
            is_destaque = (destaque_val == "SIM")

            codigo = dados.get("CODIGO") or dados.get("CÓDIGO") or row[0]
            titulo = dados.get("TITULO 1") or dados.get("TITULO") or ""
            tipo = dados.get("TIPO") or ""
            bairro = dados.get("BAIRRO") or ""
            cidade = dados.get("CIDADE") or ""
            valor = dados.get("VALOR") or "Sob consulta"
            quartos = dados.get("QUARTOS") or dados.get("DORMS") or ""
            vagas = dados.get("VAGAS") or ""
            area = dados.get("AREA UTIL") or dados.get("ÁREA ÚTIL") or dados.get("METRAGEM") or ""
            
            imoveis.append({
                "codigo": codigo,
                "titulo": titulo,
                "tipo": tipo,
                "bairro": bairro,
                "cidade": cidade,
                "valor": valor,
                "quartos": quartos,
                "vagas": vagas,
                "area": area,
                "destaque": is_destaque,
            })
            
        return imoveis
    except Exception as e:
        st.error(f"Erro ao carregar o portal: {e}")
        return []

@st.cache_data(ttl=600)
def obter_miniatura_drive(codigo):
    try:
        drive, _ = conectar_google()
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

        res_sub = drive.files().list(q=f"'{id_imovel}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false", fields="files(id, name)").execute()
        subpastas = res_sub.get("files", [])
        
        id_fotos = id_imovel
        for sub in subpastas:
            if "MINIATURA" in sub["name"].upper():
                id_fotos = sub["id"]
                break

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

if "cat" not in st.session_state:
    st.session_state["cat"] = "DESTAQUES"

col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
with col_l2:
    logo_path = Path("marca/logo.png")
    if logo_path.exists():
        st.image(str(logo_path), use_container_width=True)
    else:
        st.markdown(
            """
            <div style="text-align: center;">
                <h1 style="font-size: 1.8rem; font-weight: 300; letter-spacing: 4px; color: #f0f6fc; margin: 0;">CARVALHO FERREIRA</h1>
            </div>
            """,
            unsafe_allow_html=True
        )
    st.markdown('<div class="brand-subtitle">Consultoria Imobiliária</div>', unsafe_allow_html=True)

cols_nav = st.columns(5)
categorias = ["DESTAQUES", "CASAS", "APARTAMENTOS", "TERRENOS", "COMERCIAIS"]

for i, cat_nome in enumerate(categorias):
    with cols_nav[i]:
        if st.button(cat_nome, key=f"nav_{cat_nome}", use_container_width=True):
            st.session_state["cat"] = cat_nome

st.markdown("<br>", unsafe_allow_html=True)

busca_codigo = st.text_input("Busca rápida por código do imóvel", placeholder="Digite o código (ex: CF001)")

lista_imoveis = carregar_portal_imoveis()

if not lista_imoveis:
    st.info("Nenhum imóvel disponível no momento.")
    st.stop()

imoveis_exibidos = []
cat_ativa = st.session_state["cat"]

if busca_codigo:
    termo = normalizar(busca_codigo)
    imoveis_exibidos = [i for i in lista_imoveis if termo in normalizar(i["codigo"])]
    st.markdown(f"### Resultado da busca: {busca_codigo}")
else:
    if cat_ativa == "DESTAQUES":
        imoveis_exibidos = [i for i in lista_imoveis if i["destaque"]]
        st.markdown("### Destaques Selecionados")
    elif cat_ativa == "CASAS":
        imoveis_exibidos = [i for i in lista_imoveis if "CASA" in normalizar(i["tipo"])]
        st.markdown("### Casas Disponíveis")
    elif cat_ativa == "APARTAMENTOS":
        imoveis_exibidos = [i for i in lista_imoveis if "APARTAMENTO" in normalizar(i["tipo"]) or "APTO" in normalizar(i["tipo"])]
        st.markdown("### Apartamentos Disponíveis")
    elif cat_ativa == "TERRENOS":
        imoveis_exibidos = [i for i in lista_imoveis if "TERRENO" in normalizar(i["tipo"]) or "LOTE" in normalizar(i["tipo"])]
        st.markdown("### Terrenos e Lotes")
    elif cat_ativa == "COMERCIAIS":
        imoveis_exibidos = [i for i in lista_imoveis if "COMERCIAL" in normalizar(i["tipo"]) or "SALA" in normalizar(i["tipo"]) or "GALPÃO" in normalizar(i["tipo"])]
        st.markdown("### Imóveis Comerciais")

st.markdown("---")

if not imoveis_exibidos:
    st.info("Nenhum imóvel encontrado nesta categoria ou busca.")
else:
    imoveis_pagina = imoveis_exibidos[:6]
    
    colunas = st.columns(3)
    for indice, imovel in enumerate(imoveis_pagina):
        col = colunas[indice % 3]
        with col:
            st.markdown('<div class="imovel-card">', unsafe_allow_html=True)
            
            foto = obter_miniatura_drive(imovel["codigo"])
            if foto:
                st.image(foto, use_container_width=True)
            else:
                st.markdown("🖼️ *Em breve*")
                
            st.markdown(f"**{imovel['tipo']}** • {imovel['bairro']}")
            st.markdown(f'<div class="imovel-preco">{imovel["valor"]}</div>', unsafe_allow_html=True)
            
            detalhes_parts = []
            if imovel["area"]:
                detalhes_parts.append(f"{imovel['area']} m²")
            if imovel["quartos"]:
                detalhes_parts.append(f"{imovel['quartos']} dorm.")
            if imovel["vagas"]:
                detalhes_parts.append(f"{imovel['vagas']} vaga(s)")
                
            st.markdown(f'<div class="imovel-detalhes">{" · ".join(detalhes_parts)}</div>', unsafe_allow_html=True)
            
            msg = f"Olá! Gostaria de mais informações sobre o imóvel {imovel['codigo']} visto no portal."
            link_zap = f"https://wa.me/5512997777777?text={urllib.parse.quote(msg)}"
            st.link_button("Falar com Consultor", link_zap, use_container_width=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
    if len(imoveis_exibidos) > 6:
        st.caption(f"Mostrando 6 de {len(imoveis_exibidos)} imóveis nesta categoria.")
