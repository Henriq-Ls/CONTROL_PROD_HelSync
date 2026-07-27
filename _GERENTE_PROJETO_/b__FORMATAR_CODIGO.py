import ast
import os
import re
from collections import Counter
from pathlib import Path

try:
	from _GERENTE_PROJETO_.a__Gerente import Pasta_Raiz, _pastas_nao
except ImportError:
	def Pasta_Raiz():
		return Path(__file__).parent

def _pastas_nao():
    return {"_GERENTE_PROJETO_",".venv", ".idea", ".git", "__pycache__", "venv", "env", ".nox", ".tox",".gitattributes"
            ,".gitignore","INSTALL.txt","LICENSE","README.md","Rascunho.py","Rasc.py","Rasc1.py","VERSION","Html_app.py"
            ,"AS_Imports_Bancos.py","text.txt","","","","","",""}

PASTAS_EXCLUIDAS = _pastas_nao()
LIMITE_LINHAS = 50

# ─────────────────────────────────────────────────────
# Pulo de linha ANTES da palavra-chave
# ─────────────────────────────────────────────────────
PALAVRAS_PULO_LINHA_ANTES: tuple[str, ...] = (
	"return",
	"raise",
	"yield",
)

# ─────────────────────────────────────────────────────
# Pulo de linha DEPOIS da palavra-chave
# ─────────────────────────────────────────────────────
PALAVRAS_PULO_LINHA_DEPOIS: tuple[str, ...] = (
	"return",
	"raise",
	"yield",
)

# ─────────────────────────────────────────────────────
# Módulos da stdlib para ordenação de imports
# ─────────────────────────────────────────────────────
STDLIB_MODULOS: set[str] = {
	"ast", "os", "re", "sys", "io", "abc", "math", "time", "json",
	"copy", "enum", "uuid", "glob", "gzip", "hmac", "html", "http",
	"logging", "pathlib", "random", "shutil", "signal", "socket",
	"string", "struct", "tempfile", "threading", "traceback", "typing",
	"urllib", "warnings", "zipfile", "zlib", "functools", "itertools",
	"operator", "collections", "contextlib", "dataclasses", "datetime",
	"decimal", "fractions", "hashlib", "inspect", "pickle", "platform",
	"pprint", "queue", "readline", "statistics", "subprocess", "textwrap",
	"calendar", "csv", "sqlite3", "unittest", "argparse", "base64",
	"binascii", "bisect", "builtins", "cmath", "code", "codecs",
	"concurrent", "configparser", "ctypes", "dis", "email", "errno",
	"fileinput", "gc", "getopt", "getpass", "heapq", "importlib",
	"keyword", "locale", "multiprocessing", "numbers", "secrets",
	"select", "shelve", "smtplib", "ssl", "stat", "tarfile",
	"timeit", "token", "tokenize", "trace", "types", "venv",
	"wave", "weakref", "webbrowser", "xml", "zipimport",
}

# ─────────────────────────────────────────────────────
# Prefixos que identificam módulos locais do projeto
# ─────────────────────────────────────────────────────
PREFIXOS_LOCAIS: tuple[str, ...] = (
	"_",
	"APP",
)


# ─────────────────────────────────────────────────────
# Etapa 0: inserir nome do arquivo no topo
# ─────────────────────────────────────────────────────
def _inserir_nome_no_topo(path: Path) -> bool:
	"""
	# arquivo.py     ← RAIZ (sem emoji)
	# 📁 pasta/arquivo.py  ← COM PASTA (com emoji)
	"""
	try:
		texto = path.read_text(encoding="utf-8")
	except Exception:
		return False

	raiz = Path(Pasta_Raiz())
	caminho_relativo = path.relative_to(raiz)
	nome_completo = str(caminho_relativo).replace('\\', '/')

	# 🆕 Emoji SÓ se tem pasta (não é raiz)
	if caminho_relativo.parent == Path('.'):
		comentario = f"# {path.name}\n"  # Raiz: sem emoji
	else:
		comentario = f"# 📁 {nome_completo}\n"  # Pasta: com emoji

	# ✅ Ignora se já tem o comentário correto
	if texto.startswith(comentario):
		return False

	# ✅ Remove comentário antigo da primeira linha
	linhas = texto.splitlines(keepends=True)
	if linhas and linhas[0].strip().startswith('#'):
		# Remove se tem nome do arquivo ou emoji antigo
		if path.name in linhas[0] or '📁' in linhas[0]:
			resultado = comentario + ''.join(linhas[1:])
		else:
			resultado = comentario + texto
	else:
		resultado = comentario + texto

	path.write_text(resultado, encoding="utf-8")
	return True

# ─────────────────────────────────────────────────────
# Etapa 1: normalizar cabeçalhos multi-linha
# ─────────────────────────────────────────────────────

def _normalizar_cabecalhos_arquivo(path: Path) -> bool:
	try:
		source = path.read_text(encoding="utf-8")
		tree = ast.parse(source)
	except Exception:
		return False

	linhas = source.splitlines(keepends=True)
	nos = []

	for node in ast.walk(tree):
		if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
			if node.body:
				inicio = node.lineno - 1
				fim = node.body[0].lineno - 1

				if fim - inicio > 1:
					nos.append((inicio, fim))

	if not nos:
		return False

	nos.sort(key=lambda x: x[0], reverse=True)

	for inicio, fim in nos:
		trecho = linhas[inicio:fim]

		primeira = trecho[0] if trecho else ""
		indent = len(primeira) - len(primeira.lstrip())
		indent_str = primeira[:indent]

		linha_unica = " ".join(l.strip() for l in trecho if l.strip())
		linha_unica = indent_str + re.sub(r"\s+", " ", linha_unica).rstrip() + "\n"
		linhas[inicio:fim] = [linha_unica]

	novo = "".join(linhas)

	if novo != source:
		path.write_text(novo, encoding="utf-8")
		return True

	return False


# ─────────────────────────────────────────────────────
# Etapa 2: compactação visual inteligente
# ─────────────────────────────────────────────────────

def _compactar_layout_inteligente(path: Path) -> bool:
	try:
		texto = path.read_text(encoding="utf-8")
	except Exception:
		return False

	original = texto
	linhas = texto.splitlines()
	novas = []

	def eh_vazia(l):
		return not l.strip()

	def eh_palavra_antes(s):
		return any(
			s == kw or s.startswith(kw + " ") or s.startswith(kw + "(")
			for kw in PALAVRAS_PULO_LINHA_ANTES
		)

	def eh_palavra_depois(s):
		return any(
			s == kw or s.startswith(kw + " ") or s.startswith(kw + "(")
			for kw in PALAVRAS_PULO_LINHA_DEPOIS
		)

	i = 0

	while i < len(linhas):
		linha = linhas[i].rstrip()
		strip = linha.strip()

		anterior = linhas[i - 1].strip() if i > 0 else ""
		proxima = linhas[i + 1].strip() if i + 1 < len(linhas) else ""

		# ─────────────────────────────────────────
		# linhas vazias
		# ─────────────────────────────────────────
		if eh_vazia(linha):
			qtd = 1

			while i + qtd < len(linhas) and eh_vazia(linhas[i + qtd]):
				qtd += 1

			anterior_funcao = anterior.startswith((
				"def ", "async def ", "class ", "@",
				"import ", "from "
			))

			proxima_funcao = proxima.startswith((
				"def ", "async def ", "class ", "@",
				"import ", "from "
			))

			dentro_classe = (
					                anterior.startswith(("def ", "async def "))
					                and linhas[i - 1].startswith("    ")
			                ) or (
					                proxima.startswith(("def ", "async def "))
					                and i + 1 < len(linhas)
					                and linhas[i + 1].startswith("    ")
			                )

			comentario_secao = (
					"────" in anterior
					or "────" in proxima
			)

			if anterior_funcao or proxima_funcao:
				novas.append("")
				novas.append("")
			elif dentro_classe:
				novas.append("")
			elif comentario_secao:
				novas.append("")
			else:
				novas.append("")

			i += qtd
			continue

		# ─────────────────────────────────────────
		# compactar imports
		# ─────────────────────────────────────────
		if strip.startswith(("import ", "from ")):
			novas.append(linha)

			j = i + 1

			while j < len(linhas):
				prox = linhas[j].strip()

				if not prox:
					j += 1
					continue

				if prox.startswith(("import ", "from ")):
					novas.append(linhas[j].rstrip())
					j += 1
					continue

				break

			if j < len(linhas):
				prox_real = linhas[j].strip()

				if prox_real.startswith(("def ", "async def ", "class ")):
					novas.append("")

			i = j
			continue

		# ─────────────────────────────────────────
		# remove vazios logo após def/class
		# ─────────────────────────────────────────
		if strip.startswith(("def ", "async def ", "class ")):
			novas.append(linha)

			j = i + 1

			while j < len(linhas) and eh_vazia(linhas[j]):
				j += 1

			i = j
			continue

		# ─────────────────────────────────────────
		# pulo de linha ANTES da palavra-chave
		# ─────────────────────────────────────────
		if eh_palavra_antes(strip) and novas and novas[-1] != "":
			novas.append("")

		novas.append(linha)

		# ─────────────────────────────────────────
		# pulo de linha DEPOIS da palavra-chave
		# ─────────────────────────────────────────
		if eh_palavra_depois(strip) and proxima and not eh_vazia(proxima):
			novas.append("")

		i += 1

	texto_final = "\n".join(novas)
	texto_final = re.sub(r"\n{3,}", "\n\n", texto_final)
	texto_final = re.sub(r"[ \t]+\n", "\n", texto_final)
	texto_final = texto_final.rstrip() + "\n"

	if texto_final != original:
		path.write_text(texto_final, encoding="utf-8")
		return True

	return False


# ─────────────────────────────────────────────────────
# Etapa 3: análise de código
# ─────────────────────────────────────────────────────

def _tem_except_generico_vazio(node) -> bool:
	for sub in ast.walk(node):
		if not isinstance(sub, ast.ExceptHandler):
			continue

		generico = sub.type is None or (
				isinstance(sub.type, ast.Name)
				and sub.type.id in ("Exception", "BaseException")
		)

		if not generico:
			continue

		vazio = all(
			isinstance(s, ast.Pass)
			or (
					isinstance(s, ast.Expr)
					and isinstance(s.value, ast.Constant)
					and s.value.value is ...
			)
			or (
					isinstance(s, ast.Expr)
					and isinstance(s.value, ast.Call)
					and isinstance(s.value.func, ast.Name)
					and s.value.func.id == "print"
			)
			for s in sub.body
		)

		if vazio:
			return True

	return False


def _tem_return_com_valor(node) -> bool:
	for sub in ast.walk(node):
		if isinstance(sub, ast.Return) and sub.value is not None:
			return True

	return False


def _retorno_anotado_nao_none(node) -> bool:
	ret = node.returns

	if ret is None:
		return False

	if isinstance(ret, ast.Constant) and ret.value is None:
		return False

	if isinstance(ret, ast.Name) and ret.id == "None":
		return False

	return True


def _params_str_com_default(node) -> list[tuple[str, str]]:
	resultado = []

	n = len(node.args.defaults)

	pares = list(zip(
		node.args.args[-n:] if n else [],
		node.args.defaults
	))

	pares += [
		(a, d)
		for a, d in zip(node.args.kwonlyargs, node.args.kw_defaults)
		if d is not None
	]

	for arg, default in pares:
		if not isinstance(default, ast.Constant):
			continue

		if not isinstance(default.value, str):
			continue

		if not default.value:
			continue

		tipo = arg.annotation

		if tipo is None or (
				isinstance(tipo, ast.Name)
				and tipo.id == "str"
		):
			resultado.append((arg.arg, default.value))

	return resultado


def _analisar_funcao(node) -> tuple[list[str], list[tuple[str, str]]]:
	avisos = []

	tamanho = node.end_lineno - node.lineno + 1

	if tamanho > LIMITE_LINHAS:
		avisos.append(f"função grande ({tamanho} linhas)")

	if _tem_except_generico_vazio(node):
		avisos.append("except genérico vazio")

	if _retorno_anotado_nao_none(node) and not _tem_return_com_valor(node):
		avisos.append("sem return explícito")

	params_lit = _params_str_com_default(node)

	return avisos, params_lit


def _processar_avisos_arquivo(path: Path) -> int:
	try:
		source = path.read_text(encoding="utf-8")
		tree = ast.parse(source)
	except Exception:
		return 0

	nos = []

	for node in ast.walk(tree):
		if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
			avisos, params_lit = _analisar_funcao(node)

			if avisos or params_lit:
				nos.append((node, avisos, params_lit))

	if not nos:
		return 0

	linhas = source.splitlines(keepends=True)

	nos.sort(key=lambda x: x[0].lineno, reverse=True)

	for node, avisos, params_lit in nos:
		idx = node.lineno - 1

		while idx > 0 and linhas[idx - 1].strip().startswith(("# ⚠️", "# 💡")):
			linhas.pop(idx - 1)
			idx -= 1

		indent = re.match(r"^(\s*)", linhas[idx]).group(1)

		comentarios = []

		if avisos:
			comentarios.append(f"# ⚠️  {' | '.join(avisos)}")

		for nome, valor in params_lit:
			comentarios.append(
				f'# 💡 {nome}_opc = Literal["{valor}"] ← defina os valores válidos'
			)

		for c in reversed(comentarios):
			linhas.insert(idx, indent + c + "\n")

	path.write_text("".join(linhas), encoding="utf-8")

	return len(nos)


# ─────────────────────────────────────────────────────
# Etapa 4: strings repetidas
# ─────────────────────────────────────────────────────

def _coletar_strings(path: Path) -> list[str]:
	try:
		tree = ast.parse(path.read_text(encoding="utf-8"))
	except Exception:
		return []

	return [
		node.value.strip()
		for node in ast.walk(tree)
		if isinstance(node, ast.Constant)
		   and isinstance(node.value, str)
		   and len(node.value.strip()) > 4
	]


def _detectar_strings_repetidas(arquivos: list[Path], minimo: int = 3) -> list[tuple[str, int]]:
	counter: Counter = Counter()

	for path in arquivos:
		counter.update(_coletar_strings(path))

	return [
		(s, n)
		for s, n in counter.most_common(30)
		if n >= minimo
	]


# ─────────────────────────────────────────────────────
# Etapa 5: remover imports não utilizados
# ─────────────────────────────────────────────────────

def _nomes_usados_no_arquivo(tree: ast.Module) -> set[str]:
	usados: set[str] = set()

	for node in ast.walk(tree):
		if isinstance(node, ast.Name):
			usados.add(node.id)
		elif isinstance(node, ast.Attribute):
			n = node
			while isinstance(n, ast.Attribute):
				n = n.value
			if isinstance(n, ast.Name):
				usados.add(n.id)

	return usados


def _remover_imports_nao_usados(path: Path) -> int:
	try:
		source = path.read_text(encoding="utf-8")
		tree = ast.parse(source)
	except Exception:
		return 0

	usados = _nomes_usados_no_arquivo(tree)

	linhas_remover: set[int] = set()

	for node in ast.walk(tree):
		if isinstance(node, ast.Import):
			todos_nao_usados = all(
				# usa o alias se existir, senão o nome raiz do módulo
				(alias.asname if alias.asname else alias.name.split(".")[0]) not in usados
				for alias in node.names
			)

			if todos_nao_usados:
				for ln in range(node.lineno, node.end_lineno + 1):
					linhas_remover.add(ln)

		elif isinstance(node, ast.ImportFrom):
			if any(a.name == "*" for a in node.names):
				continue

			todos_nao_usados = all(
				# usa o alias se existir, senão o próprio nome importado
				(alias.asname if alias.asname else alias.name) not in usados
				for alias in node.names
			)

			if todos_nao_usados:
				for ln in range(node.lineno, node.end_lineno + 1):
					linhas_remover.add(ln)

	if not linhas_remover:
		return 0

	linhas = source.splitlines(keepends=True)
	novas = [
		l for i, l in enumerate(linhas, start=1)
		if i not in linhas_remover
	]

	path.write_text("".join(novas), encoding="utf-8")

	return len(linhas_remover)


# ─────────────────────────────────────────────────────
# Etapa 6: ordenar imports
# ─────────────────────────────────────────────────────

def _coletar_unidades_import(linhas: list[str], inicio: int, fim: int) -> list[list[str]]:
	"""
    Coleta imports como unidades — respeita continuações com \\
    Retorna lista de unidades, onde cada unidade é lista de linhas.
    """
	unidades: list[list[str]] = []
	i = inicio

	while i < fim:
		linha = linhas[i]
		strip = linha.strip()

		if not strip or strip.startswith("#"):
			i += 1
			continue

		if not strip.startswith(("import ", "from ")):
			i += 1
			continue

		# coleta todas as linhas de continuação (terminam com \)
		unidade = [linha]

		while linha.rstrip().endswith("\\") and i + 1 < fim:
			i += 1
			linha = linhas[i]
			unidade.append(linha)

		unidades.append(unidade)
		i += 1

	return unidades


def _modulo_raiz_import(unidade: list[str]) -> str:
	primeira = unidade[0].strip()

	if primeira.startswith("from "):
		return primeira.split()[1].split(".")[0]

	if primeira.startswith("import "):
		return primeira.split()[1].split(".")[0]

	return ""


def _grupo_import(unidade: list[str]) -> int:
	modulo = _modulo_raiz_import(unidade)

	if modulo in STDLIB_MODULOS:
		return 0

	if any(modulo.startswith(p) for p in PREFIXOS_LOCAIS):
		return 2

	return 1


def _ordenar_imports_arquivo(path: Path) -> bool:
	try:
		source = path.read_text(encoding="utf-8")
	except Exception:
		return False

	linhas = source.splitlines(keepends=True)
	n = len(linhas)

	# encontra o início do primeiro bloco de imports
	# (pula linhas em branco e comentários iniciais)
	inicio = 0

	while inicio < n:
		s = linhas[inicio].strip()

		if not s or s.startswith("#"):
			inicio += 1
			continue

		if s.startswith(("import ", "from ")):
			break

		# linha de código antes de qualquer import → nada a ordenar
		return False

	if inicio >= n:
		return False

	# encontra o fim do bloco contíguo de imports
	# para no primeiro código que NÃO é import/comentário/linha vazia
	fim = inicio
	i = inicio

	while i < n:
		s = linhas[i].strip()

		if not s or s.startswith("#"):
			# linha em branco ou comentário: inclui no bloco se o próximo
			# ainda for import, senão para
			j = i + 1
			while j < n and not linhas[j].strip():
				j += 1

			if j < n and linhas[j].strip().startswith(("import ", "from ")):
				i = j
				continue
			else:
				fim = i
				break

		if s.startswith(("import ", "from ")):
			# avança por linhas de continuação
			while linhas[i].rstrip().endswith("\\") and i + 1 < n:
				i += 1
			fim = i + 1
			i += 1
			continue

		# linha de código real (variável, def, etc.) → fim do bloco
		fim = i
		break

	if fim <= inicio:
		return False

	# coleta as unidades de import do bloco
	unidades = _coletar_unidades_import(linhas, inicio, fim)

	if not unidades:
		return False

	# ordena por grupo e depois alfabeticamente
	unidades.sort(key=lambda u: (_grupo_import(u), _modulo_raiz_import(u), u[0].strip()))

	# monta o novo bloco com linha em branco entre grupos
	novo_bloco: list[str] = []
	grupo_atual = -1

	for unidade in unidades:
		g = _grupo_import(unidade)

		if grupo_atual != -1 and g != grupo_atual:
			novo_bloco.append("\n")

		novo_bloco.extend(unidade)
		grupo_atual = g

	# compara com o bloco original
	bloco_original = linhas[inicio:fim]

	if novo_bloco == bloco_original:
		return False

	linhas[inicio:fim] = novo_bloco
	path.write_text("".join(linhas), encoding="utf-8")

	return True


# ─────────────────────────────────────────────────────
# Relatório TXT
# ─────────────────────────────────────────────────────

def _gerar_txt(
				raiz: Path,
				total_arquivos: int,
				norm: int,
				compactados: int,
				avisos_por_arquivo: dict[str, int],
				repetidas: list[tuple[str, int]],
				imports_removidos: dict[str, int],
				imports_ordenados: list[str],
) -> Path:
	sep = "─" * 60
	linhas: list[str] = []

	linhas.append("=" * 60)
	linhas.append("  RELATÓRIO DO PROJETO")
	linhas.append(f"  {raiz}")
	linhas.append("=" * 60)
	linhas.append("")
	linhas.append(f"  Arquivos analisados : {total_arquivos}")
	linhas.append(f"  Cabeçalhos normalizados : {norm}")
	linhas.append(f"  Arquivos compactados : {compactados}")
	linhas.append(f"  Funções com aviso : {sum(avisos_por_arquivo.values())}")
	linhas.append(f"  Imports removidos : {sum(imports_removidos.values())} linha(s)")
	linhas.append(f"  Arquivos com imports ordenados : {len(imports_ordenados)}")
	linhas.append("")

	linhas.append(sep)
	linhas.append("  ETAPA 3 — Avisos em funções")
	linhas.append(sep)

	if avisos_por_arquivo:
		for arq, n in sorted(avisos_por_arquivo.items(), key=lambda x: -x[1]):
			linhas.append(f"  ⚠️  {arq}  →  {n} aviso(s)")
	else:
		linhas.append("  ✅  Nenhum problema detectado.")

	linhas.append("")

	linhas.append(sep)
	linhas.append("  ETAPA 4 — Strings repetidas")
	linhas.append(sep)

	if repetidas:
		linhas.append(f"  {'Vezes':>5}  String")
		linhas.append(f"  {'─' * 5}  {'─' * 50}")

		for s, n in repetidas:
			s_limpa = s[:70].replace("\n", "↵")
			linhas.append(f'  {n:>5}x  "{s_limpa}"')
	else:
		linhas.append("  ✅  Nenhuma string repetida.")

	linhas.append("")

	linhas.append(sep)
	linhas.append("  ETAPA 5 — Imports não utilizados removidos")
	linhas.append(sep)

	if imports_removidos:
		for arq, n in imports_removidos.items():
			linhas.append(f"  ✂️   {arq}  →  {n} linha(s) removida(s)")
	else:
		linhas.append("  ✅  Nenhum import não utilizado.")

	linhas.append("")

	linhas.append(sep)
	linhas.append("  ETAPA 6 — Imports ordenados")
	linhas.append(sep)

	if imports_ordenados:
		for arq in imports_ordenados:
			linhas.append(f"  🔀  {arq}")
	else:
		linhas.append("  ✅  Imports já estavam ordenados.")

	linhas.append("")
	linhas.append("=" * 60)
	linhas.append("  Análise concluída!")
	linhas.append("=" * 60)

	saida = raiz / "relatorio_codigo.txt"
	saida.write_text("\n".join(linhas), encoding="utf-8")

	return saida


# ─────────────────────────────────────────────────────
# Principal
# ─────────────────────────────────────────────────────

def analisar_projeto():
	raiz = Path(Pasta_Raiz())
	nome_este_script = Path(__file__).name

	arquivos: list[Path] = []

	for root, dirs, files in os.walk(raiz):
		dirs[:] = [d for d in dirs if d not in PASTAS_EXCLUIDAS]

		for file in files:
			if file.endswith(".py") and file != nome_este_script:
				arquivos.append(Path(root) / file)

	total = len(arquivos)

	print(f"📁 {total} arquivo(s) encontrado(s)\n")

	# ─────────────────────────────────────────
	# Etapa 0
	# ─────────────────────────────────────────

	print("🏷️  Etapa 0: inserindo nome no topo dos arquivos...")

	nomes_inseridos = 0

	for path in arquivos:
		if _inserir_nome_no_topo(path):
			print(f"   🏷️  {path.relative_to(raiz)}")
			nomes_inseridos += 1

	print(f"   → {nomes_inseridos} arquivo(s) atualizado(s)\n")

	# ─────────────────────────────────────────
	# Etapa 1
	# ─────────────────────────────────────────

	print("🔧 Etapa 1: normalizando cabeçalhos...")

	norm = 0

	for path in arquivos:
		if _normalizar_cabecalhos_arquivo(path):
			print(f"   📐 {path.relative_to(raiz)}")
			norm += 1

	print(f"   → {norm} arquivo(s) normalizado(s)\n")

	# ─────────────────────────────────────────
	# Etapa 2
	# ─────────────────────────────────────────

	print("🧹 Etapa 2: compactando layout inteligente...")

	compactados = 0

	for path in arquivos:
		if _compactar_layout_inteligente(path):
			print(f"   📦 {path.relative_to(raiz)}")
			compactados += 1

	print(f"   → {compactados} arquivo(s) compactado(s)\n")

	# ─────────────────────────────────────────
	# Etapa 3
	# ─────────────────────────────────────────

	print("🔍 Etapa 3: analisando funções...")

	avisos_por_arquivo: dict[str, int] = {}

	for path in arquivos:
		n = _processar_avisos_arquivo(path)

		if n:
			chave = str(path.relative_to(raiz))
			avisos_por_arquivo[chave] = n
			print(f"   ⚠️ {chave} — {n} função(ões)")

	if not avisos_por_arquivo:
		print("   ✅ Nenhum problema detectado.")

	print(f"   → {sum(avisos_por_arquivo.values())} função(ões) com aviso(s)\n")

	# ─────────────────────────────────────────
	# Etapa 4
	# ─────────────────────────────────────────

	print("🔁 Etapa 4: detectando strings repetidas...")

	repetidas = _detectar_strings_repetidas(arquivos)

	if repetidas:
		print(f"   {'Vezes':>5}  String")
		print(f"   {'─' * 5}  {'─' * 60}")

		for s, n in repetidas:
			print(f'   {n:>5}x  "{s[:80]}"')
	else:
		print("   ✅ Nenhuma string repetida.")

	print()

	# ─────────────────────────────────────────
	# Etapa 5
	# ─────────────────────────────────────────

	print("🗑️  Etapa 5: removendo imports não utilizados...")

	imports_removidos: dict[str, int] = {}

	for path in arquivos:
		n = _remover_imports_nao_usados(path)

		if n:
			chave = str(path.relative_to(raiz))
			imports_removidos[chave] = n
			print(f"   ✂️  {chave} — {n} linha(s) removida(s)")

	if not imports_removidos:
		print("   ✅ Nenhum import não utilizado.")

	print()

	# ─────────────────────────────────────────
	# Etapa 6
	# ─────────────────────────────────────────

	print("📦 Etapa 6: ordenando imports...")

	imports_ordenados: list[str] = []

	for path in arquivos:
		if _ordenar_imports_arquivo(path):
			chave = str(path.relative_to(raiz))
			imports_ordenados.append(chave)
			print(f"   🔀 {chave}")

	if not imports_ordenados:
		print("   ✅ Imports já estavam ordenados.")

	print()

	# ─────────────────────────────────────────
	# Relatório TXT
	# ─────────────────────────────────────────

	print("📄 Gerando relatório...")

	txt_path = _gerar_txt(
		raiz=raiz,
		total_arquivos=total,
		norm=norm,
		compactados=compactados,
		avisos_por_arquivo=avisos_por_arquivo,
		repetidas=repetidas,
		imports_removidos=imports_removidos,
		imports_ordenados=imports_ordenados,
	)

	print(f"   ✅ Salvo em: {txt_path}\n")
	print("🎉 Análise concluída!")



analisar_projeto()