# 📁 Tratar_midias/v__Converter_video.py

import os
import re
import subprocess
FFMPEG_PATH = r"_FERRAMENTAS_\ffmpeg\bin\ffmpeg.exe"

def _get_video_info(video_path, ffmpeg_path):
    """Lê dimensões reais, rotação e duração do vídeo."""
    result = subprocess.run(
        [ffmpeg_path, "-i", video_path],
        capture_output=True, text=True
    )
    stderr = result.stderr

    # Pega dimensões da linha de Stream de vídeo (mais preciso)
    match_dim = re.search(r"Stream.*Video.*?,\s*(\d{2,5})x(\d{2,5})", stderr)
    width  = int(match_dim.group(1)) if match_dim else 1080
    height = int(match_dim.group(2)) if match_dim else 1920

    # Rotação nos metadados
    match_rot = re.search(r"rotate\s*:\s*(-?\d+)", stderr)
    rotation = int(match_rot.group(1)) if match_rot else 0

    # Duração
    match_dur = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", stderr)
    if match_dur:
        h, m, s = match_dur.groups()
        duracao = int(h) * 3600 + int(m) * 60 + float(s)
    else:
        duracao = 59

    return width, height, rotation, duracao

def _filtro_rotacao(rotation, width, height):
    """
    Corrige rotação do vídeo.
    Quando o vídeo está em paisagem sem metadado de rotação (gravado deitado),
    usa transpose=2 (anti-horário) para ficar na vertical correta.
    """
    if rotation == 90:

        return "transpose=1,"        # 90° horário

    elif rotation == -90 or rotation == 270:

        return "transpose=2,"        # 90° anti-horário

    elif rotation == 180 or rotation == -180:

        return "transpose=2,transpose=2,"

    elif rotation == 0 and width > height:

        return "transpose=2,"        # ← era transpose=1, corrigido para anti-horário

    return ""

# ⚠️  função grande (136 linhas)
def Converte_Video_Completo(ref, input_video, pasta_video, logo_path, qrcode_path, musica_path,som, link_url,max_size_mb, max_duration):
    os.makedirs(pasta_video, exist_ok=True)
    output_video = os.path.join(pasta_video, f"video_{ref}.mp4")

    fade_in  = 1.5
    fade_out = 2.0

    # ── Lê info real do vídeo ────────────────────────────────────
    width, height, rotation, dur_original = _get_video_info(input_video, FFMPEG_PATH)
    print(f"Vídeo original: {width}x{height} | rotação: {rotation}° | duração: {dur_original:.1f}s")

    # ← FIX PRINCIPAL: usa a duração REAL do vídeo, nunca maior que o limite
    duracao = min(max_duration, dur_original)

    if duracao < 10:
        print(f"AVISO: vídeo tem só {duracao:.1f}s — Shopee exige mínimo 10s.")

        return False

    transpor = _filtro_rotacao(rotation, width, height)

    # Após transpose, as dimensões se invertem
    if transpor:
        width, height = height, width

    alvo_w = min(1080, width)

    filter_complex = (
        # ── VÍDEO BASE ───────────────────────────────────────────
        f"[0:v]{transpor}scale={alvo_w}:-2,"
        f"eq=brightness=0.10:contrast=1.18:saturation=1.2,"
        f"unsharp=5:5:1.50:3:3:0.20," # Recupera nitidez e textura
        f"vibrance=0.20,"  # Deixa as cores mais vivas sem exagerar
        f"colorbalance=rs=0.003:gs=0.002:bs=-0.003,"  # Corrige equilíbrio de cores
        f"fade=t=in:st=0:d={fade_in},"
        f"fade=t=out:st={duracao - fade_out}:d={fade_out}"
        "[vbase];"

        # ── LOGO (canto superior esquerdo) ───────────────────────
        "[2:v]scale=100:100,"
        f"fade=t=in:st=0:d={fade_in}:alpha=1,"
        f"fade=t=out:st={duracao - fade_out}:d={fade_out}:alpha=1"
        "[logo];"

        # ── QR CODE (canto inferior direito) ─────────────────────
        "[3:v]scale=110:110,"
        f"fade=t=in:st=0:d={fade_in}:alpha=1,"
        f"fade=t=out:st={duracao - fade_out}:d={fade_out}:alpha=1"
        "[qrcode];"

        # ── OVERLAYS ─────────────────────────────────────────────
        "[vbase][logo]overlay=20:20[v1];"
        "[v1][qrcode]overlay=W-w-20:H-h-20[v2];"

        # ── TEXTO CENTRALIZADO EMBAIXO ────────────────────────────
        f"[v2]drawtext=text='{link_url}':"
        "fontcolor=white:fontsize=24:"
        "x=(w-text_w)/2:y=h-60:"           # w e h minúsculos = dimensão do frame atual
        "box=1:boxcolor=black@0.55:boxborderw=10"
        "[vfinal];"

        # ── ÁUDIO: mix + fade out ────────────────────────────────
        f"[0:a]volume=0.7,afade=t=out:st={duracao - fade_out}:d={fade_out}[a1];"
        f"[1:a]volume={som},afade=t=out:st={duracao - fade_out}:d={fade_out}[a2];"
        "[a1][a2]amix=inputs=2:normalize=0[a]"
    )

    cmd = [
        FFMPEG_PATH, "-y",
        "-i", input_video,
        "-i", musica_path,
        "-loop", "1", "-i", logo_path,
        "-loop", "1", "-i", qrcode_path,
        "-filter_complex", filter_complex,
        "-map", "[vfinal]",
        "-map", "[a]",
        "-t", str(duracao),           # ← agora usa a duração real
        "-c:v", "libx264",
        "-crf", "26",
        "-preset", "fast",
        "-movflags", "+faststart",
        "-c:a", "aac",
        "-b:a", "128k",
        output_video                   # ← removido -shortest (conflitava com -loop 1)
    ]

    print(f"Criando vídeo de {duracao:.1f}s...")
    print("COMANDO FFMPEG:")
    print(" ".join(cmd))
    print()
    print("FILTER COMPLEX:")
    print(filter_complex)
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Erro FFmpeg:\n{result.stderr}")

        return False

    # ── VERIFICA TAMANHO SHOPEE ───────────────────────────────────
    tamanho_mb = os.path.getsize(output_video) / (1024 * 1024)
    print(f"Tamanho gerado: {tamanho_mb:.1f}MB")

    if tamanho_mb > max_size_mb:
        print(f"Acima de {max_size_mb}MB — recomprimindo...")
        temp = output_video.replace(".mp4", "_temp.mp4")
        os.rename(output_video, temp)

        bitrate_alvo = int((max_size_mb * 8 * 1024) / duracao)

        cmd_recomp = [
            FFMPEG_PATH, "-y", "-i", temp,
            "-b:v", f"{bitrate_alvo}k",
            "-maxrate", f"{bitrate_alvo}k",
            "-bufsize", f"{bitrate_alvo * 2}k",
            "-c:v", "libx264",
            "-preset", "slow",
            "-c:a", "aac", "-b:a", "64k",
            "-movflags", "+faststart",
            output_video
        ]
        print("COMANDO FFMPEG:")
        print(" ".join(cmd))
        print()
        print("FILTER COMPLEX:")
        print(filter_complex)

        subprocess.run(cmd_recomp, capture_output=True)
        os.remove(temp)

        tamanho_final = os.path.getsize(output_video) / (1024 * 1024)
        print(f"Recomprimido: {tamanho_final:.1f}MB")

    print(f"Pronto para Shopee: {os.path.getsize(output_video) / (1024 * 1024):.1f}MB | {duracao:.1f}s | MP4")

    return True

R"""
Converte_Video_Completo('suv',
r'C:\Users\henri\Downloads\Imagens\video.mp4',
r'C:\Users\henri\Downloads\Imagens\video convert.mp4',
r'C:\Users\henri\PycharmProjects\SO_RUSTICO_SHOPEE\Imagens\video.png',
r'C:\Users\henri\PycharmProjects\SO_RUSTICO_SHOPEE\Imagens\qr_code_zap.jpg',
r'C:\Users\henri\PycharmProjects\SO_RUSTICO_SHOPEE\Imagens\Simple.mp3',0.15,
'henriqls.shop',90,60)
"""
