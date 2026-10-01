"""Fuentes de datos: archivo local (por defecto) o Google Drive (opcional).

La descarga desde Drive usa una cuenta de servicio con permiso de solo
lectura. El ID del archivo y la ruta de las credenciales se leen de
variables de entorno: nunca se escriben en el código.
"""

import io
import os
from pathlib import Path


def descargar_de_drive(destino: Path, log=print) -> Path:
    """Descarga un Excel de Google Drive tal cual está guardado.

    Variables de entorno requeridas:
      DRIVE_FILE_ID              ID del archivo en Drive
      GOOGLE_CREDENTIALS_PATH    ruta al JSON de la cuenta de servicio
    """
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload

    file_id = os.environ.get("DRIVE_FILE_ID")
    cred_path = os.environ.get("GOOGLE_CREDENTIALS_PATH")
    if not file_id or not cred_path:
        raise EnvironmentError("Define DRIVE_FILE_ID y GOOGLE_CREDENTIALS_PATH (ver .env.example).")

    creds = Credentials.from_service_account_file(
        cred_path, scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    servicio = build("drive", "v3", credentials=creds)

    log("Descargando archivo desde Google Drive...")
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, servicio.files().get_media(fileId=file_id))
    listo = False
    while not listo:
        _, listo = downloader.next_chunk()

    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(buffer.getvalue())
    log(f"Archivo guardado en {destino}")
    return destino
