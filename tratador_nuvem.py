# -*- coding: utf-8 -*-
import io
import os

from PIL import Image, ImageEnhance, ImageOps, ImageDraw, ImageFont


SATURACAO = 1.00
CONTRASTE = 1.02
TEMPERATURA = 5
NITIDEZ = 1.05

MAX_LARGURA = 2400
MAX_ALTURA = 3000

TAMANHO_LOGO = 0.085
OPACIDADE_LOGO = 0.65
MARGEM_LOGO = 30

TAMANHO_CODIGO = 24
OPACIDADE_CODIGO = 0.55
MARGEM_CODIGO = 30
COR_CODIGO = (255, 255, 255)


def aquecer_imagem(img, intensidade=5):
    img = img.convert("RGB")
    r, g, b = img.split()
    fator_r = 1 + (intensidade / 100)
    fator_g = 1 + (intensidade / 300)
    r = r.point(lambda p: min(255, int(p * fator_r)))
    g = g.point(lambda p: min(255, int(p * fator_g)))
    return Image.merge("RGB", (r, g, b))


def aplicar_logo_bytes(img, logo_bytes):
    if not logo_bytes:
        return img

    try:
        if isinstance(logo_bytes, io.BytesIO):
            logo_bytes.seek(0)

        logo = Image.open(logo_bytes).convert("RGBA")
        largura_logo = int(img.width * TAMANHO_LOGO)

        if largura_logo <= 0 or logo.width <= 0:
            return img

        proporcao = largura_logo / logo.width
        altura_logo = int(logo.height * proporcao)
        logo = logo.resize(
            (largura_logo, altura_logo),
            Image.Resampling.LANCZOS,
        )

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


def aplicar_codigo(img, codigo):
    if not codigo:
        return img

    img = img.convert("RGBA")
    draw = ImageDraw.Draw(img)

    try:
        fonte = ImageFont.truetype("arial.ttf", TAMANHO_CODIGO)
    except Exception:
        fonte = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), codigo, font=fonte)
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
        codigo,
        font=fonte,
        fill=(COR_CODIGO[0], COR_CODIGO[1], COR_CODIGO[2], alpha),
    )

    img.alpha_composite(camada)
    return img.convert("RGB")


def processar_foto_bytes(input_bytes, logo_bytes, codigo):
    """
    Recebe a foto original em bytes e retorna a foto tratada
    em BytesIO. Nenhum arquivo temporário é criado.
    """
    try:
        if not input_bytes:
            return None

        if isinstance(input_bytes, io.BytesIO):
            input_bytes.seek(0)

        img = Image.open(input_bytes)
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")

        img.thumbnail(
            (MAX_LARGURA, MAX_ALTURA),
            Image.Resampling.LANCZOS,
        )

        img = ImageEnhance.Color(img).enhance(SATURACAO)
        img = ImageEnhance.Contrast(img).enhance(CONTRASTE)
        img = aquecer_imagem(img, TEMPERATURA)
        img = ImageEnhance.Sharpness(img).enhance(NITIDEZ)

        img = aplicar_logo_bytes(img, logo_bytes)
        img = aplicar_codigo(img, codigo)

        output_buffer = io.BytesIO()
        img.save(
            output_buffer,
            format="JPEG",
            quality=95,
            optimize=True,
        )
        output_buffer.seek(0)

        try:
            img.close()
        except Exception:
            pass

        return output_buffer

    except Exception as erro:
        print(f"Erro no processamento da imagem: {erro}", flush=True)
        return None


def executar_tratamento_imovel(service, codigo_imovel, logo_bytes):
    """
    Google Drive -> RAM -> PIL -> RAM -> Google Drive.

    Nenhuma foto tratada é salva em disco local.
    """
    from drive_service import (
        encontrar_pasta_imovel,
        criar_pasta_se_nao_existir,
        baixar_foto_bytes,
        enviar_foto_tratada,
    )

    codigo_imovel = str(codigo_imovel).strip().upper()

    id_pasta_imovel = encontrar_pasta_imovel(
        service,
        codigo_imovel,
    )

    if not id_pasta_imovel:
        print(
            f"Pasta do imóvel {codigo_imovel} não encontrada.",
            flush=True,
        )
        return False

    id_pasta_tratadas = criar_pasta_se_nao_existir(
        service,
        "FOTOS TRATADAS",
        id_pasta_imovel,
    )

    if not id_pasta_tratadas:
        print(
            f"Não foi possível criar/encontrar FOTOS TRATADAS "
            f"para {codigo_imovel}.",
            flush=True,
        )
        return False

    query = (
        f"'{id_pasta_imovel}' in parents "
        f"and mimeType contains 'image/' "
        f"and trashed = false"
    )

    results = service.files().list(
        q=query,
        fields="files(id, name, mimeType)",
        orderBy="name",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()

    arquivos = results.get("files", [])

    if not arquivos:
        print(
            f"Nenhuma foto encontrada para {codigo_imovel}.",
            flush=True,
        )
        return False

    sucesso = 0
    total = len(arquivos)

    print(
        f"Encontradas {total} fotos para {codigo_imovel}.",
        flush=True,
    )

    for i, arquivo in enumerate(arquivos, start=1):
        file_id = arquivo["id"]
        nome_original = arquivo["name"]

        stream_bruto = None
        stream_tratado = None

        try:
            print(
                f"[{i}/{total}] Tratando: {nome_original}",
                flush=True,
            )

            stream_bruto = baixar_foto_bytes(
                service,
                file_id,
            )

            if not stream_bruto:
                print("    Falha ao baixar.", flush=True)
                continue

            stream_tratado = processar_foto_bytes(
                stream_bruto,
                logo_bytes,
                codigo_imovel,
            )

            if not stream_tratado:
                print("    Falha no tratamento.", flush=True)
                continue

            nome_saida = (
                f"{os.path.splitext(nome_original)[0]}.jpg"
            )

            enviado = enviar_foto_tratada(
                service,
                id_pasta_tratadas,
                nome_saida,
                stream_tratado,
            )

            if enviado:
                sucesso += 1
                print("    OK", flush=True)
            else:
                print("    Falha ao enviar.", flush=True)

        except Exception as erro:
            print(
                f"    Erro na foto '{nome_original}': {erro}",
                flush=True,
            )

        finally:
            if stream_bruto is not None and hasattr(
                stream_bruto, "close"
            ):
                try:
                    stream_bruto.close()
                except Exception:
                    pass

            if stream_tratado is not None and hasattr(
                stream_tratado, "close"
            ):
                try:
                    stream_tratado.close()
                except Exception:
                    pass

    print(
        f"Processamento concluído: {sucesso}/{total} fotos.",
        flush=True,
    )

    return sucesso > 0


def tratar(codigo_imovel, service=None, logo_bytes=None):
    """
    Entrada principal usada pelo App.
    """
    try:
        if service is None:
            from drive_service import conectar_drive
            service = conectar_drive()

        if service is None:
            return "Não foi possível conectar ao Google Drive."

        return executar_tratamento_imovel(
            service,
            codigo_imovel,
            logo_bytes,
        )

    except Exception as erro:
        print(
            f"Erro no tratamento de {codigo_imovel}: {erro}",
            flush=True,
        )
        return False


def tratar_fotos(codigo_imovel, service=None, logo_bytes=None):
    """Compatibilidade com chamadas antigas do aplicativo."""
    return tratar(
        codigo_imovel,
        service=service,
        logo_bytes=logo_bytes,
    )
