# 📁 _IAS_/Ollama.py
import subprocess
from typing import Literal
'''
ollama list
NAME               ID              SIZE      MODIFIED
llama3.2:3b        a80c4f17acd5    2.0 GB    2 months ago
codellama:7b       8fdf8f752f6e    3.8 GB    3 months ago
gemma3:1b          8648f39daa8f    815 MB    4 months ago
'''

opc = Literal["gemma3:1b","llama3.2:3b","codellama:7b"]

# 💡 prompt_opc = Literal[""]  ← defina os valores possíveis para prompt
def enviar_prompt(prompt:str,modelo:opc="gemma3:1b")->str:
    """Envia um prompt para o modelo Ollama e retorna a resposta.
    ollama list
NAME               ID              SIZE      MODIFIED
llama3.2:3b        a80c4f17acd5    2.0 GB    2 months ago
codellama:7b       8fdf8f752f6e    3.8 GB    3 months ago
gemma3:1b          8648f39daa8f    815 MB    4 months ago
"""
    try:
        instrucoes = "Responda de forma curta, direta e objetiva. Sem explicações longas.\n"
        prompt_final = instrucoes + prompt.strip()

        processo = subprocess.Popen( [r"C:\Users\henri\AppData\Local\Programs\Ollama\ollama.exe", "run", F"{opc}"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            creationflags=subprocess.CREATE_NO_WINDOW)
        stdout, stderr = processo.communicate(input=prompt_final + "\n")

        return stdout.strip()

    except Exception as e:
        print("Erro:", str(e))

        return None
