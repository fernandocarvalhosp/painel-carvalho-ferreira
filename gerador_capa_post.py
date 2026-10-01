# -*- coding: utf-8 -*-

"""
Gerador de Capa para Post / Feed / Marketplace (1080x1350)
Gera apenas 1 capa na proporção 4:5 (primeira foto da pasta) para Feed e Anúncios.
"""

import io
import zipfile

from utils_geradores import (
    COR_AZUL_ESCURO,
    COR_OFF_WHITE,
    COR_AZUL_SUAVE,
    conectar_google,
    imagem_uri,
    renderizar_png,
    montar_contexto,
)


# =============================================================================
# CAPA PARA POST / FEED
# =============================================================================

def gerar_capa_post(
    ctx,
    fotos,
):

    foto = fotos[0]

    nome_html = (
        f"<span class='nome'>{ctx['titulo_3']}</span>"
        if ctx.get("titulo_3")
        else ""
    )

    foto_uri = imagem_uri(
        foto["bytes"],
        foto["nome"],
    )

    html = f"""
    <html>
    <head>
    <meta charset="UTF-8">

    <style>

    {ctx['css_fontes']}

    @page {{
        size: 1080px 1350px;
        margin: 0;
    }}

    * {{
        box-sizing: border-box;
    }}

    body {{
        margin: 0;
        width: 1080px;
        height: 1350px;
        background: {COR_OFF_WHITE};
        overflow: hidden;
        font-family: 'Manrope', Arial, sans-serif;
    }}

    .foto {{
        position: absolute;
        top: 0;
        left: 0;
        width: 1080px;
        height: 1350px;
        object-fit: cover;
    }}

    /* Camada retangular branca de fundo parcial ajustada para a altura do feed */
    .card-fundo {{
        position: absolute;
        left: 0;
        bottom: 405px;
        width: 780px;
        height: 40px;
        background: {COR_OFF_WHITE};
        z-index: 2;
    }}

    /* Card azul principal */
    .card-azul {{
        position: absolute;
        left: 0;
        bottom: 40px;
        width: 900px;
        height: 380px;
        background: {COR_AZUL_ESCURO};
        z-index: 3;
        padding: 36px 48px 0 48px;
        color: {COR_OFF_WHITE};
        display: flex;
        flex-direction: column;
        overflow: visible;
    }}

    /* ----- Conteúdo principal (Topo) ----- */

    .topo {{
        display: flex;
        flex-direction: row;
        justify-content: space-between;
        align-items: flex-start;
        width: 100%;
    }}

    .coluna-esquerda {{
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
        max-width: 530px;
    }}

    .titulo {{
        line-height: 1.15;
    }}

    .tipo {{
        display: block;
        font-family: 'Cormorant Garamond', Georgia, serif;
        font-size: 48px;
        font-weight: 500;
        letter-spacing: 1.5px;
        text-transform: uppercase;
    }}

    .destaque {{
        display: block;
        font-family: 'Cormorant Garamond', Georgia, serif;
        font-size: 52px;
        font-weight: 600;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        color: {COR_OFF_WHITE};
    }}

    .nome {{
        display: block;
        margin-top: 4px;
        font-size: 26px;
        color: {COR_OFF_WHITE};
        font-weight: 400;
    }}

    .local {{
        margin-top: 10px;
        font-size: 16px;
        letter-spacing: 1.2px;
        color: {COR_AZUL_SUAVE};
        display: flex;
        align-items: center;
        gap: 6px;
    }}

    /* ----- Badge / Pill do Preço ----- */

    .pill-preco {{
        position: absolute;
        right: -15px;
        top: 20px;
        background: #E2E8F0;
        color: {COR_AZUL_ESCURO};
        font-size: 40px;
        font-weight: 800;
        letter-spacing: -0.3px;
        padding: 14px 24px;
        border-radius: 8px;
        white-space: nowrap;
        line-height: 1;
        text-align: center;
        z-index: 4;
    }}

    /* ----- Specs em linha centralizada ----- */

    .specs {{
        position: absolute;
        top: 250px;
        left: 50%;
        transform: translateX(-50%);
        font-size: 22px;
        font-weight: 500;
        color: #E2E8F0;
        text-align: center;
        letter-spacing: 0.5px;
        white-space: nowrap;
        width: max-content;
    }}

    .specs span + span::before {{
        content: "·";
        margin: 0 10px;
        color: {COR_AZUL_SUAVE};
        font-weight: bold;
    }}

    /* ----- Rodapé fixo ----- */

    .rodape {{
        position: absolute;
        bottom: 0;
        left: 48px;
        right: 48px;
        padding: 14px 0 18px 0;
        border-top: 1px solid rgba(226, 232, 240, 0.25);
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 12px;
        letter-spacing: 1.8px;
        font-weight: 600;
        text-transform: uppercase;
    }}

    .rodape-esquerda {{
        color: {COR_OFF_WHITE};
    }}

    .rodape-direita {{
        color: {COR_AZUL_SUAVE};
        font-weight: 500;
    }}

    </style>
    </head>

    <body>

        <img class="foto" src="{foto_uri}">

        <div class="card-fundo"></div>

        <div class="card-azul">

            <div class="topo">

                <div class="coluna-esquerda">

                    <div class="titulo">
                        <span class="tipo">{ctx['titulo_1']}</span>
                        <span class="destaque">{ctx['titulo_2']}</span>
                        {nome_html}
                    </div>

                    <div class="local">
                        {ctx['pin']}
                        <span>{ctx['bairro']} • {ctx['cidade']}</span>
                    </div>

                </div>

            </div>

            <div class="pill-preco">
                {ctx['valor']}
            </div>

            <div class="specs">
                <span>{ctx['dormitorios']} dorm.</span>
                <span>{ctx['vagas']} vagas</span>
                <span>{ctx['area']} const.</span>
            </div>

            <div class="rodape">
                <span class="rodape-esquerda">CARVALHO FERREIRA</span>
                <span class="rodape-direita">Consultoria Imobiliária</span>
            </div>

        </div>

    </body>
    </html>
    """

    png = renderizar_png(
        html,
        1080,
        1350,
    )

    return [
        (
            f"capa_post_{ctx['codigo']}.png",
            png,
        )
    ]


# =============================================================================
# GERADOR PRINCIPAL — CAPA PARA POST
# =============================================================================

def gerar_capa_para_post(
    codigo_imovel,
):

    drive, sheets = conectar_google()

    if not drive or not sheets:
        return None

    ctx, fotos = montar_contexto(
        drive,
        sheets,
        codigo_imovel,
    )

    if not ctx or not fotos:
        return None

    arquivos = gerar_capa_post(
        ctx,
        fotos,
    )

    # -------------------------------------------------------------------------
    # ZIP TOTALMENTE EM MEMÓRIA
    # -------------------------------------------------------------------------

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(
        zip_buffer,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as zf:

        for nome, dados_arquivo in arquivos:

            zf.writestr(
                nome,
                dados_arquivo,
            )

    zip_buffer.seek(0)

    print(
        "SUCESSO: Capa para Post gerada com sucesso.",
        flush=True,
    )

    return zip_buffer.getvalue()
