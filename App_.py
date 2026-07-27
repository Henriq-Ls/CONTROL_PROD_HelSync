# App_.py

import os
import shutil

from App_Cadastro_Prod import Cadastro_Produtos
from Functions import Apagar_pasta, Contar_Itens_Pasta, wrap_text, \
    recarregar_Bnaco_vendas_com_outras_pastas
from Gerar_Documentos.a__Documento_postar_prod import Step_Marketplace,Re_Anunciar
from Tratar_midias.c__Remove_Refina_IMG import Remove_IMG
from Tratar_midias.d__Trocar_Fundo_IMG import Trocar_fundo
from Tratar_midias.e__Colocar_Logos_Ref import Adicionar_logo_completa
from Tratar_midias.e__Renomeie_IMG import renomear_por_config
from Tratar_midias.f__Medidas_Graficos import Colocar_medidas
from Tratar_midias.v__Converter_video import Converte_Video_Completo
from streamlit import sidebar
from Gerar_Documentos.b__Controle_Finacions import Step_Controle_Financeiro

from _FERRAMENTAS_.Previews import Grerar_prev
from _FERRAMENTAS_.Prompts import Prompts, Description_Foot, Descrition_entrad
from _FERRAMENTAS_._Qantidades_Variations import _parse_tipo_kit, Ler_variacoes_txt, \
    montar_variacoes
from _GERENTE_PROJETO_.Decorar.Cor_Html import Cores, eccor
from _GERENTE_PROJETO_.Decorar.Materiais import Material, ver_todos_mat


def apaga_A_entrad(st):
    produtos = ler_A_ENTRADA()

    if not produtos:
        st.info("Não há itens na tabela.")
    else:
        opcoes = {
            f"{p[0]} | {p[3]} | {p[1]}": p[0]
            for p in produtos
        }

        escolha = st.selectbox("Selecione o item para apagar", list(opcoes.keys()))
        confirmar = st.checkbox("Confirmo que quero apagar este item")

        if st.button("Apagar", type="primary"):
            if confirmar:
                ID = opcoes[escolha]
                Del_A_ENTRADA(ID)
                st.success("Item apagado com sucesso.")
                st.rerun()
            else:
                st.warning("Marque a confirmação antes de apagar.")


def app():
    """ Executa a aplicação principal APP_ """
    global KIT_OPCOES
    with sidebar:
        pass

    CAB1 = st.expander('Titulo:')
    TOP1, TOP2, TOP3 = st.columns([1, 4, 4], border=True)
    MEIO1, MEIO2 = st.columns([7, 3], border=True)
    with CAB1:
        CAB1_1, CAB1_2 = st.columns([1, 8])
        stt1, stt2, stt3, stt4, stt5, stt6, stt7, stt8, stt9 = st.columns(9)
        Menu = CAB1_1.radio('opc', ['Cadastro:', 'Produção:', 'Registro Compras:'], label_visibility='collapsed')
    if Menu == 'Cadastro:':
        Cadastro_Produtos(TOP1, TOP2, TOP3, MEIO1, MEIO2)
        with CAB1_2:
            Prompts(st)

    if Menu == 'Produção:':
        # banco de dados A_ENTRADA =
        prod = ler_A_ENTRADA()[-1]  # VAI SEMPRE LER O MAIS ATUAL CADASTRADO
        PRODUTO = prod[0].upper()
        REF = prod[1]
        PASTA = prod[2]
        DESC = prod[3]
        SERVENTIA = prod[4]
        ACOMPANHA = prod[5]
        ACABAMENTO = prod[6]
        TIPO_KIT_UNICO = prod[7]
        with sidebar:
            apaga_A_entrad(st)
        # ════════════════════════════════════════════════════════════

        LOGOS_DIR, logo_path, Capa_path, Medida_path = Grerar_prev(st, PASTA, REF)

        qrcode_path = os.path.join(LOGOS_DIR, 'qr_code_zap.jpg')
        musica_path = os.path.join(LOGOS_DIR, 'Simple.mp3')
        video_path = os.path.join(LOGOS_DIR, 'video.png')

        m1, m2, m3, m4, m5 = st.columns(5)

        # CONFIGURAÇÃO MIDIAS======================================================
        Alt_Somb = m5.selectbox('Altura Sombra:', [2.0, 0.5, 1.5, 2.5,40], help='Quanto maior mais perto!')
        Som = m5.selectbox('Musica Volume:', ['', 0.15, 0.25, 0.55, 0.80], help='Quanto maior mais alto a musica!')
        Ordem = m5.selectbox('Ordem imagem:', ['', 'Crescente', 'Decrescente'])

        # CONFIGURAÇÃO INICIAL PRODUTO ======================================================
        s0, s1, s2, s3 = st.columns([1, 1, 1, 2])

        s0.code("""'alt x larg x esp',  # Placas, painéis, tábuas
            'alt x larg x comp',  # Caixas, gavetas, móveis
            'alt x diam x esp',  # Cilindros ocos (vasos, tubos)
            'alt x diam',  # Cilindros maciços (disco, bolacha)""")

        Medidas = s1.selectbox('Tipo de Medidas:', ['',
                                                    'alt x larg x esp',  # Placas, painéis, tábuas
                                                    'alt x larg x comp',  # Caixas, gavetas, móveis
                                                    'alt x diam x esp',  # Cilindros ocos (vasos, tubos)
                                                    'alt x diam',  # Cilindros maciços (disco, bolacha)
                                                    ], help='Colocar Largura ou Espessura!')

        _cfg = _parse_tipo_kit(TIPO_KIT_UNICO)
        _tipo = _cfg.get("TIPO", "").upper()

        st.write(_tipo in ("ÚNICO", "UNICO"))
        if _tipo in ("ÚNICO", "UNICO"):
                KIT_OPCOES = s2.multiselect(
                    'Formas de venda:',
                    ['Peça única', 'Kit: 2', 'Kit: 3', 'Kit: 4', 'Kit: 5', 'Kit: 6', 'Kit: 8', 'Kit: 10'])
                if KIT_OPCOES == []:
                    KIT_OPCOES = 'Sem Kit'
        else:
            KIT_OPCOES = None
        st.error(KIT_OPCOES)
        # Todos siretosios criados
        # È criada em Cadastro_Produtos(....
        Ajuste_Geral = os.path.join(PASTA, "Ajuste_Geral")
        a_Sem_Fundo = os.path.join(PASTA, "a_Sem_Fundo")
        # È criada em Trocar_fundo(....
        b_Fundo_Capa = os.path.join(PASTA, "b_Fundo_Capa")
        Fundo_Banco = os.path.join(PASTA, "Fundo_Banco")
        b_Fundo_Medida = os.path.join(PASTA, "b_Fundo_Medida")

        # E criada em renomear_por_config(...
        c_Amostra_SEM_LOGO = os.path.join(PASTA, "c_Amostra_SEM_LOGO")
        Imag_med = os.path.join(PASTA,
                                "Imag_med")  # crio ela aqiu pra colocamedidas e depois iguala a pasta c_Medida_SEM_LOGO

        # E criada em Colocar_medidas(...
        c_Medida_SEM_LOGO = os.path.join(PASTA, "c_Medida_SEM_LOGO")

        # E criada em renomear_por_config(...
        d_Amostra_COM_LOGO = os.path.join(PASTA, "d_Amostra_COM_LOGO")
        d_Medida_COM_LOGO = os.path.join(PASTA, "d_Medida_COM_LOGO")

        # Pastas temporarias
        Pre_Capas = os.path.join(PASTA, "Pre_Capas")

        _Capas = os.path.join(PASTA, "_Capas")
        descrit_comp = []
        if len(ler_A_ENTRADA()) > 0:

            if Btn_Cliq_Duplo(f':material/folder_open: Parar',f':material/folder_open: Iniciar',
                              key="cadastro_prod"):
                st.info(Capa_path)

                # Montagem das Promeiras pasta de SELEÇÃO =
                if not os.path.exists(a_Sem_Fundo) or not os.listdir(a_Sem_Fundo):
                    # ajusta a proporção da imagem
                    with st.spinner('Agurde ! Gerando pasta SEM FUNDO.'):
                        Remove_IMG(Ajuste_Geral,a_Sem_Fundo)
                if not os.path.exists(b_Fundo_Capa) or not os.listdir(b_Fundo_Capa):
                    with st.spinner('Agurde ! Gerando pasta FUNDO CAPA.'):
                        Fundo_Capa = Capa_path
                        Trocar_fundo(a_Sem_Fundo, b_Fundo_Capa, Fundo_Capa, Alt_Somb)
                if not os.path.exists(Fundo_Banco) or not os.listdir(Fundo_Banco):
                    with st.spinner('Agurde ! Gerando pasta COM FUNDO BRANCO.'):
                        Fundo_Branco = r'Midias\fumdo_branco.jpeg'
                        Trocar_fundo(a_Sem_Fundo, Fundo_Banco, Fundo_Branco, Alt_Somb)

                if not os.path.exists(b_Fundo_Medida) or not os.listdir(b_Fundo_Medida):
                    with st.spinner('Agurde ! Gerando pasta DE FUNDO MEDIDA.'):
                        Fundo_Medida = Medida_path
                        Trocar_fundo(a_Sem_Fundo, b_Fundo_Medida, Fundo_Medida, Alt_Somb)

                if not os.path.exists(c_Amostra_SEM_LOGO) or not os.listdir(c_Amostra_SEM_LOGO):
                    with st.spinner('Agurde ! Renomeando imagens e criando AMOSTRAS SEM LOGO.'):
                        renomear_por_config(st, b_Fundo_Capa, PASTA, TIPO_KIT_UNICO, REF, str(Ordem).lower())
                        renomear_por_config(st, Fundo_Banco, PASTA, TIPO_KIT_UNICO, REF, str(Ordem).lower())
                        renomear_por_config(st, b_Fundo_Medida, PASTA, TIPO_KIT_UNICO, REF, str(Ordem).lower())

                if not os.path.exists(c_Medida_SEM_LOGO) or not os.listdir(c_Medida_SEM_LOGO):
                    with st.spinner('Agurde ! Gerando imagens COM MEDIDAS.'):
                        Colocar_medidas(Imag_med, c_Medida_SEM_LOGO, TIPO_KIT_UNICO, Medidas)

                if not os.path.exists(d_Amostra_COM_LOGO) or not os.listdir(d_Amostra_COM_LOGO):
                    with st.spinner('Agurde ! Adicionando LOGO nas AMOSTRAS.'):
                        Adicionar_logo_completa(c_Amostra_SEM_LOGO, d_Amostra_COM_LOGO, logo_path, "@henriqls",
                                                '', 'Sim')

                if not os.path.exists(d_Medida_COM_LOGO) or not os.listdir(d_Medida_COM_LOGO):
                    with st.spinner('Agurde ! Adicionando LOGO nas MEDIDAS.'):
                        Adicionar_logo_completa(c_Medida_SEM_LOGO, d_Medida_COM_LOGO, logo_path, "@henriqls",
                                                '', 'Sim')

                    os.makedirs(rf"{PASTA}\Pre_Capas", exist_ok=True)

                    st.toast("9° Cadastrando Banco de Dados!")

                    del_VENDAS()
                    # AS IMAGENS DE MEDIDAS VAO PRO BANCO EXATAMENTE PQ REPRESENRA AS VARIENDADES DO PRODUTO SENDO KUT OU UNICO!!
                    for arquivo in os.listdir(d_Medida_COM_LOGO):
                        ext = arquivo.lower().split(".")[-1]
                        if ext in ["jpeg", "png", "jpg"]:
                            id_ = os.path.splitext(arquivo)[0]
                            esc_VENDAS(id_, data_sistema('data_EUA'), PRODUTO, TIPO_KIT_UNICO, os.path.join(d_Medida_COM_LOGO, arquivo))

                else:
                    st.info('Já foi Gerado as Principais Pastas!!!!')

            if os.path.exists(d_Medida_COM_LOGO):
                '''                with st.spinner('Agurde ! Limpando pastas temporárias.'):
                    Apagar_pasta(Imag_med)
                    Apagar_pasta(Ajuste_Geral)
                    Apagar_pasta(b_Fundo_Capa)
                    Apagar_pasta(b_Fundo_Medida)
                # Apagar_pasta(Fundo_Banco)
                '''
                if os.path.exists(PASTA):
                    videos = []
                    textos = []

                    for arquivo in os.listdir(PASTA):
                        ext = arquivo.lower().split(".")[-1]
                        if ext in ["mp4", "mov", "avi", "mkv"]:
                            videos.append(arquivo)
                        elif ext in ["txt", "md"]:
                            textos.append(os.path.join(PASTA, arquivo))

                    # ── Prévia na coluna p3 ──────────────────────────────────────
                    p1, p2, p3 = st.columns([1, 3, 3])
                    # ── Mapeamento novo → antigo (para compatibilidade com montar_variacoes) ──
                    _cfg = _parse_tipo_kit(TIPO_KIT_UNICO)
                    _tipo = _cfg.get("TIPO", "").upper()

                    KIT_NOME_NOVO = "Pares" if _tipo == "KIT" and _cfg.get("SUBTIPO", "").upper() == "PARES" \
                        else "Diferentes" if _tipo == "KIT" \
                        else "Unico"

                    # ── Pasta equivalente a "Imagens_com_fundo" no novo sistema ──
                    # usa b_Fundo_Medida se existir, senão d_Medida_COM_LOGO
                    _pasta_var = b_Fundo_Medida if os.path.exists(b_Fundo_Medida) else d_Medida_COM_LOGO

                    # ── Prévia na coluna p3 ───────────────────────────────────
                    p1, p2, p3 = st.columns([1, 3, 3])
                    p2.write(Ler_variacoes_txt(PASTA))

                    _variacoes = montar_variacoes(_pasta_var, KIT_OPCOES, TIPO_KIT_UNICO)
                    p3.write('\n\n'.join(_variacoes))

                    # ── Monta o prompt para IA de preço ──────────────────────
                    texto_variacoes = '\n'.join(_variacoes)

                    past_video = os.path.join(PASTA, "Video_shopee_convertido")
                    if not os.path.exists(past_video):
                        st.toast("Criando a pasta com o video!")
                        with st.spinner(f"Convertendo vídeo... aguarde ⏳"):
                            #Converte_Video(PASTA, REF, os.path.join(PASTA, videos[0]))
                            Converte_Video_Completo(
                                ref=REF,  # ref
                                input_video=os.path.join(PASTA, videos[0]),  # vídeo principal
                                pasta_video = past_video,
                                logo_path=video_path,  # logo.png (superior direito)
                                som= Som,
                                qrcode_path=qrcode_path,  # qr_code_zap.jpg (inferior direito)
                                musica_path=musica_path,  # Simple.mp3
                                link_url="henriqls.shop",  # texto inferior esquerdo
                                max_size_mb=30,
                                max_duration=59)

                    else:
                        past_video = os.path.join(past_video, f"video_{REF}.mp4")
                        p1.video(past_video)
                        p1.write(f"video_{REF}.mp4")

                        if not os.path.exists(_Capas):  # se nao tiver as IMAGENS DE CAPAS
                            # CRIA A PASTA:  Pre_Capas
                            mostrar_imagens_em_tabs(PASTA,a_Sem_Fundo,Fundo_Banco,
                            c_Amostra_SEM_LOGO,d_Medida_COM_LOGO,DESC+'\n'+SERVENTIA)  # Pode usar len() da lista cria Grade em linha ou QT cria Grade em coluna

                    if Contar_Itens_Pasta(Pre_Capas) == 3:
                        os.makedirs(rf"{PASTA}\Pre_Capas", exist_ok=True)
                        # se nao exsistir a pasta - Capas  cria a pasta Capas com  a logo:
                        if not os.path.exists(_Capas):
                            # Certifica que a pasta de saída existe
                            os.makedirs(_Capas, exist_ok=True)

                            st.toast("De pre_Capas cria a pasta Capas com  a logo")

                            # ⚠️  except genérico vazio
                            def Mover_pasta(ORIGEM, DESTINO):
                                try:
                                    os.makedirs(DESTINO, exist_ok=True)
                                    for arquivo in os.listdir(ORIGEM):
                                        origem_arq = os.path.join(ORIGEM, arquivo)
                                        destino_arq = os.path.join(DESTINO, arquivo)
                                        if os.path.isfile(origem_arq):
                                            shutil.move(origem_arq, destino_arq)
                                except FileNotFoundError:
                                    pass
                                except Exception as e:
                                    print(f"Erro ao mover arquivos: {e}")

                            Mover_pasta(Pre_Capas, _Capas)
                            Apagar_pasta(Pre_Capas)

                        else:
                            st.info('Não criou " - Capas"')
                    else:
                        st.info('Monte As Capas!')

                if os.path.exists(_Capas): # se tiver as IMAGENS DE CAPAS
                    Linha_Sep_Text('Capas e video Criadas, criar Descrição Final', Cores('verde_fosco'), 40)

                    Grade_Widget_BTN_IMG(st,_Capas,3)  # Pode usar len() da lista cria Grade em linha ou QT cria Grade em coluna

                    text = wrap_text(Descrition_entrad(
                        PRODUTO.strip()) + '\n' + SERVENTIA + '\n' + DESC + '\n'+ ACOMPANHA)
                    descrit_comp.append(text)

                    descrit_comp.append('\nInformação de Acabamento:')
                    descrit_comp.append(Description_Foot(ACABAMENTO))

                   # ── Cadastrar Final ──────────────────────────────────────────
                    Linha_Sep_Text('Cadastrar Final', Cores('verde_fosco'), 40)

                    descrit_comp.append('\nMe de o preço de cada produto Baseado nas medidas e peso:')

                    # DEPOIS
                    descrit_comp.append(
                        '\n\n'.join(montar_variacoes(d_Medida_COM_LOGO, KIT_OPCOES, TIPO_KIT_UNICO)))

                    with st.container(border=True):
                        b1, b2, b3, b4 = st.columns(4)
                        recarregar_Bnaco_vendas_com_outras_pastas(b1,PRODUTO, KIT_OPCOES, d_Amostra_COM_LOGO, 'Amostra_com_fundo')
                        recarregar_Bnaco_vendas_com_outras_pastas(b2,PRODUTO, KIT_OPCOES, c_Amostra_SEM_LOGO, 'Imagens_Originais')
                        recarregar_Bnaco_vendas_com_outras_pastas(b3,PRODUTO, KIT_OPCOES, d_Medida_COM_LOGO, 'Imagens_medida')
                        recarregar_Bnaco_vendas_com_outras_pastas(b4,PRODUTO, KIT_OPCOES, a_Sem_Fundo, 'Most_sem_fundo')
                        Grade_Widget_vendas(st,ler_VENDAS_prod(PRODUTO))

                else:
                    st.info('Pasta _Capas Não existe !')

                Linha_Sep_Text('CRIAÇÃO DE TITULOS E DESCIÇÃO:',Cores('verde_fosco'), 40)

                st1, st2 = st.columns(2)
                st1.code("\n ".join(descrit_comp), height=500)
                TITULO = st2.text_input('Titulo do Produto', '', key='titulo')
                DESCRITION = st2.text_area('Descrição do produto:', height=450)
                if st2.button('Salvar:', width=True):
                    for p, i in enumerate(ler_VENDAS_prod(PRODUTO)):
                        ATUAL_MARKET_PLACE(i[0], 'TITULO', TITULO, SOMAR=False)
                        ATUAL_MARKET_PLACE(i[0], 'DESCRITION', DESCRITION, SOMAR=False)

                Linha_Sep_Text(F" 🛒 ** `{PRODUTO} PRONTO → MARKETPLACE **",Cores('verde_fosco'), 40)
                Step_Marketplace(REF,PRODUTO,PASTA)

                Linha_Sep_Text('IMPRIMIR ETIQUETAS: ',Cores('verde_fosco'), 40)
                from  _FERRAMENTAS_.Impressora import Painel_Imprimir
                Painel_Imprimir(st,PRODUTO)






    if Menu == 'Registro Compras:':
        from Gerar_Documentos.c__Dando_Baixa import Atualizamdo_registros
        Atualizamdo_registros(TOP1, TOP2, TOP3, MEIO1, MEIO2)


    # Roda PÉ  PARTE PARA _GERENCIAMENTO-------------------- meu_foot(st,ID,TEXTO,widget,tam)

    with meu_foot(st,'foot1','💰 Controle Financeiro:','expander',):
        with st.container(border=True, height=700):
            Step_Controle_Financeiro()

    with meu_foot(st,'foot2', 'Editor Marketplace:','expander',):
        from Gerar_Documentos.c__Dando_Baixa import Editor_Marketplace
        with st.container(border=True, height=700):
            Editor_Marketplace()

    with meu_foot(st,'foot3', 'Copiar Anúncios:','expander',):
        with st.container(border=True, height=700):
            Re_Anunciar()

    st.write(saudacao_por_hora_sistema())
    dir = mostrar_estrutura(st, contar_estrutura(pasta_raiz))
    _foot = meu_foot(st, 'Estrutura_Projeto', str(F"{str(Material('gráfico alta'))} {dir}"), 'button', 710 )
    if _foot:
        with _foot:
            listar_projeto(st)
            eccor(st)
            ver_todos_mat(st)
#---------------------------
if __name__ == "__main__":
    #try:
    import streamlit as st
    from _APP_.Functions_app import meu_foot, mostrar_imagens_em_tabs, Grade_Widget_BTN_IMG, Grade_Widget_vendas, \
    Btn_Cliq_Duplo, Linha_Sep_Text
    from _GERENTE_PROJETO_.a__Gerente import Pasta_Raiz, contar_estrutura, mostrar_estrutura, listar_projeto, \
    saudacao_por_hora_sistema, data_sistema

    # chamadas internas -----
    pasta_raiz = Pasta_Raiz()
    #-----------------------
    st.set_page_config(page_title= f"{str(pasta_raiz.name).upper()}", layout="wide",page_icon='icon.ico')
    from _APP_.Html_app import Carregamento_Temas
    from _BANCOS_.Banco_Bados import ler_A_ENTRADA, del_VENDAS, esc_VENDAS, ler_VENDAS_prod, ATUAL_MARKET_PLACE, \
    Del_A_ENTRADA

    Carregamento_Temas(st)
    app( )

    '''except Exception as e:
        st.toast(f"🚨 ERRO: {e}")
        st.warning("🔄 **FECHE e REABRA o programa**")
        st.write(f"🚨{e}")'''
