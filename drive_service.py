# drive_service.py
# Versão revisada para processamento prioritariamente em memória.
# Não cria pastas temporárias nem grava arquivos intermediários no disco.

import io

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


# =============================================================================
# CONFIGURAÇÃO
# =============================================================================

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]


# =============================================================================
# CONEXÃO
# =============================================================================

def conectar_drive(creds):
    """
    Cria o serviço do Google Drive usando credenciais já autenticadas.
    """
    try:
        return build("drive", "v3", credentials=creds)
    except Exception as e:
        print(f"Erro ao conectar ao Google Drive: {e}", flush=True)
        return None


def conectar_google_com_arquivo(credenciais_file):
    """
    Conecta ao Google Drive e Google Sheets usando um arquivo de credenciais.

    Mantido como função auxiliar para compatibilidade com versões que ainda
    utilizem credentials.json. O restante do sistema pode fornecer as
    credenciais diretamente e usar conectar_drive().
    """
    try:
        creds = service_account.Credentials.from_service_account_file(
            credenciais_file,
            scopes=SCOPES,
        )

        drive = build("drive", "v3", credentials=creds)
        sheets = build("sheets", "v4", credentials=creds)

        return drive, sheets

    except Exception as e:
        print(f"Erro ao autenticar no Google: {e}", flush=True)
        return None, None


# =============================================================================
# BUSCA DE ARQUIVOS E PASTAS
# =============================================================================

def buscar_itens(service, id_pasta_pai=None, nome=None, mime_type=None):
    """
    Busca arquivos ou pastas diretamente no Google Drive.

    Retorna uma lista de dicionários com id, nome e mimeType.
    Não cria nenhum arquivo local.
    """
    if not service:
        return []

    partes = ["trashed = false"]

    if id_pasta_pai:
        partes.append(f"'{id_pasta_pai}' in parents")

    if nome:
        nome_escapado = nome.replace("'", "\'")
        partes.append(f"name = '{nome_escapado}'")

    if mime_type:
        partes.append(f"mimeType = '{mime_type}'")

    query = " and ".join(partes)

    try:
        resposta = service.files().list(
            q=query,
            fields="nextPageToken, files(id, name, mimeType, size)",
            pageSize=1000,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()

        return resposta.get("files", [])

    except Exception as e:
        print(f"Erro ao buscar itens no Google Drive: {e}", flush=True)
        return []


def buscar_id_por_nome(service, nome_item, id_pasta_pai):
    """
    Retorna o ID do primeiro item com o nome informado dentro da pasta pai.
    """
    arquivos = buscar_itens(
        service,
        id_pasta_pai=id_pasta_pai,
        nome=nome_item,
    )

    return arquivos[0]["id"] if arquivos else None


def buscar_pasta_por_nome(service, nome_pasta, id_pasta_pai):
    """
    Retorna o ID de uma pasta pelo nome.
    """
    pasta = buscar_itens(
        service,
        id_pasta_pai=id_pasta_pai,
        nome=nome_pasta,
        mime_type="application/vnd.google-apps.folder",
    )

    return pasta[0]["id"] if pasta else None


def listar_itens_pasta(service, id_pasta):
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
                q=f"'{id_pasta}' in parents and trashed = false",
                fields="nextPageToken, files(id, name, mimeType, size)",
                orderBy="name",
                pageSize=1000,
                pageToken=page_token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            ).execute()

            arquivos.extend(resposta.get("files", []))

            page_token = resposta.get("nextPageToken")
            if not page_token:
                break

        return arquivos

    except Exception as e:
        print(f"Erro ao listar pasta '{id_pasta}': {e}", flush=True)
        return []


# =============================================================================
# DOWNLOAD EM MEMÓRIA
# =============================================================================

def baixar_arquivo_em_memoria(service, id_arquivo):
    """
    Baixa um arquivo do Google Drive diretamente para RAM.

    Retorna um BytesIO posicionado no início.
    Nenhum arquivo é criado no disco da hospedagem.
    """
    if not service or not id_arquivo:
        return None

    try:
        request = service.files().get_media(fileId=id_arquivo)

        memoria = io.BytesIO()
        downloader = MediaIoBaseDownload(memoria, request)

        done = False

        while not done:
            _, done = downloader.next_chunk()

        memoria.seek(0)
        return memoria

    except Exception as e:
        print(f"Erro ao baixar arquivo para memória: {e}", flush=True)
        return None


def baixar_arquivo_bytes(service, id_arquivo):
    """
    Versão simplificada que retorna bytes diretamente.
    """
    arquivo = baixar_arquivo_em_memoria(service, id_arquivo)

    if arquivo is None:
        return None

    return arquivo.getvalue()


# =============================================================================
# BUSCA + DOWNLOAD
# =============================================================================

def baixar_arquivo_por_nome(service, nome_arquivo, id_pasta):
    """
    Localiza um arquivo dentro de uma pasta e o retorna diretamente em RAM.

    Retorna:
        {
            "id": ...,
            "name": ...,
            "mimeType": ...,
            "bytes": ...
        }

    ou None quando não encontrado.
    """
    arquivos = buscar_itens(
        service,
        id_pasta_pai=id_pasta,
        nome=nome_arquivo,
    )

    if not arquivos:
        return None

    arquivo = arquivos[0]
    dados = baixar_arquivo_bytes(service, arquivo["id"])

    if dados is None:
        return None

    return {
        "id": arquivo["id"],
        "name": arquivo["name"],
        "mimeType": arquivo.get("mimeType", ""),
        "bytes": dados,
    }


def baixar_imagens_pasta(service, id_pasta):
    """
    Localiza todas as imagens de uma pasta e baixa seus conteúdos para RAM.

    Retorna uma lista ordenada pelo nome:
        [
            {
                "id": "...",
                "name": "...",
                "mimeType": "image/jpeg",
                "bytes": b"..."
            }
        ]
    """
    arquivos = listar_itens_pasta(service, id_pasta)

    imagens = []

    for arquivo in arquivos:
        mime_type = arquivo.get("mimeType", "")

        if not mime_type.startswith("image/"):
            continue

        dados = baixar_arquivo_bytes(service, arquivo["id"])

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

    imagens.sort(key=lambda item: item["name"].lower())

    return imagens

