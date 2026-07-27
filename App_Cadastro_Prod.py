# App_Cadastro_Prod.py
import os
import shutil
import textwrap

import PIL
import streamlit as st

from _FERRAMENTAS_.Falar_Descrever import Falar_Funtion, Falar_Descrever
"""
Cadastro visual de produtos com fotos e medidas

Este módulo implementa um cadastro de produtos em Streamlit onde o usuário:
- Seleciona o tipo de produto (Único ou Kit)
- Define quantas variações de tamanho/cor possui o produto
- Se aplica, define se o produto também é vendido em kit, quantas peças o kit tem
  e quantos kits (grupos de fotos) existem.
Com base nessa configuração, o sistema:
- Lê uma pasta de origem contendo fotos e vídeos
- Mostra as fotos em blocos organizados conforme o cenário (único, kit, único + kit)
- Associa a cada grupo de fotos um conjunto de medidas (altura, largura, espessura, peso)
- Ao clicar em "Processar", o sistema:
  - Cria uma pasta de destino com o nome do produto
  - Move todas as imagens e vídeos para essa pasta
  - Gera um arquivo `produtos.txt` no formato:
      <arquivo>,<altura>x<largura>x<espessura>,<peso>
  - Essa informação de medidas servirá de referência para o próximo programa
    (por exemplo, renomear fotos, gerar etapas de embalagem ou imprimir etiquetas).

Dependências internas:
- Functions.gerar_referencia
- _BANCOS_.Banco_Bados.esc_A_ENTRADA
- _FERRAMENTAS_.Falar_Descrever.Falar_Funtion, Falar_Descrever
"""

def gerar_config_ref(tipo, qt_variacoes, tem_kit_tambem, qt_kit_tambem, qt_pecas_kit, tipo_var_kit, qt_kits):
    """
    Gera uma string resumindo a configuração usada no cadastro.

    Exemplo:
        tipo='Único', qt_variacoes=2, tem_kit_tambem='Sim', qt_kit_tambem=3, qt_kits=2
        → "TIPO:ÚNICO|VAR=2|KIT=SIM|PECAS=3|QTS_KITS=2"

        tipo='Kit', qt_pecas_kit=3, tipo_var_kit='Tamanho', qt_kits=2
        → "TIPO:KIT|PECAS=3|VAR=Tamanho|QTS_KITS=2"
    """
    ref = f"TIPO:{tipo.upper()}"

    if tipo == "Único":
        ref += f"|VAR={qt_variacoes}"
        if tem_kit_tambem == "Sim":
            ref += f"|KIT=YES|PECAS={qt_kit_tambem}|QTS_KITS={qt_kits}"
        else:
            ref += "|KIT=NO"

    elif tipo == "Kit":
        ref += f"|PECAS={qt_pecas_kit}|VAR={tipo_var_kit.upper()}|QTS_KITS={qt_kits}"

    return ref

def listar_imagens(pasta):
    exts = (".jpg", ".jpeg", ".png", ".webp", ".mp4")
    arquivos = []
    for f in os.listdir(pasta):
        if f.lower().endswith(exts):
            arquivos.append(f)

    return sorted(arquivos)

def wrap_text(text, width=80):
    lines = text.splitlines()
    wrapped_lines = []
    for line in lines:
        wrapped_lines.extend(textwrap.wrap(line, width=width) or [""])

    return "\n".join(wrapped_lines)

def _bloco_foto_medidas(arq, pasta_origem, label, key_prefix):
    """
    Mostra 1 foto ao lado dos inputs de medidas.
    Retorna (arq, altura, largura, espessura, peso).
    """
    caminho = os.path.join(pasta_origem, arq)
    col0, col1, col2, x1, col3, x2, col4, vir, col5 = st.columns(
        [2, 3, 2, 0.3, 2, 0.3, 2, 0.3, 2]
    )
    with col0:
        st.image(caminho, width=200)
    with col1:
        st.subheader(label)
        st.caption(arq)
    with col2:
        altura = st.text_input("Altura", key=f"alt_{key_prefix}")
    with x1:
        st.write("")
        st.write("X")
    with col3:
        largura = st.text_input("Largura", key=f"lar_{key_prefix}")
    with x2:
        st.write("")
        st.write("X")
    with col4:
        espessura = st.text_input("Espessura", key=f"esp_{key_prefix}")
    with vir:
        st.write("")
        st.write(",")
    with col5:
        peso = st.text_input("Peso", key=f"peso_{key_prefix}")

    return arq, altura, largura, espessura, peso

def _mostrar_fotos_grupo(grupo, pasta_origem):
    """Mostra fotos de um grupo em linha, sem inputs."""
    if not grupo:

        return

    cols = st.columns(min(len(grupo), 5))
    for idx, arq in enumerate(grupo):
        caminho = os.path.join(pasta_origem, arq)
        with cols[idx % len(cols)]:
            st.image(caminho, width=180)
            st.caption(arq)

# criar pastas  "Proportion_Ajustada" e  "Ajuste_Geral"
def _gerar_pastas(PASTA,Prop):
    """ Gera as primeiras pastas do projetos "Proportion_Ajustada" e  "Ajuste_Geral" """
    from Tratar_midias.a__Ajuste_Proportion_IMG import Proporcao_IMG
    from Tratar_midias.b__Ajuste_Geral_IMG import Ajuste_IMG
    Proportion_Ajustada = os.path.join(PASTA, "Proportion_Ajustada")
    Ajuste_Geral = os.path.join(PASTA, "Ajuste_Geral")
    # 👀 PREVIEW EM TEMPO REAL
    if not os.path.exists(Proportion_Ajustada):
        # ajusta a proporção da imagem

        Proporcao_IMG(PASTA, Proportion_Ajustada, tuple(map(int, Prop.split(':'))))
        Ajuste_IMG(Proportion_Ajustada, Ajuste_Geral)

# ==============================================================================
#  FUNÇÃO PRINCIPAL
# ==============================================================================

# ⚠️  função grande (390 linhas)
def Cadastro_Produtos(TOP1, TOP2, TOP3, MEIO1, MEIO2): # ── Cabeçalho / informações gerais ────────────────────────────────────────
    with TOP2:
        pasta_origem = st.text_input("Pasta de Origem", r'C:\Users\henri\Downloads\cel')
        Acompanha = st.text_input('Acompanha Produto')
        Usar = Falar_Funtion(st)

    with TOP1:
        nome_pro = st.text_input("Nome Produto")
        if pasta_origem and os.path.exists(pasta_origem):
            arquivos_todos = listar_imagens(pasta_origem)
            st.subheader(f"Total de arquivos: {len(arquivos_todos)}")
            for arq in arquivos_todos:
                caminho = os.path.join(pasta_origem, arq)
                if arq.lower().endswith(".mp4"):
                    st.video(caminho)

    with TOP3:
        Acabamento = st.multiselect(
            'Trabalhos:',
            ['lixado', 'lavado', 'Vernizado', 'Impressão a Laiser', 'Pode ser Estilizado pelo Cliente']
        )
        Prop = st.selectbox('Proporção imagem:', ['3:4', '1:1', '4:5', '9:16', '16:9'])
        descrit = Falar_Descrever(st)

    # ── SELETORES ──────────────────────────────────────────────────────────────
    #
    #  SELECT 1 → Único ou Kit?
    #  SELECT 2 → (se Único) quantas variações? | (se Kit) quantas peças?
    #  SELECT 3 → (se Único) também vendido em kit? | (se Kit) tipo de variação?
    #  SELECT 4 → (se Único + kit) quantas peças no kit?
    #
    #  NOVO: SELECT 4 (Kit) → QUANTOS KITS (grupos de fotos)
    #
    # --------------------------------------------------------------------------

    with MEIO2:
        st.markdown("### Classificação do Produto")

        col_s1, col_s2 = st.columns(2)

        # SELECT 1 ─────────────────────────────────────────────────────────────
        tipo_principal = col_s1.selectbox(
            '1. Tipo:',
            ['Único', 'Kit'],
            help=(
                'Único = um produto (pode ter variações de tamanho/cor).\n'
                'Kit = conjunto de peças vendidas juntas.'
            )
        )

        # Valores padrão — sobrescritos pelos selects abaixo
        qt_variacoes   = 1
        tem_kit_tambem = 'Não'
        qt_kit_tambem  = 2
        qt_pecas_kit   = 2
        tipo_var_kit   = 'Sem variação'
        qt_kits        = 1  # novo: quantos grupos de kit

        # SELECT 2 ─────────────────────────────────────────────────────────────
        if tipo_principal == 'Único':
            qt_variacoes = col_s2.selectbox(
                '2. Quantas variações de tamanho/cor?',
                [1, 2, 3, 4, 5, 6, 7, 8, 9],
                help=(
                    '1 = produto único sem variação (todas as fotos têm a mesma medida).\n'
                    '2+ = cada variação tem seu grupo de fotos e suas próprias medidas.'
                )
            )

            # SELECT 3 ─────────────────────────────────────────────────────────
            col_s3, col_s4 = st.columns(2)
            tem_kit_tambem = col_s3.selectbox(
                '3. Também vendido em kit?',
                ['Não', 'Sim'],
                help='O produto único pode também ser vendido como conjunto (kit de 3, de 6, etc.).'
            )

            # SELECT 4 ─────────────────────────────────────────────────────────
            if tem_kit_tambem == 'Sim':
                qt_kit_tambem = col_s4.selectbox(
                    '4. Quantas peças no kit?',
                    [2, 3, 4, 5, 6, 7, 8, 9, 10]
                )

        elif tipo_principal == 'Kit':
            qt_pecas_kit = col_s2.selectbox(
                '2. Quantas peças no kit?',
                [2, 3, 4, 5, 6, 7, 8, 9, 10],
                help=(
                    'O sistema vai esperar: 1 foto do kit completo + N fotos individuais.\n'
                    'Cada foto gera seu bloco de medidas.'
                )
            )

            # SELECT 3 ─────────────────────────────────────────────────────────
            tipo_var_kit = st.selectbox(
                '3. As peças do kit variam em quê?',
                ['Sem variação', 'Tamanho', 'Cor', 'Peso', 'Mista'],
                help='Apenas para organização. Não altera a quantidade de inputs.'
            )

            # SELECT 4 (NOVO) ───────────────────────────────────────────────────
            qt_kits = st.selectbox(
                '4. Quantos kits (grupos de fotos)?',
                [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                help='Quantos conjuntos completos (foto do kit + peças individuais) você tem?'
            )

        # Resumo do que o sistema vai esperar ──────────────────────────────────
        if tipo_principal == 'Único':
            if qt_variacoes == 1 and tem_kit_tambem == 'Não':
                total_blocos = 1
                resumo = (
                    f"ÚNICO SEM VARIAÇÃO  —  "
                    f"todas as fotos compartilham 1 único bloco de medidas."
                )
            elif qt_variacoes > 1 and tem_kit_tambem == 'Não':
                total_blocos = qt_variacoes
                resumo = (
                    f"ÚNICO COM {qt_variacoes} VARIAÇÕES  —  "
                    f"fotos divididas em {qt_variacoes} grupos, cada grupo com seu bloco de medidas."
                )
            elif qt_variacoes == 1 and tem_kit_tambem == 'Sim':
                total_blocos = 1 + qt_kits + qt_kits * qt_kit_tambem
                resumo = (
                    f"ÚNICO + {qt_kits} KITS DE {qt_kit_tambem} PEÇAS  —  "
                    f"1 bloco para o único + {qt_kits} grupos de kit (1 foto do kit completo "
                    f"+ {qt_kit_tambem} fotos individuais por grupo)."
                )
            else:
                total_blocos = qt_variacoes + qt_kits + qt_kits * qt_kit_tambem
                resumo = (
                    f"ÚNICO COM {qt_variacoes} VARIAÇÕES + {qt_kits} KITS DE {qt_kit_tambem} PEÇAS  —  "
                    f"{total_blocos} blocos de medidas no total."
                )
        else:
            fotos_por_kit = 1 + qt_pecas_kit
            total_esperado = fotos_por_kit * qt_kits
            resumo = (
                f"KIT DE {qt_pecas_kit} PEÇAS ({tipo_var_kit})  —  "
                f"espera {total_esperado} fotos: "
                f"{qt_kits} × (1 foto do kit completo + {qt_pecas_kit} fotos individuais)."
            )

        st.info(resumo)

    # ── ÁREA PRINCIPAL: FOTOS + INPUTS DINÂMICOS ──────────────────────────────
    with MEIO1:
        try:
            if pasta_origem and os.path.exists(pasta_origem):

                arquivos_todos = listar_imagens(pasta_origem)
                extensoes_img  = ('.jpg', '.jpeg', '.png', '.webp')
                arquivos_img   = [a for a in arquivos_todos if a.lower().endswith(extensoes_img)]

                dados = []  # lista de (arquivo, altura, largura, espessura, peso)

                # ==============================================================
                #  CENÁRIO A — ÚNICO SEM VARIAÇÃO, SEM KIT
                #  Todas as fotos → 1 bloco de medidas compartilhado
                # ==============================================================
                if tipo_principal == 'Único' and qt_variacoes == 1 and tem_kit_tambem == 'Não':

                    st.markdown("---")
                    st.markdown("#### Produto Único — medidas únicas para todas as fotos")

                    col1, col2, x1, col3, x2, col4, vir, col5 = st.columns(
                        [3, 2, 0.3, 2, 0.3, 2, 0.3, 2]
                    )
                    with col2: altura   = st.text_input("Altura",    key="alt_a")
                    with x1:   st.write(""); st.write("X")
                    with col3: largura  = st.text_input("Largura",   key="lar_a")
                    with x2:   st.write(""); st.write("X")
                    with col4: espessura = st.text_input("Espessura", key="esp_a")
                    with vir:  st.write(""); st.write(",")
                    with col5: peso     = st.text_input("Peso",      key="peso_a")

                    _mostrar_fotos_grupo(arquivos_img, pasta_origem)

                    for arq in arquivos_img:
                        dados.append((arq, altura, largura, espessura, peso))

                # ==============================================================
                #  CENÁRIO B — ÚNICO COM N VARIAÇÕES, SEM KIT
                #  Fotos divididas em N grupos iguais, cada grupo → 1 bloco
                # ==============================================================
                elif tipo_principal == 'Único' and qt_variacoes > 1 and tem_kit_tambem == 'Não':

                    total         = len(arquivos_img)
                    fotos_por_var = max(1, total // qt_variacoes)

                    st.markdown("---")
                    st.markdown(f"#### Produto Único — {qt_variacoes} Variações")

                    for v in range(qt_variacoes):
                        inicio = v * fotos_por_var
                        fim    = total if v == qt_variacoes - 1 else inicio + fotos_por_var
                        grupo  = arquivos_img[inicio:fim]

                        st.markdown(f"**Variação {v + 1}**")

                        col1, col2, x1, col3, x2, col4, vir, col5 = st.columns(
                            [3, 2, 0.3, 2, 0.3, 2, 0.3, 2]
                        )
                        with col2: alt = st.text_input("Altura",    key=f"alt_b_{v}")
                        with x1:   st.write(""); st.write("X")
                        with col3: lar = st.text_input("Largura",   key=f"lar_b_{v}")
                        with x2:   st.write(""); st.write("X")
                        with col4: esp = st.text_input("Espessura", key=f"esp_b_{v}")
                        with vir:  st.write(""); st.write(",")
                        with col5: pso = st.text_input("Peso",      key=f"peso_b_{v}")

                        _mostrar_fotos_grupo(grupo, pasta_origem)

                        for arq in grupo:
                            dados.append((arq, alt, lar, esp, pso))

                # ==============================================================
                #  CENÁRIO C — KIT (com qt_kits)
                #  Fotos em blocos: [1 foto kit completo + qt_pecas_kit] x qt_kits
                #  Cada bloco gera 1 + qt_pecas_kit blocos de medidas
                # ==============================================================
                elif tipo_principal == 'Kit':

                    fotos_por_kit       = 1 + qt_pecas_kit
                    total_fotos_kit     = fotos_por_kit * qt_kits
                    fotos_kit_raw       = arquivos_img[:total_fotos_kit] if len(arquivos_img) >= total_fotos_kit else arquivos_img

                    st.markdown("---")
                    st.markdown(f"#### Kit de {qt_pecas_kit} Peças — {tipo_var_kit} — {qt_kits} kits")
                    st.caption(
                        f"Ordem: para cada kit: 1 foto do kit completo + {qt_pecas_kit} fotos individuais "
                        f"(total esperado: {total_fotos_kit} fotos)"
                    )

                    for i, arq in enumerate(fotos_kit_raw):
                        idx_dentro_kit = i % fotos_por_kit

                        if idx_dentro_kit == 0:
                            label = f"📦 Kit Completo {i // fotos_por_kit + 1}"
                        else:
                            label = f"Kit {i // fotos_por_kit + 1} - Peça {idx_dentro_kit}"

                        resultado = _bloco_foto_medidas(arq, pasta_origem, label, f"c_{i}")
                        dados.append(resultado)

                # ==============================================================
                #  CENÁRIO D — ÚNICO + TAMBÉM KIT (com qt_kits)
                #  Parte 1: produto único (1 ou N variações)
                #  Parte 2: múltiplos kits (qt_kits grupos)
                #  O sistema assume: últimas fotos = blocos de kit
                # ==============================================================

                elif tipo_principal == 'Único' and tem_kit_tambem == 'Sim':

                    # --- Nova lógica: quantos grupos de kit ---
                    fotos_por_kit       = 1 + qt_kit_tambem
                    total_fotos_kit     = fotos_por_kit * qt_kits

                    # Único → todas MENOS o que é kit
                    fotos_unico    = arquivos_img[:-total_fotos_kit] if len(arquivos_img) > total_fotos_kit else []
                    fotos_kit_sec  = arquivos_img[-total_fotos_kit:] if len(arquivos_img) >= total_fotos_kit else []

                    # -- Parte 1: Único ----------------------------------------
                    st.markdown("---")
                    st.markdown("#### Produto Único")

                    if qt_variacoes == 1:
                        col1, col2, x1, col3, x2, col4, vir, col5 = st.columns(
                            [3, 2, 0.3, 2, 0.3, 2, 0.3, 2]
                        )
                        with col2: alt = st.text_input("Altura",    key="alt_d_unico")
                        with x1:   st.write(""); st.write("X")
                        with col3: lar = st.text_input("Largura",   key="lar_d_unico")
                        with x2:   st.write(""); st.write("X")
                        with col4: esp = st.text_input("Espessura", key="esp_d_unico")
                        with vir:  st.write(""); st.write(",")
                        with col5: pso = st.text_input("Peso",      key="peso_d_unico")

                        _mostrar_fotos_grupo(fotos_unico, pasta_origem)

                        for arq in fotos_unico:
                            dados.append((arq, alt, lar, esp, pso))

                    else:
                        total_u       = len(fotos_unico)
                        fotos_por_var = max(1, total_u // qt_variacoes)

                        for v in range(qt_variacoes):
                            inicio = v * fotos_por_var
                            fim    = total_u if v == qt_variacoes - 1 else inicio + fotos_por_var
                            grupo  = fotos_unico[inicio:fim]

                            st.markdown(f"**Variação {v + 1}**")
                            col1, col2, x1, col3, x2, col4, vir, col5 = st.columns(
                                [3, 2, 0.3, 2, 0.3, 2, 0.3, 2]
                            )
                            with col2: alt = st.text_input("Altura",    key=f"alt_d_var_{v}")
                            with x1:   st.write(""); st.write("X")
                            with col3: lar = st.text_input("Largura",   key=f"lar_d_var_{v}")
                            with x2:   st.write(""); st.write("X")
                            with col4: esp = st.text_input("Espessura", key=f"esp_d_var_{v}")
                            with vir:  st.write(""); st.write(",")
                            with col5: pso = st.text_input("Peso",      key=f"peso_d_var_{v}")

                            _mostrar_fotos_grupo(grupo, pasta_origem)

                            for arq in grupo:
                                dados.append((arq, alt, lar, esp, pso))

                    # -- Parte 2: KIT (com qt_kits) ----------------------------
                    st.markdown("---")
                    st.markdown(f"#### Kit de {qt_kit_tambem} Peças — {qt_kits} kits")
                    st.caption(
                        f"Ordem: para cada kit: 1 foto do kit completo + {qt_kit_tambem} fotos individuais "
                        f"(total esperado: {total_fotos_kit} fotos)"
                    )

                    for i, arq in enumerate(fotos_kit_sec):
                        idx_dentro_kit = i % fotos_por_kit

                        if idx_dentro_kit == 0:
                            label = f"📦 Kit Completo {i // fotos_por_kit + 1}"
                        else:
                            label = f"Kit {i // fotos_por_kit + 1} - Peça {idx_dentro_kit}"

                        resultado = _bloco_foto_medidas(arq, pasta_origem, label, f"d_kit_{i}")
                        dados.append(resultado)

                # ==============================================================
                #  BOTÃO PROCESSAR
                # ==============================================================
                if nome_pro and descrit:
                    if st.button("Processar", width=True, type='primary'):

                        pasta_destino = rf'C:\Users\henri\Downloads\PRODUTOS\{nome_pro.strip().upper()}'

                        # Depois a referência de para kit ou unico
                        ref_kit = gerar_config_ref(
                            tipo_principal,
                            qt_variacoes,
                            tem_kit_tambem,
                            qt_kit_tambem,
                            qt_pecas_kit,
                            tipo_var_kit,
                            qt_kits
                        )
                        from Functions import gerar_referencia
                        from _BANCOS_.Banco_Bados import esc_A_ENTRADA
                        esc_A_ENTRADA(
                            nome_pro.title(),
                            gerar_referencia(str(nome_pro)).lower(),  # referência do produto
                            pasta_destino,
                            descrit,
                            Usar,
                            Acompanha,
                            ', '.join(Acabamento),
                            ref_kit  # configuração de cadastro aqui em KIT
                        )

                        os.makedirs(pasta_destino, exist_ok=True)

                        caminho_txt = os.path.join(pasta_destino, "produtos.txt")

                        with open(caminho_txt, "w", encoding="utf-8") as f:
                            for arq, alt, lar, esp, pso in dados:
                                linha = f"{alt}x{lar}x{esp},{pso}"
                                f.write(linha + "\n")

                                origem_file  = os.path.join(pasta_origem, arq)
                                destino_file = os.path.join(pasta_destino, arq)
                                if os.path.exists(origem_file):
                                    shutil.copy2(origem_file, destino_file)

                            # Move vídeos (não entram nos dados, mas precisam ir junto)
                            for arq in arquivos_todos:
                                if arq.lower().endswith('.mp4'):
                                    origem_file  = os.path.join(pasta_origem, arq)
                                    destino_file = os.path.join(pasta_destino, arq)
                                    if os.path.exists(origem_file):
                                        shutil.copy2(origem_file, destino_file)

                        # criar pastas  "Proportion_Ajustada" e  "Ajuste_Geral"
                        with st.spinner('Agurde ! Gerando pastas # criar pastas  "Proportion_Ajustada" e  "Ajuste_Geral"'):
                            _gerar_pastas(pasta_destino, Prop)

                        st.success("Arquivos movidos e TXT criado com sucesso!")

        except PIL.UnidentifiedImageError:
            st.warning("Pasta Câmera Vazia!")
