# -*- coding: utf-8 -*-

import io
import os
import sys
import zipfile

from pathlib import Path

# GARANTE QUE A RAIZ ESTÁ NO CAMINHO DO PYTHON
raiz_projeto = os.path.abspath(os.path.dirname(__file__))
if raiz_projeto not in sys.path:
    sys.path.insert(0, raiz_projeto)

from PIL import (
    Image,
    ImageEnhance,
    ImageOps,
    ImageDraw,
    ImageFont,
)


# =============================================================================
# CONFIGURAÇÕES VISUAIS
# =============================================================================

SATURACAO = 1.00
CONTRASTE = 1.02
BRILHO = 1.04
TEMPERATURA = 4
NITIDEZ = 1.00

MAX_LARGURA = 2400
MAX_ALTURA = 3000

# Configurações para as miniaturas dentro do ZIP
MAX_LARGURA_MINIATURA = 600
QUALIDADE_MINIATURA = 80
QTD_MINIATURAS = 3

TAMANHO_LOGO = 0.090
OPACIDADE_LOGO = 0.55
MARGEM_LOGO = 35

TAMANHO_CODIGO = 28
OPACIDADE_CODIGO = 0.55
MARGEM_CODIGO = 35

COR_CODIGO = (255, 255, 255)

NOME_PASTA_LOGO = "LOGO"


# =============================================================================
# AJUSTES DA IMAGEM
# =============================================================================

def aquecer_imagem(img, intensidade=5):
    """
    Aplica uma leve correção de temperatura.
    """
    img = img.convert("RGB")
    r, g, b = img.split()

    fator_r = 1 + (intensidade / 100)
    fator_g = 1 + (intensidade / 300)

    r = r.point(lambda p: min(255, int(p * fator_r)))
    g = g.point(lambda p: min(255, int(p * fator_g)))

    return Image.merge("RGB", (r, g, b))


# =============================================================================
# LOGO
# =============================================================================

def aplicar_logo_bytes(img, logo_bytes):
    """
    Aplica o logo recebido diretamente em memória.
    """
    if not logo_bytes:
        return img

    logo_stream = None
    logo = None

    try:
        if isinstance(logo_bytes, io.BytesIO):
            logo_bytes.seek(0)
            logo_stream = logo_bytes
        elif isinstance(logo_bytes, (bytes, bytearray)):
            logo_stream = io.BytesIO(logo_bytes)
        else:
            return img

        logo = Image.open(logo_stream).convert("RGBA")
        largura_logo = int(img.width * TAMANHO_LOGO)

        if largura_logo <= 0 or logo.width <= 0:
            return img

        proporcao = largura_logo / logo.width
        altura_logo = int(logo.height * proporcao)

        if altura_logo <= 0:
            return img

        logo = logo.resize((largura_logo, altura_logo), Image.Resampling.LANCZOS)

        alpha = logo.getchannel("A")
        alpha = alpha.point(lambda p: int(p * OPACIDADE_LOGO))
        logo.putalpha(alpha)

        x = img.width - largura_logo - MARGEM_LOGO
        y = img.height - altura_logo - MARGEM_LOGO

        img = img.convert("RGBA")
        img.alpha_composite(logo, (x, y))
        return img.convert("RGB")

    except Exception as erro:
        print(f"Erro ao aplicar logo: {erro}", flush=True)
        return img
    finally:
        if logo is not None:
            try:
                logo.close()
            except Exception:
                pass


# =============================================================================
# CÓDIGO DO IMÓVEL
# =============================================================================

def aplicar_codigo(img, codigo):
    """
    Adiciona o código do imóvel no canto inferior esquerdo.
    """
    if not codigo:
        return img

    img = img.convert("RGBA")
    draw = ImageDraw.Draw(img)

    try:
        fonte = ImageFont.truetype("arial.ttf", TAMANHO_CODIGO)
    except Exception:
        fonte = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), str(codigo), font=fonte)
    largura_texto = bbox[2] - bbox[0]
    altura_texto = bbox[3] - bbox[1]

    x = MARGEM_CODIGO
    y = max(0, img.height - altura_texto - MARGEM_CODIGO)

    if x + largura_texto > img.width:
        x = max(0, img.width - largura_texto - MARGEM_CODIGO)

    camada = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw_camada = ImageDraw.Draw(camada)
    alpha = int(255 * OPACIDADE_CODIGO)

    draw_camada.text(
        (x, y),
        str(codigo),
        font=fonte,
        fill=(COR_CODIGO[0], COR_CODIGO[1], COR_CODIGO[2], alpha),
    )

    img.alpha_composite(camada)
    camada.close()
    return img.convert("RGB")


# =============================================================================
# PROCESSAMENTO PRINCIPAL DA FOTO
# =============================================================================

def processar_foto_bytes(input_bytes, logo_bytes, codigo):
    """
    Recebe a foto original em memória e devolve a foto tratada em memória.
    """
    img = None
    try:
        if not input_bytes:
            return None

        if isinstance(input_bytes, io.BytesIO):
            input_bytes.seek(0)
            entrada = input_bytes
        elif isinstance(input_bytes, (bytes, bytearray)):
            entrada = io.BytesIO(input_bytes)
        else:
            return None

        img = Image.open(entrada)
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")

        img.thumbnail((MAX_LARGURA, MAX_ALTURA), Image.Resampling.LANCZOS)

        img = ImageEnhance.Color(img).enhance(SATURACAO)
        img = ImageEnhance.Contrast(img).enhance(CONTRASTE)
        img = ImageEnhance.Brightness(img).enhance(BRILHO)
        img = aquecer_imagem(img, TEMPERATURA)
        img = ImageEnhance.Sharpness(img).enhance(NITIDEZ)

        img = aplicar_logo_bytes(img, logo_bytes)
        img = aplicar_codigo(img, codigo)

        output_buffer = io.BytesIO()
        img.save(output_buffer, format="JPEG", quality=95, optimize=True)
        output_buffer.seek(0)

        return output_buffer

    except Exception as erro:
        print(f"Erro no processamento da imagem: {erro}", flush=True)
        return None
    finally:
        if img is not None:
            try:
                img.close()
            except Exception:
                pass


# =============================================================================
# LOCALIZAR LOGO NO DRIVE
# =============================================================================

def obter_logo_bytes(service):
    """
    Localiza o primeiro arquivo de imagem dentro da pasta LOGO.
    """
    if not service:
        return None

    try:
        import drive_service

        ID_PASTA_MARCA = "19b_7n4ER-hmFyhvMmFIO1pBmPlRu85aA"

        id_logo = drive_service.buscar_pasta_por_nome(service, NOME_PASTA_LOGO, ID_PASTA_MARCA)
        if not id_logo:
            return None

        arquivos = drive_service.listar_itens_pasta(service, id_logo)
        for arquivo in arquivos:
            nome = arquivo.get("name", "").lower()
            mime_type = arquivo.get("mimeType", "")

            if (nome.endswith((".png", ".jpg", ".jpeg", ".webp")) or mime_type.startswith("image/")):
                dados = drive_service.baixar_arquivo_bytes(service, arquivo["id"])
                if dados:
                    return dados

        return None
    except Exception as erro:
        print(f"Erro ao carregar logo: {erro}", flush=True)
        return None


# =============================================================================
# GERAR ZIP EM MEMÓRIA COM PASTA DE MINIATURAS
# =============================================================================

def gerar_zip_fotos(fotos_tratadas, codigo_imovel):
    """
    Recebe a lista de fotos tratadas, gera as fotos normais na raiz do ZIP
    e cria obrigatoriamente a pasta 'MINIATURA/' contendo até 3 fotos redimensionadas.
    """
    if not fotos_tratadas:
        return None

    zip_buffer = io.BytesIO()

    try:
        with zipfile.ZipFile(
            zip_buffer,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=6,
        ) as zip_file:

            # 1. Adiciona todas as fotos tratadas normais na raiz do ZIP
            for item in fotos_tratadas:
                nome = item.get("nome", "foto.jpg")
                dados = item.get("dados")
                if not dados:
                    continue
                
                if isinstance(dados, io.BytesIO):
                    dados.seek(0)
                    conteudo = dados.read()
                elif isinstance(dados, (bytes, bytearray)):
                    conteudo = bytes(dados)
                else:
                    continue

                zip_file.writestr(nome, conteudo)

            # 2. Garante a criação da pasta 'MINIATURA/' e insere as primeiras fotos reduzidas
            fotos_para_mini = fotos_tratadas[:QTD_MINIATURAS]
            for item in fotos_para_mini:
                nome = item.get("nome", "foto.jpg")
                dados = item.get("dados")
                if not dados:
                    continue

                try:
                    if isinstance(dados, io.BytesIO):
                        dados.seek(0)
                        img_bytes = dados.read()
                    else:
                        img_bytes = bytes(dados)

                    img = Image.open(io.BytesIO(img_bytes))
                    img.thumbnail((MAX_LARGURA_MINIATURA, MAX_LARGURA_MINIATURA), Image.Resampling.LANCZOS)

                    buf_mini = io.BytesIO()
                    img.save(buf_mini, format="JPEG", quality=QUALIDADE_MINIATURA, optimize=True)
                    buf_mini.seek(0)
                    conteudo_mini = buf_mini.read()
                    img.close()

                    # Caminho explícito com a pasta MINIATURA no topo do ZIP
                    caminho_no_zip = f"MINIATURA/{nome}"
                    zip_file.writestr(caminho_no_zip, conteudo_mini)
                except Exception as e:
                    print(f"Erro ao gerar miniatura para o ZIP: {e}", flush=True)

        zip_buffer.seek(0)
        return zip_buffer

    except Exception as erro:
        print(f"Erro ao gerar ZIP: {erro}", flush=True)
        try:
            zip_buffer.close()
        except Exception:
            pass
        return None


# =============================================================================
# EXECUÇÃO DO TRATAMENTO DO IMÓVEL
# =============================================================================

def executar_tratamento_imovel(service, codigo_imovel, logo_bytes=None):
    """
    Busca as fotos no Google Drive, trata as imagens e devolve um ZIP
    contendo as fotos normais + a pasta MINIATURA.
    """
    import drive_service

    codigo_imovel = str(codigo_imovel).strip().upper()
    if not codigo_imovel or service is None:
        return None

    id_pasta_imovel = drive_service.encontrar_pasta_imovel(service, codigo_imovel)
    if not id_pasta_imovel:
        return None

    if logo_bytes is None:
        logo_bytes = obter_logo_bytes(service)

    arquivos = drive_service.listar_itens_pasta(service, id_pasta_imovel)
    imagens = []

    for arquivo in arquivos:
        mime_type = arquivo.get("mimeType", "")
        nome = arquivo.get("name", "").lower()

        if mime_type == "application/vnd.google-apps.folder":
            continue

        if mime_type.startswith("image/") or nome.endswith((".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif")):
            imagens.append(arquivo)

    imagens.sort(key=lambda item: item.get("name", "").lower())
    if not imagens:
        return None

    fotos_tratadas = []

    for indice, arquivo in enumerate(imagens, start=1):
        file_id = arquivo.get("id")
        nome_original = arquivo.get("name", f"foto_{indice}")
        stream_bruto = None
        stream_tratado = None

        try:
            if not file_id:
                continue

            stream_bruto = drive_service.baixar_foto_bytes(service, file_id)
            if not stream_bruto:
                continue

            stream_tratado = processar_foto_bytes(stream_bruto, logo_bytes, codigo_imovel)
            if not stream_tratado:
                continue

            nome_base = os.path.splitext(nome_original)[0]
            nome_saida = f"{nome_base}.jpg"

            stream_tratado.seek(0)
            dados_foto = stream_tratado.read()
            if not dados_foto:
                continue

            fotos_tratadas.append({
                "nome": nome_saida,
                "dados": dados_foto,
            })

        except Exception as erro:
            print(f"Erro na foto {nome_original}: {erro}", flush=True)
        finally:
            if stream_bruto and hasattr(stream_bruto, "close"):
                try:
                    stream_bruto.close()
                except Exception:
                    pass
            if stream_tratado and hasattr(stream_tratado, "close"):
                try:
                    stream_tratado.close()
                except Exception:
                    pass

    if not fotos_tratadas:
        return None

    zip_buffer = gerar_zip_fotos(fotos_tratadas, codigo_imovel)
    fotos_tratadas.clear()
    return zip_buffer


# =============================================================================
# CONEXÃO E ENTRADAS
# =============================================================================

def obter_service():
    try:
        import streamlit as st
        creds_dict = dict(st.secrets["google_credentials"])
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        import drive_service

        creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=drive_service.SCOPES)
        return build("drive", "v3", credentials=creds)
    except Exception as erro:
        print(f"Erro na conexão com Google Drive: {erro}", flush=True)
        return None

def tratar(codigo_imovel, service=None, logo_bytes=None):
    try:
        codigo_imovel = str(codigo_imovel).strip().upper()
        if not codigo_imovel:
            return None
        if service is None:
            service = obter_service()
        if service is None:
            return None
        return executar_tratamento_imovel(service, codigo_imovel, logo_bytes)
    except Exception as erro:
        print(f"Erro no tratamento: {erro}", flush=True)
        return None

def tratar_fotos(codigo_imovel, service=None, logo_bytes=None):
    return tratar(codigo_imovel, service=service, logo_bytes=logo_bytes)
