import os
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Literal

from _GERENTE_PROJETO_.Decorar.Materiais import Material

# ===== FIX WINDOWS: NÃO ABRIR CMD / POWERSHELL =====
STARTUPINFO = subprocess.STARTUPINFO()
STARTUPINFO.dwFlags |= subprocess.STARTF_USESHOWWINDOW
STARTUPINFO.wShowWindow = subprocess.SW_HIDE
CREATE_FLAGS = subprocess.CREATE_NO_WINDOW

'''
GERENCIA TODA A CRIAÇÃO DO PROJETO
'''
def _pastas_nao():
    return {"_GERENTE_PROJETO_",".venv", ".idea", ".git", "__pycache__", "venv", "env", ".nox", ".tox",".gitattributes"
            ,".gitignore","INSTALL.txt","LICENSE","README.md","Rascunho.py","Rasc.py","Rasc1.py","VERSION","Html_app.py"
            ,"AS_Imports_Bancos.py","text.txt","","","","","",""}

def Pasta_Raiz():
    """Retorna o diretório raiz do arquivo atual."""
    BASE_DIR = Path(__file__).parent.parent.resolve()
    return BASE_DIR

opc = Literal["data_br", "data_EUA", "hora", "completo"]
def data_sistema(formato: opc = "") -> str:
    """Retorna a data e/ou hora atual no formato especificado."""
    from datetime import datetime
    agora = datetime.now()
    if str(formato).lower() == "data_eua":
        return agora.strftime("%Y-%m-%d")
    elif str(formato).lower() == "hora":
        return agora.strftime("%H:%M:%S")
    elif str(formato).lower() == "data_br":
        return agora.strftime("%d/%m/%Y")
    else:
        return agora.strftime("%Y-%m-%d %H:%M:%S")

# ⚠️  função grande (171 linhas) | except genérico vazio
def listar_projeto(st):
    """Analisa e exibe a estrutura completa do projeto com funções, classes e imports."""
    from pathlib import Path
    import ast
    import os
    from collections import defaultdict

    raiz = Path(Pasta_Raiz())
    esp = ' '
    texto = f"📂 PROJETO: {raiz.name}\n"
    texto += "Estrutura atual do projeto:\n\n"

    pastas_excluidas = _pastas_nao()

    chamadas_funcoes = defaultdict(list)

    # ==========================================
    # PRIMEIRA PASSADA → MAPEAR CHAMADAS
    # ==========================================
    for root, _, files in os.walk(raiz):
        if any(x in root for x in pastas_excluidas):
            continue

        for file in files:
            if file.endswith(".py"):
                path = Path(root) / file

                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        codigo = f.read()

                    tree = ast.parse(codigo)

                    for node in ast.walk(tree):
                        if isinstance(node, ast.Call):
                            if isinstance(node.func, ast.Name):
                                chamadas_funcoes[node.func.id].append(file)

                except:
                    pass

    # ==========================================
    # SEGUNDA PASSADA → MOSTRAR ESTRUTURA
    # ==========================================
    def print_tree(directory, prefix=""):
        nonlocal texto

        items = sorted(item for item in os.listdir(directory) if item not in pastas_excluidas)

        for i, item in enumerate(items):
            is_last = i == len(items) - 1
            connector = "└── " if is_last else "├── "
            path = directory / item

            texto += f"{prefix}{connector}{item}\n"

            if path.is_dir():
                new_prefix = prefix + ("    " if is_last else "│   ")
                print_tree(path, new_prefix)

            elif item.endswith('.py'):

                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        codigo = f.read()

                    tree = ast.parse(codigo)

                    funcoes = []
                    classes = []
                    modulos = set()

                    for node in tree.body:

                        # =========================
                        # FUNÇÕES - ✅ DOCSTRING COMPLETA
                        # =========================
                        if isinstance(node, ast.FunctionDef):
                            descricao_completa = ast.get_docstring(node)
                            descricao_completa = descricao_completa.strip() if descricao_completa else "Sem descrição"

                            # Primeira linha pra exibição principal
                            descricao = descricao_completa.split('\n')[
                                0] if descricao_completa != "Sem descrição" else "Sem descrição"

                            chamadas = chamadas_funcoes.get(node.name, [])
                            qtd_chamadas = len(chamadas)
                            chamado_por = sorted(set(chamadas))
                            chamado_por_txt = ", ".join(chamado_por[:5])

                            funcoes.append({
                                "nome": node.name,
                                "descricao": descricao,
                                "descricao_completa": descricao_completa,  # ✅ Guarda completa
                                "qtd": qtd_chamadas,
                                "por": chamado_por_txt
                            })

                        # =========================
                        # CLASSES - ✅ DOCSTRING COMPLETA
                        # =========================
                        elif isinstance(node, ast.ClassDef):
                            descricao_completa = ast.get_docstring(node)
                            descricao_completa = descricao_completa.strip() if descricao_completa else "Sem descrição"
                            descricao = descricao_completa.split('\n')[
                                0] if descricao_completa != "Sem descrição" else "Sem descrição"

                            classes.append({
                                "nome": node.name,
                                "descricao": descricao,
                                "descricao_completa": descricao_completa  # ✅ Guarda completa
                            })

                    # =========================
                    # IMPORTS
                    # =========================
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ImportFrom):
                            if node.module:
                                modulos.add(node.module.split('.')[0])

                        elif isinstance(node, ast.Import):
                            for alias in node.names:
                                modulos.add(alias.name.split('.')[0])

                    modulos = sorted(modulos)

                    indent = prefix + ("    " if is_last else "│   ") + "    "

                    # ==================================
                    # RESUMO
                    # ==================================
                    texto += f"{indent}Funções ({len(funcoes)})\n"
                    texto += f"{indent}Classes ({len(classes)})\n"

                    if modulos:
                        texto += f"{indent}Imports: {', '.join(modulos)}\n"

                    # ==================================
                    # FUNÇÕES - ✅ MOSTRA DOCSTRING COMPLETA
                    # ==================================
                    if funcoes:
                        texto += f"{indent}\n"  # Linha vazia

                        for func in funcoes:
                            texto += f"{indent}• {func['nome']}\n"
                            texto += f"{indent}   ↳ {func['descricao']}\n"

                            # ✅ EXIBE LINHAS EXTRAS DA DOCSTRING!
                            linhas_extras = func['descricao_completa'].split('\n')[1:]
                            for linha in linhas_extras[:3]:  # Máx 3 linhas extras
                                if linha.strip():
                                    texto += f"{indent}   │ {linha.strip()}\n"

                            texto += f"{indent}   ↳ Chamadas: {func['qtd']}\n"

                            if func['por']:
                                texto += f"{indent}   ↳ Chamado por: {func['por']}\n"

                            texto += f"{esp}\n"

                    # ==================================
                    # CLASSES - ✅ MOSTRA DOCSTRING COMPLETA
                    # ==================================
                    if classes:
                        texto += f"{indent}\n"
                        texto += f"{indent}Classes:\n"

                        for cls in classes:
                            texto += f"{indent}• {cls['nome']}\n"
                            texto += f"{indent}   ↳ {cls['descricao']}\n"

                            # ✅ EXIBE LINHAS EXTRAS DA DOCSTRING!
                            linhas_extras = cls['descricao_completa'].split('\n')[1:]
                            for linha in linhas_extras[:2]:  # Máx 2 linhas extras
                                if linha.strip():
                                    texto += f"{indent}   │ {linha.strip()}\n"

                        texto += f"{esp}\n"

                except Exception as e:
                    indent = prefix + ("    " if is_last else "│   ") + "    "
                    texto += f"{indent}(Erro ao analisar: {e})\n"

    print_tree(raiz)
    st.code(texto, language='markdown')

# ⚠️  função grande (177 linhas) | except genérico vazio
def listar_projeto_(st):
    """Analisa e exibe a estrutura completa do projeto com funções, classes e imports."""
    from pathlib import Path
    import ast
    import os
    from collections import defaultdict
    raiz = Pasta_Raiz()

    pastas_excluidas = _pastas_nao()

    print(f"📂 PROJETO: {raiz.name}\n")
    print("Estrutura atual do projeto:")
    st.subheader(f"📂 PROJETO: {raiz.name}\n")
    st.text("Estrutura atual do projeto:")
    chamadas_funcoes = defaultdict(list)

    # ==========================================
    # PRIMEIRA PASSADA → MAPEAR CHAMADAS
    # ==========================================
    for root, _, files in os.walk(raiz):
        if any(x in root for x in pastas_excluidas):
            continue

        for file in files:
            if file.endswith(".py"):
                path = Path(root) / file

                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        tree = ast.parse(f.read())

                    for node in ast.walk(tree):
                        if isinstance(node, ast.Call):
                            if isinstance(node.func, ast.Name):
                                chamadas_funcoes[node.func.id].append(file)

                except:
                    pass

    # ==========================================
    # SEGUNDA PASSADA → MOSTRAR ESTRUTURA
    # ==========================================
    # ⚠️  função grande (129 linhas)
    def print_tree(directory, prefix=""):
        items = sorted(item for item in os.listdir(directory) if item not in pastas_excluidas)

        for i, item in enumerate(items):
            is_last = i == len(items) - 1
            connector = "└── " if is_last else "├── "
            path = directory / item

            print(f"{prefix}{connector}{item}")
            st.text(f"{prefix}{connector}{item}")

            if path.is_dir():
                new_prefix = prefix + ("    " if is_last else "│   ")
                print_tree(path, new_prefix)

            elif item.endswith('.py'):

                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        codigo = f.read()
                    tree = ast.parse(codigo)
                    funcoes = []
                    classes = []
                    modulos = set()

                    for node in tree.body:

                        # =========================
                        # FUNÇÕES
                        # =========================
                        if isinstance(node, ast.FunctionDef):

                            descricao = ast.get_docstring(node)
                            descricao = descricao.strip().split('\n')[0] if descricao else "Sem descrição"

                            chamadas = chamadas_funcoes.get(node.name, [])
                            qtd_chamadas = len(chamadas)

                            chamado_por = sorted(set(chamadas))
                            chamado_por_txt = ", ".join(chamado_por[:5])

                            funcoes.append({
                                "nome": node.name,
                                "descricao": descricao,
                                "qtd": qtd_chamadas,
                                "por": chamado_por_txt
                            })

                        # =========================
                        # CLASSES
                        # =========================
                        elif isinstance(node, ast.ClassDef):

                            descricao = ast.get_docstring(node)
                            descricao = descricao.strip().split('\n')[0] if descricao else "Sem descrição"

                            classes.append({
                                "nome": node.name,
                                "descricao": descricao
                            })

                    # =========================
                    # IMPORTS
                    # =========================
                    for node in ast.walk(tree):

                        if isinstance(node, ast.ImportFrom) and node.module:
                            modulos.add(node.module.split('.')[0])

                        elif isinstance(node, ast.Import):
                            for alias in node.names:
                                modulos.add(alias.name.split('.')[0])

                    modulos = sorted(modulos)

                    indent = prefix + ("    " if is_last else "│   ") + "    "

                    # ==================================
                    # RESUMO
                    # ==================================
                    print(f"{indent}Funções ({len(funcoes)})")
                    print(f"{indent}Classes ({len(classes)})")
                    st.text(f"{indent}Funções ({len(funcoes)})")
                    st.text(f"{indent}Classes ({len(classes)})")
                    if modulos:
                        st.text(f"{indent}Módulos: {', '.join(modulos)}")

                    # ==================================
                    # FUNÇÕES
                    # ==================================
                    if funcoes:

                        print(f"{indent}")
                        st.text(f"{indent}")
                        for func in funcoes:

                            print(f"{indent}• {func['nome']}")
                            print(f"{indent}   ↳ {func['descricao']}")
                            print(f"{indent}   ↳ Chamadas: {func['qtd']}")

                            st.text(f"{indent}• {func['nome']}")
                            st.text(f"{indent}   ↳ {func['descricao']}")
                            st.text(f"{indent}   ↳ Chamadas: {func['qtd']}")

                            if func['por']:
                                print(f"{indent}   ↳ Chamado por: {func['por']}")
                                st.text(f"{indent}   ↳ Chamado por: {func['por']}")

                            print()
                            st.text()

                    # ==================================
                    # CLASSES
                    # ==================================
                    if classes:

                        print(f"{indent}Classes:")
                        st.text(f"{indent}Classes:")

                        for cls in classes:
                            print(f"{indent}• {cls['nome']}")
                            st.text(f"{indent}   ↳ {cls['descricao']}")
                            print()
                            st.text()

                except Exception as e:

                    indent = prefix + ("    " if is_last else "│   ") + "    "
                    print(f"{indent}(Erro ao analisar: {e})")

    print_tree(raiz)

# ⚠️  função grande (79 linhas)
def contar_estrutura(caminho_base):
    """Conta pastas, arquivos, extensões e versões Python em uma estrutura de diretórios."""
    from datetime import datetime
    caminho_base = Path(caminho_base).resolve()

    nomes_envs = {
        ".venv",
        "venv",
        "env",
        ".virto_stream",
        ".tox",
        ".nox",
        "__pypackages__"
    }

    pastas_excluidas = _pastas_nao()

    total_pastas = 0
    total_arquivos = 0
    arquivos_por_extensao = defaultdict(int)
    pastas_datas = []
    python_envs = []

    # ambientes Python
    for nome_env in nomes_envs:
        env_path = caminho_base / nome_env
        if not env_path.exists():
            continue

        python_exec = env_path / "Scripts" / "python.exe"
        if not python_exec.exists():
            python_exec = env_path / "bin" / "python"

        if python_exec.exists():
            try:
                versao = subprocess.check_output(
                    [str(python_exec), "--version"],
                    stderr=subprocess.STDOUT,
                    text=True,
                    startupinfo=STARTUPINFO,
                    creationflags=CREATE_FLAGS
                ).strip()

            except Exception:
                versao = None

            python_envs.append({
                versao
            })

    for root, dirs, files in os.walk(caminho_base):
        dirs[:] = [d for d in dirs if d not in pastas_excluidas]

        for d in dirs:
            pasta_path = Path(root) / d
            st = pasta_path.stat()
            total_pastas += 1

            pastas_datas.append({
                "criado": datetime.fromtimestamp(st.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
                "modificado": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            })

        for f in files:
            total_arquivos += 1
            ext = Path(f).suffix.lower() or "SEM"
            arquivos_por_extensao[ext] += 1

    return {
        "pastas": total_pastas,
        "arquivos": total_arquivos,
        "extensao": dict(arquivos_por_extensao),
        "datas": pastas_datas,
        "versoes": python_envs
    }

def saudacao_por_hora_sistema() -> str:
    """Retorna uma saudação baseada no horário atual do sistema."""
    from datetime import datetime
    hora = datetime.now().hour

    if 5 <= hora < 12:
        return f"Bom dia {data_sistema('hora')}"
    elif 12 <= hora < 18:
        return f"Boa tarde {data_sistema('hora')}"
    elif 18 <= hora < 23:
        return f"Boa noite {data_sistema('hora')}"
    else:
        return f"Boa madrugada {data_sistema('hora')}"



def ConvE_data(Data):
    from datetime import datetime
    """
    Converte uma data no formato ISO/US (YYYY-MM-DD HH:MM:SS ou só YYYY-MM-DD)
    para uma string no formato brasileiro DD/MM/AAAA.

    Args:
        Data (str): A data a ser convertida, ex.: "2026-05-12 16:05:10" ou "2026-05-12".

    Returns:
        str: A data no formato DD/MM/AAAA.

    Raises:
        ValueError: Se a data fornecida não estiver no formato esperado ou for inválida.
    """
    try:
        # Garante string e remove parte da hora se existir
        data_str = str(Data).strip()
        data_sozinha = data_str.split()[0]  # pega só a parte da data

        # Divide em YYYY-MM-DD
        d = data_sozinha.split("-")
        if len(d) != 3:
            raise ValueError("Formato de data inválido; esperado YYYY-MM-DD")

        ano = d[0]
        mes = d[1]
        dia = d[2]

        # Converte para objeto datetime para validar
        dt = datetime(int(ano), int(mes), int(dia))

        # Retorna no formato brasileiro DD/MM/AAAA
        return f"{dia}/{mes}/{ano}"

    except (IndexError, ValueError, TypeError) as e:
        print(f"Algo errado com a data: {Data} → {e}")
        raise ValueError(f"Data inválida ou no formato incorreto: {Data}")


# ⚠️  função grande (51 linhas)
def mostrar_estrutura(st, dados):
    """Exibe informações formatadas da estrutura analisada no Streamlit."""
    try:
        pastas = dados.get("pastas", 0)
        arquivos = dados.get("arquivos", 0)
        extensoes = dados.get("extensao", {})
        datas = dados.get("datas", [{}])[0] if dados.get("datas") else {}

        # Versão do Python
        versoes = dados.get("versoes", [])
        python_version = "Não detectado"

        if versoes:
            raw = versoes[0]
            if isinstance(raw, dict):
                raw = raw.get("versao", str(raw))
            else:
                raw = str(raw)

            # Limpa strings como "Python 3.14.0", "{'Python 3.14.0'}", etc.
            import re
            match = re.search(r"(\d+\.\d+\.\d+)", raw)
            if match:
                python_version = match.group(1)
            else:
                # fallback
                python_version = raw.strip("[]{}'\" ").replace("Python ", "")

        ext_str = " • ".join(f"{k}({v})" for k, v in extensoes.items())
        criado = ConvE_data(datas.get("criado", "-"))
        modificado = ConvE_data(datas.get("modificado", "-"))

        html = f"""
        <div style="margin-left:10px; margin-bottom:-10px;margin-top:-10px;">
            <p style="margin:8px 0;">
                <strong>🐍-{python_version}</strong> / 
                <strong>{Material('calendario')} Criado:</strong> {criado} &nbsp;&nbsp;&nbsp;
                <strong>Últ.Mod.:</strong> {modificado} <br/>
                <strong>{Material('pasta')}:</strong> {pastas} &nbsp;&nbsp;&nbsp;
                <strong>{Material('documento')}:</strong> {arquivos} &nbsp;&nbsp;&nbsp;
                <strong>{Material('dashboard')}:</strong> {ext_str}
            </p>
        </div>
        """
        #st.html(html)

        return  f"""| 🐍-{python_version} &nbsp;{Material('calendario')} Criado: {criado} Mod.:{modificado} &nbsp;{Material('pasta')}:{pastas} &nbsp;{Material('documento')}:{arquivos}&nbsp; {Material('dashboard')}:{ext_str}"""

    except Exception:
        st.error("Erro ao exibir estrutura")
        st.text(dados)  # fallback


