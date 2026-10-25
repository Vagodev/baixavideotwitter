# Ponto de entrada da aplicação Flask
import os
import urllib.request
import urllib.error
from flask import Flask, request, render_template, send_file
from downloader import download_video, validate_video_url

app = Flask(__name__)

QUALITY_OPTIONS = [
    {"value": "best", "label": "Melhor disponível"},
    {"value": "2160", "label": "2160p (4K)"},
    {"value": "1440", "label": "1440p (2K / QHD)"},
    {"value": "1080", "label": "1080p (Full HD)"},
    {"value": "720", "label": "720p (HD)"},
    {"value": "480", "label": "480p (SD)"},
    {"value": "360", "label": "360p"},
]

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = (request.form.get("url") or "").strip()
        quality = (request.form.get("quality") or "").strip()
        output_format = (request.form.get("format") or "mp4").strip().lower()

        try:
            validate_video_url(url)
            if quality not in {"best", "2160", "1440", "1080", "720", "480", "360"}:
                raise ValueError("Escolha uma resolução antes de baixar.")
            if output_format != "mp4":
                raise ValueError("Formato inválido. Nesta versão, selecione MP4.")

            output_file = download_video(url, quality=quality, output_format=output_format)
            return send_file(
                output_file,
                as_attachment=True,
                download_name=os.path.basename(output_file),
                mimetype="video/mp4",
            )
        except Exception as exc:
            app.logger.exception("Falha ao processar download")
            return render_template(
                "index.html",
                result=f"Não foi possível baixar o vídeo: {exc}",
                qualities=QUALITY_OPTIONS,
                selected_quality=quality if quality in {"best", "2160", "1440", "1080", "720", "480", "360"} else "",
                url=url,
            ), 400

    return render_template(
        "index.html",
        result=None,
        qualities=QUALITY_OPTIONS,
        selected_quality="",
        url="",
    )


@app.route("/diagnostico")
def diagnostico():
    url = "http://127.0.0.1:4416/ping"

    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            body = response.read().decode("utf-8", errors="replace")

            return {
                "bgutil_status": "respondendo",
                "http_status": response.status,
                "resposta": body[:500],
            }, 200

    except Exception as exc:
        app.logger.exception("Falha ao consultar o servidor bgutil")

        return {
            "bgutil_status": "falha",
            "erro": str(exc),
        }, 503


@app.route("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
