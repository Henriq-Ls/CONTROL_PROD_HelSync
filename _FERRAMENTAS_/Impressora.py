# 📁 _FERRAMENTAS_/Impressora.py
from PIL import Image, ImageDraw, ImageFont
import io, math, os
try:
    import win32print
    import win32ui
    import win32con
except (ImportError, OSError):
    win32print = None
    win32ui = None
    win32con = None
    WIN32_DISPONIVEL = False
else:
    WIN32_DISPONIVEL = True


# INSTALA : pip install pywin32 - IMPRESSORA
# PARA DESCOBIR A IMPRESSORA
'''for i in win32print.EnumPrinters(2):
    print(i[2])'''

# INSTALA : pip install pywin32 - IMPRESSORA
# PARA DESCOBIR A IMPRESSORA
'''for i in win32print.EnumPrinters(2):
    print(i[2])'''

arquivo = os.path.join(
    os.path.dirname(__file__),
    "rodar_impressao.py"
)

def imprimir_etiquetas_grade_BANCO(
    textos,
    largura_folha_mm=210,
    altura_folha_mm=297,
    colunas=2,
    linhas=1,
    margem_folha_mm=5,
    espaco_entre_mm=2,
    tamanho_fonte=20,
    alinhamento="centro",
    borda=True,
    rotacao=0
):
    if not WIN32_DISPONIVEL:
        raise RuntimeError(
            "A impressão direta de etiquetas exige uma instalação Windows "
            "com pywin32 disponível."
        )

    from PIL import ImageWin

    total_celulas = colunas * linhas

    if isinstance(textos, str):
        lista = [textos] * total_celulas
    else:
        lista = list(textos)
        lista += [""] * max(0, total_celulas - len(lista))
        lista = lista[:total_celulas]

    # Gera a MESMA imagem do preview
    preview = gerar_preview(
        textos=lista,
        largura_mm=largura_folha_mm,
        altura_mm=altura_folha_mm,
        colunas=colunas,
        linhas=linhas,
        margem_mm=margem_folha_mm,
        espaco_mm=espaco_entre_mm,
        tamanho_fonte=tamanho_fonte,
        alinhamento=alinhamento,
        borda=borda,
        rotacao=rotacao
    )

    printer_name = win32print.GetDefaultPrinter()

    hDC = win32ui.CreateDC()
    hDC.CreatePrinterDC(printer_name)

    dpi_x = hDC.GetDeviceCaps(win32con.LOGPIXELSX)
    dpi_y = hDC.GetDeviceCaps(win32con.LOGPIXELSY)

    def mm2px_x(mm):
        return int(mm * dpi_x / 25.4)

    def mm2px_y(mm):
        return int(mm * dpi_y / 25.4)

    page_w = mm2px_x(largura_folha_mm)
    page_h = mm2px_y(altura_folha_mm)

    # Ajusta imagem para resolução real da impressora
    img_print = preview.resize((page_w, page_h), Image.LANCZOS)

    if img_print.mode != "RGB":
        img_print = img_print.convert("RGB")

    dib = ImageWin.Dib(img_print)

    hDC.StartDoc("Etiquetas")
    hDC.StartPage()

    dib.draw(
        hDC.GetHandleOutput(),
        (0, 0, page_w, page_h)
    )

    hDC.EndPage()
    hDC.EndDoc()
    hDC.DeleteDC()

def gerar_preview(textos, largura_mm, altura_mm, colunas, linhas, margem_mm, espaco_mm, tamanho_fonte, alinhamento, borda, rotacao=0):
    escala = 10
    W = int(largura_mm * escala)
    H = int(altura_mm * escala)

    img = Image.new('RGB', (W, H), color='#f5f5f5')
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W - 1, H - 1], outline='#aaaaaa', width=2)

    margem_px = margem_mm * escala
    espaco_px = espaco_mm * escala

    area_w = W - 2 * margem_px - espaco_px * (colunas - 1)
    area_h = H - 2 * margem_px - espaco_px * (linhas - 1)
    cel_w  = area_w / colunas
    cel_h  = area_h / linhas

    total = colunas * linhas
    lista = (list(textos) + [''] * total)[:total]

    for linha in range(linhas):
        for coluna in range(colunas):
            idx   = linha * colunas + coluna
            texto = lista[idx]

            x0 = int(margem_px + coluna * (cel_w + espaco_px))
            y0 = int(margem_px + linha  * (cel_h + espaco_px))
            x1 = int(x0 + cel_w)
            y1 = int(y0 + cel_h)

            draw.rectangle([x0, y0, x1, y1], fill='white',
                           outline='black' if borda else '#dddddd', width=2)

            # Para 90/270° inverte dimensões do canvas de texto
            if rotacao in (90, 270):
                tw = int(cel_h)
                th = int(cel_w)
            else:
                tw = int(cel_w)
                th = int(cel_h)

            linhas_texto = texto.split('\n')

            # Auto-ajuste: reduz fonte até o texto caber na célula
            fonte_atual = int(tamanho_fonte * escala / 4)
            margem_int  = int(min(tw, th) * 0.05)

            while fonte_atual > 5:
                try:
                    font_teste = ImageFont.truetype("arial.ttf", fonte_atual)
                except:
                    font_teste = ImageFont.load_default()

                line_h_teste = fonte_atual + 2
                bloco_h_teste = line_h_teste * len(linhas_texto)

                max_w = 0
                for lt in linhas_texto:
                    try:
                        bbox = font_teste.getbbox(lt)
                        max_w = max(max_w, bbox[2] - bbox[0])
                    except:
                        max_w = max(max_w, len(lt) * fonte_atual * 0.6)

                if max_w <= (tw - 2 * margem_int) and bloco_h_teste <= (th - 2 * margem_int):
                    break
                fonte_atual -= 1

            try:
                font = ImageFont.truetype("arial.ttf", fonte_atual)
            except:
                font = ImageFont.load_default()

            line_h  = fonte_atual + 2
            bloco_h = line_h * len(linhas_texto)

            cel_img  = Image.new('RGBA', (tw, th), (255, 255, 255, 0))
            cel_draw = ImageDraw.Draw(cel_img)

            if "esquerda" in alinhamento:
                ax    = margem_int
                align = "left"
            elif "direita" in alinhamento:
                ax    = tw - margem_int
                align = "right"
            else:
                ax    = tw // 2
                align = "center"

            if "topo" in alinhamento:
                ay = margem_int
            elif "baixo" in alinhamento:
                ay = th - margem_int - bloco_h
            else:
                ay = (th - bloco_h) // 2

            for i, linha_txt in enumerate(linhas_texto):
                cel_draw.text((ax, ay + i * line_h), linha_txt,
                              fill='black', font=font, align=align)

            if rotacao != 0:
                cel_img = cel_img.rotate(rotacao, expand=True)

            img.paste(cel_img, (x0, y0), cel_img)

    return img


# ── Interface Streamlit ──────────────────────────────────────────────────
def quebrar_texto(texto,qt):
    """
    Quebra uma string a cada 10 caracteres, cortando apenas em espaços (' ').
    Processa linha por linha até o final.

    Exemplo:
    >>> quebrar_texto("Este é um texto bem longo para testar a função de quebra.")
    'Este é um\ntexto bem\nlongo para\ntestar a\nfunção de\nquebra.'
    """
    linhas = []
    inicio = 0

    while inicio < len(texto):
        # Encontra o próximo corte: próximo espaço após 10 chars ou fim da string
        fim = inicio + qt
        if fim >= len(texto):
            linhas.append(texto[inicio:])
            break

        # Procura o espaço mais próximo após o limite de 10 chars
        espaco_pos = texto.find(' ', fim)
        if espaco_pos == -1:
            # Sem espaço até o fim, quebra no fim da string
            linhas.append(texto[inicio:])
            break

        # Quebra no espaço encontrado
        linha = texto[inicio:espaco_pos].rstrip()
        if linha:  # Só adiciona se não vazia
            linhas.append(linha)

        inicio = espaco_pos + 1  # Pula o espaço

    return '\n'.join(linhas)

def Painel_Imprimir(st, PRODUTO):
    from _BANCOS_.Banco_Bados import ler_VENDAS_IMPRIMI
    vendas = ler_VENDAS_IMPRIMI(PRODUTO)
    textos = []
    col_esq, col_dir = st.columns([1, 2])
    cont = col_esq.container(height=700)

    qt = cont.selectbox('Quebra linha:', [20, 5, 10, 15, 25])

    for i in vendas:
        try:
            valor = f"R$ {float(i[3]):.2f}"
        except (TypeError, ValueError):
            valor = "R$ --"
        textos.append(f" {i[0]} \n {i[1]} \n {quebrar_texto(i[2], qt)} \n {valor} ")

    with cont:
        rotacao = st.selectbox('Rotação do texto:', [0, 90, 180, 270])
        folha   = st.selectbox('Papel:', ['100 x 150', '50 x 30'])
        tam     = st.selectbox('Tamanho do Texto:', [15, 5, 10, 20, 25, 30])
        alinha  = st.selectbox('Alinhamento:', [
            "topo-esquerda", "topo-centro", "topo-direita",
            "meio-esquerda", "centro",      "meio-direita",
            "baixo-esquerda","baixo-centro","baixo-direita"
        ])
        caixa = st.checkbox('Borda Caixa')
        cluna = st.selectbox('Colunas:', [2, 1, 3, 4, 5, 6, 7, 8])

        if st.button('🖨️ Imprimir'):
            import subprocess, json, sys
            dados = json.dumps({
                "textos":           textos,
                "largura_folha_mm": int(folha.split(' x ')[0]),
                "altura_folha_mm":  int(folha.split(' x ')[1]),
                "colunas":          cluna,
                "linhas":           math.ceil(len(textos) / cluna),
                "margem_folha_mm":  5,
                "espaco_entre_mm":  2,
                "tamanho_fonte":    tam,
                "alinhamento":      alinha,
                "borda":            caixa,
                "rotacao":          rotacao
            })
            subprocess.Popen([sys.executable, arquivo, dados])
            st.success("Enviado para impressão!")

    cont = col_dir.container(height=700)
    with cont:
        preview = gerar_preview(
            textos=textos,
            largura_mm=int(folha.split(' x ')[0]),
            altura_mm=int(folha.split(' x ')[1]),
            colunas=cluna,
            linhas=math.ceil(len(textos) / cluna),
            margem_mm=5,
            espaco_mm=2,
            tamanho_fonte=tam,
            alinhamento=alinha,
            borda=caixa,
            rotacao=rotacao  # ← agora passa a rotação!
        )

        max_h = 800
        if preview.height > max_h:
            ratio  = max_h / preview.height
            novo_w = int(preview.width * ratio)
            preview = preview.resize((novo_w, max_h), Image.LANCZOS)

        st.image(preview)
