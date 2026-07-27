# 📁 Tratar_midias/e__Colocar_Logos_Ref.py
# ==========================================================
# ADICIONAR REFERÊNCIA NAS IMAGENS
# ==========================================================

import os

from PIL import (
    Image,
    ImageDraw,
    ImageFont
)

# ==========================================================
# FONTE
# ==========================================================

# ⚠️  except genérico vazio
def carregar_fonte(tamanho):
    fontes = [
        "arialbd.ttf",
        "Arial Bold.ttf",
        "Arial_Bold.ttf",
        "DejaVuSans-Bold.ttf",
        "arial.ttf"
    ]

    for fonte in fontes:
        try:

            return ImageFont.truetype(fonte, tamanho)

        except:
            pass

    return ImageFont.load_default()

# ⚠️  função grande (74 linhas) | except genérico vazio
def Adicionar_logo_completa(pasta_entrada, pasta_saida, caminho_logo=None, texto_site=None, nome_produto=None, adicionar_referencia=None):
    os.makedirs(pasta_saida, exist_ok=True)

    extensoes = (".jpg", ".jpeg", ".png", ".webp")

    logo_base = None
    if caminho_logo:
        try:
            logo_base = Image.open(caminho_logo).convert("RGBA")
        except:
            logo_base = None

    for arquivo in os.listdir(pasta_entrada):
        if not arquivo.lower().endswith(extensoes):
            continue

        try:
            caminho = os.path.join(pasta_entrada, arquivo)
            img = Image.open(caminho).convert("RGBA")
            W, H = img.size
            draw = ImageDraw.Draw(img)

            margem = 25
            logo_size = int(W * 0.11)

            # ====================== TOPO ESQUERDO: LOGO (TROQUDADO) ======================
            if logo_base:
                logo = logo_base.copy()
                logo.thumbnail((logo_size, logo_size))
                lx = margem  # Agora à esquerda
                ly = margem
                img.alpha_composite(logo, (lx, ly))

            # ====================== TOPO DIREITO: NOME DO PRODUTO (TROQUDADO) ======================
            if nome_produto:
                fonte_nome = carregar_fonte(max(28, int(W * 0.023)))
                bbox_nome = draw.textbbox((0, 0), str(nome_produto), font=fonte_nome)
                tw = bbox_nome[2] - bbox_nome[0]
                tx = W - tw - margem  # Agora à direita
                ty = margem
                draw.text((tx, ty), str(nome_produto), fill=(0, 0, 0),
                          font=fonte_nome, stroke_width=3, stroke_fill=(255, 255, 255))

            # ====================== INFERIOR ESQUERDO: TEXTO DO SITE ======================
            if texto_site:
                fonte_site = carregar_fonte(max(24, int(W * 0.019)))
                bbox_site = draw.textbbox((0, 0), str(texto_site), font=fonte_site)
                tx = margem
                ty = H - bbox_site[3] + bbox_site[1] - margem
                draw.text((tx, ty), str(texto_site), fill=(0, 0, 0),
                          font=fonte_site, stroke_width=2, stroke_fill=(255, 255, 255))

            # ====================== INFERIOR DIREITO: REFERÊNCIA ======================
            if adicionar_referencia == "Sim" or adicionar_referencia == True or adicionar_referencia is None:
                texto_ref = f"REF: {os.path.splitext(arquivo)[0].strip()}"
                fonte_ref = carregar_fonte(max(26, int(W * 0.021)))
                bbox_ref = draw.textbbox((0, 0), texto_ref, font=fonte_ref)
                tw = bbox_ref[2] - bbox_ref[0]
                x_ref = W - tw - margem
                y_ref = H - bbox_ref[3] + bbox_ref[1] - margem
                draw.text((x_ref, y_ref), texto_ref, fill=(0, 0, 0),
                          font=fonte_ref, stroke_width=3, stroke_fill=(255, 255, 255))

            # ====================== SALVAR ======================
            img = img.convert("RGB")
            nome_saida = os.path.splitext(arquivo)[0] + ".jpg"
            destino = os.path.join(pasta_saida, nome_saida)
            img.save(destino, quality=95)
            print(f"Salvo: {destino}")

        except Exception as e:
            print(f"Erro em {arquivo}: {e}")

    print(f"FINALIZADO → {pasta_saida}")
