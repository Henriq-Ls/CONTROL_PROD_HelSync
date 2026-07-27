# 📁 Tratar_midias/b__Ajuste_Geral_IMG.py

import os
from pathlib import Path

from PIL import Image, ImageFilter, ImageEnhance
EXTENSOES = (".jpg", ".jpeg", ".png", ".webp")

def aprimorar_produto(produto: Image.Image, madeira_crua: bool = False) -> Image.Image:
    r, g, b, alpha = produto.split()
    rgb = Image.merge("RGB", (r, g, b))

    gamma = 1.1
    rgb = rgb.point(lambda i: 255 * ((i / 255.0) ** (1.0 / gamma)))

    r_c, g_c, b_c = rgb.split()
    r_c = r_c.point(lambda i: min(255, int(i * 1.05)))
    b_c = b_c.point(lambda i: min(255, int(i * 0.97)))
    rgb = Image.merge("RGB", (r_c, g_c, b_c))

    rgb = ImageEnhance.Brightness(rgb).enhance(1.02)

    if madeira_crua:

        rgb = ImageEnhance.Contrast(rgb).enhance(1.15)
        rgb = ImageEnhance.Color(rgb).enhance(1.15)
        rgb = ImageEnhance.Sharpness(rgb).enhance(2.0)

    else:

        rgb = ImageEnhance.Contrast(rgb).enhance(1.22)
        rgb = ImageEnhance.Color(rgb).enhance(1.30)
        rgb = ImageEnhance.Sharpness(rgb).enhance(2.0)

    rgb = rgb.filter(ImageFilter.UnsharpMask(radius=1.5, percent=120, threshold=3))

    r2, g2, b2 = rgb.split()

    return Image.merge("RGBA", (r2, g2, b2, alpha))

# ⚠️  função grande (60 linhas) | except genérico vazio
def Ajuste_IMG(pasta_entrada, pasta_saida, madeira_crua=False):
    """Aplica os ajustes de cor e nitidez nas imagens.

    Parâmetros:
        pasta_entrada : pasta com os PNGs transparentes (saída do b__)
        pasta_saida   : pasta onde os resultados serão salvos
        madeira_crua  : True = ajuste suave (madeira sem verniz)
                        False = ajuste forte (madeira envernizada / padrão)
    """
    pasta_entrada = Path(pasta_entrada)
    pasta_saida   = Path(pasta_saida)
    pasta_saida.mkdir(parents=True, exist_ok=True)

    arquivos = sorted([
        a for a in os.listdir(pasta_entrada)
        if a.lower().endswith(EXTENSOES)
    ])

    print(f"\n{'='*52}")
    print(f"  d__Ajuste_IMG — {len(arquivos)} imagens")
    print(f"  Entrada      : {pasta_entrada}")
    print(f"  Saída        : {pasta_saida}")
    print(f"  Madeira crua : {madeira_crua}")
    print(f"{'='*52}")

    for arquivo in arquivos:
        caminho = pasta_entrada / arquivo
        print(f"\nProcessando: {arquivo}")

        try:
            produto   = Image.open(caminho).convert("RGBA")
            resultado = aprimorar_produto(produto, madeira_crua)
            resultasaida = pasta_saida / arquivo
            saida = pasta_saida / arquivo
            ext_original = saida.suffix.lower()

            img_final = resultado

            if img_final.mode == "RGBA":
                alpha = img_final.split()[-1]
                tem_transparencia = alpha.getextrema()[0] < 255
            else:
                tem_transparencia = False

            if tem_transparencia:
                img_final = img_final.convert("RGBA")
                saida = saida.with_suffix(".png")
            else:
                img_final = img_final.convert("RGB")
                saida = saida.with_suffix(".jpg")

            img_final.save(saida)
            print(f"  Salvo: {arquivo}")

        except Exception as e:
            print(f"  Erro em {arquivo}: {e}")

    print(f"\nFINALIZADO — {len(arquivos)} imagens em: {pasta_saida}\n")

    return str(pasta_saida)

r'''Ajuste_IMG(r'C:\Users\henri\Downloads\PRODUTOS\PORTA CANETAS CARTAO\01 - Proporção Ajustada',
r'C:\Users\henri\Downloads\PRODUTOS\PORTA CANETAS CARTAO\02 - Ajuste Geral',
)
'''
