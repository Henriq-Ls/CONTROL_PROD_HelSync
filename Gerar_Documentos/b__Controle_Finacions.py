# 📁 Gerar_Documentos/b__Controle_Finacions.py
from _BANCOS_.Banco_Bados import ler_MARKET_PLACE
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
COLUNAS_MP = [
    "ID", "IMAGEM", "DATA", "NOME_PRODUTO", "KIT",
    "PLATAFORMAS_POSTADO", "PLATAFORMA_VENDA",
    "CLIENTE_NOME", "CLIENTE_CPF", "CLIENTE_TELEFONE",
    "ENDERECO",
    "VALOR_VENDA", "CUSTO_PRODUTO", "TAXA_PLATAFORMA", "LUCRO",
    "QUANTIDADE",
    "TITULO", "DESCRITION"
]

def formatar_moeda(valor):
    try:

        return f"R$ {float(valor):,.2f}".replace(".", "X").replace(",", ".").replace("X", ",")

    except:

        return "R$ 0,00"

def carregar_df():
    dados = ler_MARKET_PLACE()
    if not dados:

        return pd.DataFrame(columns=COLUNAS_MP)

    df = pd.DataFrame(dados, columns=COLUNAS_MP)
    df["DATA"]            = pd.to_datetime(df["DATA"], errors="coerce")
    df["VALOR_VENDA"]     = pd.to_numeric(df["VALOR_VENDA"],     errors="coerce").fillna(0)
    df["CUSTO_PRODUTO"]   = pd.to_numeric(df["CUSTO_PRODUTO"],   errors="coerce").fillna(0)
    df["TAXA_PLATAFORMA"] = pd.to_numeric(df["TAXA_PLATAFORMA"], errors="coerce").fillna(0)
    df["LUCRO"]           = pd.to_numeric(df["LUCRO"],           errors="coerce").fillna(0)
    df["QUANTIDADE"]      = pd.to_numeric(df["QUANTIDADE"],      errors="coerce").fillna(0).astype(int)

    return df

def is_venda_real(df):
    """Venda real = tem CLIENTE_NOME preenchido."""

    return (

        df["CLIENTE_NOME"].notna() &
        (df["CLIENTE_NOME"].str.strip() != "")
    )

# ⚠️  função grande (374 linhas) | except genérico vazio
def Step_Controle_Financeiro():
    df_full = carregar_df()
    if df_full.empty:
        st.warning("Nenhum dado encontrado no banco.")

        return

    # Separa anúncios de vendas reais
    df_anuncios = df_full[~is_venda_real(df_full)].copy()
    df_vendas   = df_full[is_venda_real(df_full)].copy()

    # ── FILTROS SIDEBAR ───────────────────────────────────────────
    st.sidebar.header("🔍 Filtros")

    produtos = sorted(df_full["NOME_PRODUTO"].dropna().unique().tolist())
    prod_sel = st.sidebar.multiselect("Produto", produtos, default=produtos)

    plataformas = sorted(df_full["PLATAFORMAS_POSTADO"].dropna().unique().tolist())
    plat_sel = st.sidebar.multiselect("Plataforma", plataformas, default=plataformas)

    # Filtro de data só em vendas reais (anúncios não têm data de venda)
    if not df_vendas.empty:
        d_min = df_vendas["DATA"].dropna().min()
        d_max = df_vendas["DATA"].dropna().max()
        if pd.notna(d_min) and pd.notna(d_max):
            d_inicio, d_fim = st.sidebar.date_input(
                "Período das vendas",
                value=(d_min.date(), d_max.date()),
                min_value=d_min.date(),
                max_value=d_max.date()
            )
            df_vendas = df_vendas[
                (df_vendas["DATA"].isna()) |
                ((df_vendas["DATA"].dt.date >= d_inicio) & (df_vendas["DATA"].dt.date <= d_fim))
            ].copy()

    df_vendas   = df_vendas[df_vendas["NOME_PRODUTO"].isin(prod_sel)]
    df_anuncios = df_anuncios[df_anuncios["NOME_PRODUTO"].isin(prod_sel)]

    aba = st.tabs([
        "📊 Dashboard",
        "📦 Anúncios Cadastrados",
        "💸 Vendas Realizadas",
        "👤 Por Cliente",
        "📅 Por Data",
    ])

    # ═══════════════════════════════════════════════════════════════
    # ABA 1 — DASHBOARD
    # ═══════════════════════════════════════════════════════════════
    with aba[0]:

        # ── STATUS GERAL ──────────────────────────────────────────
        st.subheader("📌 Status Geral")
        c1, c2, c3 = st.columns(3)
        c1.metric("📋 Produtos cadastrados",   str(len(df_anuncios)))
        c2.metric("✅ Vendas realizadas",       str(len(df_vendas)))
        c3.metric("🛍️ Produtos únicos",        str(df_full["NOME_PRODUTO"].nunique()))

        st.divider()

        if df_vendas.empty:
            st.info("Nenhuma venda realizada ainda. Os dados abaixo são do catálogo de anúncios.")

            # Mostra resumo do catálogo
            st.subheader("📦 Catálogo de Anúncios")

            total_anuncios      = len(df_anuncios)
            soma_venda          = df_anuncios["VALOR_VENDA"].sum()
            soma_custo          = df_anuncios["CUSTO_PRODUTO"].sum()
            lucro_potencial     = soma_venda - soma_custo
            margem_potencial    = (lucro_potencial / soma_venda * 100) if soma_venda > 0 else 0
            preco_min           = df_anuncios["VALOR_VENDA"].min()
            preco_max           = df_anuncios["VALOR_VENDA"].max()
            preco_medio         = df_anuncios["VALOR_VENDA"].mean()

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("💰 Valor total a vender",   formatar_moeda(soma_venda))
            c2.metric("💸 Custo total investido",  formatar_moeda(soma_custo))
            c3.metric("📈 Lucro potencial",        formatar_moeda(lucro_potencial),
                      delta=f"{margem_potencial:.1f}% margem")
            c4.metric("📋 Total de anúncios",      str(total_anuncios))

            c5, c6, c7 = st.columns(3)
            c5.metric("Preço mínimo",  formatar_moeda(preco_min))
            c6.metric("Preço máximo",  formatar_moeda(preco_max))
            c7.metric("Preço médio",   formatar_moeda(preco_medio))

            st.divider()

            fig_cat = go.Figure(go.Bar(
                x=["Valor Total a Vender", "Custo Total", "Lucro Potencial"],
                y=[soma_venda, soma_custo, lucro_potencial],
                marker_color=["#2196F3", "#F44336", "#4CAF50"],
                text=[formatar_moeda(v) for v in [soma_venda, soma_custo, lucro_potencial]],
                textposition="outside"
            ))
            fig_cat.update_layout(title="Projeção Financeira do Catálogo", yaxis_title="R$", showlegend=False)
            st.plotly_chart(fig_cat, width=True)

            st.divider()

            # Validação Shopee 4x por produto
            st.subheader("⚠️ Validação Shopee — limite de preço 4x")
            alertas = []
            for nome, grupo in df_anuncios.groupby("NOME_PRODUTO"):
                precos = grupo["VALOR_VENDA"][grupo["VALOR_VENDA"] > 0].tolist()
                if len(precos) >= 2:
                    ratio = max(precos) / min(precos)
                    if ratio > 4:
                        alertas.append((nome, ratio, min(precos), max(precos)))
            if alertas:
                for nome, ratio, pmin, pmax in alertas:
                    st.error(
                        f"🚨 **{nome}** — Razão: **{ratio:.1f}x** | "
                        f"Min: {formatar_moeda(pmin)} | Max: {formatar_moeda(pmax)}"
                    )
            else:
                st.success("✅ Todos os produtos estão dentro do limite de 4x da Shopee.")

        else:
            # ── RESUMO FINANCEIRO DAS VENDAS REAIS ────────────────
            st.subheader("💰 Resumo Financeiro — Vendas Reais")

            total_qty     = int(df_vendas["QUANTIDADE"].sum())
            total_receita = df_vendas["VALOR_VENDA"].sum()
            total_custo   = df_vendas["CUSTO_PRODUTO"].sum()
            total_taxa    = df_vendas["TAXA_PLATAFORMA"].sum()
            total_lucro   = df_vendas["LUCRO"].sum() if df_vendas["LUCRO"].sum() != 0 \
                            else total_receita - total_custo - total_taxa
            margem        = (total_lucro / total_receita * 100) if total_receita > 0 else 0
            ticket_medio  = total_receita / len(df_vendas) if len(df_vendas) > 0 else 0

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("💰 Receita Total", formatar_moeda(total_receita))
            c2.metric("💸 Custo Total",   formatar_moeda(total_custo))
            c3.metric("🏦 Taxas",         formatar_moeda(total_taxa))
            c4.metric("📈 Lucro Líquido", formatar_moeda(total_lucro),
                      delta=f"{margem:.1f}% margem")

            c5, c6, c7 = st.columns(3)
            c5.metric("📦 Itens vendidos", f"{total_qty:,}")
            c6.metric("🎟️ Ticket médio",  formatar_moeda(ticket_medio))
            c7.metric("👤 Clientes",       str(df_vendas["CLIENTE_CPF"].nunique()))

            fig_comp = go.Figure(go.Bar(
                x=["Receita", "Custo", "Taxa", "Lucro"],
                y=[total_receita, total_custo, total_taxa, total_lucro],
                marker_color=["#2196F3","#F44336","#FF9800",
                              "#4CAF50" if total_lucro >= 0 else "#F44336"],
                text=[formatar_moeda(v) for v in [total_receita, total_custo, total_taxa, total_lucro]],
                textposition="outside"
            ))
            fig_comp.update_layout(title="Composição Financeira", yaxis_title="R$", showlegend=False)
            st.plotly_chart(fig_comp, width=True)

    # ═══════════════════════════════════════════════════════════════
    # ABA 2 — ANÚNCIOS CADASTRADOS (sem venda)
    # ═══════════════════════════════════════════════════════════════
    with aba[1]:
        st.subheader("📦 Anúncios Cadastrados no Shopee")
        st.caption(f"{len(df_anuncios)} anúncios — sem venda realizada")

        if df_anuncios.empty:
            st.info("Nenhum anúncio cadastrado.")
        else:
            # Validação Shopee 4x
            st.subheader("⚠️ Validação Shopee — limite de preço 4x")
            alertas = []
            for nome, grupo in df_anuncios.groupby("NOME_PRODUTO"):
                precos = grupo["VALOR_VENDA"][grupo["VALOR_VENDA"] > 0].tolist()
                if len(precos) >= 2:
                    ratio = max(precos) / min(precos)
                    if ratio > 4:
                        alertas.append((nome, ratio, min(precos), max(precos)))
            if alertas:
                for nome, ratio, pmin, pmax in alertas:
                    st.error(
                        f"🚨 **{nome}** — Razão: **{ratio:.1f}x** | "
                        f"Min: {formatar_moeda(pmin)} | Max: {formatar_moeda(pmax)}"
                    )
            else:
                st.success("✅ Todos dentro do limite de 4x da Shopee.")

            st.divider()

            # Tabela de anúncios
            df_an_show = df_anuncios[[
                "ID","NOME_PRODUTO","KIT","PLATAFORMAS_POSTADO",
                "QUANTIDADE","VALOR_VENDA","CUSTO_PRODUTO","DATA"
            ]].copy()
            df_an_show["VALOR_VENDA"]   = df_an_show["VALOR_VENDA"].apply(formatar_moeda)
            df_an_show["CUSTO_PRODUTO"] = df_an_show["CUSTO_PRODUTO"].apply(formatar_moeda)
            df_an_show["DATA"]          = df_an_show["DATA"].dt.strftime("%d/%m/%Y").fillna("—")

            # Ordena por referência numérica
            try:
                df_an_show = df_an_show.iloc[
                    df_anuncios["ID"].apply(
                        lambda x: int(''.join(filter(str.isdigit, str(x).split("_")[0])))
                        if any(c.isdigit() for c in str(x)) else 0
                    ).argsort().values
                ]
            except:
                pass

            st.dataframe(df_an_show.rename(columns={
                "ID":"ID","NOME_PRODUTO":"Produto","KIT":"Kit",
                "PLATAFORMAS_POSTADO":"Plataforma","QUANTIDADE":"Qtd",
                "VALOR_VENDA":"Preço Venda","CUSTO_PRODUTO":"Custo","DATA":"Data Cadastro"
            }), width=True, hide_index=True)

            # Gráfico de preços
            fig_precos = px.bar(
                df_anuncios.sort_values("VALOR_VENDA"),
                x="ID", y="VALOR_VENDA",
                title="Preços dos Anúncios",
                labels={"ID":"Produto","VALOR_VENDA":"Preço (R$)"},
                color="VALOR_VENDA", color_continuous_scale="Blues"
            )
            fig_precos.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_precos, width=True)

    # ═══════════════════════════════════════════════════════════════
    # ABA 3 — VENDAS REALIZADAS
    # ═══════════════════════════════════════════════════════════════
    with aba[2]:
        st.subheader("💸 Vendas Realizadas")

        if df_vendas.empty:
            st.info("Nenhuma venda realizada ainda. Quando uma venda for registrada com nome do cliente, aparecerá aqui.")
        else:
            rank = (
                df_vendas.groupby("NOME_PRODUTO")
                .agg(QTD=("QUANTIDADE","sum"), RECEITA=("VALOR_VENDA","sum"),
                     CUSTO=("CUSTO_PRODUTO","sum"), LUCRO=("LUCRO","sum"),
                     VENDAS=("ID","count"))
                .reset_index().sort_values("RECEITA", ascending=False)
            )
            rank["MARGEM_%"] = (rank["LUCRO"] / rank["RECEITA"] * 100).round(1).fillna(0)

            fig_v = px.bar(rank, x="NOME_PRODUTO", y="RECEITA",
                           color="LUCRO", text="QTD",
                           title="Receita por Produto",
                           color_continuous_scale="Greens",
                           labels={"NOME_PRODUTO":"Produto","RECEITA":"Receita (R$)"})
            fig_v.update_layout(xaxis_tickangle=-35)
            st.plotly_chart(fig_v, width=True)

            rank_exib = rank.copy()
            for col in ["RECEITA","CUSTO","LUCRO"]:
                rank_exib[col] = rank_exib[col].apply(formatar_moeda)
            rank_exib["MARGEM_%"] = rank_exib["MARGEM_%"].astype(str) + "%"
            st.dataframe(rank_exib.rename(columns={
                "NOME_PRODUTO":"Produto","QTD":"Qtd","RECEITA":"Receita",
                "CUSTO":"Custo","LUCRO":"Lucro","MARGEM_%":"Margem","VENDAS":"Nº Vendas"
            }), width=True, hide_index=True)

    # ═══════════════════════════════════════════════════════════════
    # ABA 4 — POR CLIENTE
    # ═══════════════════════════════════════════════════════════════
    with aba[3]:
        st.subheader("👤 Análise por Cliente")

        if df_vendas.empty:
            st.info("Nenhuma venda com dados de cliente ainda.")
        else:
            rank_cli = (
                df_vendas.groupby(["CLIENTE_CPF","CLIENTE_NOME"])
                .agg(COMPRAS=("ID","count"), QTD=("QUANTIDADE","sum"),
                     RECEITA=("VALOR_VENDA","sum"), LUCRO=("LUCRO","sum"))
                .reset_index().sort_values("RECEITA", ascending=False)
            )
            rank_cli["TICKET_MEDIO"] = rank_cli["RECEITA"] / rank_cli["COMPRAS"]

            top = rank_cli.iloc[0]
            c1, c2, c3, c4 = st.columns(4)
            c1.success(f"🥇 **{top['CLIENTE_NOME']}**")
            c2.metric("Compras",      str(int(top["COMPRAS"])))
            c3.metric("Total gasto",  formatar_moeda(top["RECEITA"]))
            c4.metric("Ticket médio", formatar_moeda(top["TICKET_MEDIO"]))

            fig_cli = px.bar(rank_cli.head(15), x="CLIENTE_NOME", y="RECEITA",
                             color="COMPRAS", text="COMPRAS",
                             title="Top Clientes — Receita Total",
                             color_continuous_scale="Purples",
                             labels={"CLIENTE_NOME":"Cliente","RECEITA":"Receita (R$)"})
            fig_cli.update_layout(xaxis_tickangle=-35)
            st.plotly_chart(fig_cli, width=True)

            rank_exib = rank_cli.copy()
            for col in ["RECEITA","LUCRO","TICKET_MEDIO"]:
                rank_exib[col] = rank_exib[col].apply(formatar_moeda)
            st.dataframe(rank_exib.rename(columns={
                "CLIENTE_CPF":"CPF","CLIENTE_NOME":"Nome","COMPRAS":"Compras",
                "QTD":"Qtd","RECEITA":"Receita","LUCRO":"Lucro","TICKET_MEDIO":"Ticket Médio"
            }), width=True, hide_index=True)

            st.divider()
            st.subheader("🔎 Histórico por cliente")
            opcoes = {f"{r['CLIENTE_NOME']} — {r['CLIENTE_CPF']}": r["CLIENTE_CPF"]
                      for _, r in rank_cli.iterrows()}
            cpf_sel = opcoes[st.selectbox("Cliente", list(opcoes.keys()))]
            df_hist = df_vendas[df_vendas["CLIENTE_CPF"] == cpf_sel][
                ["DATA","NOME_PRODUTO","KIT","PLATAFORMAS_POSTADO","QUANTIDADE",
                 "VALOR_VENDA","CUSTO_PRODUTO","LUCRO","CLIENTE_TELEFONE","ENDERECO"]
            ].copy()
            df_hist["DATA"]          = df_hist["DATA"].dt.strftime("%d/%m/%Y").fillna("—")
            df_hist["VALOR_VENDA"]   = df_hist["VALOR_VENDA"].apply(formatar_moeda)
            df_hist["CUSTO_PRODUTO"] = df_hist["CUSTO_PRODUTO"].apply(formatar_moeda)
            df_hist["LUCRO"]         = df_hist["LUCRO"].apply(formatar_moeda)
            st.dataframe(df_hist.rename(columns={
                "DATA":"Data","NOME_PRODUTO":"Produto","KIT":"Kit",
                "PLATAFORMAS_POSTADO":"Plataforma","QUANTIDADE":"Qtd",
                "VALOR_VENDA":"Venda","CUSTO_PRODUTO":"Custo","LUCRO":"Lucro",
                "CLIENTE_TELEFONE":"Telefone","ENDERECO":"Endereço"
            }), width=True, hide_index=True)

    # ═══════════════════════════════════════════════════════════════
    # ABA 5 — POR DATA (só vendas reais)
    # ═══════════════════════════════════════════════════════════════
    with aba[4]:
        st.subheader("📅 Evolução de Vendas por Data")

        if df_vendas.empty:
            st.info("Nenhuma venda realizada ainda.")
        else:
            df_d = df_vendas[df_vendas["DATA"].notna()].copy()
            df_d["DIA"] = df_d["DATA"].dt.date
            dia_df = (
                df_d.groupby("DIA")
                .agg(RECEITA=("VALOR_VENDA","sum"), LUCRO=("LUCRO","sum"), QTD=("QUANTIDADE","sum"))
                .reset_index()
            )
            fig_dia = go.Figure()
            fig_dia.add_trace(go.Scatter(x=dia_df["DIA"], y=dia_df["RECEITA"],
                                         name="Receita", mode="lines+markers",
                                         line=dict(color="#2196F3")))
            fig_dia.add_trace(go.Scatter(x=dia_df["DIA"], y=dia_df["LUCRO"],
                                         name="Lucro", mode="lines+markers",
                                         line=dict(color="#4CAF50")))
            fig_dia.add_trace(go.Bar(x=dia_df["DIA"], y=dia_df["QTD"],
                                     name="Qtd", yaxis="y2", opacity=0.25,
                                     marker_color="#FF9800"))
            fig_dia.update_layout(
                title="Receita e Lucro por Dia",
                yaxis=dict(title="R$"),
                yaxis2=dict(title="Quantidade", overlaying="y", side="right"),
                legend=dict(orientation="h")
            )
            st.plotly_chart(fig_dia, width=True)

            df_d["MES"] = df_d["DATA"].dt.to_period("M").astype(str)
            mes_df = (
                df_d.groupby("MES")
                .agg(RECEITA=("VALOR_VENDA","sum"), CUSTO=("CUSTO_PRODUTO","sum"),
                     LUCRO=("LUCRO","sum"), QTD=("QUANTIDADE","sum"))
                .reset_index()
            )
            st.plotly_chart(px.bar(
                mes_df, x="MES", y=["RECEITA","CUSTO","LUCRO"], barmode="group",
                title="Receita vs Custo vs Lucro por Mês",
                color_discrete_map={"RECEITA":"#2196F3","CUSTO":"#F44336","LUCRO":"#4CAF50"},
                labels={"value":"R$","MES":"Mês","variable":""}
            ), width=True)

            if not mes_df.empty:
                melhor = mes_df.loc[mes_df["RECEITA"].idxmax()]
                st.success(
                    f"🏆 Melhor mês: **{melhor['MES']}** — "
                    f"Receita: {formatar_moeda(melhor['RECEITA'])} | "
                    f"Lucro: {formatar_moeda(melhor['LUCRO'])} | "
                    f"Qtd: {int(melhor['QTD'])}"
                )
