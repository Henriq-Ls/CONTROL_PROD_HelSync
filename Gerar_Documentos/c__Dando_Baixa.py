# 📁 Gerar_Documentos/c__Dando_Baixa.py
import os

from _BANCOS_.Banco_Bados import listar_produtos_disponiveis, registrar_compra
from _BANCOS_.Banco_Bados import ler_MARKET_PLACE, ATUAL_MARKET_PLACE

import streamlit as st

# ⚠️  função grande (86 linhas)
def tela_registrar_venda_feitas(MEIO1, MEIO2):
    MEIO2.title('🛒 Registrar Compra')

    produtos = listar_produtos_disponiveis()

    if not produtos:
        st.warning('Nenhum produto disponível no estoque.')

        return

    with MEIO2:
        st.subheader('Estoque disponível')

        opcoes = {f"{p[1]}  —  {p[7]} unid.  —  R$ {p[4]:.2f}": p for p in produtos}
        escolha = st.selectbox('Selecione o produto:', list(opcoes.keys()))

        produto = opcoes[escolha]
        ID            = produto[0]
        NOME_PRODUTO  = produto[1]
        IMAGEM        = produto[2]
        KIT           = produto[3]
        VALOR_VENDA   = produto[4]
        CUSTO_PRODUTO = produto[5]
        PLATAFORMAS   = produto[6]
        ESTOQUE       = produto[7]

    with MEIO1:
        col_img, col_info = st.columns([1, 2])

        with col_img:
            if IMAGEM and os.path.exists(IMAGEM):
                st.image(IMAGEM, width=250)
            else:
                st.info('Sem imagem')

        with col_info:
            st.markdown(f"**Produto:** {NOME_PRODUTO}")
            st.markdown(f"**Kit:** {KIT}")
            st.markdown(f"**Valor de Venda:** R$ {VALOR_VENDA:.2f}")
            st.markdown(f"**Custo:** R$ {CUSTO_PRODUTO:.2f}")
            st.markdown(f"**Plataformas postadas:** {PLATAFORMAS}")
            st.markdown(f"**Estoque disponível:** `{ESTOQUE} unidades`")

        st.markdown('---')
        st.subheader('Dados da Compra')

        # SEM st.form — atualiza em tempo real
        col1, col2 = st.columns(2)
        with col1:
            qt           = st.number_input('Quantidade comprada:', min_value=1, max_value=ESTOQUE, value=1, key=f'qt_{ID}')
            cliente_nome = st.text_input('Nome do Cliente:', key=f'nome_{ID}')
            cliente_cpf  = st.text_input('CPF:', key=f'cpf_{ID}')
        with col2:
            cliente_tel = st.text_input('Telefone:', key=f'tel_{ID}')
            plataforma  = st.selectbox('Plataforma de Venda:', ['Shopee', 'Mercado Livre', 'Amazon', 'Site'], key=f'plat_{ID}')
            taxa        = st.number_input('Taxa da Plataforma (R$):', min_value=0.0, value=0.0, key=f'taxa_{ID}')

        endereco = st.text_area('Endereço de Entrega:', key=f'end_{ID}')

        # Atualiza em tempo real conforme digita
        lucro_estimado = (VALOR_VENDA - CUSTO_PRODUTO - taxa) * qt
        st.info(f'Lucro estimado: R$ {lucro_estimado:.2f}  |  Total da venda: R$ {VALOR_VENDA * qt:.2f}')

    if MEIO2.button('✅ Registrar Compra', type='primary', width=True, key=f'btn_{ID}'):
        erros = []
        if not cliente_nome.strip():
            erros.append('Nome do cliente obrigatório')
        if qt > ESTOQUE:
            erros.append(f'Quantidade maior que o estoque ({ESTOQUE})')

        if erros:
            for e in erros:
                st.error(e)
        else:
            atualizadas = registrar_compra(
                ID, qt,
                cliente_nome.strip(),
                cliente_cpf.strip(),
                cliente_tel.strip(),
                endereco.strip(),
                plataforma,
                taxa
            )
            st.success(f'✅ {atualizadas} unidade(s) registrada(s) para {cliente_nome}!')
            st.balloons()
            st.rerun()

def Atualizamdo_registros(TOP1, TOP2, TOP3, MEIO1, MEIO2):
    TOP2.title('Vendas Marketplace')

    aba = TOP3.radio('Menu', ['🛒 Registrar Compra', '📦 Vendas Realizadas'])

    if aba == '🛒 Registrar Compra':
        tela_registrar_venda_feitas(MEIO1, MEIO2)
    elif aba == '📦 Vendas Realizadas':
        tela_vendas_realizadas()

# ⚠️  função grande (214 linhas)
def Editor_Marketplace():
    import os
    import pandas as pd
    import streamlit as st
    from _BANCOS_.Banco_Bados import ler_MARKET_PLACE, ATUAL_MARKET_PLACE
    # from App_Functions import calcular_medidas_com_margem, extrair_medidas, contar_estoque  # descomenta se usar

    dados = ler_MARKET_PLACE()
    if not dados:
        st.warning("Nenhum produto encontrado.")
        st.stop()

    colunas = [
        "ID","IMAGEM","DATA","NOME_PRODUTO","KIT",
        "PLATAFORMAS_POSTADO","PLATAFORMA_VENDA",
        "CLIENTE_NOME","CLIENTE_CPF","CLIENTE_TELEFONE",
        "ENDERECO","VALOR_VENDA","CUSTO_PRODUTO",
        "TAXA_PLATAFORMA","LUCRO","QUANTIDADE",
        "TITULO","DESCRITION"
    ]

    df = pd.DataFrame(dados, columns=colunas)

    # 1. BUSCA POR NOME/ID/TEXTO + SELECTBOX DE NOME
    busca = st.text_input("Buscar produto (nome, ID ou texto)")

    # nomes únicos para selectbox
    nomes_unicos = df["NOME_PRODUTO"].dropna().astype(str).unique()
    nomes_unicos = sorted(nomes_unicos, key=lambda x: x.lower())

    selecionar_nome = st.selectbox(
        "Selecionar Produto",
        [""] + list(nomes_unicos),
        placeholder="Selecione um produto",
        index=0,
    )

    if selecionar_nome != '' or len(selecionar_nome) > 0:
        # filtra por busca ou selectbox (ou ambos)
        df_filtrado = df.copy()

        if busca:
            mask_texto = (
                (df_filtrado["NOME_PRODUTO"].astype(str).str.contains(busca, case=False, na=False)) |
                (df_filtrado["ID"].astype(str).str.contains(busca, case=False, na=False))
            )
            df_filtrado = df_filtrado[mask_texto]

        if selecionar_nome:
            mask_nome = df_filtrado["NOME_PRODUTO"].astype(str) == str(selecionar_nome)
            df_filtrado = df_filtrado[mask_nome]

        if df_filtrado.empty:
            st.info("Nenhum produto encontrado com esses filtros.")

            return

        # 2. AGRUPA POR NOME_PRODUTO (um bloco por produto)
        produtos_unicos = {}

        for _, row in df_filtrado.iterrows():
            nome = str(row["NOME_PRODUTO"]).strip()

            if nome not in produtos_unicos:
                produtos_unicos[nome] = {
                    "NOME_PRODUTO": nome,
                    "TITULO": row["TITULO"],
                    "DESCRITION": row["DESCRITION"],
                    "VALOR_VENDA": row["VALOR_VENDA"],
                    "CUSTO_PRODUTO": row["CUSTO_PRODUTO"],
                    "KIT": row["KIT"],
                    "PLATAFORMAS_POSTADO": row["PLATAFORMAS_POSTADO"],
                    "IMAGEM": row["IMAGEM"],
                    "ITEMS": [],
                }

            produtos_unicos[nome]["ITEMS"].append(row)

        lista_produtos = list(produtos_unicos.values())

        # 3. MOSTRA BLOCOS POR PRODUTO (ex.: BOLACHAS MADEIRA PERSONALIZADA FLOR ROCHA)
        for i, prod in enumerate(lista_produtos):
            with st.container(border=True, key=f"bloco_prod_{i}"):
                col1, col2 = st.columns([2, 8])

                with col1:
                    if prod["IMAGEM"] and os.path.exists(str(prod["IMAGEM"])):
                        st.image(prod["IMAGEM"], width=200)

                with col2:
                    st.markdown(f"### 📦 {prod['NOME_PRODUTO']}")

                    # 3.1 TÍTULO / DESCRIÇÃO / VALOR / CUSTO / KIT GERAL (opcional)
                    tit = st.text_input(
                        "Título (geral, vai pro banco de dados)",
                        value=prod["TITULO"] or "",
                        key=f"tit_{prod['NOME_PRODUTO']}",
                    )

                    desc = st.text_area(
                        "Descrição (geral)",
                        value=prod["DESCRITION"] or "",
                        height=200,
                        key=f"desc_{prod['NOME_PRODUTO']}",
                    )

                    val = st.number_input(
                        "Valor Venda (geral)",
                        value=float(prod["VALOR_VENDA"] or 0),
                        key=f"val_{prod['NOME_PRODUTO']}",
                    )

                    cus = st.number_input(
                        "Custo Produto (geral)",
                        value=float(prod["CUSTO_PRODUTO"] or 0),
                        key=f"custo_{prod['NOME_PRODUTO']}",
                    )

                    kit = st.text_input(
                        "Kit (geral)",
                        value=prod["KIT"] or "",
                        key=f"kit_{prod['NOME_PRODUTO']}",
                    )

                    # 3.2 PLATAFORMA
                    plataformas = str(prod["PLATAFORMAS_POSTADO"] or "")

                    add_plat = st.selectbox(
                        "Adicionar plataforma",
                        ["", "Shopee", "Mercado Livre", "Amazon", "Site", "Elo7"],
                        key=f"plat_{prod['NOME_PRODUTO']}",
                    )

                    if st.button(
                        "➕ Adicionar Plataforma",
                        key=f"btn_plat_{prod['NOME_PRODUTO']}",
                        width=True,
                    ):
                        lista = [p.strip() for p in plataformas.split(",") if p.strip()]

                        if add_plat and add_plat not in lista:
                            lista.append(add_plat)

                        plataformas_final = ", ".join(lista)

                        for item in prod["ITEMS"]:
                            ATUAL_MARKET_PLACE(item["ID"], "PLATAFORMAS_POSTADO", plataformas_final)

                        st.success("Plataforma adicionada a todas as referências.")
                        st.rerun()

                # 3.3 BLOCO DE CADA REFERÊNCIA (ID)
                st.markdown("### 📌 Referências / Variações")

                cols_vars = st.columns(2)

                for j, item in enumerate(prod["ITEMS"]):
                    with cols_vars[j % 2]:
                        with st.container(border=True, key=f"card_{item['ID']}"):
                            c1, c2 = st.columns([1, 2])

                            with c1:
                                if item["IMAGEM"] and os.path.exists(str(item["IMAGEM"])):
                                    st.image(item["IMAGEM"], width=150)

                            with c2:
                                st.code(f"ID: {item['ID']} | REF: {item['ID']}")

                                tit_row = st.text_input(
                                    "Título item",
                                    value=item["TITULO"] or tit,
                                    key=f"tit_item_{item['ID']}",
                                )

                                val_row = st.number_input(
                                    "Valor item",
                                    value=float(item["VALOR_VENDA"] or val),
                                    key=f"val_item_{item['ID']}",
                                )

                                cus_row = st.number_input(
                                    "Custo item",
                                    value=float(item["CUSTO_PRODUTO"] or cus),
                                    key=f"custo_item_{item['ID']}",
                                )

                                if st.button(
                                    "💾 Salvar item",
                                    key=f"salvar_item_{item['ID']}",
                                    width=True,
                                ):
                                    ATUAL_MARKET_PLACE(item["ID"], "TITULO", tit_row)
                                    ATUAL_MARKET_PLACE(item["ID"], "VALOR_VENDA", val_row)
                                    ATUAL_MARKET_PLACE(item["ID"], "CUSTO_PRODUTO", cus_row)

                                    st.success("Alterações salvas para essa referência.")
                                    st.rerun()

                # 3.4 SALVAR TUDO EM BLOCO (TÍTULO/DESC/VALOR/CUSTO/KIT para todas as variações)
                if st.button(
                    "💾 Salvar tudo para esse produto",
                    key=f"salvar_tudo_{prod['NOME_PRODUTO']}",
                    width=True,
                ):
                    # atualiza o título/desc em “um” registro (ou usa loop)
                    for item in prod["ITEMS"]:
                        ATUAL_MARKET_PLACE(item["ID"], "TITULO", tit)
                        ATUAL_MARKET_PLACE(item["ID"], "DESCRITION", desc)
                        ATUAL_MARKET_PLACE(item["ID"], "VALOR_VENDA", val)
                        ATUAL_MARKET_PLACE(item["ID"], "CUSTO_PRODUTO", cus)
                        ATUAL_MARKET_PLACE(item["ID"], "KIT", kit)

                    st.success("Todas as referências atualizadas.")
                    st.rerun()
