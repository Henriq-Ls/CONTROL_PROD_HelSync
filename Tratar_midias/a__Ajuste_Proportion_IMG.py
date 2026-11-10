# 📁 Tratar_midias/a__Ajuste_Proportion_IMG.py

import os
from pathlib import Path

from PIL import Image, ImageOps
EXTENSOES=(".jpg",".jpeg",".png",".webp")

def Proporcao_IMG(
    pasta_entrada,
    pasta_saida,
    proporcao,
    preservar_resolucao=False,
):
    pasta_entrada=Path(pasta_entrada)
    pasta_saida=Path(pasta_saida)
    pasta_saida.mkdir(parents=True,exist_ok=True)

    arquivos=[a for a in os.listdir(pasta_entrada) if a.lower().endswith(EXTENSOES)]

    for arq in arquivos:
        img = Image.open(pasta_entrada / arq)
        img = ImageOps.exif_transpose(img).convert("RGB")
        w,h=img.size

        pw,ph=proporcao

        if preservar_resolucao:
            if w * ph > h * pw:
                aw = w
                ah = (w * ph + pw - 1) // pw
            else:
                ah = h
                aw = (h * pw + ph - 1) // ph
            nw, nh = w, h
        else:
            base=1600
            aw=base
            ah=int(base*ph/pw)

            # NÃO REDUZ FORÇADO
            ratio=min(aw/w,ah/h)
            nw=int(w*ratio)
            nh=int(h*ratio)

            img=img.resize((nw,nh),Image.LANCZOS)

        canvas=Image.new("RGB",(aw,ah),(255,255,255))
        x=(aw-nw)//2
        y=(ah-nh)//2

        canvas.paste(img,(x,y))

        nome=Path(arq).stem+".png"
        canvas.save(pasta_saida/nome)

    return str(pasta_saida)

R'''# 1:1 — quadrado
Proporcao_IMG(
r'C:\Users\henri\Downloads\PRODUTOS\PORTA CANETAS CARTAO',
r'C:\Users\henri\Downloads\PRODUTOS\PORTA CANETAS CARTAO\01 - Proporção Ajustada',
proporcao=(3,4),
)'''
