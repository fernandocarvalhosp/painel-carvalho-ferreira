# -*- coding: utf-8 -*-
"""
drive_service.py

Serviço central de comunicação com o Google Drive.

Princípios:
- Não cria arquivos temporários no disco.
- Downloads são feitos diretamente para RAM.
- Fotos tratadas são enviadas diretamente para o Google Drive.
- Mantém compatibilidade com o tratador de fotos.
- Respeita a estrutura:
    RAIZ
      └── PORTFOLIO
            └── IMOVEIS
                  └── CFxxx
                        ├── fotos brutas
                        └── FOTOS TRATADAS
"""

import io

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import (
    MediaIoBaseDownload,
    MediaIoBaseUpload,
)


# =============================================================================
# CONFIGURAÇÃO
# =============================================================================

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]

# Estrutura principal do Google Drive
ID_RAIZ = "1NaZ7kv_jHVCTlLV8vqxCzBwbTX5y3fR7"

NOME_PASTA_PORTFOLIO = "PORTFOLIO"
NOME_PASTA_IMOVEIS = "IMOVEIS"
NOME_PASTA_FOTOS_TRATADAS = "FOTOS TRATADAS"

MIME_FOLDER = "application/vnd.google-apps.folder"


# =============================================================================
# CONEXÃO
# =============================================================================

def conectar_drive(creds):
    """
    Cria o serviço do Google Drive usando credenciais já autenticadas.
    """

    try:
        return build(
            "drive",
            "v3",
            credentials=creds,
        )

    except Exception as e:
        print(
            f"Erro ao conectar ao Google Drive: {e}",
            flush=True,
        )
        return None


def conectar_google_com_arquivo(credenciais_file):
    """
    Conecta ao Google Drive e ao Google Sheets usando um arquivo de
    credenciais.

    Mantida para compatibilidade com versões anteriores do sistema.
    """

    try:
        creds = service_account.Credentials.from_service_account_file(
            credenciais_file,
            scopes=SCOPES,
        )

        drive = build(
            "drive",
            "v3",
            credentials=creds,
        )

        sheets = build(
            "sheets",
            "v4",
            credentials=creds,
        )

        return drive, sheets

    except Exception as e:
        print(
            f"Erro ao autenticar no Google: {e}",
            flush=True,
        )
        return None, None


# =============================================================================
# BUSCA DE ITENS
# =============================================================================

def buscar_itens(
    service,
    id_pasta_pai=None,
    nome=None,
    mime_type=None,
):
    """
    Busca arquivos ou pastas diretamente no Google Drive.

    Não cria nenhum arquivo local.
    """

    if not service:
        return []

    partes = [
        "trashed = false"
    ]

    if id_pasta_pai:
        partes.append(
            f"'{id_pasta_pai}' in parents"
        )

    if nome:
        nome_escapado = str(nome).replace("'", "\\'")

        partes.append(
            f"name = '{nome_escapado}'"
        )

    if mime_type:
        partes.append(
            f"mimeType = '{mime_type}'"
        )

    query = " and ".join(partes)

    try:
        resposta = service.files().list(
            q=query,
            fields=(
                "nextPageToken,"
                "files(id,name,mimeType,size)"
            ),
            pageSize=1000,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()

        return resposta.get(
            "files",
            [],
        )

    except Exception as e:
        print(
            f"Erro ao buscar itens no Google Drive: {e}",
            flush=True,
        )
        return []


def buscar_id_por_nome(
    service,
    nome_item,
    id_pasta_pai,
):
    """
    Retorna o ID do primeiro item com o nome informado
    dentro da pasta pai.
    """

    arquivos = buscar_itens(
        service,
        id_pasta_pai=id_pasta_pai,
        nome=nome_item,
    )

    return (
        arquivos[0]["id"]
        if arquivos
        else None
    )


def buscar_pasta_por_nome(
    service,
    nome_pasta,
    id_pasta_pai,
):
    """
    Retorna o ID de uma pasta pelo nome.
    """

    pastas = buscar_itens(
        service,
        id_pasta_pai=id_pasta_pai,
        nome=nome_pasta,
        mime_type=MIME_FOLDER,
    )

    return (
        pastas[0]["id"]
        if pastas
        else None
    )


# =============================================================================
# ESTRUTURA DO PORTFOLIO
# =============================================================================

def obter_id_portfolio(service):
    """
    Localiza a pasta PORTFOLIO dentro da raiz configurada.
    """

    return buscar_pasta_por_nome(
        service,
        NOME_PASTA_PORTFOLIO,
        ID_RAIZ,
    )


def obter_id_imoveis(service):
    """
    Localiza a pasta IMOVEIS dentro de PORTFOLIO.
    """

    id_portfolio = obter_id_portfolio(service)

    if not id_portfolio:
        print(
            "Pasta PORTFOLIO não encontrada.",
            flush=True,
        )
        return None

    id_imoveis = buscar_pasta_por_nome(
        service,
        NOME_PASTA_IMOVEIS,
        id_portfolio,
    )

    if not id_imoveis:
        print(
            "Pasta IMOVEIS não encontrada dentro de PORTFOLIO.",
            flush=True,
        )
        return None

    return id_imoveis


def encontrar_pasta_imovel(
    service,
    codigo_imovel,
):
    """
    Localiza a pasta do imóvel seguindo a estrutura oficial:

        RAIZ
          └── PORTFOLIO
                └── IMOVEIS
                      └── CFxxx

    Aceita também nomes como:

        CF001
        CF001 CASA GERUZA
        CF001 - CASA GERUZA

    O código precisa ser o início do nome da pasta.
    """

    codigo = str(
        codigo_imovel
    ).strip().upper()

    if not codigo:
        return None

    id_imoveis = obter_id_imoveis(service)

    if not id_imoveis:
        return None

    try:
        resposta = service.files().list(
            q=(
                f"'{id_imoveis}' in parents "
                f"and mimeType = '{MIME_FOLDER}' "
                f"and trashed = false"
            ),
            fields="files(id,name,mimeType)",
            orderBy="name",
            pageSize=1000,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()

        pastas = resposta.get(
            "files",
            [],
        )

        for pasta in pastas:
            nome = pasta.get(
                "name",
                "",
            ).strip().upper()

            if (
                nome == codigo
                or nome.startswith(codigo + " ")
                or nome.startswith(codigo + "-")
                or nome.startswith(codigo + "_")
            ):
                return pasta["id"]

        print(
            f"Pasta do imóvel '{codigo}' não encontrada dentro de IMOVEIS.",
            flush=True,
        )

        return None

    except Exception as e:
        print(
            f"Erro ao localizar pasta do imóvel '{codigo}': {e}",
            flush=True,
        )
        return None


# =============================================================================
# LISTAGEM DE PASTA
# =============================================================================

def listar_itens_pasta(
    service,
    id_pasta,
):
    """
    Lista todos os itens diretamente dentro de uma pasta.

    A paginação é tratada automaticamente.
    """

    if not service or not id_pasta:
        return []

    arquivos = []
    page_token = None

    try:

        while True:

            resposta = service.files().list(
                q=(
                    f"'{id_pasta}' in parents "
                    f"and trashed = false"
                ),
                fields=(
                    "nextPageToken,"
                    "files(id,name,mimeType,size)"
                ),
                orderBy="name",
                pageSize=1000,
                pageToken=page_token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            ).execute()

            arquivos.extend(
                resposta.get(
                    "files",
                    [],
                )
            )

            page_token = resposta.get(
                "nextPageToken"
            )

            if not page_token:
                break

        return arquivos

    except Exception as e:
        print(
            f"Erro ao listar pasta '{id_pasta}': {e}",
            flush=True,
        )
        return []


# =============================================================================
# DOWNLOAD EM RAM
# =============================================================================

def baixar_arquivo_em_memoria(
    service,
    id_arquivo,
):
    """
    Baixa um arquivo diretamente para RAM.

    Retorna BytesIO posicionado no início.
    """

    if not service or not id_arquivo:
        return None

    try:

        request = service.files().get_media(
            fileId=id_arquivo
        )

        memoria = io.BytesIO()

        downloader = MediaIoBaseDownload(
            memoria,
            request,
        )

        done = False

        while not done:

            _, done = downloader.next_chunk()

        memoria.seek(0)

        return memoria

    except Exception as e:
        print(
            f"Erro ao baixar arquivo para memória: {e}",
            flush=True,
        )
        return None


def baixar_arquivo_bytes(
    service,
    id_arquivo,
):
    """
    Retorna o conteúdo do arquivo diretamente como bytes.
    """

    arquivo = baixar_arquivo_em_memoria(
        service,
        id_arquivo,
    )

    if arquivo is None:
        return None

    return arquivo.getvalue()


# =============================================================================
# BUSCA + DOWNLOAD
# =============================================================================

def baixar_arquivo_por_nome(
    service,
    nome_arquivo,
    id_pasta,
):
    """
    Localiza um arquivo dentro de uma pasta e retorna
    seus dados diretamente em RAM.
    """

    arquivos = buscar_itens(
        service,
        id_pasta_pai=id_pasta,
        nome=nome_arquivo,
    )

    if not arquivos:
        return None

    arquivo = arquivos[0]

    dados = baixar_arquivo_bytes(
        service,
        arquivo["id"],
    )

    if dados is None:
        return None

    return {
        "id": arquivo["id"],
        "name": arquivo["name"],
        "mimeType": arquivo.get(
            "mimeType",
            "",
        ),
        "bytes": dados,
    }


def baixar_imagens_pasta(
    service,
    id_pasta,
):
    """
    Localiza todas as imagens de uma pasta e baixa
    seus conteúdos diretamente para RAM.

    Retorna:

        [
            {
                "id": "...",
                "name": "...",
                "mimeType": "image/jpeg",
                "bytes": b"..."
            }
        ]
    """

    arquivos = listar_itens_pasta(
        service,
        id_pasta,
    )

    imagens = []

    for arquivo in arquivos:

        mime_type = arquivo.get(
            "mimeType",
            "",
        )

        if not mime_type.startswith(
            "image/"
        ):
            continue

        dados = baixar_arquivo_bytes(
            service,
            arquivo["id"],
        )

        if dados is None:
            continue

        imagens.append(
            {
                "id": arquivo["id"],
                "name": arquivo["name"],
                "mimeType": mime_type,
                "bytes": dados,
            }
        )

    imagens.sort(
        key=lambda item: item["name"].lower()
    )

    return imagens


# =============================================================================
# CRIAÇÃO DE PASTAS
# =============================================================================

def criar_pasta_se_nao_existir(
    service,
    nome_pasta,
    id_pasta_pai,
):
    """
    Verifica se uma subpasta existe.

    Se existir:
        retorna o ID existente.

    Se não existir:
        cria a pasta no Google Drive
        e retorna o novo ID.

    Nenhum arquivo local é criado.
    """

    if not service:
        return None

    if not id_pasta_pai:
        return None

    id_existente = buscar_pasta_por_nome(
        service,
        nome_pasta,
        id_pasta_pai,
    )

    if id_existente:
        return id_existente

    try:

        metadata = {
            "name": nome_pasta,
            "mimeType": MIME_FOLDER,
            "parents": [
                id_pasta_pai
            ],
        }

        pasta = service.files().create(
            body=metadata,
            fields="id",
            supportsAllDrives=True,
        ).execute()

        id_nova_pasta = pasta.get(
            "id"
        )

        if id_nova_pasta:
            print(
                f"Pasta '{nome_pasta}' criada com sucesso.",
                flush=True,
            )

        return id_nova_pasta

    except Exception as e:
        print(
            f"Erro ao criar pasta '{nome_pasta}': {e}",
            flush=True,
        )
        return None


# =============================================================================
# FOTOS DO IMÓVEL
# =============================================================================

def baixar_foto_bytes(
    service,
    file_id,
):
    """
    Atalho compatível para baixar uma foto
    diretamente para RAM.
    """

    return baixar_arquivo_bytes(
        service,
        file_id,
    )


def obter_pasta_fotos_tratadas(
    service,
    codigo_imovel,
):
    """
    Localiza a pasta do imóvel e retorna o ID da pasta
    FOTOS TRATADAS.

    Se a pasta ainda não existir, ela será criada.

    Estrutura:

        PORTFOLIO
          └── IMOVEIS
                └── CFxxx
                      └── FOTOS TRATADAS
    """

    id_pasta_imovel = encontrar_pasta_imovel(
        service,
        codigo_imovel,
    )

    if not id_pasta_imovel:
        return None

    return criar_pasta_se_nao_existir(
        service,
        NOME_PASTA_FOTOS_TRATADAS,
        id_pasta_imovel,
    )


# =============================================================================
# UPLOAD DE FOTO TRATADA
# =============================================================================

def enviar_foto_tratada(
    service,
    id_pasta_destino,
    nome_arquivo,
    stream_tratado,
):
    """
    Envia uma foto tratada diretamente para o Google Drive.

    O arquivo permanece em RAM até o upload terminar.
    """

    if not service:
        return False

    if not id_pasta_destino:
        return False

    if not stream_tratado:
        return False

    try:

        if isinstance(
            stream_tratado,
            io.BytesIO,
        ):
            stream_tratado.seek(0)

        metadata = {
            "name": nome_arquivo,
            "parents": [
                id_pasta_destino
            ],
        }

        media = MediaIoBaseUpload(
            stream_tratado,
            mimetype="image/jpeg",
            resumable=True,
        )

        arquivo = service.files().create(
            body=metadata,
            media_body=media,
            fields="id,name",
           # supportsAllDrives=True,
        ).execute()

        return bool(
            arquivo.get("id")
        )

    except Exception as e:
        print(
            f"Erro ao enviar foto tratada "
            f"'{nome_arquivo}': {e}",
            flush=True,
        )
        return False


# =============================================================================
# FUNÇÃO COMPLETA PARA O TRATADOR
# =============================================================================

def preparar_pastas_tratamento(
    service,
    codigo_imovel,
):
    """
    Localiza o imóvel e garante que a pasta
    FOTOS TRATADAS exista.

    Retorna:

        {
            "id_pasta_imovel": "...",
            "id_pasta_tratadas": "..."
        }

    ou None em caso de erro.
    """

    id_pasta_imovel = encontrar_pasta_imovel(
        service,
        codigo_imovel,
    )

    if not id_pasta_imovel:
        return None

    id_pasta_tratadas = criar_pasta_se_nao_existir(
        service,
        NOME_PASTA_FOTOS_TRATADAS,
        id_pasta_imovel,
    )

    if not id_pasta_tratadas:
        return None

    return {
        "id_pasta_imovel": id_pasta_imovel,
        "id_pasta_tratadas": id_pasta_tratadas,
    }
