import io
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

def conectar_drive(creds):
    try:
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"Erro ao conectar ao Google Drive: {e}")
        return None

def encontrar_pasta_imovel(service, nome_pasta):
    try:
        query = f"name = '{nome_pasta}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = service.files().list(q=query, pageSize=1, fields="files(id, name)").execute()
        files = results.get('files', [])
        if files:
            return files[0]['id']
        return None
    except Exception as e:
        print(f"Erro ao buscar pasta: {e}")
        return None

def criar_pasta_se_nao_existir(service, nome_pasta, id_pai=None):
    try:
        query = f"name = '{nome_pasta}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        if id_pai:
            query += f" and '{id_pai}' in parents"
           
        results = service.files().list(q=query, pageSize=1, fields="files(id, name)").execute()
        files = results.get('files', [])
       
        if files:
            return files[0]['id']
           
        file_metadata = {
            'name': nome_pasta,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if id_pai:
            file_metadata['parents'] = [id_pai]
           
        folder = service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')
    except Exception as e:
        print(f"Erro ao criar pasta: {e}")
        return None

def baixar_foto_bytes(service, file_id):
    try:
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        fh.seek(0)
        return fh
    except Exception as e:
        print(f"Erro ao baixar arquivo: {e}")
        return None

def enviar_foto_tratada(service, id_pasta_destino, nome_arquivo, arquivo_bytes):
    try:
        file_metadata = {
            'name': nome_arquivo,
            'parents': [id_pasta_destino]
        }
        media = MediaIoBaseUpload(arquivo_bytes, mimetype='image/jpeg', resumable=True)
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return file.get('id')
    except Exception as e:
        print(f"Erro ao enviar arquivo: {e}")
        return None