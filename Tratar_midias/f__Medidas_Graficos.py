# 📁 Tratar_midias/f__Medidas_Graficos.py

from io import BytesIO
import math
import os

from PIL import (
    Image,
    ImageDraw,
    ImageFont
)

from rembg import remove
# ──────────────────────────────────────────────────────────────────────

# ==========================================================
# CONFIG
# ==========================================================

COR_LINHA            = (0, 0, 0)
COR_TEXTO            = (210, 20, 20)
COR_STROKE           = (255, 255, 255)
COR_PESO             = (0, 0, 0)
COR_PONTILHADO       = (210, 20, 20)
PONTILHADO           = 16
ESPESSURA_PONTILHADO = 8

# ==========================================================
# RÓTULOS POR TIPO DE MEDIDA
#   (label_alt, label_larg, label_box)
#   label_box = None  → não desenha terceira medida
#   label_box = 'comp'→ seta diagonal (comprimento/profundidade)
#   label_box = outro → retângulo (espessura etc.)
# ==========================================================

ROTULOS = {
    'alt x larg x esp':  ('', '', ''),
    'alt x larg x comp': ('', '', 'comp'),
    'alt x diam x esp':  ('', 'Diam', ''),
    'alt x diam':        ('', 'Diam', None),
}

# ==========================================================
# CONVERSOR config_str → kit antigo
# ==========================================================

def _config_para_kit(tipo_kit_config: str):
    """
    Converte o novo config_str para o valor de kit que as
    funções internas esperam.

    "TIPO:ÚNICO|VAR=4|KIT=NO"   → None
    "TIPO:KIT|PECAS=3|..."      → "Diferentes"
    'Pares' / None / 'Diferentes' → passa direto (formato antigo)
    """
    if not tipo_kit_config or "|" not in str(tipo_kit_config):

        return tipo_kit_config  # formato antigo, passa direto

    cfg = {}
    for parte in tipo_kit_config.split("|"):
        if ":" in parte and "=" not in parte:
            chave, valor = parte.split(":", 1)
        elif "=" in parte:
            chave, valor = parte.split("=", 1)
        else:
            continue
        cfg[chave.strip()] = valor.strip()

    tipo = cfg.get("TIPO", "").upper()

    return "Diferentes" if tipo == "KIT" else None

# ==========================================================
# EXTRAIR MEDIDAS DO NOME DO ARQUIVO
#   Padrão: ref1_77x45x3_490gm.jpg
#           ref1_1_77x45x3_490gm.jpg  (peça de kit)
# ==========================================================

def _extrair_medidas(nome_arquivo: str):
    """
    Extrai (n1, n2, n3, peso_str) do nome do arquivo.
    n3 pode ser None se o tipo de medida não tiver terceira dimensão.
    """
    nome = os.path.splitext(nome_arquivo)[0]
    partes = nome.split("_")
    try:
        peso_str = partes[-1]          # ex: '490gm' ou '1.2kg'
        medidas  = partes[-2]          # ex: '77x45x3'
        dims     = medidas.split("x")
        n1 = dims[0] if len(dims) > 0 else "0"
        n2 = dims[1] if len(dims) > 1 else "0"
        n3 = dims[2] if len(dims) > 2 else None

        return n1, n2, n3, peso_str

    except Exception:

        return "0", "0", None, "0gm"

# ==========================================================
# REMOVE FUNDO / BBOX
# ==========================================================

def detectar_bbox(imagem_path):
    with open(imagem_path, "rb") as f:
        dados = f.read()

    mask_bytes = remove(dados, alpha_matting=True, only_mask=True)
    mask       = Image.open(BytesIO(mask_bytes)).convert("L")
    bbox       = mask.getbbox()
    img        = Image.open(imagem_path).convert("RGBA")

    if not bbox:

        return img, (0, 0, img.width, img.height)

    return img, bbox

# ==========================================================
# FONTES
# ==========================================================

# ⚠️  except genérico vazio
def carregar_fonte(tamanho):
    fontes = [
        "arialbd.ttf", "Arial Bold.ttf", "Arial_Bold.ttf",
        "DejaVuSans-Bold.ttf", "arial.ttf"
    ]
    for f in fontes:
        try:

            return ImageFont.truetype(f, tamanho)

        except Exception:
            pass

    return ImageFont.load_default()

# ==========================================================
# HELPERS DE TEXTO — rótulo pequeno + valor grande
# ==========================================================

def imagem_texto_duplo(label, valor, fonte_label, fonte_valor):
    dummy = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    bl = dummy.textbbox((0, 0), label, font=fonte_label)
    bv = dummy.textbbox((0, 0), valor, font=fonte_valor)
    wl, hl = bl[2] - bl[0], bl[3] - bl[1]
    wv, hv = bv[2] - bv[0], bv[3] - bv[1]

    pad    = 16
    margin = 6
    W      = max(wl, wv) + pad * 2
    H      = hl + hv + margin + pad * 2

    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    xl  = pad + (W - pad * 2 - wl) // 2
    xv  = pad + (W - pad * 2 - wv) // 2

    d.text((xl, pad),                label, fill=COR_TEXTO, font=fonte_label, stroke_width=3, stroke_fill=COR_STROKE)
    d.text((xv, pad + hl + margin),  valor, fill=COR_TEXTO, font=fonte_valor, stroke_width=5, stroke_fill=COR_STROKE)

    return img

# ==========================================================
# SETAS
# ==========================================================

def seta_cima(draw, x, y, t):
    draw.polygon([(x - t, y + t), (x, y), (x + t, y + t)], fill=COR_LINHA)

def seta_baixo(draw, x, y, t):
    draw.polygon([(x - t, y - t), (x, y), (x + t, y - t)], fill=COR_LINHA)

def seta_esq(draw, x, y, t):
    draw.polygon([(x + t, y - t), (x, y), (x + t, y + t)], fill=COR_LINHA)

def seta_dir(draw, x, y, t):
    draw.polygon([(x - t, y - t), (x, y), (x - t, y + t)], fill=COR_LINHA)

def seta_diagonal(draw, x, y, t, angulo_graus=45):
    rad  = math.radians(angulo_graus)
    perp = math.radians(angulo_graus + 90)
    bx   = x - t * math.cos(rad)
    by   = y - t * math.sin(rad)
    p1   = (bx + t * 0.6 * math.cos(perp), by + t * 0.6 * math.sin(perp))
    p2   = (bx - t * 0.6 * math.cos(perp), by - t * 0.6 * math.sin(perp))
    draw.polygon([(x, y), p1, p2], fill=COR_LINHA)

# ==========================================================
# LINHA PONTILHADA
# ==========================================================

def linha_pontilhada(draw, inicio, fim, horizontal=True, largura=9):
    if horizontal:
        x1, y = inicio
        x2, _ = fim
        for x in range(x1, x2, PONTILHADO * 2):
            draw.line([(x, y), (min(x + PONTILHADO, x2), y)],
                      fill=COR_PONTILHADO, width=largura)
    else:
        x, y1 = inicio
        _, y2  = fim
        for y in range(y1, y2, PONTILHADO * 2):
            draw.line([(x, y), (x, min(y + PONTILHADO, y2))],
                      fill=COR_PONTILHADO, width=largura)

# ==========================================================
# GERAR MEDIDAS — função principal
# ==========================================================

# ⚠️  função grande (148 linhas)
def gerar_medidas(imagem_path, n1, n2, n3, peso, kit, tipo_medidas):
    """
    n1 = altura
    n2 = largura ou diâmetro
    n3 = espessura / comprimento (ignorado em 'alt x diam')
    kit: None = único | 'Diferentes' = kit com peças | 'Pares' = pares
    """
    print(f"Processando: {os.path.basename(imagem_path)}  [{tipo_medidas}]")

    label_alt, label_larg, label_box = ROTULOS.get(
        tipo_medidas, ('', '', '')
    )

    img, (left, top, right, bottom) = detectar_bbox(imagem_path)
    W, H   = img.size
    escala = max(W, H) / 1200

    fonte       = carregar_fonte(max(32, int(60 * escala)))
    fonte_peq   = carregar_fonte(max(20, int(38 * escala)))
    fonte_label = carregar_fonte(max(18, int(30 * escala)))
    fonte_esp   = carregar_fonte(max(18, int(28 * escala)))

    draw      = ImageDraw.Draw(img)
    esp_linha = max(5,  int(7  * escala))
    seta      = max(20, int(34 * escala))

    # ======================================================
    # ALTURA — seta vertical à esquerda
    # ======================================================

    x_alt    = max(int(W * 0.06), left - int(W * 0.10))
    y_top    = top    + 10
    y_bottom = bottom - 10

    draw.line([(x_alt, y_top), (x_alt, y_bottom)], fill=COR_LINHA, width=esp_linha)
    seta_cima( draw, x_alt, y_top,    seta)
    seta_baixo(draw, x_alt, y_bottom, seta)

    linha_pontilhada(draw, (x_alt, y_top),    (left, y_top),    horizontal=True, largura=ESPESSURA_PONTILHADO)
    linha_pontilhada(draw, (x_alt, y_bottom), (left, y_bottom), horizontal=True, largura=ESPESSURA_PONTILHADO)

    txt_img_alt = imagem_texto_duplo(label_alt, f"{n1}cm", fonte_label, fonte)
    txt_img_alt = txt_img_alt.rotate(90, expand=True)
    px = max(2, x_alt - txt_img_alt.width - esp_linha - 4)
    py = max(4, min((y_top + y_bottom) // 2 - txt_img_alt.height // 2,
                    H - txt_img_alt.height - 4))
    img.paste(txt_img_alt, (px, py), txt_img_alt)
    draw = ImageDraw.Draw(img)

    # ======================================================
    # LARGURA / DIÂMETRO — seta horizontal embaixo
    # ======================================================

    y_larg = min(int(H * 0.92), bottom + int(H * 0.06))
    x1     = left  + 20
    x2     = right - 20

    draw.line([(x1, y_larg), (x2, y_larg)], fill=COR_LINHA, width=esp_linha)
    seta_esq(draw, x1, y_larg, seta)
    seta_dir(draw, x2, y_larg, seta)

    linha_pontilhada(draw, (x1, bottom), (x1, y_larg), horizontal=False, largura=ESPESSURA_PONTILHADO)
    linha_pontilhada(draw, (x2, bottom), (x2, y_larg), horizontal=False, largura=ESPESSURA_PONTILHADO)

    txt_img_larg = imagem_texto_duplo(label_larg, f"{n2}cm", fonte_label, fonte)
    tw = txt_img_larg.width
    th = txt_img_larg.height
    tx = (x1 + x2) // 2 - tw // 2
    ty = y_larg - th - 4
    if ty < bottom:
        ty = y_larg + esp_linha + 4
    ty = max(4, min(ty, H - th - 4))
    img.paste(txt_img_larg, (tx, ty), txt_img_larg)
    draw = ImageDraw.Draw(img)

    # ======================================================
    # TERCEIRA MEDIDA — espessura ou comprimento
    #   Só quando kit != 'Pares' e label_box não é None
    # ======================================================

    if kit != 'Pares' and label_box is not None and n3 is not None:

        if label_box == 'comp':
            # ── COMPRIMENTO — seta diagonal (profundidade 3D) ──
            x_diag = right  - int(W * 0.08)
            y_diag = top    + int(H * 0.08)
            comp   = max(60, int(90 * escala))

            x_ini = x_diag
            y_ini = y_diag + comp
            x_fim = x_diag + comp
            y_fim = y_diag

            draw.line([(x_ini, y_ini), (x_fim, y_fim)], fill=COR_LINHA, width=esp_linha)
            seta_diagonal(draw, x_fim, y_fim, seta, angulo_graus=45)
            seta_diagonal(draw, x_ini, y_ini, seta, angulo_graus=225)

            txt_comp = imagem_texto_duplo(label_box, f"{n3}cm", fonte_label, fonte)
            cx = x_fim + 6
            cy = y_fim - txt_comp.height // 2
            cx = min(cx, W - txt_comp.width - 4)
            cy = max(4, cy)
            img.paste(txt_comp, (cx, cy), txt_comp)

        else:
            # ── ESPESSURA — retângulo à direita ──
            box_w  = max(60, int(80  * escala))
            box_h  = max(40, int(160 * escala))
            box_x1 = min(right + int(W * 0.04), W - box_w - 10)
            box_y1 = (top + bottom) // 2 - box_h // 2
            box_x2 = box_x1 + box_w
            box_y2 = box_y1 + box_h

            draw.rectangle([box_x1, box_y1, box_x2, box_y2],
                           outline=COR_LINHA, width=esp_linha)

            # setas verticais dentro do box
            cx_box = (box_x1 + box_x2) // 2
            seta_cima( draw, cx_box, box_y1 + seta // 2, seta // 2)
            seta_baixo(draw, cx_box, box_y2 - seta // 2, seta // 2)

            # pontilhado conectando box ao produto
            linha_pontilhada(draw, (right, (top + bottom) // 2),
                             (box_x1, (box_y1 + box_y2) // 2),
                             horizontal=True, largura=ESPESSURA_PONTILHADO)

            txt_esp = imagem_texto_duplo(label_box, f"{n3}cm", fonte_esp, fonte_peq)
            ex = box_x1 + (box_w - txt_esp.width)  // 2
            ey = box_y1 + (box_h - txt_esp.height) // 2
            img.paste(txt_esp, (ex, ey), txt_esp)

        draw = ImageDraw.Draw(img)

    # ======================================================
    # PESO — canto superior direito
    # ======================================================

    if peso and str(peso).strip() not in ("", "0gm", "0"):
        txt_peso = imagem_texto_duplo("Peso", str(peso), fonte_label, fonte_peq)
        px_peso  = W - txt_peso.width - 12
        py_peso  = 12
        img.paste(txt_peso, (px_peso, py_peso), txt_peso)

    # ======================================================
    # RETORNA imagem RGBA com medidas desenhadas
    # ======================================================

    return img

# ==========================================================
# COLOCAR MEDIDAS — processa a pasta inteira
# ==========================================================

# ⚠️  except genérico vazio
def Colocar_medidas(pasta_entrada, pasta_saida, tipo_kit_config, tipo_medidas):
    """
    Lê todas as imagens de pasta_entrada, aplica as medidas
    com base no nome do arquivo e salva em pasta_saida.

    tipo_kit_config: config_str nova ("TIPO:ÚNICO|VAR=4|KIT=NO")
                     OU formato antigo ('Pares', 'Diferentes', None)
    tipo_medidas:    ex. 'alt x larg x esp'
    """
    kit = _config_para_kit(tipo_kit_config)
    os.makedirs(pasta_saida, exist_ok=True)

    extensoes = (".jpg", ".jpeg", ".png", ".webp")
    arquivos  = sorted([
        a for a in os.listdir(pasta_entrada)
        if a.lower().endswith(extensoes)
    ])

    print(f"\n{'='*52}")
    print(f"  Colocar_medidas — {len(arquivos)} imagens | kit={kit} | {tipo_medidas}")
    print(f"{'='*52}\n")

    for arq in arquivos:
        caminho_entrada = os.path.join(pasta_entrada, arq)
        nome_saida      = os.path.splitext(arq)[0] + ".jpg"
        caminho_saida   = os.path.join(pasta_saida, nome_saida)

        try:
            n1, n2, n3, peso = _extrair_medidas(arq)

            img_result = gerar_medidas(
                caminho_entrada, n1, n2, n3, peso, kit, tipo_medidas
            )

            # Compõe sobre fundo branco e salva como JPG
            fundo = Image.new("RGB", img_result.size, (255, 255, 255))
            fundo.paste(img_result, mask=img_result.split()[3])
            fundo.save(caminho_saida, "JPEG", quality=95, optimize=True)
            print(f"  ✓ {arq} → {nome_saida}")

        except Exception as e:
            print(f"  ✗ Erro em {arq}: {e}")

    print(f"\n  ✓ Colocar_medidas finalizado → {pasta_saida}\n")

    return pasta_saida
