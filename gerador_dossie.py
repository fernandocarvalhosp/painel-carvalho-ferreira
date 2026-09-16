def localizar_pastas_documentacao(service, codigo_imovel):
    """
    Localiza a estrutura documental do imóvel.

    Estrutura esperada:

    PORTFOLIO
        └── IMOVEIS
            └── [PASTA DO IMÓVEL]
                └── documentos
                    └── documentos do comprador   (opcional)

    Retorna:
        {
            "principal": ID da pasta principal de documentos,
            "comprador": ID da pasta de documentos do comprador ou None
        }
    """

    id_portfolio = buscar_id_por_nome(service, "PORTFOLIO", ID_RAIZ)

    if not id_portfolio:
        raise FileNotFoundError(
            "Pasta PORTFOLIO não encontrada no Drive."
        )

    id_imoveis = buscar_id_por_nome(
        service,
        "IMOVEIS",
        id_portfolio
    )

    if not id_imoveis:
        raise FileNotFoundError(
            "Pasta IMOVEIS não encontrada dentro de PORTFOLIO."
        )

    id_imovel = buscar_pasta_imovel(
        service,
        codigo_imovel,
        id_imoveis
    )

    if not id_imovel:
        raise FileNotFoundError(
            f"Pasta do imóvel {codigo_imovel} não encontrada."
        )

    # -----------------------------------------------------
    # PASTA PRINCIPAL DE DOCUMENTOS
    # -----------------------------------------------------

    id_documentos = buscar_id_por_nome(
        service,
        "documentos",
        id_imovel
    )

    if not id_documentos:
        id_documentos = buscar_id_por_nome(
            service,
            "documentacao",
            id_imovel
        )

    if not id_documentos:
        id_documentos = buscar_id_por_nome(
            service,
            "docs",
            id_imovel
        )

    if not id_documentos:
        raise FileNotFoundError(
            f"A pasta 'documentos' não foi encontrada "
            f"dentro do imóvel {codigo_imovel}."
        )

    # -----------------------------------------------------
    # SUBPASTA OPCIONAL DO COMPRADOR
    # -----------------------------------------------------

    nomes_comprador = [
        "documentos do comprador",
        "documento do comprador",
        "documentacao do comprador",
        "documentacao comprador",
        "docs do comprador",
        "docs comprador",
    ]

    id_comprador = None

    for nome in nomes_comprador:
        id_comprador = buscar_id_por_nome(
            service,
            nome,
            id_documentos
        )

        if id_comprador:
            break

    return {
        "principal": id_documentos,
        "comprador": id_comprador,
    }


def localizar_pasta_documentacao(service, codigo_imovel):
    """
    Alias de compatibilidade.

    Continua retornando somente a pasta principal,
    preservando o comportamento esperado por outras partes do sistema.
    """

    pastas = localizar_pastas_documentacao(
        service,
        codigo_imovel
    )

    return pastas["principal"]