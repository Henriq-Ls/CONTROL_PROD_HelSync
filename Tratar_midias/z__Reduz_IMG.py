from pathlib import Path
from PIL import Image

QUALIDADE = 90
EXTENSOES = (".jpg", ".jpeg", ".png", ".webp")

def Reduzir_IMG(pasta_entrada, fator=0.5):
    pasta_entrada = Path(pasta_entrada)

    for caminho_img in pasta_entrada.rglob("*"):
        if caminho_img.is_file() and caminho_img.suffix.lower() in EXTENSOES:
            try:
                img = Image.open(caminho_img).convert("RGB")
                w, h = img.size

                novo_w = max(1, int(w * fator))
                novo_h = max(1, int(h * fator))

                img = img.resize((novo_w, novo_h), Image.LANCZOS)

                img.save(caminho_img, quality=QUALIDADE, optimize=True)

            except Exception as e:
                print(f"Erro em {caminho_img}: {e}")


Reduzir_IMG(r'C:\Users\henri\Downloads\PRODUTOS\tttt', fator=0.5)