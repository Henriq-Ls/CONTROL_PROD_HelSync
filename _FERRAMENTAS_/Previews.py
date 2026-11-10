# 📁 _FERRAMENTAS_/Previews.py

from io import BytesIO
import os
from pathlib import Path

from PIL import Image, ImageFilter, ImageEnhance
import numpy as np
from rembg import remove, new_session
GERAR_SOMBRA    = True
COMBINAR_CORES  = False  # Desativado — lavava a madeira
ANCORAR_BASE    = True
SUAVIZAR_BORDAS = True
_SESSAO_PREVIEW = None

def remover_fundo_(imagem_path: Path) -> Image.Image:
    global _SESSAO_PREVIEW
    with open(imagem_path, "rb") as f:
        dados = f.read()
    if _SESSAO_PREVIEW is None:
        _SESSAO_PREVIEW = new_session(
            "u2net",
            providers=["CPUExecutionProvider"],
        )
    resultado = remove(dados, session=_SESSAO_PREVIEW)

    return Image.open(BytesIO(resultado)).convert("RGBA")

def refinar_bordas(imagem: Image.Image) -> Image.Image:
    r, g, b, alpha = imagem.split()
    alpha_np = np.array(alpha)

    # 1. Suaviza dentes do rembg
    alpha_blur = Image.fromarray(alpha_np).filter(ImageFilter.GaussianBlur(radius=1.0))
    alpha_blur_np = np.array(alpha_blur)

    # 2. Erosão afiada — corta tudo que não for quase 100% sólido
    alpha_eroded_np = np.where(alpha_blur_np > 180, 255, 0).astype(np.uint8)

    # 3. Micro anti-aliasing final
    alpha_final = Image.fromarray(alpha_eroded_np).filter(ImageFilter.GaussianBlur(radius=0.5))

    return Image.merge("RGBA", (r, g, b, alpha_final))

def gerar_sombra(produto: Image.Image) -> Image.Image:
    w, h = produto.size
    _, _, _, alpha = produto.split()

    # Camada 1 — sombra ambiente (suave, espalhada)
    sombra_amb = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sombra_amb.putalpha(alpha.point(lambda p: int(p * 0.30)))
    sombra_amb = sombra_amb.filter(ImageFilter.GaussianBlur(radius=15))
    sombra_amb = sombra_amb.resize((w, int(h * 0.15)), Image.LANCZOS)

    # Camada 2 — sombra de contato (escura, fininha, colada na base)
    sombra_contato = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sombra_contato.putalpha(alpha.point(lambda p: int(p * 0.70)))
    sombra_contato = sombra_contato.filter(ImageFilter.GaussianBlur(radius=4))
    sombra_contato = sombra_contato.resize((w, int(h * 0.05)), Image.LANCZOS)

    # Monta as duas camadas
    tela_sombra = Image.new("RGBA", (w, int(h * 0.25)), (0, 0, 0, 0))
    tela_sombra.paste(sombra_amb, (0, 10), sombra_amb)

    y_contato = int((tela_sombra.height - sombra_contato.height) / 2) - 5
    tela_sombra.paste(sombra_contato, (0, y_contato), sombra_contato)

    return tela_sombra

# ⚠️  função grande (55 linhas)
def compor(produto, fundo_path, sombra_altura, centralizar=False):
    largura, altura = produto.size

    fundo       = Image.open(fundo_path).convert("RGBA")
    fundo_ratio = fundo.width / fundo.height
    alvo_ratio  = largura / altura

    if fundo_ratio > alvo_ratio:
        nova_h = altura
        nova_w = int(altura * fundo_ratio)
    else:
        nova_w = largura
        nova_h = int(largura / fundo_ratio)

    fundo = fundo.resize((nova_w, nova_h), Image.LANCZOS)
    esq   = (nova_w - largura) // 2
    topo  = (nova_h - altura)  // 2
    fundo = fundo.crop((esq, topo, esq + largura, topo + altura))

    tela = Image.new("RGBA", (largura, altura))
    tela.paste(fundo, (0, 0))

    arr_alpha       = np.array(produto.split()[3])
    linhas_visiveis = np.where(arr_alpha.max(axis=1) > 30)[0]

    if len(linhas_visiveis) > 0:
        topo_produto = linhas_visiveis[0]
        base_produto = linhas_visiveis[-1]

        if centralizar:
            ancora_pct     = 0.55
            centro_produto = (topo_produto + base_produto) // 2
            pos_y          = int(altura * ancora_pct) - centro_produto
            pos_y          = max(0, pos_y)
        elif ANCORAR_BASE:
            ancora_y = int(altura * 0.88)
            pos_y    = ancora_y - base_produto
        else:
            pos_y = (altura - produto.height) // 2

        pos_x = (largura - produto.width) // 2
    else:
        pos_x = (largura - produto.width) // 2
        pos_y = (altura  - produto.height) // 2 if not ANCORAR_BASE else 0

    if GERAR_SOMBRA:
        sombra = gerar_sombra(produto)
        sw, sh = sombra.size
        sx     = pos_x + (largura - sw) // 2 + 8
        sy     = pos_y + produto.height - int(sh * sombra_altura)
        tela.paste(sombra, (sx, sy), mask=sombra)

    tela.paste(produto, (pos_x, pos_y), mask=produto)

    return tela

def preview_produto_com_fundo(imagem_produto_path, imagem_fundo_path, sombra_altura=0.18):
    try:
        produto = remover_fundo_(Path(imagem_produto_path))

        if SUAVIZAR_BORDAS:
            produto = refinar_bordas(produto)

        resultado = compor(produto, imagem_fundo_path, sombra_altura, centralizar=True)

        return resultado

    except:

        return None

# ⚠️  função grande (113 linhas) | except genérico vazio
def Grerar_prev(st, PASTA, REF):
    l1, l2 = st.columns([1, 9])
    c1, x, c2 = st.columns([1, .3, 9])
    m1, l, m2 = st.columns([1, .3, 9])

    BASE_DIR = Path(__file__).resolve().parent.parent
    LOGOS_DIR = BASE_DIR / "Midias"

    PASTA_PREVIEWS = Path(PASTA) / "PREVIEWS"

    logos = [f for f in os.listdir(LOGOS_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg"))]
    logos_logo      = [f for f in logos if f.lower().startswith("logo")]
    logos_fundo     = [f for f in logos if f.lower().startswith("medida")]
    logos_fundo_capa= [f for f in logos if f.lower().startswith("capa")]

    Img_logo       = l1.selectbox("Logo:", logos_logo)
    Img_Fundo_capa = c1.selectbox("Fundo Capa:", logos_fundo_capa)
    Img_Fundo      = m1.selectbox("Fundo Medida:", logos_fundo)

    logo_path  = os.path.join(LOGOS_DIR, Img_logo)
    fundo_path = os.path.join(LOGOS_DIR, Img_Fundo)
    fundo_path2= os.path.join(LOGOS_DIR, Img_Fundo_capa)

    l1.image(logo_path,  width=200)
    c1.image(fundo_path2, width=200)
    m1.image(fundo_path,  width=200)

    def gerar_todos_previews():
        PASTA_PREVIEWS.mkdir(exist_ok=True)
        pasta_produtos = Path(PASTA)
        imagens_produto = (
            sorted(pasta_produtos.glob("*.jpg")) +
            sorted(pasta_produtos.glob("*.jpeg")) +
            sorted(pasta_produtos.glob("*.png"))
        )

        # ── DEBUG ──────────────────────────────────────────
        st.write("📂 PASTA:", str(pasta_produtos))
        st.write("🖼 Imagens encontradas:", [f.name for f in imagens_produto])
        st.write("🎨 Fundos capa:", logos_fundo_capa)
        st.write("📐 Fundos medida:", logos_fundo)
        # ───────────────────────────────────────────────────

        if not imagens_produto:
            st.error("❌ Nenhuma imagem .jpg/.png encontrada na raiz da PASTA!")

            return

        img_atual = imagens_produto[-1]
        st.write("🔍 Usando imagem:", img_atual.name)

        for fundo_capa in logos_fundo_capa:
            caminho = PASTA_PREVIEWS / f"CAPA_{REF}_{fundo_capa.replace(' ', '_')}.png"
            if not caminho.exists():
                preview = preview_produto_com_fundo(img_atual, os.path.join(LOGOS_DIR, fundo_capa))
                if preview:
                    Image.LOAD_TRUNCATED_IMAGES = True
                    preview.save(caminho, 'PNG', quality=95)
                    st.write(f"✅ Salvo: {caminho.name}")
                else:
                    st.write(f"⚠️ preview_produto_com_fundo retornou None para: {fundo_capa}")

        for fundo_medida in logos_fundo:
            caminho = PASTA_PREVIEWS / f"MEDIDA_{REF}_{fundo_medida.replace(' ', '_')}.png"
            if not caminho.exists():
                preview = preview_produto_com_fundo(img_atual, os.path.join(LOGOS_DIR, fundo_medida))
                if preview:
                    Image.LOAD_TRUNCATED_IMAGES = True
                    preview.save(caminho, 'PNG', quality=95)
                    st.write(f"✅ Salvo: {caminho.name}")
                else:
                    st.write(f"⚠️ preview_produto_com_fundo retornou None para: {fundo_medida}")

    total_esperado = len(logos_fundo_capa) + len(logos_fundo)

    if PASTA_PREVIEWS.exists():
        preview_files = list(PASTA_PREVIEWS.glob("*.png"))

        if len(preview_files) < total_esperado:
            with st.spinner(f"🎯 Gerando {total_esperado - len(preview_files)} previews..."):
                gerar_todos_previews()
            st.rerun()

        capas   = sorted([f for f in preview_files if f.name.startswith("CAPA_")])
        medidas = sorted([f for f in preview_files if f.name.startswith("MEDIDA_")])
        l2.info(f"✅ **{len(capas)} CAPAS + {len(medidas)} MEDIDAS**")

        with m2:
            if st.button("🌈 TODAS MEDIDAS", width=True, type='secondary'):
                cols_medida = st.columns(4)
                for i, img_path in enumerate(medidas):
                    with cols_medida[i % 4]:
                        try:
                            st.image(img_path, width=140, caption=img_path.stem[-25:])
                        except: pass

        with c2:
            if st.button("🖼️ TODAS CAPAS", width=True, type='secondary'):
                cols_capa = st.columns(4)
                for i, img_path in enumerate(capas):
                    with cols_capa[i % 4]:
                        try:
                            st.image(img_path, width=140, caption=img_path.stem[-25:])
                        except: pass

    else:
        l2.warning("⚠️ Pasta PREVIEWS não existe")
        if l2.button("▶ Gerar Previews", type='primary'):
            with st.spinner("Gerando previews..."):
                gerar_todos_previews()
            st.rerun()

    return LOGOS_DIR, logo_path, fundo_path2, fundo_path
