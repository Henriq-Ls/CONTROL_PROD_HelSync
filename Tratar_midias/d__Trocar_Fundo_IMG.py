# 📁 Tratar_midias/d__Trocar_Fundo_IMG.py

import os
from pathlib import Path
from typing import Callable

from PIL import Image, ImageFilter, ImageEnhance
GERAR_SOMBRA    = True
ANCORAR_BASE    = False

def gerar_sombra(produto: Image.Image) -> Image.Image:
    w, h = produto.size
    _, _, _, alpha = produto.split()

    sombra = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sombra.putalpha(alpha.point(lambda p: int(p * 0.35)))
    sombra = sombra.filter(ImageFilter.GaussianBlur(radius=12))

    sombra_final = sombra.resize((w, int(h * 0.20)), Image.LANCZOS)

    tela = Image.new("RGBA", (w, int(h * 0.20)), (0, 0, 0, 0))
    tela.paste(sombra_final, (0, 0), mask=sombra_final)

    return tela

def compor(produto, fundo_path, sombra_altura, centralizar=False):
    largura, altura = produto.size

    fundo = Image.open(fundo_path).convert("RGBA")

    fundo = fundo.resize((largura, altura), Image.LANCZOS)

    tela = Image.new("RGBA", (largura, altura))
    tela.paste(fundo, (0, 0))

    pos_x = (largura - produto.width) // 2
    pos_y = (altura - produto.height) // 2 if not ANCORAR_BASE else int(altura * 0.88) - produto.height

    if GERAR_SOMBRA:
        sombra = gerar_sombra(produto)
        sx = pos_x
        sy = pos_y + produto.height - int(sombra.height * sombra_altura)
        tela.paste(sombra, (sx, sy), sombra)

    tela.paste(produto, (pos_x, pos_y), produto)

    return tela

# ⚠️  except genérico vazio
def Trocar_fundo(
    pasta_imagens,
    pasta_saida,
    imagem_fundo,
    sombra_altura=0.2,
    progress: Callable[[str], None] | None = None,
):
    pasta_imagens = Path(pasta_imagens)
    imagem_fundo = Path(imagem_fundo)

    pasta_saida = Path(pasta_saida)
    pasta_saida.mkdir(parents=True, exist_ok=True)

    extensoes = (".jpg", ".jpeg", ".png", ".webp")

    arquivos = [
        arquivo
        for arquivo in sorted(os.listdir(pasta_imagens))
        if arquivo.lower().endswith(extensoes)
    ]
    if progress:
        progress(f"Pasta pronta: {pasta_saida}")
        progress(f"Aplicando fundo em {len(arquivos)} imagem(ns)...")

    processados = 0
    for arquivo in arquivos:
        if not arquivo.lower().endswith(extensoes):
            continue

        caminho = pasta_imagens / arquivo
        print(f"Processando: {arquivo}")

        try:
            produto = Image.open(caminho).convert("RGBA")

            resultado = compor(produto, imagem_fundo, sombra_altura, centralizar=True)

            saida = pasta_saida / arquivo

            if saida.suffix.lower() in [".jpg", ".jpeg"]:
                resultado.convert("RGB").save(saida, quality=97)
            else:
                resultado.save(saida)

            print(f"Salvo: {saida}")
            processados += 1
            if progress:
                progress(f"Fundo {processados}/{len(arquivos)}: {arquivo}")

        except Exception as e:
            print(f"Erro em {arquivo}: {e}")
            if progress:
                progress(f"Erro em {arquivo}: {e}")

    print("\nFINALIZADO")
    if progress:
        progress(f"Pasta concluída: {pasta_saida}")

r'''Trocar_fundo(r'C:\Users\henri\Downloads\PRODUTOS\PORTA CANETAS CARTAO\03 - Sem Fundo',
r'C:\Users\henri\Downloads\PRODUTOS\PORTA CANETAS CARTAO\04 - Imagem Amostra',
             r'C:\Users\henri\PycharmProjects\CONTROLE_PRODUTOS_HelSync\Midias\capa.jpeg'
)

Trocar_fundo(r'C:\Users\henri\Downloads\PRODUTOS\PORTA CANETAS CARTAO\03 - Sem Fundo',
r'C:\Users\henri\Downloads\PRODUTOS\PORTA CANETAS CARTAO\04 - Imagem Medidas',
             r'C:\Users\henri\PycharmProjects\CONTROLE_PRODUTOS_HelSync\Midias\medida.jpeg'
)'''
