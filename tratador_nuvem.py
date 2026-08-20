# -*- coding: utf-8 -*-

import io
import os
import zipfile

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
BRILHO = 1.03
TEMPERATURA = 5
NITIDEZ = 1.00

MAX_LARGURA = 2400
MAX_ALTURA = 3000

TAMANHO_LOGO = 0.085
OPACIDADE_LOGO = 0.65
MARGEM_LOGO = 30

TAMANHO_CODIGO = 24
OPACIDADE_CODIGO = 0.55
MARGEM_CODIGO = 30

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

    r = r.point(
        lambda p: min(
            255,
            int(p * fator_r),
        )
    )

    g = g.point(
        lambda p: min(
            255,
            int(p * fator_g),
        )
    )

    return Image.merge(
        "RGB",
        (r, g, b),
    )


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

        if isinstance(
            logo_bytes,
            io.BytesIO,
        ):
            logo_bytes.seek(0)
            logo_stream = logo_bytes

        elif isinstance(
            logo_bytes,
            (bytes, bytearray),
        ):
            logo_stream = io.BytesIO(
                logo_bytes
            )

        else:
            return img

        logo = Image.open(
            logo_stream
        ).convert("RGBA")

        largura_logo = int(
            img.width * TAMANHO_LOGO
        )

        if (
            largura_logo <= 0
            or logo.width <= 0
        ):
            return img

        proporcao = (
            largura_logo / logo.width
        )

        altura_logo = int(
            logo.height * proporcao
        )

        if altura_logo <= 0:
            return img

        logo = logo.resize(
            (
                largura_logo,
                altura_logo,
            ),
            Image.Resampling.LANCZOS,
        )

        alpha = logo.getchannel("A")

        alpha = alpha.point(
            lambda p: int(
                p * OPACIDADE_LOGO
            )
        )

        logo.putalpha(alpha)

        x = (
            img.width
            - largura_logo
            - MARGEM_LOGO
        )

        y = (
            img.height
            - altura_logo
            - MARGEM_LOGO
        )

        img = img.convert("RGBA")

        img.alpha_composite(
            logo,
            (
                x,
                y,
            ),
        )

        return img.convert("RGB")

    except Exception as erro:

        print(
            f"Erro ao aplicar logo: {erro}",
            flush=True,
        )

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

def aplicar_codigo(
    img,
    codigo,
):
    """
    Adiciona o código do imóvel no canto inferior esquerdo.
    """

    if not codigo:
        return img

    img = img.convert(
        "RGBA"
    )

    draw = ImageDraw.Draw(
        img
    )

    try:

        fonte = ImageFont.truetype(
            "arial.ttf",
            TAMANHO_CODIGO,
        )

    except Exception:

        fonte = ImageFont.load_default()

    bbox = draw.textbbox(
        (
            0,
            0,
        ),
        str(codigo),
        font=fonte,
    )

    largura_texto = (
        bbox[2] - bbox[0]
    )

    altura_texto = (
        bbox[3] - bbox[1]
    )

    x = MARGEM_CODIGO

    y = max(
        0,
        img.height
        - altura_texto
        - MARGEM_CODIGO,
    )

    if (
        x + largura_texto
        > img.width
    ):
        x = max(
            0,
            img.width
            - largura_texto
            - MARGEM_CODIGO,
        )

    camada = Image.new(
        "RGBA",
        img.size,
        (
            0,
            0,
            0,
            0,
        ),
    )

    draw_camada = ImageDraw.Draw(
        camada
    )

    alpha = int(
        255 * OPACIDADE_CODIGO
    )

    draw_camada.text(
        (
            x,
            y,
        ),
        str(codigo),
        font=fonte,
        fill=(
            COR_CODIGO[0],
            COR_CODIGO[1],
            COR_CODIGO[2],
            alpha,
        ),
    )

    img.alpha_composite(
        camada
    )

    camada.close()

    return img.convert(
        "RGB"
    )


# =============================================================================
# PROCESSAMENTO PRINCIPAL DA FOTO
# =============================================================================

def processar_foto_bytes(
    input_bytes,
    logo_bytes,
    codigo,
):
    """
    Recebe a foto original em memória
    e devolve a foto tratada em memória.
    """

    img = None

    try:

        if not input_bytes:
            return None

        if isinstance(
            input_bytes,
            io.BytesIO,
        ):
            input_bytes.seek(0)
            entrada = input_bytes

        elif isinstance(
            input_bytes,
            (bytes, bytearray),
        ):
            entrada = io.BytesIO(
                input_bytes
            )

        else:
            return None

        img = Image.open(
            entrada
        )

        img = ImageOps.exif_transpose(
            img
        )

        img = img.convert(
            "RGB"
        )

        img.thumbnail(
            (
                MAX_LARGURA,
                MAX_ALTURA,
            ),
            Image.Resampling.LANCZOS,
        )

        # --------------------------------------------------------
        # AJUSTES FOTOGRÁFICOS
        # --------------------------------------------------------

        img = ImageEnhance.Color(
            img
        ).enhance(
            SATURACAO
        )

        img = ImageEnhance.Contrast(
            img
        ).enhance(
            CONTRASTE
        )

        img = ImageEnhance.Brightness(
            img
        ).enhance(
            BRILHO
        )

        img = aquecer_imagem(
            img,
            TEMPERATURA,
        )

        img = ImageEnhance.Sharpness(
            img
        ).enhance(
            NITIDEZ
        )

        # --------------------------------------------------------
        # IDENTIDADE VISUAL
        # --------------------------------------------------------

        img = aplicar_logo_bytes(
            img,
            logo_bytes,
        )

        img = aplicar_codigo(
            img,
            codigo,
        )

        # --------------------------------------------------------
        # SAÍDA EM RAM
        # --------------------------------------------------------

        output_buffer = io.BytesIO()

        img.save(
            output_buffer,
            format="JPEG",
            quality=95,
            optimize=True,
        )

        output_buffer.seek(0)

        return output_buffer

    except Exception as erro:

        print(
            f"Erro no processamento da imagem: {erro}",
            flush=True,
        )

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

def obter_logo_bytes(
    service,
):
    """
    Localiza o primeiro arquivo de imagem
    dentro da pasta LOGO.
    """

    if not service:
        return None

    try:

        from drive_service import (
            buscar_pasta_por_nome,
            listar_itens_pasta,
            baixar_arquivo_bytes,
        )

        ID_PASTA_MARCA = (
            "19b_7n4ER-hmFyhvMmFIO1pBmPlRu85aA"
        )

        id_logo = buscar_pasta_por_nome(
            service,
            NOME_PASTA_LOGO,
            ID_PASTA_MARCA,
        )

        if not id_logo:

            print(
                "Pasta LOGO não encontrada.",
                flush=True,
            )

            return None

        arquivos = listar_itens_pasta(
            service,
            id_logo,
        )

        for arquivo in arquivos:

            nome = arquivo.get(
                "name",
                "",
            ).lower()

            mime_type = arquivo.get(
                "mimeType",
                "",
            )

            extensao_valida = nome.endswith(
                (
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".webp",
                )
            )

            imagem_valida = mime_type.startswith(
                "image/"
            )

            if not (
                extensao_valida
                or imagem_valida
            ):
                continue

            dados = baixar_arquivo_bytes(
                service,
                arquivo["id"],
            )

            if dados:

                print(
                    f"Logo carregado: {arquivo['name']}",
                    flush=True,
                )

                return dados

        return None

    except Exception as erro:

        print(
            f"Erro ao carregar logo: {erro}",
            flush=True,
        )

        return None


# =============================================================================
# GERAR ZIP EM MEMÓRIA
# =============================================================================

def gerar_zip_fotos(
    fotos_tratadas,
    codigo_imovel,
):
    """
    Recebe uma lista de fotos tratadas e
    gera um ZIP totalmente em memória.

    Não cria arquivo físico no servidor.
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

            for item in fotos_tratadas:

                nome = item.get(
                    "nome",
                    "foto.jpg",
                )

                dados = item.get(
                    "dados",
                )

                if not dados:
                    continue

                if isinstance(
                    dados,
                    io.BytesIO,
                ):
                    dados.seek(0)
                    conteudo = dados.read()

                elif isinstance(
                    dados,
                    (bytes, bytearray),
                ):
                    conteudo = bytes(
                        dados
                    )

                else:
                    continue

                zip_file.writestr(
                    nome,
                    conteudo,
                )

        zip_buffer.seek(0)

        return zip_buffer

    except Exception as erro:

        print(
            f"Erro ao gerar ZIP: {erro}",
            flush=True,
        )

        try:
            zip_buffer.close()
        except Exception:
            pass

        return None


# =============================================================================
# EXECUÇÃO DO TRATAMENTO DO IMÓVEL
# =============================================================================

def executar_tratamento_imovel(
    service,
    codigo_imovel,
    logo_bytes=None,
):
    """
    Busca as fotos no Google Drive,
    trata as imagens e devolve um ZIP
    em memória.

    Nenhum arquivo tratado é enviado
    de volta ao Google Drive.
    """

    from drive_service import (
        encontrar_pasta_imovel,
        listar_itens_pasta,
        baixar_foto_bytes,
    )

    codigo_imovel = str(
        codigo_imovel
    ).strip().upper()

    if not codigo_imovel:
        return None

    if service is None:
        return None

    # --------------------------------------------------------
    # LOCALIZA IMÓVEL
    # --------------------------------------------------------

    id_pasta_imovel = encontrar_pasta_imovel(
        service,
        codigo_imovel,
    )

    if not id_pasta_imovel:
        return None

    # --------------------------------------------------------
    # CARREGAR LOGO
    # --------------------------------------------------------

    if logo_bytes is None:

        logo_bytes = obter_logo_bytes(
            service
        )

    # --------------------------------------------------------
    # LISTAR FOTOS ORIGINAIS
    # --------------------------------------------------------

    arquivos = listar_itens_pasta(
        service,
        id_pasta_imovel,
    )

    imagens = []

    for arquivo in arquivos:

        mime_type = arquivo.get(
            "mimeType",
            "",
        )

        nome = arquivo.get(
            "name",
            "",
        ).lower()

        if mime_type == (
            "application/vnd.google-apps.folder"
        ):
            continue

        if mime_type.startswith(
            "image/"
        ):
            imagens.append(
                arquivo
            )
            continue

        if nome.endswith(
            (
                ".jpg",
                ".jpeg",
                ".png",
                ".webp",
                ".heic",
                ".heif",
            )
        ):
            imagens.append(
                arquivo
            )

    imagens.sort(
        key=lambda item: item.get(
            "name",
            "",
        ).lower()
    )

    if not imagens:
        return None

    # --------------------------------------------------------
    # PROCESSAMENTO
    # --------------------------------------------------------

    fotos_tratadas = []

    for indice, arquivo in enumerate(
        imagens,
        start=1,
    ):

        file_id = arquivo.get(
            "id"
        )

        nome_original = arquivo.get(
            "name",
            f"foto_{indice}",
        )

        stream_bruto = None
        stream_tratado = None

        try:

            if not file_id:
                continue

            stream_bruto = baixar_foto_bytes(
                service,
                file_id,
            )

            if not stream_bruto:
                continue

            stream_tratado = processar_foto_bytes(
                stream_bruto,
                logo_bytes,
                codigo_imovel,
            )

            if not stream_tratado:
                continue

            nome_base = os.path.splitext(
                nome_original
            )[0]

            nome_saida = (
                f"{nome_base}.jpg"
            )

            # ------------------------------------------------
            # COPIA OS BYTES PARA O RESULTADO
            # ------------------------------------------------

            stream_tratado.seek(0)

            dados_foto = (
                stream_tratado.read()
            )

            if not dados_foto:
                continue

            fotos_tratadas.append(
                {
                    "nome": nome_saida,
                    "dados": dados_foto,
                }
            )

        except Exception as erro:

            print(
                f"Erro na foto {nome_original}: {erro}",
                flush=True,
            )

        finally:

            if (
                stream_bruto is not None
                and hasattr(
                    stream_bruto,
                    "close",
                )
            ):
                try:
                    stream_bruto.close()
                except Exception:
                    pass

            if (
                stream_tratado is not None
                and hasattr(
                    stream_tratado,
                    "close",
                )
            ):
                try:
                    stream_tratado.close()
                except Exception:
                    pass

    if not fotos_tratadas:
        return None

    # --------------------------------------------------------
    # GERA ZIP
    # --------------------------------------------------------

    zip_buffer = gerar_zip_fotos(
        fotos_tratadas,
        codigo_imovel,
    )

    # --------------------------------------------------------
    # LIBERA MEMÓRIA DAS FOTOS INDIVIDUAIS
    # --------------------------------------------------------

    fotos_tratadas.clear()

    return zip_buffer


# =============================================================================
# CONEXÃO COM GOOGLE DRIVE
# =============================================================================

def obter_service():
    """
    Cria a conexão com o Google Drive usando
    os secrets do Streamlit.
    """

    try:

        import streamlit as st

        creds_dict = dict(
            st.secrets[
                "google_credentials"
            ]
        )

        from google.oauth2 import (
            service_account,
        )

        from googleapiclient.discovery import (
            build,
        )

        from drive_service import SCOPES

        creds = (
            service_account
            .Credentials
            .from_service_account_info(
                creds_dict,
                scopes=SCOPES,
            )
        )

        return build(
            "drive",
            "v3",
            credentials=creds,
        )

    except Exception as erro:

        print(
            f"Erro na conexão com Google Drive: {erro}",
            flush=True,
        )

        return None


# =============================================================================
# ENTRADA PRINCIPAL DO APP
# =============================================================================

def tratar(
    codigo_imovel,
    service=None,
    logo_bytes=None,
):
    """
    Trata as fotos do imóvel e devolve
    o ZIP em memória.
    """

    try:

        codigo_imovel = str(
            codigo_imovel
        ).strip().upper()

        if not codigo_imovel:
            return None

        if service is None:

            service = obter_service()

        if service is None:
            return None

        return executar_tratamento_imovel(
            service,
            codigo_imovel,
            logo_bytes,
        )

    except Exception as erro:

        print(
            f"Erro no tratamento: {erro}",
            flush=True,
        )

        return None


def tratar_fotos(
    codigo_imovel,
    service=None,
    logo_bytes=None,
):
    """
    Compatibilidade com o restante do aplicativo.
    """

    return tratar(
        codigo_imovel,
        service=service,
        logo_bytes=logo_bytes,
    )