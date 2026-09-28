# -*- coding: utf-8 -*-

"""
Gerador de Posts / Carrossel (1080x1350)
Gera apenas: capa + fotos + ficha técnica + lâmina final.
"""

import io
import zipfile

from utils_geradores import (
    COR_AZUL_ESCURO,
    COR_AZUL_BLOCO,
    COR_OFF_WHITE,
    COR_AZUL_SUAVE,
    COR_LINHA,
    conectar_google,
    imagem_uri,
    renderizar_png,
    montar_contexto,
)


# =============================================================================
# CSS CARD PRINCIPAL
# =============================================================================

def css_card_principal():

    return f"""
    .card-fundo {{
        position: absolute;
        left: 0;
        bottom: 0px;
        width: 775px;
        height: 397px;
        background: {COR_OFF_WHITE};
        z-index: 2;
    }}

    .card-azul {{
        position: absolute;
        left: 0;
        bottom: 36px;
        width: 875px;
        height: 341px;
        background: {COR_AZUL_ESCURO};
        z-index: 3;
        padding: 48px 55px 38px 55px;
        color: {COR_OFF_WHITE};
    }}

    .card-conteudo {{
        position: relative;
        z-index: 5;
    }}
    """


# =============================================================================
# LÂMINA DE CAPA
# =============================================================================

def gerar_lamina_capa(
    ctx,
    foto,
):

    nome_html = (
        f"<span class='nome'>{ctx['titulo_3']}</span>"
        if ctx["titulo_3"]
        else ""
    )

    foto_uri = imagem_uri(
        foto["bytes"],
        foto["nome"],
    )

    condominio_html = (
        f"<div class='condominio-texto'>Condomínio: {ctx['condominio']}</div>"
        if ctx["condominio"] and ctx["condominio"] != "-"
        else ""
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
        padding: 20px;
        box-sizing: border-box;
        object-fit: contain;
        display: block;
    }}

    {css_card_principal()}

    .titulo {{
        font-size: 39px;
        line-height: 1.15;
        margin: 0;
    }}

    .tipo {{
        display: block;
        font-family: 'Cormorant Garamond', Georgia, serif;
        font-size: 38px;
        font-weight: 500;
        letter-spacing: 2px;
        text-transform: uppercase;
        color: {COR_OFF_WHITE};
    }}

    .destaque {{
        display: block;
        font-family: 'Cormorant Garamond', Georgia, serif;
        font-size: 45px;
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
    }}

    .local {{
        margin-top: 24px;
        font-size: 18px;
        letter-spacing: 1px;
        text-transform: uppercase;
        color: {COR_AZUL_SUAVE};
        display: flex;
        align-items: center;
        gap: 9px;
    }}

    .valor {{
        margin-top: 23px;
        font-size: 43px;
        font-weight: 600;
        color: {COR_OFF_WHITE};
    }}

    .condominio-texto {{
        margin-top: 4px;
        font-size: 16px;
        color: {COR_AZUL_SUAVE};
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}

    .linha {{
        width: 100%;
        height: 1px;
        background: {COR_LINHA};
        margin-top: 27px;
        margin-bottom: 19px;
    }}

    .rodape {{
        font-size: 13px;
        letter-spacing: 1.8px;
    }}

    .marca {{
        float: left;
        color: {COR_OFF_WHITE};
        font-weight: 600;
    }}

    .deslize {{
        float: right;
        color: {COR_AZUL_SUAVE};
        font-weight: 500;
    }}

    </style>
    </head>

    <body>

        <img class="foto" src="{foto_uri}">

        <div class="card-fundo"></div>

        <div class="card-azul">

            <div class="card-conteudo">

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

                <div class="valor">
                    {ctx['valor']}
                </div>

                {condominio_html}

                <div class="linha"></div>

                <div class="rodape">

                    <span class="marca">
                        CARVALHO FERREIRA
                    </span>

                    <span class="deslize">
                        DESLIZE PARA CONHECER
                    </span>

                </div>

            </div>

        </div>

    </body>
    </html>
    """

    return renderizar_png(
        html,
        1080,
        1350,
    )


# =============================================================================
# LÂMINAS DE FOTO
# =============================================================================

def gerar_lamina_foto(
    ctx,
    foto,
):

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

    .barra-inferior {{
        position: absolute;
        bottom: 0;
        left: 0;
        width: 100%;
        height: 90px;
        background: {COR_AZUL_ESCURO};
        color: {COR_OFF_WHITE};
        padding: 31px 55px;
    }}

    .marca {{
        font-size: 13px;
        font-weight: 600;
        letter-spacing: 2px;
    }}

    </style>
    </head>

    <body>

        <img class="foto" src="{foto_uri}">

        <div class="barra-inferior">
            <div class="marca">
                CARVALHO FERREIRA
            </div>
        </div>

    </body>
    </html>
    """

    return renderizar_png(
        html,
        1080,
        1350,
    )


# =============================================================================
# FICHA TÉCNICA
# =============================================================================

def gerar_lamina_ficha(
    ctx,
):

    cards_html = ""

    for item in ctx["ficha_tecnica"]:

        cards_html += f"""
        <div class="card">

            <div class="icone">
                {item["icone"]}
            </div>

            <div class="label">
                {item["label"]}
            </div>

            <div class="valor">
                {item["valor"]}
            </div>

        </div>
        """

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
        padding: 70px 65px;
        background: {COR_AZUL_ESCURO};
        color: {COR_OFF_WHITE};
        font-family: 'Manrope', Arial, sans-serif;
        overflow: hidden;
    }}

    .titulo {{
        font-size: 39px;
        font-weight: 500;
        letter-spacing: 2px;
        margin-bottom: 55px;
    }}

    .grid {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 22px;
        width: 100%;
    }}

    .card {{
        height: 245px;
        background: {COR_AZUL_BLOCO};
        padding: 30px 32px;
        color: {COR_OFF_WHITE};
        position: relative;
        overflow: hidden;
    }}

    .icone {{
        height: 34px;
        margin-bottom: 26px;
    }}

    .icone svg {{
        width: 31px;
        height: 31px;
    }}

    .label {{
        font-size: 15px;
        letter-spacing: 2px;
        text-transform: uppercase;
        color: {COR_AZUL_SUAVE};
        font-weight: 500;
    }}

    .valor {{
        margin-top: 9px;
        font-size: 37px;
        font-weight: 600;
        color: {COR_OFF_WHITE};
        line-height: 1;
    }}

    .rodape {{
        position: absolute;
        left: 65px;
        right: 65px;
        bottom: 50px;
        padding-top: 22px;
        border-top: 1px solid #D8DDE2;
        font-size: 13px;
        letter-spacing: 2px;
        color: {COR_AZUL_SUAVE};
        text-transform: uppercase;
    }}

    </style>
    </head>

    <body>

        <div class="titulo">
            ESPECIFICACOES
        </div>

        <div class="grid">

            {cards_html}

        </div>

        <div class="rodape">
            CARVALHO FERREIRA • CONSULTORIA IMOBILIARIA
        </div>

    </body>
    </html>
    """

    return renderizar_png(
        html,
        1080,
        1350,
    )


# =============================================================================
# LÂMINA FINAL
# =============================================================================

def gerar_lamina_final(
    ctx,
):

    logo_html = ""

    if ctx.get(
        "logo_uri"
    ):

        logo_html = (
            '<img class="logo" '
            f'src="{ctx["logo_uri"]}">'
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
        background: {COR_AZUL_ESCURO};
        font-family: 'Manrope', Arial, sans-serif;
        text-align: center;
        position: relative;
        overflow: hidden;
    }}

    .topo {{
        position: absolute;
        top: 100px;
        left: 80px;
        right: 80px;
    }}

    .logo {{
        max-width: 300px;
        max-height: 125px;
        display: block;
        margin: 0 auto 22px;
    }}

    .submarca {{
        font-size: 15px;
        letter-spacing: 3px;
        color: {COR_OFF_WHITE};
        text-transform: uppercase;
        font-weight: 600;
    }}

    .centro {{
        position: absolute;
        top: 50%;
        left: 80px;
        right: 80px;
        transform: translateY(-35%);
    }}

    .titulo {{
        font-family: 'Cormorant Garamond', Georgia, serif;
        font-size: 55px;
        line-height: 1.2;
        color: {COR_OFF_WHITE};
        font-weight: 600;
        letter-spacing: 1px;
    }}

    .linha {{
        width: 75px;
        height: 2px;
        background: {COR_OFF_WHITE};
        margin: 30px auto 0;
    }}

    </style>
    </head>

    <body>

        <div class="topo">

            {logo_html}

            <div class="submarca">
                CARVALHO FERREIRA • CONSULTORIA IMOBILIARIA
            </div>

        </div>

        <div class="centro">

            <div class="titulo">
                TALVEZ ESTE SEJA O IMOVEL.<br>
                QUE VOCE ESTAVA PROCURANDO.
            </div>

            <div class="linha"></div>

        </div>

    </body>
    </html>
    """

    return renderizar_png(
        html,
        1080,
        1350,
    )


# =============================================================================
# GERADOR PRINCIPAL — APENAS CARROSSEL
# =============================================================================

def gerar_carrossel(
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

    codigo = ctx["codigo"]

    arquivos = []

    # -------------------------------------------------------------------------
    # CAPA
    # -------------------------------------------------------------------------

    arquivos.append(
        (
            f"carrossel_{codigo}_01.png",
            gerar_lamina_capa(
                ctx,
                fotos[0],
            ),
        )
    )

    # -------------------------------------------------------------------------
    # FOTOS DO CARROSSEL (todas as fotos restantes da pasta)
    # -------------------------------------------------------------------------

    numero = 2

    for foto in fotos[1:]:

        arquivos.append(
            (
                f"carrossel_{codigo}_{numero:02d}.png",
                gerar_lamina_foto(
                    ctx,
                    foto,
                )
            )
        )

        numero += 1

    # -------------------------------------------------------------------------
    # FICHA TÉCNICA
    # -------------------------------------------------------------------------

    arquivos.append(
        (
            f"carrossel_{codigo}_{numero:02d}.png",
            gerar_lamina_ficha(
                ctx
            ),
        )
    )

    numero += 1

    # -------------------------------------------------------------------------
    # LÂMINA FINAL
    # -------------------------------------------------------------------------

    arquivos.append(
        (
            f"carrossel_{codigo}_{numero:02d}.png",
            gerar_lamina_final(
                ctx
            ),
        )
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
        "SUCESSO: Carrossel gerado com sucesso.",
        flush=True,
    )

    return zip_buffer.getvalue()
