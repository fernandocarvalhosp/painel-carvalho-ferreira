import io
from PIL import Image, ImageEnhance, ImageOps, ImageDraw, ImageFont

# ============================================================
# CONFIGURAÇÕES VISUAIS (Mantidas do seu padrão)
# ============================================================

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


# ============================================================
# FUNÇÕES DE TRATAMENTO EM MEMÓRIA (BytesIO)
# ============================================================

def aquecer_imagem(img, intensidade=5):
    img = img.convert("RGB")
    r, g, b = img.split()
    fator_r = 1 + (intensidade / 100)
    fator_g = 1 + (intensidade / 300)
    r = r.point(lambda p: min(255, int(p * fator_r)))
    g = g.point(lambda p: min(255, int(p * fator_g)))
    return Image.merge("RGB", (r, g, b))


def aplicar_logo_bytes(img, logo_bytes):
    """Aplica o logo utilizando os bytes baixados da pasta MARCA/LOGO"""
    if not logo_bytes:
        return img
   
    logo = Image.open(logo_bytes).convert("RGBA")
    largura_logo = int(img.width * TAMANHO_LOGO)
    proporcao = largura_logo / logo.width
    altura_logo = int(logo.height * proporcao)
   
    logo = logo.resize((largura_logo, altura_logo), Image.Resampling.LANCZOS)
   
    alpha = logo.getchannel("A")
    alpha = alpha.point(lambda p: int(p * OPACIDADE_LOGO))
    logo.putalpha(alpha)
   
    x = img.width - largura_logo - MARGEM_LOGO
    y = img.height - altura_logo - MARGEM_LOGO
   
    img = img.convert("RGBA")
    img.alpha_composite(logo, (x, y))
    return img.convert("RGB")


def aplicar_codigo(img, codigo):
    if not codigo:
        return img

    img = img.convert("RGBA")
    draw = ImageDraw.Draw(img)
   
    # Tentativa de carregar fonte padrão do sistema ou fallback
    try:
        fonte = ImageFont.truetype("arial.ttf", TAMANHO_CODIGO)
    except Exception:
        fonte = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), codigo, font=fonte)
    largura_texto = bbox[2] - bbox[0]
    altura_texto = bbox[3] - bbox[1]

    x = MARGEM_CODIGO
    y = img.height - altura_texto - MARGEM_CODIGO

    camada = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw_camada = ImageDraw.Draw(camada)
    alpha = int(255 * OPACIDADE_CODIGO)

    draw_camada.text(
        (x, y),
        codigo,
        font=fonte,
        fill=(COR_CODIGO[0], COR_CODIGO[1], COR_CODIGO[2], alpha)
    )

    img.alpha_composite(camada)
    return img.convert("RGB")


def processar_foto_bytes(input_bytes, logo_bytes, codigo):
    """
    Processa a imagem recebida em bytes (RAM) e retorna os bytes da imagem tratada.
    """
    try:
        img = Image.open(input_bytes)
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")

        # Redimensionamento
        img.thumbnail((MAX_LARGURA, MAX_ALTURA), Image.Resampling.LANCZOS)

        # Ajustes fotográficos
        img = ImageEnhance.Color(img).enhance(SATURACAO)
        img = ImageEnhance.Contrast(img).enhance(CONTRASTE)
        img = aquecer_imagem(img, TEMPERATURA)
        img = ImageEnhance.Sharpness(img).enhance(NITIDEZ)

        # Identidade visual
        img = aplicar_logo_bytes(img, logo_bytes)
        img = aplicar_codigo(img, codigo)

        # Salvar para um buffer de memória (BytesIO) em formato JPEG
        output_buffer = io.BytesIO()
        img.save(output_buffer, "JPEG", quality=95, optimize=True)
        output_buffer.seek(0)
       
        return output_buffer

    except Exception as erro:
        print(f"❌ Erro no processamento da imagem: {erro}")
        return None


# ============================================================
# ORQUESTRADOR PRINCIPAL DO DRIVE
# ============================================================

def executar_tratamento_imovel(service, codigo_imovel, logo_bytes):
    """
    1. Localiza a pasta do imóvel pelo prefixo (ex: CF001)
    2. Lê as fotos brutas da raiz da pasta
    3. Cria a pasta 'FOTOS TRATADAS' se não existir
    4. Processa uma a uma e envia o resultado para o Drive
    """
    from drive_service import encontrar_pasta_imovel, criar_pasta_se_nao_existir, baixar_foto_bytes, enviar_foto_tratada

    # 1. Encontrar pasta do imóvel
    id_pasta_imovel = encontrar_pasta_imovel(service, codigo_imovel)
    if not id_pasta_imovel:
        print(f"❌ Pasta do imóvel com código {codigo_imovel} não encontrada no Drive.")
        return False

    # 2. Criar ou obter a subpasta 'FOTOS TRATADAS'
    id_pasta_tratadas = criar_pasta_se_nao_existir(service, "FOTOS TRATADAS", id_pasta_imovel)

    # 3. Listar arquivos na pasta raiz do imóvel (fotos brutas)
    query = f"'{id_pasta_imovel}' in parents and mimeType contains 'image/' and trashed = false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    arquivos = results.get('files', [])

    if not arquivos:
        print(f"⚠️ Nenhuma foto encontrada na pasta do imóvel {codigo_imovel}.")
        return False

    sucesso = 0
    total = len(arquivos)

    print(f"✓ Encontradas {total} fotos para o imóvel {codigo_imovel}. Iniciando processamento...")

    for i, arquivo in enumerate(arquivos, start=1):
        file_id = arquivo['id']
        nome_original = arquivo['name']
       
        print(f"[{i}/{total}] Baixando e tratando: {nome_original}")

        # Baixa os bytes da foto bruta
        stream_bruto = baixar_foto_bytes(service, file_id)

        # Processa a foto em memória
        stream_tratado = processar_foto_bytes(stream_bruto, logo_bytes, codigo_imovel)

        if stream_tratado:
            # Define o nome de saída (garantindo extensão .jpg)
            nome_saida = f"{os.path.splitext(nome_original)[0]}.jpg"
           
            # Envia para a pasta 'FOTOS TRATADAS' no Drive
            enviar_foto_tratada(service, id_pasta_tratadas, nome_saida, stream_tratado)
            sucesso += 1
            print(f"    ✓ OK")
        else:
            print(f"    ✗ ERRO")

    print(f"\nProcessamento concluído! {sucesso}/{total} fotos tratadas e salvas em 'FOTOS TRATADAS'.")
    return True