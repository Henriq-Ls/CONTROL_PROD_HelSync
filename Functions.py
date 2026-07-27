# Functions.py
import os
from pathlib import Path
import shutil
import subprocess
import textwrap
# ===== FIX WINDOWS: NÃO ABRIR CMD / POWERSHELL =====
STARTUPINFO = subprocess.STARTUPINFO()
STARTUPINFO.dwFlags |= subprocess.STARTF_USESHOWWINDOW
STARTUPINFO.wShowWindow = subprocess.SW_HIDE
CREATE_FLAGS = subprocess.CREATE_NO_WINDOW

def DATA_SISTEMA(port=None):
    from datetime import datetime
    from datetime import date
    if port == None:

        return date.today()

    else:
        hoje = datetime.now()

        return hoje.strftime('%d/%m/%Y')

def Grade_Widget(lista, qt_col): # Pode usar len() da lista cria Grade em linha ou QT cria Grade em coluna
    import streamlit as st
    for im in range(0, len(lista), qt_col):
        linha = st.columns(qt_col)
        for j, i in enumerate(lista[im:im + qt_col]):
            with linha[j]:
                if j < len(lista):
                    Botoes = st.code(str(i))

def nome_base(arquivo):

    return os.path.splitext(arquivo)[0]

def carregar_imagens(pasta):
    extensoes = (".png", ".jpg", ".jpeg", ".webp")

    if not os.path.exists(pasta):

        return []

    return [

        os.path.join(pasta, f)
        for f in sorted(os.listdir(pasta))
        if f.lower().endswith(extensoes)
    ]

def Criar_Arquivo_TEXTO(caminho, titulo, conteudo, ext):
    caminho_txt = rf"{caminho}\\{titulo}{ext}"

    with open(caminho_txt, "w", encoding="utf-8") as f:
        f.write(conteudo)

    return caminho_txt

# Enquandra testo dentro do st.code
def wrap_text(text, width=80): # Quebra o texto nas linhas originais
    lines = text.splitlines()
    wrapped_lines = []
    for line in lines:
        # Aplica wrap apenas em cada linha separadamente
        wrapped_lines.extend(textwrap.wrap(line, width=width) or [""])

    return "\n".join(wrapped_lines)

# Henrique, essa função é só pra olhar na pasta se tem um arquivo com o mesmo nome e se tiver ele procura outro nome diferente.
def gerar_nome_unico(pasta_base: Path, nome_desejado: str) -> Path:
    """
    Gera um caminho único dentro de pasta_base.
    Ex:
    Projeto
    Projeto_2
    Projeto_3
    """
    pasta_base = Path(pasta_base)
    nome_desejado = nome_desejado.strip()

    caminho = pasta_base / nome_desejado
    if not caminho.exists():

        return caminho

    contador = 2
    while True:
        novo_nome = f"{nome_desejado}_{contador}"
        novo_caminho = pasta_base / novo_nome
        if not novo_caminho.exists():

            return novo_caminho

        contador += 1

def escreve(texto):
    import streamlit as st

    return st.write(texto)

def Valdando_produto(st,pasta):
    if os.path.exists(pasta):
        imagens = []
        videos = []
        textos = []
        outros = []

        for arquivo in os.listdir(pasta):

            ext = arquivo.lower().split(".")[-1]

            if ext in ["jpg", "jpeg", "png", "webp"]:
                imagens.append(arquivo)

            elif ext in ["mp4", "mov", "avi", "mkv"]:
                videos.append(arquivo)

            elif ext in ["txt", "md"]:
                textos.append(os.path.join(pasta, arquivo))

            else:
                outros.append(arquivo)

        # validação
        if len(videos) == 0:
            st.error("⚠️ A pasta precisa ter um VÍDEO")

        if len(textos) == 0:
            st.error("⚠️ A pasta precisa ter um ARQUIVO DE TEXTO")

        if len(videos) > 0 and len(textos) > 0:
            st.success("✅ Estrutura da pasta válida")

            return True

    else:
        st.error("Pasta não encontrada")

def Apagar_pasta(PASTA):
    try:
        shutil.rmtree(os.path.join(PASTA))
    except FileNotFoundError: pass

def resetar_imagens_medidas(PASTA):
    origem = os.path.join(PASTA, "Imagens_com_mosaicos")
    destino = os.path.join(PASTA, "Imagens_com_medidas")
    os.makedirs(destino, exist_ok=True)

    # apagar tudo dentro de Imagens_com_medidas
    for item in os.listdir(destino):
        caminho_item = os.path.join(destino, item)

        if os.path.isfile(caminho_item) or os.path.islink(caminho_item):
            os.remove(caminho_item)
        elif os.path.isdir(caminho_item):
            shutil.rmtree(caminho_item)

    # copiar tudo de Imagens_com_mosaicos para Imagens_com_medidas
    for item in os.listdir(origem):
        src = os.path.join(origem, item)
        dst = os.path.join(destino, item)

        if os.path.isfile(src):
            shutil.copy2(src, dst)
        elif os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)

def Contar_Itens_Pasta(pasta):
    import os
    try:
         itens = [
             f for f in os.listdir(pasta)
             if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
         ]

         return len(itens)

    except FileNotFoundError : pass

def extrair_medidas(nome_arquivo):
    nome = os.path.splitext(os.path.basename(nome_arquivo))[0]

    try:
        partes = nome.split("_")

        referencia = partes[0]
        medidas    = partes[1]
        altura, largura, espessura = medidas.split("x")
        peso       = partes[2]

        return {

            "referencia": referencia,
            "altura":     altura,
            "largura":    largura,
            "espessura":  espessura,
            "peso":       peso
        }

    except:

        return None

def gerar_referencia(nome_pro):
    """
    FINAL PERFEITA: ESPAÇO E _ | SEMPRE 3 PRIMEIRAS LETRAS!
    """
    # Converte _ para espaço primeiro
    nome = str(nome_pro).strip().lower().replace('_', ' ')
    palavras = [p for p in nome.split() if len(p) >= 2]

    if len(palavras) < 3:
        if len(palavras) == 1:
            p1 = palavras[0]

            return p1[0] + p1[1] + p1[-1]

        elif len(palavras) == 2:

            return palavras[0][0] + palavras[1][0] + palavras[1][-1]

        else:

            return palavras[0][0] + palavras[0][1] + palavras[0][-1]

    else:
        # 3+ palavras: 1ª letra das 3 PRIMEIRAS

        return palavras[0][0] + palavras[1][0] + palavras[2][0]

def Apagar_Todas(PASTA):
    Apagar_pasta(PASTA, "Imag_most")
    Apagar_pasta(PASTA, "Imag_med")
    Apagar_pasta(PASTA, "Imagens_logo_e_referencia")
    Apagar_pasta(PASTA, "Most_com_fundo")

    Apagar_pasta(PASTA, "Imagens_referencia")
    Apagar_pasta(PASTA, "Imagens_com_medidas")
    Apagar_pasta(PASTA, "Imagens_com_fundos")
    Apagar_pasta(PASTA, "Imagens_com_fundo")
    Apagar_pasta(PASTA, "Imagens_medida")
    Apagar_pasta(PASTA, "Amostra_com_fundo")
    Apagar_pasta(PASTA, "Most_sem_fundo")
    Apagar_pasta(PASTA, "Imagens_mostra")
    Apagar_pasta(PASTA, "Pre_Capas")
    Apagar_pasta(PASTA, "- Capas")
    Apagar_pasta(PASTA, "Imagens_sem_fundo")

def recarregar_Bnaco_vendas_com_outras_pastas(col,PRODUTO,KIT,pasta,text):
    from _BANCOS_.Banco_Bados import del_VENDAS, esc_VENDAS
    if col.button(f'Carregar Banco Com {text}:'):
        del_VENDAS()
        for arquivo in os.listdir(pasta):
            ext = arquivo.lower().split(".")[-1]
            if ext in ["jpeg", "png", "jpg"]:
                id_ = os.path.splitext(arquivo)[0]
                esc_VENDAS(id_, DATA_SISTEMA(), PRODUTO, KIT, os.path.join(pasta, arquivo))
