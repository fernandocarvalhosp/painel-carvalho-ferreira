# -*- coding: utf-8 -*-
"""
gerador_dossie.py
Gera a compilação do Dossiê de Documentos (PDF) em memória (bytes).
Sem upload no Drive. Sem interface.
"""
import io
from pathlib import Path
from pypdf import PdfReader, PdfWriter

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCRIPT_DIR = Path(__file__).resolve().parent

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
]

ID_RAIZ = "1NaZ7kv_jHVCTlLV8vqxCzBwbTX5y3fR7"


def conectar_google():
    """Autentica via st.secrets['google_credentials']."""
    try:
        import streamlit as st

        creds_dict = dict(st.secrets["google_credentials"])
        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=SCOPES
        )
        drive = build("drive", "v3", credentials=creds)
        return drive
    except Exception as e:
        print(f"Erro ao autenticar no Google: {e}", flush=True)
        return None


def buscar_id_por_nome(service, nome_item, id_pasta_pai):
    if not service or not id_pasta_pai:
        return None

    query = (
        f"'{id_pasta_pai}' in parents "
        f"and name = '{nome_item}' "
        f"and trashed = false"
    )

    try:
        results = service.files().list(
            q=query,
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()

        files = results.get("files", [])
        return files[0]["id"] if files else None

    except Exception as e:
        print(f"Erro ao buscar '{nome_item}': {e}", flush=True)
        return None


def buscar_pasta_imovel_por_codigo(service, codigo_imovel, id_pasta_imoveis):
    if not service or not id_pasta_imoveis:
        return None

    codigo = codigo_imovel.strip().upper()

    query = (
        f"'{id_pasta_imoveis}' in parents "
        f"and mimeType = 'application/vnd.google-apps.folder' "
        f"and name contains '{codigo}' "
        f"and trashed = false"
    )

    try:
        results = service.files().list(
            q=query,
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()

        files = results.get("files", [])

        if not files:
            return None

        for f in files:
            nome = f["name"].strip().upper()

            if (
                nome == codigo
                or nome.startswith(codigo + " ")
                or nome.startswith(codigo + "-")
            ):
                return f["id"]

        return files[0]["id"]

    except Exception as e:
        print(f"Erro ao buscar pasta do imovel '{codigo_imovel}': {e}", flush=True)
        return None


def obter_id_pasta_imovel(service, codigo_imovel):
    id_portfolio = buscar_id_por_nome(service, "PORTFOLIO", ID_RAIZ)

    if not id_portfolio:
        print("Pasta PORTFOLIO nao encontrada.", flush=True)
        return None

    id_imoveis = buscar_id_por_nome(service, "IMOVEIS", id_portfolio)

    if not id_imoveis:
        print("Pasta IMOVEIS nao encontrada.", flush=True)
        return None

    id_imovel = buscar_pasta_imovel_por_codigo(service, codigo_imovel, id_imoveis)

    if not id_imovel:
        print(f"Pasta do imovel '{codigo_imovel}' nao encontrada.", flush=True)
        return None

    return id_imovel


def baixar_bytes(service, id_arquivo):
    """Baixa arquivo do Drive direto para bytes (RAM)."""
    try:
        request = service.files().get_media(fileId=id_arquivo)
        memoria = io.BytesIO()
        downloader = MediaIoBaseDownload(memoria, request)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        return memoria.getvalue()

    except Exception as e:
        print(f"Erro ao baixar arquivo {id_arquivo}: {e}", flush=True)
        return None


def compilar_dossie_documentos(codigo_imovel):
    """
    Retorna os bytes do PDF do Dossiê unificado, ou None.
    Não grava no Google Drive. Não abre interface.
    """
    drive = conectar_google()

    if not drive:
        return None

    codigo_imovel = str(codigo_imovel).strip().upper()

    if not codigo_imovel:
        return None

    id_pasta_imovel = obter_id_pasta_imovel(drive, codigo_imovel)

    if not id_pasta_imovel:
        return None

    # Busca a subpasta DOCUMENTOS (em caixa alta)
    id_pasta_docs = buscar_id_por_nome(drive, "DOCUMENTOS", id_pasta_imovel)

    if not id_pasta_docs:
        print("Pasta DOCUMENTOS nao encontrada.", flush=True)
        return None

    try:
        query_pdfs = (
            f"'{id_pasta_docs}' in parents "
            f"and mimeType = 'application/pdf' "
            f"and trashed = false"
        )

        results = drive.files().list(
            q=query_pdfs,
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()

        arquivos_pdf = results.get("files", [])

        if not arquivos_pdf:
            print("Nenhum PDF encontrado na pasta DOCUMENTOS.", flush=True)
            return None

        # Ordena em ordem alfabética para manter uma sequência padronizada
        arquivos_pdf = sorted(arquivos_pdf, key=lambda x: x.get("name", "").upper())

        merger = PdfWriter()
        pdfs_adicionados = 0

        for pdf_file in arquivos_pdf:
            nome_arquivo = pdf_file.get("name", "").upper()

            # Evita reprocessar um dossiê antigo compilado
            if "DOSSIE_COMPLETO" in nome_arquivo:
                continue

            bytes_pdf = baixar_bytes(drive, pdf_file["id"])

            if not bytes_pdf:
                continue

            stream_pdf = io.BytesIO(bytes_pdf)
            leitor = PdfReader(stream_pdf)
            merger.append(leitor)
            pdfs_adicionados += 1

        if pdfs_adicionados == 0:
            print("Nenhum arquivo PDF valido para fusao.", flush=True)
            return None

        pdf_buffer = io.BytesIO()
        merger.write(pdf_buffer)
        merger.close()

        pdf_bytes = pdf_buffer.getvalue()

        if len(pdf_bytes) < 5000:
            print("PDF do Dossiê gerado parece vazio ou incompleto.", flush=True)
            return None

        return pdf_bytes

    except Exception as e:
        print(f"Erro ao compilar o dossie de documentos: {e}", flush=True)
        return None
