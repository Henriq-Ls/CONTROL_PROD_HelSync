#!/usr/bin/env python3
"""Clareia e ilumina um vídeo ou todos os vídeos de uma pasta usando FFmpeg."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


EXTENSOES_VIDEO = {".avi", ".m4v", ".mkv", ".mov", ".mp4", ".webm", ".wmv"}
SUFIXO_SAIDA = "_iluminado"


def localizar_ffmpeg(caminho_informado: str | None) -> str:
    """Encontra o FFmpeg informado, o FFmpeg do projeto ou o do PATH."""
    if caminho_informado:
        caminho = Path(caminho_informado).expanduser()
        if caminho.is_file():
            return str(caminho)
        raise FileNotFoundError(f"FFmpeg não encontrado em: {caminho}")

    raiz = Path(__file__).resolve().parent
    candidatos = [
        raiz / "_FERRAMENTAS_" / "ffmpeg" / "bin" / "ffmpeg.exe",
        raiz / "prod" / "_FERRAMENTAS_" / "ffmpeg" / "bin" / "ffmpeg.exe",
        raiz / "_FERRAMENTAS_" / "ffmpeg" / "bin" / "ffmpeg",
        raiz / "prod" / "_FERRAMENTAS_" / "ffmpeg" / "bin" / "ffmpeg",
    ]
    for candidato in candidatos:
        if candidato.is_file():
            return str(candidato)

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg
    raise FileNotFoundError(
        "FFmpeg não foi encontrado. Informe o caminho usando --ffmpeg."
    )


def resolver_caminho(caminho: str) -> Path:
    """Resolve caminhos relativos a partir da pasta deste script."""
    caminho_path = Path(caminho).expanduser()
    if not caminho_path.is_absolute():
        caminho_path = Path(__file__).resolve().parent / caminho_path
    return caminho_path.resolve()


def criar_filtro() -> str:
    """Usa as configurações declaradas no final deste arquivo."""
    return (
        f"eq=brightness={BRILHO}:contrast={CONTRASTE}:"
        f"gamma={GAMMA}:saturation={SATURACAO},"
        f"unsharp=5:5:{NITIDEZ}:3:3:0.20,"
        "format=yuv420p"
    )


def validar_configuracoes() -> None:
    """Impede valores que podem estourar ou inutilizar a imagem."""
    limites = {
        "BRILHO": (BRILHO, -1.0, 1.0),
        "CONTRASTE": (CONTRASTE, 0.0, 2.0),
        "GAMMA": (GAMMA, 0.1, 10.0),
        "SATURACAO": (SATURACAO, 0.0, 3.0),
        "NITIDEZ": (NITIDEZ, 0.0, 5.0),
    }
    for nome, (valor, minimo, maximo) in limites.items():
        if not minimo <= valor <= maximo:
            raise ValueError(
                f"{nome}={valor} está fora do limite permitido "
                f"({minimo} até {maximo})."
            )


def converter_video(
    entrada: Path,
    saida: Path,
    ffmpeg: str,
    filtro: str,
    substituir: bool,
) -> bool:
    """Aplica o filtro e salva o vídeo em MP4."""
    comando = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y" if substituir else "-n",
        "-i",
        str(entrada),
        "-vf",
        filtro,
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-crf",
        "20",
        "-preset",
        "medium",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        str(saida),
    ]

    print(f"Convertendo: {entrada.name}")
    resultado = subprocess.run(comando, text=True, capture_output=True)
    if resultado.returncode == 0:
        print(f"Salvo em: {saida}")
        return True

    print(f"ERRO ao converter {entrada.name}:")
    print(resultado.stderr.strip() or "O FFmpeg não informou o motivo.")
    return False


def processar_entrada(
    entrada: Path,
    saida: Path,
    ffmpeg: str,
    substituir: bool,
) -> int:
    """Detecta automaticamente se a entrada é arquivo ou pasta."""
    filtro = criar_filtro()
    print(f"Filtro: {filtro}")

    if entrada.is_file():
        print(f"Entrada detectada como ARQUIVO: {entrada}")
        if entrada.suffix.lower() not in EXTENSOES_VIDEO:
            print(f"Arquivo de vídeo não suportado: {entrada}")
            return 2

        arquivo_saida = (
            saida
            if saida.suffix.lower() in EXTENSOES_VIDEO
            else saida / f"{entrada.stem}{SUFIXO_SAIDA}.mp4"
        )
        arquivo_saida.parent.mkdir(parents=True, exist_ok=True)
        return 0 if converter_video(
            entrada, arquivo_saida, ffmpeg, filtro, substituir
        ) else 1

    if entrada.is_dir():
        print(f"Entrada detectada como PASTA: {entrada}")
        videos = sorted(
            arquivo
            for arquivo in entrada.iterdir()
            if arquivo.is_file()
            and arquivo.suffix.lower() in EXTENSOES_VIDEO
            and not arquivo.stem.endswith(SUFIXO_SAIDA)
        )
        if not videos:
            print(f"Nenhum vídeo encontrado em: {entrada}")
            return 0

        saida.mkdir(parents=True, exist_ok=True)
        sucessos = 0
        for video in videos:
            arquivo_saida = saida / f"{video.stem}{SUFIXO_SAIDA}.mp4"
            if converter_video(video, arquivo_saida, ffmpeg, filtro, substituir):
                sucessos += 1
        print(f"Concluído: {sucessos}/{len(videos)} vídeo(s).")
        return 0 if sucessos == len(videos) else 1

    print(f"Entrada não encontrada: {entrada}")
    return 2


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Clareia e ilumina um vídeo ou uma pasta de vídeos."
    )
    parser.add_argument("entrada", nargs="?", help="Substitui DIRETORIO_ENTRADA.")
    parser.add_argument("saida", nargs="?", help="Substitui DIRETORIO_SAIDA.")
    parser.add_argument(
        "--nao-substituir",
        action="store_true",
        help="Protege o arquivo de saída e não o substitui.",
    )
    parser.add_argument("--ffmpeg", help="Caminho do executável do FFmpeg.")
    return parser


def main() -> int:
    args = criar_parser().parse_args()
    caminho_entrada = args.entrada or DIRETORIO_ENTRADA
    caminho_saida = args.saida or DIRETORIO_SAIDA

    if not caminho_entrada or not caminho_saida:
        print("Preencha DIRETORIO_ENTRADA e DIRETORIO_SAIDA no final do arquivo.")
        return 2

    entrada = resolver_caminho(caminho_entrada)
    saida = resolver_caminho(caminho_saida)
    if not entrada.exists():
        print(f"Entrada não encontrada: {entrada}")
        return 2

    try:
        ffmpeg = localizar_ffmpeg(args.ffmpeg)
    except FileNotFoundError as erro:
        print(erro)
        return 2

    try:
        validar_configuracoes()
    except ValueError as erro:
        print(f"Configuração inválida: {erro}")
        return 2

    print(f"FFmpeg: {ffmpeg}")
    return processar_entrada(entrada, saida, ffmpeg, not args.nao_substituir)


# ============================================================
# CAMINHOS: EDITE ESTAS DUAS VARIÁVEIS
# Pode ser um arquivo ou uma pasta.
# ============================================================
DIRETORIO_ENTRADA = r"D:\Hein_Projetos\CONTROL_PROD_HelSync\Video_Ent.mp4"
DIRETORIO_SAIDA = r"D:\Hein_Projetos\CONTROL_PROD_HelSync\Video_Said.mp4"

# ============================================================
# CONFIGURAÇÕES DO CLAREAMENTO E DA ILUMINAÇÃO
# O script valida automaticamente os limites técnicos.
# ============================================================
# BRILHO:
#   Clareia ou escurece a imagem.
#   Limite técnico: -1.0 (muito escuro) até 1.0 (muito claro).
#   Recomendado: 0.05 até 0.30. Acima de 0.40 pode estourar áreas brancas.
BRILHO = 0.10

# CONTRASTE:
#   Distância entre as partes claras e escuras.
#   Limite técnico: 0.0 até 2.0.
#   Recomendado: 1.00 até 1.35. Use 1.18 para um contraste equilibrado.
CONTRASTE = 1.15

# GAMMA:
#   Clareia principalmente os meios-tons e as sombras, preservando melhor
#   as áreas já claras. É o ajuste principal para enxergar detalhes no escuro.
#   Limite técnico: 0.1 até 10.0.
#   Para clarear sombras, use menos de 1.0:
#     0.90 = efeito leve | 0.75 = efeito forte | 0.60 = muito forte.
#   Abaixo de 0.60 pode deixar a imagem lavada e revelar muito ruído.
GAMMA = 0.75

# SATURACAO:
#   Intensidade das cores.
#   Limite técnico: 0.0 (sem cor) até 3.0 (cores muito fortes).
#   Recomendado: 1.00 até 1.35. Acima de 1.50 pode deixar as cores artificiais.
SATURACAO = 1.20

# NITIDEZ:
#   Realça contornos e detalhes do vídeo.
#   Limite técnico usado pelo script: 0.0 até 5.0.
#   Recomendado: 0.50 até 2.00. Valores altos podem criar halos e ruído.
NITIDEZ = 1.50


if __name__ == "__main__":
    sys.exit(main())
