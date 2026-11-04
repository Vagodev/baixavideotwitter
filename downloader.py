   """Download de vídeos do YouTube e X/Twitter usando yt-dlp.

O seletor prioriza MP4 e respeita a resolução máxima escolhida.
Para YouTube, aceita cookies Netscape via YOUTUBE_COOKIES_B64 (Base64).
Os cookies são usados somente em URLs do YouTube e o arquivo temporário é
removido ao final do trabalho.
"""
import base64
import binascii
import os
import tempfile
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

YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
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

    return (
        f"bv*[height<={height}][ext=mp4]+ba[ext=m4a]/"
        f"b[height<={height}][ext=mp4]/"
        f"bv*[height<={height}]+ba/"
        f"b[height<={height}]"
    )


def _create_youtube_cookie_file(url: str):
    """Cria arquivo Netscape temporário a partir do segredo Base64 do Render.

    Retorna (caminho, deve_ser_removido). Não aplica cookies a X/Twitter.
    """
    host = (urlparse(url).hostname or "").lower().rstrip(".")
    if host not in YOUTUBE_HOSTS:
        return None, False

    cookies_b64 = os.environ.get("YOUTUBE_COOKIES_B64", "").strip()
    if not cookies_b64:
        return None, False

    try:
        cookie_data = base64.b64decode(cookies_b64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(
            "A variável YOUTUBE_COOKIES_B64 não contém Base64 válido. "
            "Gere novamente a variável a partir do arquivo cookies.txt."
        ) from exc

    if not cookie_data.strip():
        raise ValueError("O arquivo de cookies do YouTube está vazio.")

    # O yt-dlp espera cookies no formato Netscape, não JSON.
    first_lines = cookie_data.decode("utf-8-sig", errors="replace").splitlines()[:5]
    if not any(line.startswith("# Netscape HTTP Cookie File")
               or line.startswith("# HTTP Cookie File")
               for line in first_lines):
        raise ValueError(
            "Os cookies precisam estar no formato Netscape (cookies.txt). "
            "Exporte novamente os cookies do YouTube nesse formato."
        )

    temp = tempfile.NamedTemporaryFile(
        mode="wb",
        suffix=".txt",
        prefix="youtube-cookies-",
        delete=False,
    )
    try:
        temp.write(cookie_data)
        temp.flush()
    finally:
        temp.close()

    # Restringe permissões do arquivo temporário quando o sistema permite.
    try:
        os.chmod(temp.name, 0o600)
    except OSError:
        pass

    return temp.name, True


def download_video(
    url: str,
    quality: str = "720",
    output_format: str = "mp4",
) -> str:
    """Baixa um vídeo e devolve o caminho do arquivo MP4 concluído."""
    validate_video_url(url)

    if output_format != "mp4":
        raise ValueError("Formato de saída não suportado.")

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    job_id = uuid.uuid4().hex
    output_template = os.path.join(DOWNLOAD_DIR, f"{job_id}.%(ext)s")
    cookie_file, remove_cookie_file = _create_youtube_cookie_file(url)

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
        "socket_timeout": 30,
        "retries": 3,
        "fragment_retries": 3,
        "quiet": False,
        "no_warnings": False,
        "verbose": True,
        "remote_components": ["ejs:npm"],
        "js_runtimes": {"deno": {}},
        "extractor_args": {
            "youtube": {
                "player_client": ["mweb", "tv", "web_safari"],
            },
            "youtubepot-bgutilscript": {
                "server_home": os.path.join(
                    os.getcwd(),
                    "bgutil-ytdlp-pot-provider",
                    "server",
                ),
            },
            "youtubepot-bgutilhttp": {
                "base_url": "http://127.0.0.1:4416",
            },
        },
    }

    # Cookies são enviados somente ao extrator do YouTube.
    if cookie_file:
        opts["cookiefile"] = cookie_file

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            requested = ydl.prepare_filename(info)
            candidates = [
                os.path.splitext(requested)[0] + ".mp4",
                requested,
                os.path.join(DOWNLOAD_DIR, f"{job_id}.mp4"),
            ]

            for path in candidates:
                if os.path.isfile(path) and os.path.getsize(path) > 0:
                    return path

            # Alguns extractors informam a extensão original após o remux.
            for name in os.listdir(DOWNLOAD_DIR):
                if name.startswith(job_id + "."):
                    path = os.path.join(DOWNLOAD_DIR, name)
                    if os.path.isfile(path) and os.path.getsize(path) > 0:
                        return path

            raise RuntimeError(
                "O download terminou, mas o arquivo final não foi encontrado."
            )

    except Exception:
        # Remove somente os arquivos pertencentes a este trabalho.
        for name in os.listdir(DOWNLOAD_DIR):
            if name.startswith(job_id + "."):
                try:
                    os.remove(os.path.join(DOWNLOAD_DIR, name))
                except OSError:
                    pass
        raise

    finally:
        if remove_cookie_file and cookie_file:
            try:
                os.remove(cookie_file)
            except OSError:
                pass
