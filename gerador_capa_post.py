# -*- coding: utf-8 -*-

"""
Gerador de Capa para Post (1080x1350)
Gera a capa para feed/post do imóvel.
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
# CAPA PARA POST
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

    # -------------------------------------------------------------------------
    # Cálculo dinâmico dos tamanhos de fonte (Destaque e Nome)
    # -------------------------------------------------------------------------
    texto_destaque = ctx.get("titulo_2", "")
    tam_destaque = len(texto_destaque)

    if tam_destaque > 12:
        tam_fonte_destaque = "45px"
    elif tam_destaque > 8:
        tam_fonte_destaque = "55px"
    else:
        tam_fonte_destaque = "75px"

    texto_nome = ctx.get("titulo_3", "")
    tam_nome = len(texto_nome)

    if tam_nome > 20:
        tam_fonte_nome = "28px"
    elif tam_nome > 12:
        tam_fonte_nome = "32px"
    else:
        tam_fonte_nome = "38px"

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

    /* Camada retangular branca de fundo parcial */
    .card-fundo {{
        position: absolute;
        left: 0;
        bottom: 445px;
        width: 780px;
        height: 40px;
        background: {COR_OFF_WHITE};
        z-index: 2;
    }}

    /* Card azul principal */
    .card-azul {{
        position: absolute;
        left: 0;
        bottom: 50px;
        width: 900px;
        height: 420px;
        background: {COR_AZUL_ESCURO};
        z-index: 3;
        padding: 40px 48px 0 48px;
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
        max-width: 460px; /* Margem ajustada para dar espaço à lista */
    }}

    .coluna-direita {{
        display: flex;
        align-items: flex-start;
        justify-content: flex-end;
        padding-top: 2px;
    }}

    .titulo {{
        line-height: 1.15;
    }}

    .tipo {{
        display: block;
        font-family: 'Cormorant Garamond', Georgia, serif;
        font-size: 50px;
        font-weight: 500;
        letter-spacing: -1px;
        text-transform: uppercase;
    }}

    .destaque {{
        display: block;
        font-family: 'Cormorant Garamond', Georgia, serif;
        font-size: {tam_fonte_destaque}; /* Ajuste dinâmico */
        font-weight: 500;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        color: {COR_OFF_WHITE};
        word-wrap: break-word;
    }}

    .nome {{
        display: block;
        margin-top: 4px;
        font-size: {tam_fonte_nome}; /* Ajuste dinâmico */
        color: {COR_OFF_WHITE};
        font-weight: 400;
    }}

    .local {{
        position: absolute;
        left: 48px;
        bottom: 70px;
        font-size: 20px;
        letter-spacing: 1.2px;
        color: {COR_AZUL_SUAVE};
        display: flex;
        align-items: center;
        gap: 8px;
    }}

    .local svg, .local img, .local i {{
        width: 22px;
        height: 22px;
        flex-shrink: 0;
    }}

    /* ----- Badge / Pill do Preço ----- */

    .pill-preco {{
        position: absolute;
        right: -20px;
        top: 20px;
        background: #E2E8F0;
        color: {COR_AZUL_ESCURO};
        font-size: 60px;
        font-weight: 800;
        letter-spacing: -3px;
        padding: 16px 28px;
        border-radius: 8px;
        white-space: nowrap;
        line-height: 1;
        text-align: center;
        z-index: 4;
    }}

    /* ----- Specs em Lista Vertical (Posicionado abaixo do Preço) ----- */

    .specs {{
        position: absolute;
        left: 530px;
        top: 140px;
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        gap: 8px;
        font-size: 30px;
        font-weight: 600;
        color: #E2E8F0;
        letter-spacing: 0.5px;
        z-index: 4;
    }}

    .specs div {{
        display: flex;
        align-items: center;
        white-space: nowrap;
    }}

    .specs div::before {{
        content: "•";
        margin-right: 8px;
        color: {COR_AZUL_SUAVE};
        font-size: 24px;
        font-weight: bold;
    }}

    /* ----- Rodapé fixo ----- */

    .rodape {{
        position: absolute;
        bottom: 0;
        left: 48px;
        right: 48px;
        padding: 16px 0 20px 0;
        border-top: 1px solid rgba(226, 232, 240, 0.25);
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 13px;
        letter-spacing: 1.8px;
        font-weight: 600;
        text-transform: uppercase;
    }}

    .rodape-esquerda {{
        color: {COR_OFF_WHITE};
    }}

    .rodape-direita {{
        color: {COR_AZUL_SUAVE};
        font-weight: 600;
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

            <!-- Lista de Especificações posicionada abaixo do preço -->
            <div class="specs">
                <div>{ctx['dormitorios']} dorm.</div>
                <div>{ctx['vagas']} vagas</div>
                <div>{ctx['area']} const.</div>
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
