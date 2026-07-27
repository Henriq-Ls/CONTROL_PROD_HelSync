# 📁 _IAS_/OpenRouter.py
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
# ====================== CONFIGURAÇÃO ======================
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / "_GERENTE_PROJETO_" / ".senhas"

load_dotenv(ENV_FILE)

api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:

    raise ValueError("❌ OPENROUTER_API_KEY não encontrada no .senhas")

# ====================== CLIENTE ======================
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
)

# ====================== FUNÇÃO ======================
# 💡 modelo_opc = Literal["openai/gpt-4o-mini"] ← defina os valores válidos
def ChatOpenRouter( pergunta: str, modelo: str = "openai/gpt-4o-mini", temperatura: float = 0.7 ) -> str:
    """
    Executa uma consulta ao modelo de linguagem ChatOpenRouter.

    Esta função envia uma pergunta para o modelo especificado e retorna a resposta gerada.

    Args:
        pergunta (str): A pergunta a ser enviada ao modelo.
        modelo (str, opcional): O modelo a ser utilizado para gerar a resposta. O padrão é "openai/gpt-4o-mini".
        temperatura (float, opcional): O nível de aleatoriedade da resposta gerada. O padrão é 0.7.

    Returns:
        str: A resposta gerada pelo modelo para a pergunta fornecida.
    """
    try:
        response = client.chat.completions.create(
            model=modelo,
            messages=[
                {"role": "system", "content": "Você é um assistente útil, direto e responde em português."},
                {"role": "user", "content": pergunta}
            ],
            max_tokens=1500,
            temperature=temperatura,
            extra_headers={
                "HTTP-Referer": "http://localhost",
                "X-OpenRouter-Title": "CONTROLE_PRODUTOS_HelSync",
            }
        )

        return response.choices[0].message.content.strip()

    except Exception as e:

        return f"❌ Erro ao chamar a API: {str(e)}"
