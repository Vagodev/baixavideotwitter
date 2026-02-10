# Ponto de entrada da aplicação Flask

from flask import Flask, request, render_template, send_file
from downloader import download_twitter_video
import os

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form.get("url")
        try:
            output_file = download_twitter_video(url)
            return send_file(output_file, as_attachment=True)
        except Exception as e:
            return render_template("index.html", result=f"Erro: {e}")
    return render_template("index.html", result=None)

if __name__ == "__main__": 
    port = int(os.environ.get("PORT", 5000)) 
    app.run(host="0.0.0.0", port=port)