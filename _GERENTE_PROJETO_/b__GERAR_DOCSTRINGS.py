from pathlib import Path

import ast, subprocess, re, os
import os
from pathlib import Path
from dotenv import load_dotenv



load_dotenv(".senhas")

api_key = os.getenv("OPENROUTER_API_KEY")


from _GERENTE_PROJETO_.a__Gerente import Pasta_Raiz, _pastas_nao
PROVEDOR="openrouter" # ── Escolha o provedor: "ollama" ou "openrouter" ──────

# ── Ollama ────────────────────────────────────────────
OLLAMA_EXE=r"C:\Users\henri\AppData\Local\Programs\Ollama\ollama.exe"
OLLAMA_MODELO="llama3.2"

# ── OpenRouter ────────────────────────────────────────
OPENROUTER_API_KEY= api_key
OPENROUTER_MODELO="openai/gpt-4o-mini"

PASTAS_EXCLUIDAS= _pastas_nao()
_RE_ANSI=re.compile(r"\x1b\[[0-9;]*[A-Za-z]|\x08|\r")

def _limpar(t):return _RE_ANSI.sub("",t)
def _parece(t):
    l=t.strip().splitlines()[0].strip() if t.strip() else ""

    return l.startswith(("def ","async def ","class ","import ","from ")) or l.endswith(":")

def _cabecalho(linhas,node):
    ini=node.lineno-1
    fim=node.body[0].lineno-1
    cab=" ".join(l.strip() for l in linhas[ini:fim] if l.strip())

    return re.sub(r"\s+"," ",cab).strip()

def enviar(cab):
    instr=("Gere docstring Google em português.\n"
           'Responda apenas entre """ """\n'
           "Cabeçalho:\n")
    p=instr+cab
    try:
        proc=subprocess.Popen(
            [OLLAMA_EXE,"run",OLLAMA_MODELO],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        out,_=proc.communicate(input=p+"\n",timeout=60)

        return _limpar(out).strip()

    except Exception as e:
        print(f"   ❌ Erro Ollama: {e}")

        return None

def enviar_openrouter(cab):
    try:
        from openai import OpenAI
    except ImportError:
        print("   ❌ Instale openai: pip install openai")
        return None

    instr=("Gere uma docstring no estilo Google em português para a função abaixo.\n"
           'Responda APENAS o conteúdo entre """ """, sem código extra.\n'
           "Cabeçalho:\n")
    try:
        client=OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
        )
        response=client.chat.completions.create(
            model=OPENROUTER_MODELO,
            messages=[
                {"role":"system","content":"Você é um assistente que gera docstrings Python no estilo Google, em português."},
                {"role":"user","content":instr+cab},
            ],
            max_tokens=500,
            temperature=0.3,
            extra_headers={
                "HTTP-Referer":"http://localhost",
                "X-OpenRouter-Title":"BET_HLS_HT",
            },
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"   ❌ Erro OpenRouter: {e}")

        return None

def extrair(r):
    for m in ("```python","```"):r=r.replace(m,"")
    r=r.strip()
    for d in ('"""',"'''"):
        i=r.find(d)
        if i==-1:continue
        f=r.find(d,i+3)
        if f==-1:
            v=[x.strip() for x in r[i+3:].splitlines() if x.strip()]

            return v[0] if v and not _parece(v[0]) else None

        c=r[i+3:f].strip()

        return None if _parece(c) else c

    return r if r and not _parece(r) else None

def montar(c,ind):
    l=c.splitlines()
    if len(l)==1:return ind+f'"""{l[0]}"""\n'
    o=ind+'"""\n'
    for x in l:o+=ind+x+"\n"

    return o+ind+'"""\n'

def processar(path):
    try:
        src=path.read_text(encoding="utf-8")
        tree=ast.parse(src)
    except Exception as e:
        print(f"   ❌ Erro leitura {path.name}: {e}")

        return False

    linhas=src.splitlines(keepends=True)

    # Coleta só os nós que realmente precisam de docstring
    nos=[
        n for n in ast.walk(tree)
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))
        and not ast.get_docstring(n)
        and n.body
    ]

    if not nos:
        return False

    # Ordena de baixo para cima: inserções não deslocam os índices anteriores
    nos.sort(key=lambda n:n.lineno,reverse=True)

    mod=False

    for n in nos:
        nome=n.name
        print(f"   🔍 {nome} — sem docstring, gerando ({PROVEDOR})...")

        cab=_cabecalho(linhas,n)

        if PROVEDOR=="openrouter":
            r=enviar_openrouter(cab)
        else:
            r=enviar(cab)

        if not r:
            print(f"   ⚠️  Pulando {nome} (sem resposta)")
            continue

        c=extrair(r)

        if not c:
            print(f"   ⚠️  Pulando {nome} (conteúdo inválido)")
            continue

        idx=n.body[0].lineno-1
        ind=re.match(r'^(\s*)',linhas[idx]).group(1)

        linhas.insert(idx,montar(c,ind))
        mod=True
        print(f"   ✅ Docstring inserida em {nome}")

    if mod:
        path.write_text("".join(linhas),encoding="utf-8")
        print(f"   💾 Arquivo salvo.")

    return mod

def executar():
    raiz=Path(Pasta_Raiz())
    nome=Path(__file__).name

    arquivos=[]
    for r,d,f in os.walk(raiz):
        d[:]=[x for x in d if x not in PASTAS_EXCLUIDAS]
        for file in f:
            if file.endswith(".py") and file!=nome:
                arquivos.append(Path(r)/file)

    total=len(arquivos)
    print(f"📦 Total de arquivos: {total}")

    for i,p in enumerate(arquivos,1):
        rel=str(p.relative_to(raiz))
        print(f"\n📄 [{i}/{total}] {rel}")
        processar(p)

if __name__=="__main__":
    executar()
