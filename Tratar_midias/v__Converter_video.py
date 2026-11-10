# 📁 Tratar_midias/v__Converter_video.py

import os
import re
import subprocess
from typing import Callable

FFMPEG_PATH = r"_FERRAMENTAS_\ffmpeg\bin\ffmpeg.exe"

def _get_video_info(video_path, ffmpeg_path):
    """Lê dimensões, rotação, duração e presença de áudio do vídeo."""
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

    tem_audio = bool(
        re.search(r"Stream\s+#\d+:\d+.*\bAudio:", stderr, re.IGNORECASE)
    )
    return width, height, rotation, duracao, tem_audio

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
def Converte_Video_Completo(
    ref,
    input_video,
    pasta_video,
    logo_path,
    qrcode_path,
    musica_path,
    som,
    link_url,
    max_size_mb,
    max_duration,
    progress: Callable[[str], None] | None = None,
):
    os.makedirs(pasta_video, exist_ok=True)
    output_video = os.path.join(pasta_video, f"video_{ref}.mp4")
    if progress:
        progress(f"Pasta de vídeo pronta: {pasta_video}")
        progress("Preparando conversão do vídeo...")

    fade_in  = 1.5
    fade_out = 2.0

    # ── Lê info real do vídeo ────────────────────────────────────
    width, height, rotation, dur_original, tem_audio = _get_video_info(
        input_video,
        FFMPEG_PATH,
    )
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

    argumentos = [FFMPEG_PATH, "-y", "-i", input_video]
    proximo_indice = 1
    indice_musica = None
    indice_logo = None
    indice_qr = None

    if musica_path and float(som) > 0:
        if not os.path.isfile(musica_path):
            raise FileNotFoundError(f"Arquivo de música não encontrado: {musica_path}")
        argumentos.extend(["-i", musica_path])
        indice_musica = proximo_indice
        proximo_indice += 1

    if logo_path:
        if not os.path.isfile(logo_path):
            raise FileNotFoundError(f"Logo de vídeo não encontrada: {logo_path}")
        argumentos.extend(["-loop", "1", "-i", logo_path])
        indice_logo = proximo_indice
        proximo_indice += 1

    if qrcode_path:
        if not os.path.isfile(qrcode_path):
            raise FileNotFoundError(f"QR Code não encontrado: {qrcode_path}")
        argumentos.extend(["-loop", "1", "-i", qrcode_path])
        indice_qr = proximo_indice

    filtros = [
        (
            f"[0:v]{transpor}scale={alvo_w}:-2,"
            "eq=brightness=0.10:contrast=1.18:saturation=1.2,"
            "unsharp=5:5:1.50:3:3:0.20,"
            "vibrance=0.20,"
            "colorbalance=rs=0.003:gs=0.002:bs=-0.003,"
            f"fade=t=in:st=0:d={fade_in},"
            f"fade=t=out:st={duracao - fade_out}:d={fade_out}"
            "[vbase]"
        )
    ]
    rotulo_video = "vbase"

    if indice_logo is not None:
        filtros.append(
            f"[{indice_logo}:v]scale=100:100,"
            f"fade=t=in:st=0:d={fade_in}:alpha=1,"
            f"fade=t=out:st={duracao - fade_out}:d={fade_out}:alpha=1[logo]"
        )
        filtros.append(f"[{rotulo_video}][logo]overlay=20:20[vlogo]")
        rotulo_video = "vlogo"

    if indice_qr is not None:
        filtros.append(
            f"[{indice_qr}:v]scale=110:110,"
            f"fade=t=in:st=0:d={fade_in}:alpha=1,"
            f"fade=t=out:st={duracao - fade_out}:d={fade_out}:alpha=1[qrcode]"
        )
        filtros.append(
            f"[{rotulo_video}][qrcode]overlay=W-w-20:H-h-20[vqr]"
        )
        rotulo_video = "vqr"

    if link_url:
        texto_link = (
            str(link_url)
            .replace("\\", "\\\\")
            .replace("'", "\\'")
            .replace(":", "\\:")
            .replace(",", "\\,")
            .replace("%", "\\%")
        )
        filtros.append(
            f"[{rotulo_video}]drawtext=text='{texto_link}':"
            "fontcolor=white:fontsize=24:"
            "x=(w-text_w)/2:y=h-60:"
            "box=1:boxcolor=black@0.55:boxborderw=10[vfinal]"
        )
    else:
        filtros.append(f"[{rotulo_video}]null[vfinal]")

    rotulo_audio = None
    if tem_audio:
        filtros.append(
            f"[0:a]volume=0.7,"
            f"afade=t=out:st={duracao - fade_out}:d={fade_out}[a_original]"
        )
        rotulo_audio = "a_original"

    if indice_musica is not None:
        filtros.append(
            f"[{indice_musica}:a]volume={som},"
            f"afade=t=out:st={duracao - fade_out}:d={fade_out}[a_musica]"
        )
        if rotulo_audio:
            filtros.append(
                "[a_original][a_musica]amix=inputs=2:normalize=0[a_final]"
            )
            rotulo_audio = "a_final"
        else:
            rotulo_audio = "a_musica"

    filter_complex = ";".join(filtros)
    cmd = argumentos + [
        "-filter_complex", filter_complex,
        "-map", "[vfinal]",
    ]
    if rotulo_audio:
        cmd.extend(
            [
                "-map",
                f"[{rotulo_audio}]",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
            ]
        )
    else:
        cmd.append("-an")
    cmd.extend(
        [
            "-t", str(duracao),
            "-c:v", "libx264",
            "-crf", "26",
            "-preset", "fast",
            "-movflags", "+faststart",
            output_video,
        ]
    )

    print(f"Criando vídeo de {duracao:.1f}s...")
    print("COMANDO FFMPEG:")
    print(" ".join(cmd))
    print()
    print("FILTER COMPLEX:")
    print(filter_complex)
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Erro FFmpeg:\n{result.stderr}")
        if progress:
            progress(f"Erro na conversão do vídeo: {result.stderr.strip()}")

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
    if progress:
        progress(f"Vídeo concluído: {output_video}")

    return True
