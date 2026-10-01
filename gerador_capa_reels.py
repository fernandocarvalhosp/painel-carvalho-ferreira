# -*- coding: utf-8 -*-

"""
Gerador de Capa para Reels (1080x1920)
Gera apenas 1 capa vertical (primeira foto da pasta) para usar em Reels.
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
# CAPA PARA REELS
# =============================================================================

def gerar_capa_reels(
    ctx,
    fotos,
):

    foto = fotos[0]

    nome_html = (
        f"<span class='nome'>{ctx['titulo_3']}</span>"
        if ctx["titulo_3"]
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
        size: 1080px 1920px;
        margin: 0;
    }}

    * {{
        box-sizing: border-box;
    }}

    body {{
        margin: 0;
        width: 1080px;
        height: 1920px;
        background: {COR_OFF_WHITE};
        overflow: hidden;
        font-family: 'Manrope', Arial, sans-serif;
    }}

    .foto {{
        position: absolute;
        top: 0;
        left: 0;
        width: 1080px;
        height: 1920px;
        object-fit: cover;
    }}

    .card-fundo {{
        position: absolute;
        left: 0;
        bottom: 70px;
        width: 780px;
        height: 420px;
        background: {COR_OFF_WHITE};
        z-index: 2;
    }}

    .card-azul {{
        position: absolute;
        left: 0;
        bottom: 51px;
        width: 900px;
        height: 400px;
        background: {COR_AZUL_ESCURO};
        z-index: 3;
        padding: 42px 50px 0 50px;
        color: {COR_OFF_WHITE};
        display: flex;
        flex-direction: column;
    }}

    /* ----- Conteúdo principal ----- */

    .topo {{
        display: flex;
        flex-direction: row;
        align-items: flex-start;
        gap: 28px;
        min-height: 0;
    }}

    .coluna-esquerda {{
        flex: 1;
        min-width: 0;
        max-width: 480px;
    }}

    .coluna-direita {{
        flex-shrink: 0;
        width: 300px;
        display: flex;
        justify-content: flex-end;
        padding-top: 6px;
    }}

    .titulo {{
        line-height: 1.1;
    }}

    .tipo {{
        display: block;
        font-family: 'Cormorant Garamond', Georgia, serif;
        font-size: 38px;
        font-weight: 500;
        letter-spacing: 1.5px;
        text-transform: uppercase;
    }}

    .destaque {{
        display: block;
        font-family: 'Cormorant Garamond', Georgia, serif;
        font-size: 44px;
        font-weight: 500;
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
        margin-top: 18px;
        font-size: 17px;
        letter-spacing: 1px;
        text-transform: uppercase;
        color: {COR_AZUL_SUAVE};
        display: flex;
        align-items: center;
        gap: 8px;
    }}

    /* ----- Pill do preço ----- */

    .pill-preco {{
        background: {COR_OFF_WHITE};
        color: {COR_AZUL_ESCURO};
        font-size: 34px;
        font-weight: 700;
        letter-spacing: -0.3px;
        padding: 14px 26px;
        border-radius: 10px;
        white-space: nowrap;
        line-height: 1.15;
        text-align: center;
        max-width: 300px;
    }}

    /* ----- Specs em linha ----- */

    .specs {{
        margin-top: 28px;
        font-size: 18px;
        font-weight: 500;
        color: #E2E8F0;
        text-align: center;
        letter-spacing: 0.3px;
    }}

    .specs span + span::before {{
        content: "·";
        margin: 0 12px;
        color: {COR_AZUL_SUAVE};
    }}

    /* ----- Rodapé fixo ----- */

    .rodape {{
        margin-top: auto;
        padding: 16px 0 20px 0;
        border-top: 1px solid rgba(148, 163, 184, 0.35);
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 13px;
        letter-spacing: 1.5px;
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

                <div class="coluna-direita">
                    <div class="pill-preco">
                        {ctx['valor']}
                    </div>
                </div>

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
        1920,
    )

    return [
        (
            f"capa_reels_{ctx['codigo']}.png",
            png,
        )
    ]


# =============================================================================
# GERADOR PRINCIPAL — CAPA PARA REELS
# =============================================================================

def gerar_capa_para_reels(
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

    arquivos = gerar_capa_reels(
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
        "SUCESSO: Capa para Reels gerada com sucesso.",
        flush=True,
    )

    return zip_buffer.getvalue()
