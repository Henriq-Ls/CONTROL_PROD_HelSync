# 📁 Tratar_midias/e__Renomeie_IMG.py
import os
from pathlib import Path

from PIL import Image, ImageOps
EXTENSOES = (".jpg", ".jpeg", ".png", ".webp")

# ============================================================
# UTILITÁRIOS
# ============================================================

def _parse_peso(peso_str: str) -> int:
    """Converte string de peso para int em gramas. Retorna 0 se vazio ou inválido."""
    try:

        return int(peso_str.strip())

    except (ValueError, AttributeError):

        return 0

def _peso_fmt(peso_g: int) -> str:
    if peso_g <= 0:

        return "0gm"

    return f"{peso_g / 1000:.1f}kg" if peso_g >= 1000 else f"{peso_g}gm"

def _salvar(origem: Path, destino: Path, thumbnail: bool = False):
    img = Image.open(origem)
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGB")
    if thumbnail:
        img.thumbnail((1600, 1600), Image.LANCZOS)
        img.save(destino, optimize=False, quality=85)
    else:
        img.save(destino, optimize=False, quality=100)

def _ler_txt(pasta: Path) -> list:
    """
    Lê o produtos.txt gerado pelo cadastro.
    Formato: medidas,peso  (1 linha por foto, em ordem)

    Exemplo:
        1x1x1,1
        1x1x1,1
        2x2x2,2
        2x2x2,2

    Retorna: [('1x1x1', '1'), ('1x1x1', '1'), ('2x2x2', '2'), ...]
    """
    for arq in os.listdir(pasta):
        if arq.lower().endswith(".txt"):
            linhas = []
            with open(pasta / arq, "r", encoding="utf-8") as f:
                for linha in f:
                    linha = linha.strip()
                    if not linha:
                        continue
                    partes = linha.split(",")
                    if len(partes) >= 2:
                        linhas.append((partes[0].strip(), partes[1].strip()))
                    elif len(partes) == 1 and partes[0].strip():
                        linhas.append((partes[0].strip(), "0"))

            return linhas

    return []

# 💡 ordem_opc = Literal["crescente"] ← defina os valores válidos
def _listar_imagens(pasta: Path, ordem: str = "crescente") -> list:
    arqs = [a for a in os.listdir(pasta) if a.lower().endswith(EXTENSOES)]

    return sorted(arqs, reverse=(ordem.lower() == "decrescente"))

def _parse_config(config_str: str) -> dict:
    resultado = {}
    for parte in config_str.split("|"):
        sep = ":" if parte.count(":") == 1 and "=" not in parte else "="
        if sep in parte:
            chave, valor = parte.split(sep, 1)
            resultado[chave.strip()] = valor.strip()

    return resultado

# ============================================================
# 1. ÚNICO — VAR=1 ou VAR=N
#
#    TXT lido de pasta_saida (raiz do produto)
#    Fotos pares: [0]=MED, [1]=MOST, [2]=MED, [3]=MOST ...
#
#    MOST: ref1_77x45x3_490gm.jpg
#    MED:  ref1_77x45x3_490gm.jpg
# ============================================================

# 💡 ordem_opc = Literal["crescente"] ← defina os valores válidos
def Renomear_Unico(pasta_entrada, pasta_saida, ref, ordem="crescente"):
    pasta_entrada = Path(pasta_entrada)
    pasta_saida   = Path(pasta_saida)
    pasta_med     = pasta_saida / "c_Amostra_SEM_LOGO"
    pasta_most    = pasta_saida / "Imag_med"
    pasta_med.mkdir(parents=True, exist_ok=True)
    pasta_most.mkdir(parents=True, exist_ok=True)

    linhas   = _ler_txt(pasta_saida)      # ← TXT está na raiz (pasta_saida)
    arquivos = _listar_imagens(pasta_entrada, ordem)

    if not linhas:
        print("Nenhum TXT encontrado.")

        return "Erro: TXT não encontrado."

    print(f"\n{'='*52}")
    print(f"  Renomear_Unico — {len(arquivos)} imagens | {len(linhas)} linhas TXT")
    print(f"{'='*52}")

    contador = 1
    is_most  = False  # False=MED, True=MOST

    for i, arquivo in enumerate(arquivos):
        if i >= len(linhas):
            print("  TXT acabou.")
            break

        medidas, peso = linhas[i]
        novo_nome = f"{ref}{contador}_{medidas}_{_peso_fmt(_parse_peso(peso))}.jpg"

        if not is_most:
            _salvar(pasta_entrada / arquivo, pasta_med / novo_nome)
            print(f"  [MED]  {arquivo} → {novo_nome}")
        else:
            _salvar(pasta_entrada / arquivo, pasta_most / novo_nome)
            print(f"  [MOST] {arquivo} → {novo_nome}")
            contador += 1

        is_most = not is_most

    print(f"\n  ✓ Único finalizado → {pasta_saida}\n")

    return str(pasta_saida)

# ============================================================
# 2. KIT DIFERENTES — PECAS=N, QTS_KITS=M
#
#    TXT lido de pasta_saida (raiz do produto)
#    Grupo = 1 foto kit completo (MOST) + N fotos peças (MED)
#
#    MOST: ref1_medidas_peso.jpg
#    MED:  ref1_1_medidas_peso.jpg
#          ref1_2_medidas_peso.jpg
# ============================================================

# ⚠️  função grande (62 linhas)
# 💡 ordem_opc = Literal["crescente"] ← defina os valores válidos
def Renomear_Kit(st, pasta_entrada, pasta_saida, ref, qtd_pecas, ordem="crescente"):
    from _APP_.Functions_app import Alerta
    pasta_entrada     = Path(pasta_entrada)
    pasta_saida       = Path(pasta_saida)
    pasta_med         = pasta_saida / "c_Amostra_SEM_LOGO"
    pasta_most        = pasta_saida / "Imag_med"
    pasta_med.mkdir(parents=True, exist_ok=True)
    pasta_most.mkdir(parents=True, exist_ok=True)

    linhas            = _ler_txt(pasta_saida)      # ← TXT está na raiz (pasta_saida)
    arquivos          = _listar_imagens(pasta_entrada, ordem)
    imagens_por_grupo = 1 + qtd_pecas
    num_imagens       = len(arquivos)

    if not linhas:
        Alerta(st, "ERRO: TXT não encontrado.")

        return

    if num_imagens % imagens_por_grupo != 0:
        Alerta(st, f"ERRO: {num_imagens} imagens não é divisível por {imagens_por_grupo}.\n"
                   f"(1 kit completo + {qtd_pecas} peças por grupo)")

        return

    if len(linhas) != num_imagens:
        Alerta(st, f"ERRO: TXT tem {len(linhas)} linhas, mas há {num_imagens} imagens.")

        return

    num_grupos = num_imagens // imagens_por_grupo
    print(f"\n{'='*52}")
    print(f"  Renomear_Kit — {num_grupos} grupos × {qtd_pecas} peças")
    print(f"{'='*52}")

    contador = 1
    idx_txt  = 0
    i        = 0

    while i < len(arquivos):
        medidas, peso = linhas[idx_txt]
        nome_most = f"{ref}{contador}_{medidas}_{_peso_fmt(_parse_peso(peso))}.jpg"
        _salvar(pasta_entrada / arquivos[i], pasta_most / nome_most, thumbnail=True)
        print(f"  [MOST] {arquivos[i]} → {nome_most}")
        idx_txt += 1

        for k in range(1, qtd_pecas + 1):
            idx_img = i + k
            if idx_img >= len(arquivos):
                break
            medidas, peso = linhas[idx_txt]
            nome_med = f"{ref}{contador}_{k}_{medidas}_{_peso_fmt(_parse_peso(peso))}.jpg"
            _salvar(pasta_entrada / arquivos[idx_img], pasta_med / nome_med, thumbnail=True)
            print(f"  [MED {k}] {arquivos[idx_img]} → {nome_med}")
            idx_txt += 1

        contador += 1
        i        += imagens_por_grupo

    print(f"\n  ✓ Kit finalizado → {pasta_saida}\n")

    return str(pasta_saida)

# ============================================================
# 3. ÚNICO + KIT
# ============================================================

# 💡 ordem_opc = Literal["crescente"] ← defina os valores válidos
def Renomear_Unico_com_Kit(st, pasta_entrada, pasta_saida, ref, qtd_pecas_kit, qt_kits, ordem="crescente"):
    resultado = Renomear_Unico(pasta_entrada, pasta_saida, ref, ordem)
    for n in range(1, qt_kits + 1):
        sub_ref = f"{ref}_k{n}"
        Renomear_Kit(st, pasta_entrada, pasta_saida, sub_ref, qtd_pecas_kit, ordem)

    return resultado

# ============================================================
# DISPATCHER — uma chamada, a função entende o tipo
# ============================================================

# 💡 ordem_opc = Literal["crescente"] ← defina os valores válidos
def renomear_por_config(st, pasta_entrada, pasta_saida, config_str: str ,ref, ordem="crescente"):
    cfg     = _parse_config(config_str)
    tipo    = cfg.get("TIPO", "").upper()
    kit     = cfg.get("KIT", "NO").upper()
    pecas   = int(cfg.get("PECAS", 2))
    qt_kits = int(cfg.get("QTS_KITS", 1))

    if tipo == "ÚNICO":
        if kit == "NO":

            return Renomear_Unico(pasta_entrada, pasta_saida, ref, ordem)

        elif kit == "YES":

            return Renomear_Unico_com_Kit(

                st, pasta_entrada, pasta_saida, ref, pecas, qt_kits, ordem
            )

    elif tipo == "KIT":

        return Renomear_Kit(st, pasta_entrada, pasta_saida, ref, pecas, ordem)

    else:
        from _APP_.Functions_app import Alerta
        Alerta(st, f"ERRO: tipo desconhecido → '{config_str}'")

        return None
