# 📁 _FERRAMENTAS_/_Qantidades_Variations.py

import os
# ── ADICIONA AQUI ──────────────────────────────────────────
def parse_peso(peso_raw: str) -> int:
    try:
        s = str(peso_raw).strip().lower()
        if 'kg' in s:

            return int(float(s.replace('kg', '').replace(',', '.')) * 1000)

        return int(''.join(filter(str.isdigit, s)))

    except:

        return 0

# ───────────────────────────────────────────────────────────

def _parse_tipo_kit(config_str: str) -> dict:
    ...
    """
    "TIPO:ÚNICO|VAR=4|KIT=NO"              → {'TIPO':'ÚNICO','VAR':'4','KIT':'NO'}
    "TIPO:ÚNICO|VAR=1|KIT=YES|PECAS=3|..." → {'TIPO':'ÚNICO','KIT':'YES','PECAS':'3',...}
    "TIPO:KIT|PECAS=3|VAR=TAMANHO|..."     → {'TIPO':'KIT','PECAS':'3','VAR':'TAMANHO',...}
    """
    cfg = {}
    for parte in str(config_str).split("|"):
        if ":" in parte and "=" not in parte:
            chave, valor = parte.split(":", 1)
        elif "=" in parte:
            chave, valor = parte.split("=", 1)
        else:
            continue
        cfg[chave.strip()] = valor.strip()

    return cfg

def Ler_variacoes_txt(pasta_origem):
    """Lê o produtos.txt gerado pelo App_Cadastro_Prod e formata para exibição."""
    arquivo_txt = None
    for arq in os.listdir(pasta_origem):
        if arq.lower().endswith(".txt"):
            arquivo_txt = os.path.join(pasta_origem, arq)
            break
    if not arquivo_txt:

        return ""

    with open(arquivo_txt, "r", encoding="utf-8") as f:
        linhas = [x.strip() for x in f.readlines() if x.strip()]
    saida = []
    total = 0
    for linha in linhas:
        try:
            medidas, peso = linha.split(",")
            dims = medidas.split("x")
            alt = dims[0] if len(dims) > 0 else "?"
            lar = dims[1] if len(dims) > 1 else "?"
            esp = dims[2] if len(dims) > 2 else "?"
            peso_g   = parse_peso(peso)
            peso_fmt = f"{peso_g/1000:.1f}kg" if peso_g >= 1000 else f"{peso_g}gr"
            saida.append(f"* {alt} x {lar} x {esp} cm | Peso: {peso_fmt}")
            total += 1
        except:
            continue

    return f"TODAS variações no TXT: {total}\n" + "\n".join(saida)

# ============================================================
# ÚNICO + KIT — repete o mesmo produto N vezes por opção
# ============================================================

def montar_variacoes_unico(pasta_imagens, kit_opcoes):
    """
    ÚNICO que também vende em kit.
    Lê o primeiro arquivo da pasta, repete N vezes por opção selecionada.
    kit_opcoes = ['Peça única', 'Kit: 3']
    """
    extensoes = ('.jpg', '.jpeg', '.png', '.webp')
    arquivo_ref = None
    for arq in sorted(os.listdir(pasta_imagens)):
        if arq.lower().endswith(extensoes):
            arquivo_ref = os.path.splitext(arq)[0]
            break
    if not arquivo_ref:

        return ['Nenhuma imagem encontrada na pasta.']

    try:
        partes     = arquivo_ref.split('_')
        referencia = partes[0].upper()
        medidas    = partes[-2]
        peso_raw   = partes[-1]
        dims       = medidas.split('x')
        alt  = dims[0] if len(dims) > 0 else "?"
        larg = dims[1] if len(dims) > 1 else "?"
        esp  = dims[2] if len(dims) > 2 else "?"
        peso_g = parse_peso(peso_raw)
    except Exception as e:

        return [f'Erro ao ler medidas de "{arquivo_ref}": {e}']

    if not kit_opcoes:
        kit_opcoes = ['Peça única']
    resultado = []
    for opcao in kit_opcoes:
        qt    = 1 if opcao == 'Peça única' else int(opcao.split(':')[1].strip())
        label = 'Peça única' if qt == 1 else f'Kit com {qt} peças'
        peso_total = peso_g * qt
        peso_fmt   = f"{peso_total/1000:.1f}kg" if peso_total >= 1000 else f"{peso_total}g"
        itens = '\n'.join(
            f'  • {referencia} | alt:{alt} larg:{larg} esp:{esp} cm | peso:{peso_raw}'
            for _ in range(qt)
        )
        resultado.append(f'--- {label} | peso total: {peso_fmt} | Total = R$?\n{itens}')

    return resultado

# ============================================================
# KIT DE PEÇAS DIFERENTES
# ============================================================

def listar_nomes_pasta(pasta, kit_qt):
    """Agrupa os arquivos da pasta em kits de kit_qt peças."""
    arquivos = []
    try:
        for arquivo in os.listdir(pasta):
            if os.path.isfile(os.path.join(pasta, arquivo)):
                arquivos.append(os.path.splitext(arquivo)[0])
        arquivos.sort()
    except FileNotFoundError:

        return {}

    kits = {}
    contador = 1
    for i in range(0, len(arquivos), kit_qt):
        kits[f'KIT_{contador}'] = arquivos[i:i + kit_qt]
        contador += 1

    return kits

def organizar_kits(dados):
    """Formata os kits em texto para o prompt da IA de preços."""
    resultado = []
    cabecalho = (
        '"Valide os preços das variações da Shopee para que a variação '
        'mais cara não ultrapasse 4x o valor da mais barata."\n'
        '"Organize os preços das minhas variações dentro da regra 1:4 da Shopee.":\n\n'
    )
    for kit_nome, itens in dados.items():
        texto    = cabecalho + f'{kit_nome} contém:\n'
        peso_kit = 0
        for item in itens:
            try:
                partes     = item.split('_')
                referencia = partes[0].upper()
                medidas    = partes[-2]
                peso       = partes[-1]
                dims       = medidas.split('x')
                alt  = dims[0] if len(dims) > 0 else "?"
                larg = dims[1] if len(dims) > 1 else "?"
                esp  = dims[2] if len(dims) > 2 else "?"
                peso_g    = parse_peso(peso)
                peso_kit += peso_g
                peso_fmt  = f"{peso_g/1000:.1f}kg" if peso_g >= 1000 else f"{peso_g}g"
                texto += f'  • {referencia} | alt:{alt} larg:{larg} esp:{esp} cm | peso:{peso_fmt}\n'
            except:
                texto += f'  • {item} (erro ao ler)\n'
        peso_kit_fmt = f"{peso_kit/1000:.1f}kg" if peso_kit >= 1000 else f"{peso_kit}g"
        texto += f'  Peso total do kit: {peso_kit_fmt}\n'
        texto += f'  Total desse kit = R$?\n'
        resultado.append(texto)

    return resultado

# ============================================================
# FUNÇÃO UNIVERSAL
# ============================================================

# ⚠️  função grande (51 linhas)
def montar_variacoes(pasta_imagens, kit_opcoes, tipo_kit_config):
    """
    Decide o que fazer com base em kit_opcoes:

    lista      → ÚNICO + kit       → montar_variacoes_unico
    'Sem Kit'  → ÚNICO N variações → lista cada arquivo com suas medidas
    None       → KIT de peças      → agrupa em kits e formata para IA

    tipo_kit_config vem direto de TIPO_KIT_UNICO (config_str do novo sistema).
    """
    if isinstance(kit_opcoes, list):

        return montar_variacoes_unico(pasta_imagens, kit_opcoes)

    elif kit_opcoes == 'Sem Kit':
        extensoes = ('.jpg', '.jpeg', '.png', '.webp')
        cabecalho = (
            '"Valide os preços das variações da Shopee para que a variação '
            'mais cara não ultrapasse 4x o valor da mais barata."\n\n'
        )
        resultado = [cabecalho]
        for arq in sorted(os.listdir(pasta_imagens)):
            if not arq.lower().endswith(extensoes):
                continue
            nome = os.path.splitext(arq)[0]
            try:
                partes     = nome.split('_')
                referencia = partes[0].upper()
                medidas    = partes[-2]
                peso_raw   = partes[-1]
                dims       = medidas.split('x')
                alt  = dims[0] if len(dims) > 0 else "?"
                larg = dims[1] if len(dims) > 1 else "?"
                esp  = dims[2] if len(dims) > 2 else "?"
                peso_g   = parse_peso(peso_raw)
                peso_fmt = f"{peso_g/1000:.1f}kg" if peso_g >= 1000 else f"{peso_g}g"
                resultado.append(
                    f'- {referencia} | alt:{alt} larg:{larg} esp:{esp} cm '
                    f'| peso:{peso_fmt} | Total = R$?'
                )
            except:
                resultado.append(f'- {nome} (erro ao ler medidas)')

        return resultado

    else:
        cfg  = _parse_tipo_kit(tipo_kit_config)
        qtd  = int(cfg.get("PECAS", 2))
        dados = listar_nomes_pasta(pasta_imagens, qtd)

        return organizar_kits(dados)
