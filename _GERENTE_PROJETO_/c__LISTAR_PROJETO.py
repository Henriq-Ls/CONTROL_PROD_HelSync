import ast
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from _IAS_.OpenRouter import ChatOpenRouter

try:
    from _GERENTE_PROJETO_.a__Gerente import Pasta_Raiz, _pastas_nao
except ImportError:
    def Pasta_Raiz():
        return Path(__file__).parent


PASTAS_EXCLUIDAS = _pastas_nao()
ARQUIVO_SAIDA = "docstrings_relatorio.txt"

VERBOSE = True


# ─────────────────────────────────────────────────────
# Logger com timestamp
# ─────────────────────────────────────────────────────

def log(msg: str) -> None:
    if VERBOSE:
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {msg}")



def enviar_resumo(conteudo: str, nome_arquivo: str) -> str | None:
    prompt = (
        "Explique o que esse arquivo Python faz de forma objetiva.\n"
        "Não cite código.\n\n"
        "Arquivo:\n"
    ) + conteudo[:12000]

    log(f"  → Enviando para IA: {nome_arquivo}")

    try:
        resultado = ChatOpenRouter(prompt)

        if resultado.startswith("❌"):
            log(f"  ⚠️  IA retornou erro ({nome_arquivo}): {resultado}")
            return None

        log(f"  ✅ Resumo recebido ({len(resultado)} chars)")
        return resultado or None

    except Exception as e:
        log(f"  ⚠️  Falha inesperada na IA ({nome_arquivo}): {e}")
        return None
# ─────────────────────────────────────────────────────
# AST: coleta funções e classes
# ─────────────────────────────────────────────────────

def coletar_nos(tree: ast.AST) -> list:
    nos = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]
    return sorted(nos, key=lambda n: n.lineno)


def tipo_no(node) -> str:
    if isinstance(node, ast.ClassDef):
        return "classe"
    if isinstance(node, ast.AsyncFunctionDef):
        return "async def"
    return "def"


# ─────────────────────────────────────────────────────
# Principal
# ─────────────────────────────────────────────────────

def executar() -> None:
    log("INICIANDO SCRIPT")

    raiz = Path(Pasta_Raiz())
    nome_este_script = Path(__file__).name
    log(f"Raiz do projeto: {raiz}")

    # ── Coleta de arquivos ──────────────────────────
    log("Varrendo arquivos do projeto...")

    arquivos: list[Path] = []
    for root, dirs, files in os.walk(raiz):
        dirs[:] = [d for d in dirs if d not in PASTAS_EXCLUIDAS]
        for file in files:
            if file.endswith(".py") and file != nome_este_script:
                arquivos.append(Path(root) / file)

    total = len(arquivos)
    log(f"Arquivos encontrados: {total}")

    if total == 0:
        log("Nenhum arquivo .py encontrado. Encerrando.")
        return

    # ── Processamento ───────────────────────────────
    linhas: list[str] = []
    falhos: list[Path] = []

    for i, path in enumerate(arquivos, 1):
        log(f"Processando [{i}/{total}]: {path.relative_to(raiz)}")

        try:
            src = path.read_text(encoding="utf-8")
            tree = ast.parse(src)
        except Exception as e:
            log(f"  ⛔ Falha ao ler/parsear: {e}")
            falhos.append(path)
            continue

        resumo = enviar_resumo(src, path.name)

        # Cabeçalho do arquivo
        linhas.append("")
        linhas.append("=" * 70)
        linhas.append(f"ARQUIVO: {path.relative_to(raiz)}")
        linhas.append("=" * 70)

        if resumo:
            linhas.append("")
            linhas.append("RESUMO IA:")
            linhas.append(resumo)
        else:
            linhas.append("")
            linhas.append("RESUMO IA: (não disponível)")

        # Funções e classes
        nos = coletar_nos(tree)
        if nos:
            linhas.append("")
            linhas.append(f"ESTRUTURA ({len(nos)} item(s)):")

            for node in nos:
                indent = "  " if getattr(node, "col_offset", 0) > 0 else ""
                doc = ast.get_docstring(node)
                linhas.append(f"{indent}- [{tipo_no(node)}] {node.name}  (linha {node.lineno})")
                if doc:
                    primeira_linha = doc.splitlines()[0].strip()
                    linhas.append(f'{indent}    "{primeira_linha}"')
        else:
            linhas.append("")
            linhas.append("ESTRUTURA: (nenhuma função ou classe encontrada)")

        linhas.append("")

    # ── Rodapé de falhas ────────────────────────────
    if falhos:
        linhas.append("=" * 70)
        linhas.append(f"ARQUIVOS COM FALHA DE PARSE ({len(falhos)}):")
        for f in falhos:
            linhas.append(f"  - {f.relative_to(raiz)}")
        linhas.append("")

    # ── Salva relatório ─────────────────────────────
    saida = raiz / ARQUIVO_SAIDA
    log(f"Salvando relatório em: {saida}")

    saida.write_text("\n".join(linhas), encoding="utf-8")

    log(f"Relatório gerado: {saida}")
    log(f"FINALIZADO — {total - len(falhos)}/{total} arquivo(s) processado(s)")


if __name__ == "__main__":
    executar()
