# 📁 _APP_/Functions_app.py

import os
from time import sleep

from Gerar_Documentos.App_Prompts import gerar_prompt_shopee
import streamlit as st

from _BANCOS_.Banco_Bados import ATUAL_VENDAS, esc_MARKET_PLACE, del_MARKET_PLACE, del_VENDAS

def limpar_CASH():
    import streamlit as st
    st.toast('Limpando CACHE! ')
    st.cache_data.clear()
    st.cache_resource.clear()

def Alerta(st, msg):
    @st.dialog("Alerta ")
    def menu_principal():
        st.warning(msg)

    menu_principal()

def escreve(txt):
    HtmL = f'<div style=" display: block; font-size: 18px; background-color: white; width: 100%; height: 25px; border-bottom: 2px solid black; color: black;  text-align: center;">{txt}</div>'

    return st.iframe(HtmL, height=50, scrolling=True)

def _LOGS_popover(st, titulo, logs):
    """
    Cria uma área de log em um popover com container limitado.
    Retorna uma função 'log' para adicionar mensagens.
    """
    with st.popover(titulo):
        with st.container(border=True, height=200):
            log_area = st.empty()

            def log(msg):
                logs.append(str(msg))
                if len(logs) <= 50:  # Limita a 50 logs para não travar o Streamlit
                    log_area.code("\n".join(logs), language="bash")

            return log

def Btn_Cliq_Duplo(nome_aberto, nome_fechado, key, fechar_outras=None):
    import streamlit as st
    state_key = f"{key}_state"
    widget_key = f"{key}_widget"

    if state_key not in st.session_state:
        st.session_state[state_key] = False

    def toggle():
        st.session_state[state_key] = not st.session_state[state_key]
        if fechar_outras:
            for k in fechar_outras:
                st.session_state[f"{k}_state"] = False

    if st.session_state[state_key]:
        st.button(
            nome_aberto,
            key=widget_key,
            on_click=toggle,
            width='stretch',
            type="primary"
        )
    else:
        st.button(
            nome_fechado,
            key=widget_key,
            on_click=toggle,
            width='stretch',
            type="secondary"
        )

    return st.session_state[state_key]

    '''  EXEMPLI DE USO:
    aberto = Button_Nao_Fecha(
        nome_aberto="Painel aberto",
        nome_fechado="Abrir painel",
        key="painel_exemplo"
    )

    if aberto:
        st.markdown("### Conteúdo do painel")
        st.write("Qualquer coisa aqui dentro")

        # BOTÃO INTERNO QUE FECHA
        if st.button("Fechar painel", key="fechar_painel"):
            st.session_state["painel_exemplo_state"] = False
            st.rerun()
    '''

def controlar_altura(st,chave, altura_inicial=100, passo=10, minimo=0, maximo=None):
    estado_altura = f"{chave}_altura"

    if estado_altura not in st.session_state:
        st.session_state[estado_altura] = altura_inicial

    if st.button(":material/keyboard_double_arrow_up:", key=f"{chave}_mais"):
        st.session_state[estado_altura] += passo

    if st.button(":material/keyboard_double_arrow_down:", key=f"{chave}_menos"):
        st.session_state[estado_altura] -= passo

    if st.session_state[estado_altura] < minimo:
        st.session_state[estado_altura] = minimo

    if maximo is not None and st.session_state[estado_altura] > maximo:
        st.session_state[estado_altura] = maximo

    return st.session_state[estado_altura]

def controlar_altura_horiz(st,chave, altura_inicial=100, passo=10, minimo=0, maximo=None):
    estado_altura = f"{chave}_altura1"

    if estado_altura not in st.session_state:
        st.session_state[estado_altura] = altura_inicial
    st1, st2 = st.columns(2)

    if st1.button(":material/keyboard_double_arrow_down:", key=f"{chave}_mais1"):
        st.session_state[estado_altura] += passo

    if st2.button(":material/keyboard_double_arrow_up:", key=f"{chave}_menos1"):
        st.session_state[estado_altura] -= passo

    if st.session_state[estado_altura] < minimo:
        st.session_state[estado_altura] = minimo

    if maximo is not None and st.session_state[estado_altura] > maximo:
        st.session_state[estado_altura] = maximo

    return st.session_state[estado_altura]

def Apagar_Arq(st, nome, diretorio):
    @st.dialog(f"Apagar {nome}")
    def menu_principal():
        st1, st2 = st.columns([9, 1])
        st1.text(f"🗑️ Tem certeza de que deseja apagar?")
        st1.code(f"{diretorio}")
        if st2.button("x", key="fechar_painel", ):
            st.session_state["botao_apagar_arquivos_state"] = False
            st.rerun()

        if st.button(f"**❌ Apagar Sim!**", key=f"{nome}_btn_del2", width='stretch', type="secondary"):
            st.session_state.Apagar_Arquivos = False

            sleep(1.5)
            st.session_state["botao_apagar_arquivos_state"] = False

            st.rerun()

    menu_principal()

@st.cache_data
def car_imag(PASTA, lista):
    caminhos = [os.path.join(PASTA, i) for i in lista]

    return caminhos

def Grade_Widget_BTN_IMG(st, PASTA, qt_col):
    lista = os.listdir(PASTA)
    caminhos = car_imag(PASTA, lista)
    # render normal (leve agora)
    for im in range(0, len(caminhos), qt_col):
        cols = st.columns(qt_col)

        for j, caminho in enumerate(caminhos[im:im + qt_col]):
            with cols[j]:
                st.image(caminho)
                st.code(caminho)

def Grade_Widget_vendas(st, dados):
    qtt = 2
    caminhos = dados

    st.markdown("---")
    col_global1, col_global2 = st.columns(2)
    with col_global1:
        valor_global = st.number_input('Venda (TODOS):', value=0.0, key='valor_todos')
    with col_global2:
        gasto_global = st.number_input('Gasto (TODOS):', value=0.0, key='gasto_todos')

    st.markdown("---")

    for im in range(0, len(caminhos), qtt):
        cols = st.columns(qtt)
        for j, i in enumerate(caminhos[im:im + qtt]):
            with cols[j]:
                with st.container(border=True):

                    # --- APAGAR COM CONFIRMAÇÃO ---
                    col_apagar, col_confirmar = st.columns([2, 2])
                    with col_apagar:
                        if st.button(f'❌ Apagar {i[0]}', key=f'apagar_{i[0]}'):
                            st.session_state[f'confirmar_{i[0]}'] = True

                    if st.session_state.get(f'confirmar_{i[0]}', False):
                        with col_confirmar:
                            st.warning(f'Tem certeza?')
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button('✅ Sim, apagar', key=f'sim_{i[0]}'):
                                del_VENDAS(i[0])
                                st.session_state[f'confirmar_{i[0]}'] = False
                                st.success(f'Produto {i[0]} apagado!')
                                st.rerun()
                        with c2:
                            if st.button('↩️ Cancelar', key=f'nao_{i[0]}'):
                                st.session_state[f'confirmar_{i[0]}'] = False
                                st.rerun()

                    s1, s2 = st.columns([3, 3])
                    if i[-1] and os.path.isfile(i[-1]):
                        s1.image(i[-1], width=350)
                    else:
                        s1.caption("Imagem não encontrada")
                    s2.text(f'{i[2]}')
                    s2.subheader(i[0])

                    marky_places = s2.multiselect('Markt Places:',
                                                  ['Site', 'Shopee', 'Amozon', 'Mercado Livre'],
                                                  key=f'market_{i[0]}')

                    s1, s2 = s2.columns([3, 3])
                    valor_local = s1.number_input(f' Venda:', value=0.0, key=f'valor_{i[0]}')
                    gasto_local = s2.number_input(f'Gasto:', value=0.0, key=f'gasto_{i[0]}')
                    QUANTIDADE = s1.number_input(f' Qt:', min_value=1, key=f'qt_{i[0]}')

    if st.button('🔄 ATUALIZAR TODOS OS PRODUTOS', type='primary', width=True, key='atualizar_todos'):
        produtos = caminhos
        erros = []

        # --- VERIFICAÇÃO SE TODOS OS INPUTS ESTÃO PREENCHIDOS ---
        for item in produtos:
            marky_places = st.session_state.get(f'market_{item[0]}', [])
            valor = valor_global if valor_global > 0 else st.session_state.get(f'valor_{item[0]}', 0.0)
            gasto = gasto_global if gasto_global > 0 else st.session_state.get(f'gasto_{item[0]}', 0.0)

            if not marky_places:
                erros.append(f'• {item[0]}: nenhum Marketplace selecionado')
            if valor <= 0:
                erros.append(f'• {item[0]}: Valor de Venda não preenchido')
            if gasto <= 0:
                erros.append(f'• {item[0]}: Gasto não preenchido')

        if erros:
            st.error('Corrija os campos antes de atualizar:\n\n' + '\n'.join(erros))
        else:
            # --- ATUALIZA TODOS ---
            for item in produtos:
                marky_places = st.session_state.get(f'market_{item[0]}', [])
                valor = valor_global if valor_global > 0 else st.session_state.get(f'valor_{item[0]}', 0.0)
                gasto = gasto_global if gasto_global > 0 else st.session_state.get(f'gasto_{item[0]}', 0.0)
                qt = st.session_state.get(f'qt_{item[0]}', 1)

                ATUAL_VENDAS(item[0], 'PLATAFORMAS_POSTADO', ', '.join(marky_places), SOMAR=False)
                ATUAL_VENDAS(item[0], 'VALOR_VENDA', valor, SOMAR=False)
                ATUAL_VENDAS(item[0], 'CUSTO_PRODUTO', gasto, SOMAR=False)

                # Apaga as linhas antigas do produto no marketplace
                del_MARKET_PLACE(item[0])

                # Grava uma linha por unidade — todas com o mesmo ID
                for n in range(qt):
                    esc_MARKET_PLACE(item[0], item[-1], item[1], item[2], item[3], ', '.join(marky_places),
                                     valor, gasto, 1, 'TITULO', 'DESCRITION')

            st.success(f'✅ Atualizados {len(produtos)} produtos!')
            st.rerun()

def Linha_Sep_Text(TEXT,Cor,Larg):
    import streamlit as st
    HtmL =f'<div style=" display: block; font-size: 28px; background-color: {Cor}; width: 100%; height: {Larg}px; border-bottom: 2px solid black; color: black;  text-align: center;">{TEXT}</div>'

    return st.iframe(HtmL, height=Larg+20)

def Linha_Sep(Cor, Larg):
    import streamlit as st
    HtmL = f'<div style="display: block; background-color: {Cor}; width: 100%; height: {Larg}px;"></div>'

    return st.iframe(HtmL, height=Larg, scrolling=False)

def meu_foot(st, ID, TEXTO, widget, tam=600):
    """
    Gera um rodapé personalizado para um widget.

    Esta função cria um rodapé que pode ser utilizado em um widget, permitindo a inclusão de texto e identificação específicos.

    Args:
        st (str): O estado ou status a ser exibido no rodapé.
        ID (int): Um identificador único para o rodapé.
        TEXTO (str): O texto a ser exibido no rodapé.
        widget (object): O widget onde o rodapé será aplicado.
        tam (int, opcional): A largura do rodapé em pixels. O valor padrão é 600.

    Returns:
        None: A função não retorna nenhum valor, mas modifica o widget passado como argumento.
    """
    if widget == 'container':
        with st.container(border=True, key=ID):

            return st.expander(TEXTO, key=f'1{ID}')

    if widget == 'expander':
        with st.container(border=True, key=ID):
            with st.expander(TEXTO, key=f'1{ID}'):

                return st.container(border=True, height=tam, key=f'2{ID}', autoscroll=True)

    if widget == 'button':
        with st.container(border=True, key=ID):
            if Btn_Cliq_Duplo(TEXTO, TEXTO, ID, fechar_outras=None):

                return st.container(border=True, height=tam, autoscroll=True)

            else:

                return None  # fechado = sem conteúdo

# Sua função de callback (pode permanecer aqui ou no topo)
def toggle_selection(caminho): # Verificação extra de segurança para o callback
    if "selecionadas" not in st.session_state:
        st.session_state.selecionadas = []

    if caminho in st.session_state.selecionadas:
        st.session_state.selecionadas.remove(caminho)
    else:
        if len(st.session_state.selecionadas) < 3:
            st.session_state.selecionadas.append(caminho)
        else:
            st.warning("Limite máximo de 3 imagens atingido!")

def mostrar_imagens_em_tabs(PASTA, pasta1, pasta2, pasta3, pasta4, DESC): # Inicializa o estado se ainda não existir
    if "selecionadas" not in st.session_state:
        st.session_state.selecionadas = []

    def nome_base(arquivo):

        return os.path.splitext(arquivo)[0]

    arquivos1 = sorted(os.listdir(pasta1))
    abas = st.tabs([nome_base(a) for a in arquivos1])

    for tab, nome in zip(abas, arquivos1):
        with tab:
            base = nome_base(nome)

            def achar_arquivo(pasta): # 1ª tentativa: nome exato
                for f in os.listdir(pasta):
                    if nome_base(f) == base:

                        return os.path.join(pasta, f)

                # 2ª tentativa: início do nome parecido
                prefixo = base.split('_')[0]
                for f in os.listdir(pasta):
                    if nome_base(f).startswith(prefixo):

                        return os.path.join(pasta, f)

                return None

            caminho1 = achar_arquivo(pasta1)
            caminho2 = achar_arquivo(pasta2)
            caminho3 = achar_arquivo(pasta3)
            caminho4 = achar_arquivo(pasta4)

            nome_pasta1 = os.path.basename(pasta1)
            nome_pasta2 = os.path.basename(pasta2)
            nome_pasta3 = os.path.basename(pasta3)
            nome_pasta4 = os.path.basename(pasta4)

            col1, col2, col3, col4 = st.columns(4)

            # Aplicação dos callbacks em cada checkbox
            with col1:
                if caminho1:
                    st.checkbox(
                        nome_pasta1,
                        key=f"c1_{base}",
                        value=caminho1 in st.session_state.selecionadas,
                        on_change=toggle_selection,
                        args=(caminho1,)
                    )
                    st.image(caminho1)

            with col3:
                if caminho2:
                    st.checkbox(
                        nome_pasta2,
                        key=f"c2_{base}",
                        value=caminho2 in st.session_state.selecionadas,
                        on_change=toggle_selection,
                        args=(caminho2,)
                    )
                    st.image(caminho2)

            with col2:
                if caminho3:
                    st.checkbox(
                        nome_pasta3,
                        key=f"c3_{base}",
                        value=caminho3 in st.session_state.selecionadas,
                        on_change=toggle_selection,
                        args=(caminho3,)
                    )
                    st.image(caminho3)

            with col4:
                if caminho4:
                    st.checkbox(
                        nome_pasta4,
                        key=f"c4_{base}",
                        value=caminho3 in st.session_state.selecionadas,
                        on_change=toggle_selection,
                        args=(caminho4,)
                    )
                    st.image(caminho4)

    # Exibição dos resultados e processamento
    Linha_Sep_Text(f'{len(st.session_state.selecionadas)} Imagens Selecionadas Para capa', 'green', 20)

    imagens = st.session_state.selecionadas
    if len(imagens) > 0:
        try:
            prompts = gerar_prompt_shopee(imagens, DESC)
            col1, col2, col3 = st.columns(3)

            colunas_interface = [col1, col2, col3]
            # Usamos enumerate para lidar apenas com as imagens realmente selecionadas
            for i, (col, img) in enumerate(zip(colunas_interface, imagens)):
                with col:
                    prompt_key = f"prompt_{i + 1}"
                    prompt = prompts.get(prompt_key, "")
                    s1, s2 = st.columns([3, 7])
                    s1.image(img)
                    s1.code(img)
                    s2.code(prompt, height=220)

            pasta_capas = os.path.join(PASTA, "Pre_Capas")
            if not os.path.exists(pasta_capas):
                os.makedirs(pasta_capas, exist_ok=True)

            st.button('Agora crie as capas e coloque dentro da pasta "Pre_Capas" e aperte aqui!',
                      width=True)

        except Exception as e:
            st.error(f"Erro ao processar prompts: {e}")
