# 📁 Gerar_Documentos/a__Documento_postar_prod.py
import math
import math

from Functions import extrair_medidas, escreve
import pandas as pd
import streamlit as st
# ⚠️  função grande (74 linhas) | except genérico vazio
def calcular_medidas_com_margem(id_produto):
    Sob_peso = 100
    """
    Extrai e ajusta medidas com folgas seguras para Correios/Shopee.
    Formato esperado do ID: ref_AltxLargxComp_Pesokg  ex: pjd1_30x43x6_1.0kg
    """
    import re, math
    # ── DEFAULTS SEGUROS ────────────────────────────────────────────
    ref          = "SEM_REF"
    altura       = 0.0
    largura      = 0.0
    comprimento  = 0.0
    peso_soma   = 0

    try:
        partes = str(id_produto).strip().lower().split("_")

        # ── REFERÊNCIA ───────────────────────────────────────────────
        ref = partes[0].upper() if partes else "SEM_REF"
        peso = partes[2].upper() if partes else "SEM_REF"

        # ── DIMENSÕES (parte 1: AltxLargxComp) ──────────────────────
        if len(partes) > 1:
            dim_str = partes[1]
            if "x" in dim_str:
                meds = dim_str.split("x")
                if len(meds) >= 1:
                    try: altura      = float(meds[0])
                    except: pass
                if len(meds) >= 2:
                    try: largura     = float(meds[1])
                    except: pass
                if len(meds) >= 3:
                    try: comprimento = float(meds[2])
                    except: pass

        # ── PESO (parte 2: ex 1.0kg / 500g / 1,5kg) ─────────────────
        peso_sem_letra = int(str(peso).replace('K','').replace('G','')
                             .replace('M','').replace('R',''))
        if 'K' in str(peso):
            peso_soma = str(int(round(peso_sem_letra + Sob_peso)))+'kg'

        elif 'G' in str(peso):
            peso_soma = str(int(round(peso_sem_letra + Sob_peso)))+'gr'
        else:
            if len(peso) > 3 :
                peso_soma = str(int(round(peso_sem_letra + Sob_peso)))+'kg'

            else:
                peso_soma = str(int(round(peso_sem_letra + Sob_peso))) +'gr'

    except Exception:
        # Qualquer erro inesperado → usa defaults seguros
        pass

    # ── MARGEM DE EMBALAGEM ──────────────────────────────────────────
    # Correios: mínimo 16cm(C) x 11cm(L) x 2cm(A)
    # +2cm de folga em cada dimensão
    altura_cm      = max(2,  math.ceil(altura      + 2))
    largura_cm     = max(11, math.ceil(largura      + 2))
    comprimento_cm = max(16, math.ceil(comprimento  + 2))

    # +100g de folga de embalagem
    peso_g = peso_soma

    volume = altura_cm * largura_cm * comprimento_cm

    return {"ref":         ref.upper(),

        "altura":      altura_cm,
        "largura":     largura_cm,
        "comprimento": comprimento_cm,
        "peso":        peso_g,
        "volume":      volume}

def formatar_moeda(valor):
    """R$ 12,34 brasileiro."""
    if not valor:

        return "R$ 0,00"

    try:
        float_val = float(str(valor).replace(",", "."))

        return f"R$ {float_val:,.2f}".replace(".", "X").replace(",", ".").replace("X", ",")

    except ValueError:

        return f"R$ {valor}"

# ⚠️  função grande (72 linhas)
def organizar_para_shopee(id,nome_produto):
    """
    Organiza dados para Shopee - MOSTRA APENAS 1 ITEM POR ID ÚNICO
    (não repete itens iguais, só mostra IDs diferentes)
    """
    from _BANCOS_.Banco_Bados import ler_MARKET_PLACE_prod, contar_estoque
    from Functions import extrair_medidas
    dados = ler_MARKET_PLACE_prod(nome_produto.strip())
    if not dados:

        return None

    # 🔥 NOVO: Dicíonário para pegar APENAS 1 registro por ID
    dados_unicos = {}
    for registro in dados:
        ID = registro[0]  # ID único
        if ID not in dados_unicos:  # Só pega o PRIMEIRO de cada ID
            dados_unicos[ID] = registro

    # Converte para lista (mantém ordem de aparição)
    dados_filtrados = list(dados_unicos.values())

    # Título/Descrição (primeiro registro)
    primeiro_registro = dados_filtrados[0]
    titulo = primeiro_registro[16] or "Produto sem título"
    descricao = primeiro_registro[17] or "Produto sem descrição"

    itens = []
    for registro in dados_filtrados:
        # Índices da tabela MARKET_PLACE
        ID = registro[0]
        IMAGEM = registro[1]
        NOME_PRODUTO = registro[3]
        KIT = registro[4]
        PLATAFORMAS = registro[5]
        VALOR_VENDA = registro[11]
        CUSTO_PRODUTO = registro[12]
        QUANTIDADE = registro[15]

        medidas = calcular_medidas_com_margem(ID)
        medidas_original = extrair_medidas(ID)

        itens.append({
            "ID": ID,
            "REFERENCIA": medidas["ref"],
            "NOME": NOME_PRODUTO,
            "IMAGEM": IMAGEM or "",
            "KIT": KIT or "",
            "PLATAFORMAS": PLATAFORMAS or "",
            "VENDA": formatar_moeda(VALOR_VENDA),
            "CUSTO": formatar_moeda(CUSTO_PRODUTO),
            "MEDIDAS_ORIGINAL": medidas_original,
            "QUANTIDADE": QUANTIDADE or 0,
            "ALTURA": f"{medidas['altura']}cm",
            "LARGURA": f"{medidas['largura']}cm",
            "COMPRIMENTO": f"{medidas['comprimento']}cm",
            "PESO": f"{medidas['peso']}g",
            "VOLUME": f"{medidas['volume']:,}cm³",
            "LUCRO": formatar_moeda(registro[14]) if registro[14] else "R$ 0,00",
            "ESTOQUE_DISPONIVEL": contar_estoque(ID)  # 🔥 QUANTOS ainda estão livres
        })

    itens.sort(key=lambda x: int(''.join(filter(str.isdigit, x['REFERENCIA']))))

    return {

        "titulo": titulo,
        "descricao": descricao,
        "itens": itens,
        "total_itens": len(itens),
        "total_ids_unicos": len(itens)  # 🔥 Número de IDs diferentes
    }

# ⚠️  função grande (71 linhas)
def Step_Marketplace(id,nome_produto, PASTA):
    resultado = organizar_para_shopee(id,nome_produto)

    if not resultado:
        st.error(f"❌ ** {nome_produto} Produto não encontrado! Verifique o nome exato no banco MARKET_PLACE . **")

        return

    col1, col2 = st.columns([4, 6])
    with col1:
        st.success(f"✅ **{resultado['total_itens']} ITENS**")  # Sua linha original
    with col1:
        st.subheader(f"📦 **{nome_produto.upper()}**")

    col1.markdown("### 📝 **TÍTULO (copie para TODOS anúncios)**")
    col1.code(resultado["titulo"], language=None)

    col2.markdown("### 📄 **DESCRIÇÃO (copie para TODOS anúncios)**")
    col2.code(resultado["descricao"], language=None, height=500)

    resultado["itens"].sort(key=lambda x: int(''.join(filter(str.isdigit, x['REFERENCIA']))))

    # Começa o texto com cabeçalho
    texto_final = f"📦 ITENS PARA POSTAR ({len(resultado['itens'])}):\n"
    texto_final += f"PRODUTO: {nome_produto.upper()}\n"
    texto_final += f"TÍTULO: {resultado['titulo']}\n"
    texto_final += "=" * 60 + "\n"

    cols_cards = st.columns(2)

    for i, item in enumerate(resultado["itens"], 1):
        dados = item['MEDIDAS_ORIGINAL']
        medidas_texto = ""
        if dados:
            medidas_texto = f"{dados['altura']} x {dados['largura']} x {dados['espessura']} | {dados['peso']}"

        texto_item = f"""
    📦 REF: {item['REFERENCIA']} | KIT: {item['KIT']} | QT: {item["ESTOQUE_DISPONIVEL"]}
    ID: {item['ID']}

    💰 VENDA: {item['VENDA']} | CUSTO: {item['CUSTO']}

    📏 MEDIDAS:
    ORIGINAL: {medidas_texto}
    NOVA: {item['ALTURA']} x {item['LARGURA']} x {item['COMPRIMENTO']} | {item['PESO']}
    """
        # Acumula cada item no texto_final
        texto_final += texto_item + "\n" + "-" * 40 + "\n"

        with cols_cards[(i - 1) % 2]:
            with st.container(border=True):
                c1, c2 = st.columns([1, 3])
                with c1:
                    if item["IMAGEM"]:
                        st.image(item["IMAGEM"], caption=item['REFERENCIA'], width=180)
                with c2:
                    st.code(texto_item, language=None)

    import os
    caminho_salvamento = PASTA
    if not os.path.exists(caminho_salvamento):
        os.makedirs(caminho_salvamento)

    nome_arquivo = f"itens_{nome_produto.strip()}.txt"
    caminho_completo = os.path.join(caminho_salvamento, nome_arquivo)

    # Agora salva texto_final com TODOS os itens
    with open(caminho_completo, "w", encoding="utf-8") as f:
        f.write(texto_final)

    st.success(f"✅ **Arquivo salvo com sucesso em:** {caminho_completo}")

# ⚠️  função grande (153 linhas)
def Re_Anunciar():
    import streamlit as st
    import pandas as pd
    import os
    from _BANCOS_.Banco_Bados import ler_MARKET_PLACE, ATUAL_MARKET_PLACE, contar_estoque

    from Functions import extrair_medidas
    # 1. Lê todos os produtos
    dados = ler_MARKET_PLACE()
    if not dados:
        st.error("Nenhum produto encontrado.")
        st.stop()

    colunas = [
        "ID",
        "IMAGEM",
        "DATA",
        "NOME_PRODUTO",
        "KIT",
        "PLATAFORMAS_POSTADO",
        "PLATAFORMA_VENDA",
        "CLIENTE_NOME",
        "CLIENTE_CPF",
        "CLIENTE_TELEFONE",
        "ENDERECO",
        "VALOR_VENDA",
        "CUSTO_PRODUTO",
        "TAXA_PLATAFORMA",
        "LUCRO",
        "QUANTIDADE",
        "TITULO",
        "DESCRITION",
    ]

    df = pd.DataFrame(dados, columns=colunas)

    # 2. 🔥 LÓGICA PARECIDA: agrupa por NOME_PRODUTO (poderia ser por ID tb)
    produtos_unicos = {}

    for _, row in df.iterrows():
        nome = str(row["NOME_PRODUTO"]).strip()
        pid = row["ID"]

        if nome not in produtos_unicos:
            produtos_unicos[nome] = {
                "NOME_PRODUTO": nome,
                "IMAGEM": row["IMAGEM"],
                "KIT": row["KIT"],
                "PLATAFORMAS_POSTADO": row["PLATAFORMAS_POSTADO"],
                "PLATAFORMA_VENDA": row["PLATAFORMA_VENDA"],
                "VALOR_VENDA": row["VALOR_VENDA"],
                "CUSTO_PRODUTO": row["CUSTO_PRODUTO"],
                "TITULO": row["TITULO"],
                "DESCRITION": row["DESCRITION"],
                "IDS": [],  # armazena todos os IDs iguais
                "ESTOQUE": 0,
            }

        # adiciona esse ID ao grupo do produto
        produtos_unicos[nome]["IDS"].append(pid)
        produtos_unicos[nome]["ESTOQUE"] += contar_estoque(pid)

    lista_produtos = list(produtos_unicos.values())

    # 3. Selectbox com os produtos únicos
    opcoes = [
        f"{p['NOME_PRODUTO']} | QT: {p['ESTOQUE']} | {p['PLATAFORMAS_POSTADO'] or 'Sem plataformas'}"
        for p in lista_produtos
    ]

    produto_select = st.selectbox("Selecionar Produto", opcoes, index=None)

    if not produto_select:
        st.info("Selecione um produto acima para editar.")

        return

    item = lista_produtos[opcoes.index(produto_select)]

    plataformas_atuais = str(item["PLATAFORMAS_POSTADO"] or "")

    nova_plataforma = st.multiselect("Adicionar Marketplace",
        ["", "Shopee", "Mercado Livre", "Amazon", "Site", "Elo7"],key=f"plat_{item['NOME_PRODUTO']}")

    st1, st2 = st.columns([1, 2])
    st2.markdown('### 📝 TÍTULO')
    st2.code(item['TITULO'] or '', language=None)

    st2.markdown('### 📄 DESCRIÇÃO')
    st2.code(item['DESCRITION'] or '', language=None, height=400)

    st1.markdown('### 📦 KIT')
    st1.code(item['KIT'] or '', language=None)

    st1.markdown('### 💰 VALOR')
    st1.code(f"R$ {float(item['VALOR_VENDA'] or 0):.2f}", language=None)

    st1.markdown('### 💸 CUSTO')
    st1.code(f"R$ {float(item['CUSTO_PRODUTO'] or 0):.2f}", language=None)

    st1.markdown('### 🚚 PLATAFORMAS')
    st1.code(item['PLATAFORMAS_POSTADO'] or '', language=None)

    if st.button("➕ Adicionar Plataforma",key=f"btn_{item['NOME_PRODUTO']}",width=True):
        for pid in item["IDS"]:
            ATUAL_MARKET_PLACE(pid, "PLATAFORMAS_POSTADO", ', '+", ".join(nova_plataforma),True)

        st.success(f"Plataforma adicionada: {nova_plataforma}")
        st.rerun()

    st.markdown("---")
    st.markdown(f"## {item['NOME_PRODUTO']}")

    cols = st.columns(2)

    for i, pid in enumerate(item["IDS"]):
        dados_medidas = calcular_medidas_com_margem(pid)
        dados_original = extrair_medidas(pid)

        # ✅ PEGAR OS VALORES DESSE PID ESPECÍFICO, NÃO DO ITEM
        row = df[df["ID"] == pid].iloc[0]
        valor_venda = row["VALOR_VENDA"]
        custo_produto = row["CUSTO_PRODUTO"]

        medidas_texto = ""
        if dados_original:
            medidas_texto = (
                f"{dados_original.get('altura', 0)} x "
                f"{dados_original.get('largura', 0)} x "
                f"{dados_original.get('espessura', 0)} | {dados_original.get('peso', 0)}"
            )

        texto_item = f"""
    📦 REF: {dados_medidas['ref']} | QT: {contar_estoque(pid)}
    ID: {pid}

    💰 VENDA: R$ {float(valor_venda or 0):.2f} | CUSTO: R$ {float(custo_produto or 0):.2f}

    📏 MEDIDAS:
    ORIGINAL: {medidas_texto}
    NOVA: {dados_medidas.get("altura", 0)} x {dados_medidas.get("largura", 0)} x {dados_medidas.get("comprimento", 0)} | {dados_medidas.get("peso", 0)}
        """.strip()

        with cols[i % 2]:
            with st.container(border=True):
                c1, c2 = st.columns([1, 3])

                with c1:
                    img = df[df["ID"] == pid]["IMAGEM"].values
                    if len(img) and img[0] and os.path.exists(str(img[0])):
                        st.image(img[0], width=160)

                with c2:
                    st.code(texto_item, language=None)
