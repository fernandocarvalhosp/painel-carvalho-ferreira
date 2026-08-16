import io
import os
import zipfile
import tempfile
from pathlib import Path
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseDownload
from weasyprint import HTML
import fitz
import streamlit as st

# =============================================================================
# CONFIGURACAO
# =============================================================================
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]

ID_RAIZ = "1NaZ7kv_jHVCTlLV8vqxCzBwbTX5y3fR7"
ID_PASTA_MARCA = "19b_7n4ER-hmFyhvMmFIO1pBmPlRu85aA"
SPREADSHEET_ID = "1nVEpOZFYFKcq0MXtOwxn22nqxafmJBHnf6zhHQlyT8w"
NOME_ABA = "Imoveis"

COR_AZUL_ESCURO = "#0A1F2E"
COR_AZUL_BLOCO = "#0D2538"
COR_OFF_WHITE = "#F7F5F0"
COR_AZUL_SUAVE = "#94A3B8"
COR_LINHA = "#26384A"


# =============================================================================
# GOOGLE CONEXAO E BUSCA (Híbrida: Local / Nuvem via st.secrets)
# =============================================================================
def conectar_google():
    try:
        # Tenta carregar credenciais via secrets do Streamlit (nuvem)
        if hasattr(st, "secrets") and "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        else:
            # Fallback para arquivo local se estiver testando na máquina
            credencial_path = Path(__file__).resolve().parent / "config" / "credentials.json"
            creds = service_account.Credentials.from_service_account_file(str(credencial_path), scopes=SCOPES)
           
        return (
            build("drive", "v3", credentials=creds),
            build("sheets", "v4", credentials=creds),
        )
    except Exception as e:
        print(f"Erro ao autenticar: {e}", flush=True)
        return None, None


def buscar_id_por_nome(service, nome_item, id_pasta_pai):
    if not service or not id_pasta_pai:
        return None
    try:
        results = service.files().list(
            q=(
                f"'{id_pasta_pai}' in parents "
                f"and name = '{nome_item}' "
                f"and trashed = false"
            ),
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()
        files = results.get("files", [])
        return files[0]["id"] if files else None
    except Exception as e:
        print(f"Erro ao buscar '{nome_item}': {e}", flush=True)
        return None


def buscar_pasta_imovel_por_codigo(service, codigo, id_imoveis):
    codigo = codigo.strip().upper()
    try:
        results = service.files().list(
            q=(
                f"'{id_imoveis}' in parents "
                f"and mimeType = 'application/vnd.google-apps.folder' "
                f"and name contains '{codigo}' "
                f"and trashed = false"
            ),
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()
        files = results.get("files", [])
        for f in files:
            nome = f["name"].strip().upper()
            if (
                nome == codigo
                or nome.startswith(codigo + " ")
                or nome.startswith(codigo + "-")
            ):
                return f["id"]
        return files[0]["id"] if files else None
    except Exception as e:
        print(f"Erro ao buscar pasta do imovel: {e}", flush=True)
        return None


def obter_id_pasta_imovel(service, codigo):
    id_portfolio = buscar_id_por_nome(service, "PORTFOLIO", ID_RAIZ)
    if not id_portfolio:
        return None
    id_imoveis = buscar_id_por_nome(service, "IMOVEIS", id_portfolio)
    if not id_imoveis:
        return None
    return buscar_pasta_imovel_por_codigo(service, codigo, id_imoveis)


def baixar_arquivo_bytes(service, id_arquivo):
    """Baixa arquivos diretamente para a memória RAM (BytesIO) evitando disco local."""
    try:
        request = service.files().get_media(fileId=id_arquivo)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        fh.seek(0)
        return fh
    except Exception as e:
        print(f"Erro download em memória: {e}", flush=True)
        return None


def obter_ativo_marca_base64(service, subpasta, nome_arquivo):
    """Converte assets fixos (como fontes, logos) para Base64/URI em memória."""
    id_sub = buscar_id_por_nome(service, subpasta, ID_PASTA_MARCA)
    if not id_sub:
        return ""
    id_arq = buscar_id_por_nome(service, nome_arquivo, id_sub)
    if not id_arq:
        return ""
   
    fh = baixar_arquivo_bytes(service, id_arq)
    if not fh:
        return ""
   
    import base64
    ext = Path(nome_arquivo).suffix.lower()
    mime = "application/font-ttf" if ext in [".ttf", ".otf"] else "image/png"
    if ext == ".svg":
        mime = "image/svg+xml"
    elif ext in [".jpg", ".jpeg"]:
        mime = "image/jpeg"
       
    encoded = base64.b64encode(fh.read()).decode("utf-8")
    return f"data:{mime};charset=utf-8;base64,{encoded}"


def montar_css_fontes(service):
    itens = [
        ("CormorantGaramond-Medium.ttf", "Cormorant Garamond", 500),
        ("CormorantGaramond-SemiBold.ttf", "Cormorant Garamond", 600),
        ("Manrope-Regular.ttf", "Manrope", 400),
        ("Manrope-Medium.ttf", "Manrope", 500),
        ("Manrope-SemiBold.ttf", "Manrope", 600),
    ]
    blocos = []
    for arq, fam, peso in itens:
        uri = obter_ativo_marca_base64(service, "FONTES", arq)
        if uri:
            blocos.append(
                f"""
                @font-face {{
                    font-family: '{fam}';
                    src: url('{uri}') format('truetype');
                    font-weight: {peso};
                    font-style: normal;
                }}
                """
            )
    return "\n".join(blocos)


def buscar_logo_uri(service):
    id_logo = buscar_id_por_nome(service, "LOGO", ID_PASTA_MARCA)
    if not id_logo:
        return None
    results = service.files().list(
        q=f"'{id_logo}' in parents and trashed = false",
        fields="files(id, name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()
    for f in results.get("files", []):
        if Path(f["name"]).suffix.lower() in {".png", ".jpg", ".jpeg", ".svg", ".webp"}:
            return obter_ativo_marca_base64(service, "LOGO", f["name"])
    return None


def carregar_icone_base64(service, nome_arquivo, cor=None):
    id_sub = buscar_id_por_nome(service, "ICONES", ID_PASTA_MARCA)
    if not id_sub:
        return ""
    id_arq = buscar_id_por_nome(service, nome_arquivo, id_sub)
    if not id_arq:
        return ""
   
    fh = baixar_arquivo_bytes(service, id_arq)
    if not fh:
        return ""
   
    svg = fh.read().decode("utf-8")
    if cor:
        for antigo in ["currentColor", "#000000", "#000", "black", "#111111", "#1a1a1a"]:
            svg = svg.replace(antigo, cor)
           
    import base64
    encoded = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
    return f"data:image/svg+xml;base64,{encoded}"


def icone_pin(service, cor):
    svg_uri = carregar_icone_base64(service, "localizacao.svg", cor)
    if svg_uri:
        return f'<img src="{svg_uri}" style="width: 21px; height: 21px; vertical-align: middle;">'
    return f"""
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
         stroke="{cor}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 10c0 7-9 13-9 13S3 17 3 10a9 9 0 0 1 18 0z"></path>
        <circle cx="12" cy="10" r="3"></circle>
    </svg>
    """


def normalizar(texto):
    if not texto:
        return ""
    return " ".join(str(texto).strip().upper().split())


def ler_dados_sheets(sheets, codigo):
    result = sheets.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"'{NOME_ABA}'!A:Z",
    ).execute()
    rows = result.get("values", [])
    if not rows:
        return {}
    cab = [normalizar(h) for h in rows[0]]
    cod = normalizar(codigo)
    for row in rows[1:]:
        if not row:
            continue
        while len(row) < len(cab):
            row.append("")
        if normalizar(row[0]) == cod:
            return {cab[i]: row[i] for i in range(len(cab))}
    return {}


def get_dado(dados, *chaves, default="-"):
    for c in chaves:
        v = dados.get(normalizar(c), "")
        if v not in ("", None):
            return v
    return default


def carregar_fotos_base64(drive, codigo):
    id_imovel = obter_id_pasta_imovel(drive, codigo)
    if not id_imovel:
        return []
   
    id_fotos = buscar_id_por_nome(drive, "FOTOS TRATADAS", id_imovel)
    if not id_fotos:
        id_fotos = buscar_id_por_nome(drive, "FOTOS SELECIONADAS", id_imovel)
    if not id_fotos:
        id_fotos = id_imovel

    files = []
    token = None
    while True:
        resp = drive.files().list(
            q=f"'{id_fotos}' in parents and trashed = false",
            fields="nextPageToken, files(id, name, mimeType)",
            orderBy="name",
            pageToken=token,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()
        files.extend(resp.get("files", []))
        token = resp.get("nextPageToken")
        if not token:
            break

    import base64
    fotos_uris = []
    for f in sorted(files, key=lambda x: x["name"].lower()):
        mime = f.get("mimeType", "")
        if not mime.startswith("image/"):
            continue
        fh = baixar_arquivo_bytes(drive, f["id"])
        if fh:
            encoded = base64.b64encode(fh.read()).decode("utf-8")
            fotos_uris.append(f"data:{mime};base64,{encoded}")
    return fotos_uris


def renderizar_png(html_string, caminho_saida, largura, altura):
    caminho_saida = Path(caminho_saida)
    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    pdf_temp = caminho_saida.parent / f"_tmp_{caminho_saida.stem}.pdf"

    HTML(string=html_string).write_pdf(str(pdf_temp))
    doc = fitz.open(str(pdf_temp))
    page = doc[0]
    matriz = fitz.Matrix(largura / page.rect.width, altura / page.rect.height)
    pix = page.get_pixmap(matrix=matriz, alpha=False)
    pix.save(str(caminho_saida))
    doc.close()
    try:
        pdf_temp.unlink()
    except Exception:
        pass


def css_card_principal():
    return f"""
    .card-fundo {{
        position: absolute; left: 0; bottom: 0px;
        width: 775px; height: 397px; background: {COR_OFF_WHITE}; z-index: 2;
    }}
    .card-azul {{
        position: absolute; left: 0; bottom: 36px;
        width: 875px; height: 341px; background: {COR_AZUL_ESCURO};
        z-index: 3; padding: 48px 55px 38px 55px; color: {COR_OFF_WHITE};
    }}
    .card-conteudo {{ position: relative; z-index: 5; }}
    """


# =============================================================================
# LAMINAS (Mesmos layouts mantidos, com dados via base64/URI)
# =============================================================================
def gerar_lamina_capa(ctx, destino):
    nome_html = f"<span class='nome'>{ctx['titulo_3']}</span>" if ctx["titulo_3"] else ""
    html = f"""
    <html><head><meta charset="UTF-8"><style>
    {ctx['css_fontes']}
    @page {{ size: 1080px 1350px; margin: 0; }}
    * {{ box-sizing: border-box; }}
    body {{
        margin: 0; width: 1080px; height: 1350px;
        background: {COR_OFF_WHITE}; overflow: hidden;
        font-family: 'Manrope', Arial, sans-serif;
    }}
    .foto {{
        position: absolute; top: 0; left: 0; width: 1080px; height: 1350px;
        padding: 20px; box-sizing: border-box; object-fit: contain; display: block;
    }}
    {css_card_principal()}
    .titulo {{ font-size: 39px; line-height: 1.15; margin: 0; }}
    .tipo {{
        font-family: 'Cormorant Garamond', Georgia, serif;
        font-size: 38px; font-weight: 500; letter-spacing: 2px;
        text-transform: uppercase; color: {COR_OFF_WHITE}; margin: 0;
    }}
    .destaque {{
        font-family: 'Cormorant Garamond', Georgia, serif;
        font-size: 45px; font-weight: 500; letter-spacing: 2px;
        text-transform: uppercase; margin: 0; color: {COR_OFF_WHITE};
    }}
    .nome {{
        display: block; margin-top: 4px; font-family: 'Manrope', Arial, sans-serif;
        font-size: 28px; font-weight: 400; color: {COR_OFF_WHITE}; letter-spacing: .5px;
    }}
    .local {{
        font-family: 'Manrope', Arial, sans-serif; font-weight: 400;
        margin-top: 24px; font-size: 18px; letter-spacing: 1px;
        text-transform: uppercase; color: {COR_AZUL_SUAVE};
        display: flex; align-items: center; gap: 9px;
    }}
    .valor {{
        margin-top: 23px; font-size: 43px; font-weight: 600;
        color: {COR_OFF_WHITE}; letter-spacing: .5px;
    }}
    .linha {{
        width: 100%; height: 1px; background: {COR_LINHA};
        margin-top: 27px; margin-bottom: 19px;
    }}
    .rodape {{ font-size: 13px; letter-spacing: 1.8px; width: 100%; }}
    .marca {{ float: left; color: {COR_OFF_WHITE}; font-weight: 600; }}
    .deslize {{ float: right; color: {COR_AZUL_SUAVE}; font-weight: 500; }}
    .clear {{ clear: both; }}
    </style></head><body>
        <img class="foto" src="{ctx['foto_capa']}">
        <div class="card-fundo"></div>
        <div class="card-azul">
            <div class="card-conteudo">
                <div class="titulo">
                    <span class="tipo">{ctx['titulo_1']}</span>
                    <span class="destaque">{ctx['titulo_2']}</span>
                    {nome_html}
                </div>
                <div class="local">
                    {ctx['pin']}
                    <span>{ctx['bairro']} • {ctx['cidade']}</span>
                </div>
                <div class="valor">{ctx['valor']}</div>
                <div class="linha"></div>
                <div class="rodape">
                    <span class="marca">CARVALHO FERREIRA</span>
                    <span class="deslize">DESLIZE PARA CONHECER</span>
                    <div class="clear"></div>
                </div>
            </div>
        </div>
    </body></html>
    """
    renderizar_png(html, destino, 1080, 1350)


def gerar_lamina_foto(ctx, destino, foto):
    html = f"""
    <html><head><meta charset="UTF-8"><style>
    {ctx['css_fontes']}
    @page {{ size: 1080px 1350px; margin: 0; }}
    * {{ box-sizing: border-box; }}
    body {{
        margin: 0; width: 1080px; height: 1350px;
        background: {COR_OFF_WHITE}; overflow: hidden; font-family: 'Manrope', Arial, sans-serif;
    }}
    .foto {{ position: absolute; top: 0; left: 0; width: 1080px; height: 1350px; object-fit: cover; }}
    .barra-inferior {{
        position: absolute; bottom: 0; left: 0; width: 100%; height: 90px;
        background: {COR_AZUL_ESCURO}; color: {COR_OFF_WHITE}; padding: 31px 55px;
    }}
    .marca {{ font-size: 13px; font-weight: 600; letter-spacing: 2px; }}
    </style></head><body>
        <img class="foto" src="{foto}">
        <div class="barra-inferior">
            <div class="marca">CARVALHO FERREIRA</div>
        </div>
    </body></html>
    """
    renderizar_png(html, destino, 1080, 1350)


def gerar_lamina_ficha(ctx, destino):
    html = f"""
    <html><head><meta charset="UTF-8"><style>
    {ctx['css_fontes']}
    @page {{ size: 1080px 1350px; margin: 0; }}
    * {{ box-sizing: border-box; }}
    body {{
        margin: 0; width: 1080px; height: 1350px; padding: 70px 65px;
        background: {COR_AZUL_ESCURO}; color: {COR_OFF_WHITE};
        font-family: 'Manrope', Arial, sans-serif; overflow: hidden;
    }}
    .titulo {{
        font-size: 39px; font-weight: 500; letter-spacing: 2px;
        color: {COR_OFF_WHITE}; margin-bottom: 55px;
    }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 22px; width: 100%; }}
    .card {{
        height: 245px; background: {COR_AZUL_BLOCO}; padding: 30px 32px;
        color: {COR_OFF_WHITE}; position: relative; overflow: hidden;
    }}
    .card::after {{
        content: ""; position: absolute; bottom: 0; right: 0;
        width: 55px; height: 55px; background: {COR_OFF_WHITE}; opacity: .08;
    }}
    .icone {{ height: 34px; margin-bottom: 26px; }}
    .label {{
        font-size: 15px; letter-spacing: 2px; text-transform: uppercase;
        color: {COR_AZUL_SUAVE}; font-weight: 500;
    }}
    .valor {{
        margin-top: 9px; font-size: 37px; font-weight: 600;
        color: {COR_OFF_WHITE}; line-height: 1;
    }}
    .rodape {{
        position: absolute; left: 65px; right: 65px; bottom: 50px;
        padding-top: 22px; border-top: 1px solid #D8DDE2;
        font-size: 13px; letter-spacing: 2px; color: {COR_AZUL_SUAVE}; text-transform: uppercase;
    }}
    </style></head><body>
        <div class="titulo">ESPECIFICACOES</div>
        <div class="grid">
            <div class="card"><div class="icone">{ctx['svg_dorm']}</div><div class="label">Dormitorios</div><div class="valor">{ctx['dormitorios']}</div></div>
            <div class="card"><div class="icone">{ctx['svg_suites']}</div><div class="label">Suites</div><div class="valor">{ctx['suites']}</div></div>
            <div class="card"><div class="icone">{ctx['svg_banheiros']}</div><div class="label">Banheiros</div><div class="valor">{ctx['banheiros']}</div></div>
            <div class="card"><div class="icone">{ctx['svg_vagas']}</div><div class="label">Vagas</div><div class="valor">{ctx['vagas']}</div></div>
            <div class="card"><div class="icone">{ctx['svg_area']}</div><div class="label">Area util</div><div class="valor">{ctx['area']}</div></div>
            <div class="card"><div class="icone">{ctx['svg_terreno']}</div><div class="label">Area do terreno</div><div class="valor">{ctx['terreno']}</div></div>
        </div>
        <div class="rodape">CARVALHO FERREIRA • CONSULTORIA IMOBILIARIA</div>
    </body></html>
    """
    renderizar_png(html, destino, 1080, 1350)


def gerar_lamina_final(ctx, destino):
    logo_html = f'<img class="logo" src="{ctx["logo_uri"]}">' if ctx.get("logo_uri") else ""
    html = f"""
    <html><head><meta charset="UTF-8"><style>
    {ctx['css_fontes']}
    @page {{ size: 1080px 1350px; margin: 0; }}
    * {{ box-sizing: border-box; }}
    body {{
        margin: 0; width: 1080px; height: 1350px; background: {COR_AZUL_ESCURO};
        font-family: 'Manrope', Arial, sans-serif; text-align: center; position: relative; overflow: hidden;
    }}
    .topo {{ position: absolute; top: 100px; left: 80px; right: 80px; }}
    .logo {{ max-width: 300px; max-height: 125px; display: block; margin: 0 auto 22px; }}
    .submarca {{ font-size: 15px; letter-spacing: 3px; color: {COR_OFF_WHITE}; text-transform: uppercase; font-weight: 600; }}
    .centro {{ position: absolute; top: 50%; left: 80px; right: 80px; transform: translateY(-35%); }}
    .titulo {{
        font-family: 'Cormorant Garamond', Georgia, serif; font-size: 55px; line-height: 1.2;
        color: {COR_OFF_WHITE}; font-weight: 600; letter-spacing: 1px;
    }}
    .linha {{ width: 75px; height: 2px; background: {COR_OFF_WHITE}; margin: 30px auto 0; }}
    </style></head><body>
        <div class="topo">{logo_html}<div class="submarca">CARVALHO FERREIRA • CONSULTORIA IMOBILIARIA</div></div>
        <div class="centro"><div class="titulo">TALVEZ ESTE SEJA O IMOVEL.<br>QUE VOCE ESTAVA PROCURANDO.</div><div class="linha"></div></div>
    </body></html>
    """
    renderizar_png(html, destino, 1080, 1350)


def gerar_thumbnail(ctx, destino):
    nome_html = f"<span class='nome'>{ctx['titulo_3']}</span>" if ctx["titulo_3"] else ""
    html = f"""
    <html><head><meta charset="UTF-8"><style>
    {ctx['css_fontes']}
    @page {{ size: 1080px 1350px; margin: 0; }}
    * {{ box-sizing: border-box; }}
    body {{
        margin: 0; width: 1080px; height: 1350px; background: {COR_OFF_WHITE}; overflow: hidden; font-family: 'Manrope', Arial, sans-serif;
    }}
    .foto {{ position: absolute; top: 0; left: 0; width: 1080px; height: 1350px; padding: 20px; box-sizing: border-box; object-fit: contain; }}
    {css_card_principal()}
    .card-azul {{ padding: 48px 55px 38px 55px; }}
    .titulo {{ font-size: 38px; line-height: 1.15; }}
    .tipo {{ font-family: 'Cormorant Garamond', Georgia, serif; font-size: 36px; font-weight: 500; letter-spacing: 2px; text-transform: uppercase; color: {COR_OFF_WHITE}; }}
    .destaque {{ font-family: 'Cormorant Garamond', Georgia, serif; font-size: 45px; font-weight: 500; letter-spacing: 2px; text-transform: uppercase; margin: 0; color: {COR_OFF_WHITE}; }}
    .nome {{ display: block; margin-top: 3px; font-size: 27px; font-weight: 400; color: {COR_OFF_WHITE}; }}
    .local {{ margin-top: 20px; font-size: 17px; letter-spacing: 1px; text-transform: uppercase; color: {COR_AZUL_SUAVE}; display: flex; align-items: center; gap: 8px; }}
    .valor {{ margin-top: 19px; font-size: 42px; font-weight: 600; color: {COR_OFF_WHITE}; }}
    .marca {{ margin-top: 24px; padding-top: 16px; border-top: 1px solid rgba(255,255,255,.3); font-size: 13px; letter-spacing: 2px; font-weight: 600; color: {COR_OFF_WHITE}; }}
    </style></head><body>
        <img class="foto" src="{ctx['foto_capa']}">
        <div class="card-fundo"></div>
        <div class="card-azul">
            <div class="card-conteudo">
                <div class="titulo"><span class="tipo">{ctx['titulo_1']}</span><span class="destaque">{ctx['titulo_2']}</span>{nome_html}</div>
                <div class="local">{ctx['pin']}<span>{ctx['bairro']} • {ctx['cidade']}</span></div>
                <div class="valor">{ctx['valor']}</div>
                <div class="marca">CARVALHO FERREIRA</div>
            </div>
        </div>
    </body></html>
    """
    renderizar_png(html, destino, 1080, 1350)


def gerar_stories(ctx, pasta, fotos):
    gerados = []
    for indice, foto in enumerate(fotos[:4], start=1):
        nome_html = f"<span class='nome'>{ctx['titulo_3']}</span>" if ctx["titulo_3"] else ""
        html = f"""
        <html><head><meta charset="UTF-8"><style>
        {ctx['css_fontes']}
        @page {{ size: 1080px 1920px; margin: 0; }}
        * {{ box-sizing: border-box; }}
        body {{ margin: 0; width: 1080px; height: 1920px; background: {COR_OFF_WHITE}; overflow: hidden; font-family: 'Manrope', Arial, sans-serif; }}
        .foto {{ position: absolute; top: 0; left: 0; width: 1080px; height: 1920px; object-fit: cover; }}
        .card-fundo {{ position: absolute; left: 0; bottom: 70px; width: 780px; height: 450px; background: {COR_OFF_WHITE}; z-index: 2; }}
        .card-azul {{ position: absolute; left: 0; bottom: 51px; width: 900px; height: 431px; background: {COR_AZUL_ESCURO}; z-index: 3; padding: 60px 62px 45px 62px; color: {COR_OFF_WHITE}; }}
        .titulo {{ font-size: 43px; line-height: 1.15; }}
        .tipo {{ font-family: 'Cormorant Garamond', Georgia, serif; font-size: 36px; font-weight: 500; letter-spacing: 2px; text-transform: uppercase; margin: 0; }}
        .destaque {{ font-family: 'Cormorant Garamond', Georgia, serif; font-size: 45px; font-weight: 500; letter-spacing: 2px; text-transform: uppercase; margin: 0; color: {COR_OFF_WHITE}; }}
        .nome {{ display: block; margin-top: 5px; font-size: 30px; color: {COR_OFF_WHITE}; font-weight: 400; }}
        .local {{ margin-top: 25px; font-size: 20px; letter-spacing: 1px; text-transform: uppercase; color: {COR_AZUL_SUAVE}; display: flex; align-items: center; gap: 9px; }}
        .valor {{ margin-top: 23px; font-size: 52px; font-weight: 600; color: {COR_OFF_WHITE}; }}
        .info {{ margin-top: 25px; font-size: 20px; font-weight: 500; color: #E2E8F0; display: flex; gap: 28px; flex-wrap: wrap; }}
        .marca {{ margin-top: 30px; padding-top: 18px; border-top: 1px solid rgba(255,255,255,.3); font-size: 14px; letter-spacing: 2px; font-weight: 600; }}
        </style></head><body>
            <img class="foto" src="{foto}">
            <div class="card-fundo"></div>
            <div class="card-azul">
                <div class="titulo"><span class="tipo">{ctx['titulo_1']}</span><span class="destaque">{ctx['titulo_2']}</span>{nome_html}</div>
                <div class="local">{ctx['pin']}<span>{ctx['bairro']} • {ctx['cidade']}</span></div>
                <div class="valor">{ctx['valor']}</div>
                <div class="info"><div>{ctx['dormitorios']} dorm.</div><div>{ctx['vagas']} vagas</div><div>{ctx['area']} const.</div></div>
                <div class="marca">CARVALHO FERREIRA</div>
            </div>
        </body></html>
        """
        dest = pasta / f"story_{ctx['codigo']}_{indice:02d}.png"
        renderizar_png(html, dest, 1080, 1920)
        gerados.append(dest)
    return gerados


# =============================================================================
# EXECUTAVEL PRINCIPAL (Em ambiente seguro temporário)
# =============================================================================
def gerar_posts(codigo_imovel):
    drive, sheets = conectar_google()
    if not drive or not sheets:
        return None

    codigo = codigo_imovel.strip().upper()
    dados = ler_dados_sheets(sheets, codigo)
    if not dados:
        print(f"Imovel '{codigo}' nao encontrado no Google Sheets.", flush=True)
        return None

    fotos = carregar_fotos_base64(drive, codigo)
    if not fotos:
        print("Nenhuma foto encontrada.", flush=True)
        return None

    # Cria diretório temporário isolado compatível com nuvem
    temp_dir = tempfile.TemporaryDirectory()
    pasta = Path(temp_dir.name) / codigo
    pasta.mkdir(parents=True, exist_ok=True)

    ctx = {
        "codigo": codigo,
        "css_fontes": montar_css_fontes(drive),
        "foto_capa": fotos[0],
        "logo_uri": buscar_logo_uri(drive) or "",
        "pin": icone_pin(drive, COR_OFF_WHITE),
        "titulo_1": get_dado(dados, "TITULO 1", default=""),
        "titulo_2": get_dado(dados, "TITULO 2", default=""),
        "titulo_3": get_dado(dados, "TITULO 3", default=""),
        "valor": get_dado(dados, "VALOR"),
        "bairro": get_dado(dados, "BAIRRO", default=""),
        "cidade": get_dado(dados, "CIDADE", default=""),
        "dormitorios": get_dado(dados, "DORMITORIOS"),
        "suites": get_dado(dados, "SUITES", default="-"),
        "banheiros": get_dado(dados, "BANHEIROS"),
        "vagas": get_dado(dados, "VAGAS"),
        "area": get_dado(dados, "AREA UTIL"),
        "terreno": get_dado(dados, "AREA TOTAL"),
        "svg_dorm": carregar_icone_base64(drive, "dormitorios.svg", COR_OFF_WHITE),
        "svg_suites": carregar_icone_base64(drive, "suites.svg", COR_OFF_WHITE),
        "svg_banheiros": carregar_icone_base64(drive, "banheiros.svg", COR_OFF_WHITE),
        "svg_vagas": carregar_icone_base64(drive, "vagas.svg", COR_OFF_WHITE),
        "svg_area": carregar_icone_base64(drive, "area.svg", COR_OFF_WHITE),
        "svg_terreno": carregar_icone_base64(drive, "terreno.svg", COR_OFF_WHITE),
    }

    gerados = []

    dest = pasta / f"thumbnail_{codigo}.png"
    gerar_thumbnail(ctx, dest)
    gerados.append(dest)

    dest = pasta / f"carrossel_{codigo}_01.png"
    gerar_lamina_capa(ctx, dest)
    gerados.append(dest)

    n = 2
    for foto in fotos[1:4]:
        dest = pasta / f"carrossel_{codigo}_{n:02d}.png"
        gerar_lamina_foto(ctx, dest, foto)
        gerados.append(dest)
        n += 1

    dest = pasta / f"carrossel_{codigo}_{n:02d}.png"
    gerar_lamina_ficha(ctx, dest)
    gerados.append(dest)
    n += 1

    dest = pasta / f"carrossel_{codigo}_{n:02d}.png"
    gerar_lamina_final(ctx, dest)
    gerados.append(dest)

    gerados.extend(gerar_stories(ctx, pasta, fotos))

    zip_path = Path(temp_dir.name) / f"posts_{codigo}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for arq in gerados:
            zf.write(arq, arcname=arq.name)

    # Lê o ZIP para bytes em memória para que o Streamlit possa disponibilizar o download sem travar na nuvem
    with open(zip_path, "rb") as f:
        zip_bytes = f.read()

    temp_dir.cleanup()
    print("SUCESSO: Posts gerados na nuvem com sucesso.", flush=True)
    return zip_bytes