"""Download de vídeos usando yt-dlp.

O selector tenta obter MP4 até a resolução escolhida, combinando vídeo e áudio
quando necessário. Se não existir uma faixa MP4 adequada, recua para o melhor
formato compatível até a altura escolhida e pede ao FFmpeg para remuxar para MP4.
"""
import os
import re
import uuid
from urllib.parse import urlparse

import yt_dlp

DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR", "downloads")
ALLOWED_HOSTS = {
     "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
    "twitter.com",
    "www.twitter.com",
    "mobile.twitter.com",
    "x.com",
    "www.x.com",
    "mobile.x.com",
}

def validate_video_url(url: str) -> str:
    """Valida esquema e domínio para reduzir risco de SSRF/URLs arbitrárias."""
    if not url or len(url) > 2048:
        raise ValueError("Informe uma URL válida.")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("A URL precisa começar com http:// ou https://.")
    host = (parsed.hostname or "").lower().rstrip(".")
    if host not in ALLOWED_HOSTS:
        raise ValueError("Use um link público do YouTube, X ou Twitter.")
    if parsed.username or parsed.password:
        raise ValueError("URLs com credenciais não são aceitas.")
    return url

def _format_selector(quality: str) -> str:
    if quality == "best":
        height = None
    else:
        try:
            height = int(quality)
        except (TypeError, ValueError):
            raise ValueError("Qualidade inválida.")
        if height not in {360, 480, 720, 1080, 1440, 2160}:
            raise ValueError("Qualidade não suportada.")

    if height is None:
        return "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b"

    # Prioriza MP4/H.264 e áudio M4A; depois tenta outros codecs até a altura
    # escolhida. A opção final cobre vídeos que já têm áudio e vídeo juntos.
    return (
        f"bv*[height<={height}][ext=mp4]+ba[ext=m4a]/"
        f"b[height<={height}][ext=mp4]/"
        f"bv*[height<={height}]+ba/"
        f"b[height<={height}]"
    )

def download_video(url: str, quality: str = "720", output_format: str = "mp4") -> str:
    """Baixa um vídeo e devolve o caminho do MP4 concluído."""
    validate_video_url(url)
    if output_format != "mp4":
        raise ValueError("Formato de saída não suportado.")
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    job_id = uuid.uuid4().hex
    output_template = os.path.join(DOWNLOAD_DIR, f"{job_id}.%(ext)s")
    opts = {
        "outtmpl": output_template,
        "format": _format_selector(quality),
        "merge_output_format": "mp4",
        "postprocessors": [
            {"key": "FFmpegVideoRemuxer", "preferedformat": "mp4"},
        ],
        "noplaylist": True,
        "restrictfilenames": True,
        "windowsfilenames": True,
        
        "socket_timeout": 20,
        "retries": 2,
        "fragment_retries": 2,
        "quiet": False,
        "no_warnings": False,
        "verbose": True,
        "remote_components": ["ejs:npm"],
        "js_runtimes": {"deno": {}},
        "extractor_args": {
    "youtube": {
        "player_client": ["mweb", "tv", "web_safari"]
    },
    "youtubepot-bgutilscript": {
    "server_home": os.path.join(
        os.getcwd(),
        "bgutil-ytdlp-pot-provider",
        "server"
    )
},
"youtubepot-bgutilhttp": {
    "base_url": "http://127.0.0.1:4416"
}
},
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # O nome final pode mudar quando yt-dlp/FFmpeg mescla faixas.
            requested = ydl.prepare_filename(info)
            candidates = [
                os.path.splitext(requested)[0] + ".mp4",
                requested,
                os.path.join(DOWNLOAD_DIR, f"{job_id}.mp4"),
            ]
            for path in candidates:
                if os.path.isfile(path) and os.path.getsize(path) > 0:
                    return path

            # Alguns extractors reportam a extensão do arquivo final de outra forma.
            for name in os.listdir(DOWNLOAD_DIR):
                if name.startswith(job_id + ".") and os.path.isfile(os.path.join(DOWNLOAD_DIR, name)):
                    path = os.path.join(DOWNLOAD_DIR, name)
                    if os.path.getsize(path) > 0:
                        return path
            raise RuntimeError("O download terminou, mas o arquivo final não foi encontrado.")
    except Exception:
        # Remove apenas arquivos temporários deste trabalho.
        for name in os.listdir(DOWNLOAD_DIR):
            if name.startswith(job_id + "."):
                try:
                    os.remove(os.path.join(DOWNLOAD_DIR, name))
                except OSError:
                    pass
        raise
