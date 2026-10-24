# Patch: seleção de qualidade e suporte a YouTube

## O que muda
- Aceita links públicos do YouTube/Shorts e X/Twitter.
- Permite selecionar melhor disponível, 1080p, 720p, 480p ou 360p.
- Nenhuma resolução vem pré-selecionada: o usuário precisa escolher uma opção antes de baixar.
- Opções: melhor disponível, 2160p (4K), 1440p (2K/QHD), 1080p, 720p, 480p e 360p.
- Solicita MP4 e mescla faixas de áudio/vídeo com FFmpeg quando necessário.
- Mantém uma única rota Flask e a estrutura simples do repositório.

## Aplicação
1. Faça backup/commit do repositório atual.
2. Substitua `app.py`, `downloader.py`, `templates/index.html` e `requirements.txt` pelos arquivos deste patch.
3. Instale dependências:
   ```bash
   python -m pip install -r requirements.txt
   ```
4. Instale o FFmpeg no sistema e confirme que `ffmpeg` está no PATH. Em hospedagem Render, configure-o conforme a estratégia de build do serviço.
5. Execute localmente:
   ```bash
   python app.py
   ```
6. Abra `http://127.0.0.1:5000`.

## Render
- Mantenha o comando de start compatível com o projeto, por exemplo `gunicorn app:app`.
- O FFmpeg precisa estar instalado no ambiente de execução para mesclar áudio e vídeo.
- O disco local de hospedagem pode ser efêmero; o download é retornado na mesma requisição, por isso não trate `downloads/` como armazenamento permanente.

## Observações
- A seleção representa a resolução máxima solicitada. Se não houver a resolução exata, o yt-dlp usa a melhor opção disponível abaixo dela.
- O MP4 é preferido, mas alguns vídeos podem precisar de remux/mesclagem. `merge_output_format` não reencoda o vídeo; remux não é garantido se os codecs não forem compatíveis.
- A consulta/transferência depende de mudanças nas plataformas e da versão do yt-dlp. Mantenha-o atualizado.
- Use apenas para conteúdo que você tem direito ou autorização para baixar.
