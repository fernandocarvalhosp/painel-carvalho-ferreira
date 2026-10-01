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
        height: 450px;
        background: {COR_OFF_WHITE};
        z-index: 2;
    }}

    .card-azul {{
        position: absolute;
        left: 0;
        bottom: 51px;
        width: 900px;
        height: 431px;
        background: {COR_AZUL_ESCURO};
        z-index: 3;
        padding: 48px 55px 0 55px;
        color: {COR_OFF_WHITE};
        display: flex;
        flex-direction: column;
    }}

    .conteudo {{
        flex: 1;
        display: flex;
        flex-direction: row;
        gap: 40px;
        min-height: 0;
    }}

    .coluna-esquerda {{
        flex: 1;
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
        min-width: 0;
    }}

    .coluna-direita {{
        width: 280px;
        flex-shrink: 0;
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
        align-items: flex-end;
        text-align: right;
    }}

    .titulo {{
        line-height: 1.12;
    }}

    .tipo {{
        display: block;
        font-family: 'Cormorant Garamond', Georgia, serif;
        font-size: 34px;
        font-weight: 500;
        letter-spacing: 2px;
        text-transform: uppercase;
    }}

    .destaque {{
        display: block;
        font-family: 'Cormorant Garamond', Georgia, serif;
        font-size: 42px;
        font-weight: 500;
        letter-spacing: 2px;
        text-transform: uppercase;
        color: {COR_OFF_WHITE};
    }}

    .nome {{
        display: block;
        margin-top: 4px;
        font-size: 28px;
        color: {COR_OFF_WHITE};
        font-weight: 400;
    }}

    .local {{
        margin-top: 22px;
        font-size: 18px;
        letter-spacing: 1px;
        text-transform: uppercase;
        color: {COR_AZUL_SUAVE};
        display: flex;
        align-items: center;
        gap: 8px;
    }}

    .valor {{
        font-size: 48px;
        font-weight: 700;
        color: {COR_OFF_WHITE};
        letter-spacing: -0.5px;
        line-height: 1.1;
    }}

    .specs {{
        margin-top: 18px;
        font-size: 18px;
        font-weight: 500;
        color: #E2E8F0;
        display: flex;
        flex-direction: column;
        gap: 8px;
        align-items: flex-end;
    }}

    .rodape {{
        flex-shrink: 0;
        margin-top: auto;
        padding: 16px 0 22px 0;
        border-top: 1px solid rgba(148, 163, 184, 0.35);
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 13px;
        letter-spacing: 1.5px;
        font-weight: 600;
        text-transform: uppercase;
        color: {COR_AZUL_SUAVE};
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

            <div class="conteudo">

                <div class="coluna-esquerda">

                    <div class="titulo">

                        <span class="tipo">
                            {ctx['titulo_1']}
                        </span>

                        <span class="destaque">
                            {ctx['titulo_2']}
                        </span>

                        {nome_html}

                    </div>

                    <div class="local">

                        {ctx['pin']}

                        <span>
                            {ctx['bairro']} • {ctx['cidade']}
                        </span>

                    </div>

                </div>

                <div class="coluna-direita">

                    <div class="valor">
                        {ctx['valor']}
                    </div>

                    <div class="specs">
                        <div>{ctx['dormitorios']} dorm.</div>
                        <div>{ctx['vagas']} vagas</div>
                        <div>{ctx['area']} const.</div>
                    </div>

                </div>

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
