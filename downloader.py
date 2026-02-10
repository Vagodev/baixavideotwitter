# Funções responsáveis pelo download (yt-dlp)
import yt_dlp
import uuid
import os
from logger import logger

DOWNLOAD_DIR = "downloads"

def download_twitter_video(url: str) -> str:
    """Baixa vídeo do Twitter usando yt-dlp e retorna o caminho do arquivo."""
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    filename = f"{uuid.uuid4()}.mp4"
    output_path = os.path.join(DOWNLOAD_DIR, filename)

    logger.info(f"Iniciando download: {url}")

    ydl_opts = {
        "outtmpl": output_path,
        "format": "best"
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        logger.info(f"Download concluído: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Erro ao baixar {url}: {e}")
        raise
