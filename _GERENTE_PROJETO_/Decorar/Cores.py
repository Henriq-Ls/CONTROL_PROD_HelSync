from typing import Optional, Literal
Nomes = Literal[
    "vermelho", "vermelho sublinhado", "vermelho negatigo", "vermelho fundo",
    "branco", "branco sublinhado", "branco negatigo", "branco fundo",
    "verde", "verde sublinhado", "verde negatigo", "verde fundo",
    "amarelo", "amarelo sublinhado", "amarelo negatigo", "amarelo fundo",
    "azul", "azul sublinhado", "azul negatigo", "azul fundo",
    "roxo", "roxo sublinhado", "roxo negatigo", "roxo fundo",
    "cinza", "cinza sublinhado", "cinza negatigo", "cinza fundo",
    "ciano", "ciano sublinhado", "ciano negatigo", "ciano fundo",
    "italico"
]

def Cor( nome: Nomes, variavel: str = '', quantidade: Optional[int] = None, help: Optional[str] = None ) -> str:
    cor = {
        "vermelho": f'\033[1;31m{variavel}\033[m',
        "vermelho sublinhado": f'\033[4;31m{variavel}\033[m',
        "vermelho negatigo": f'\033[7;31m{variavel}\033[m',
        "vermelho fundo": f'\033[41m{variavel}\033[m',

        "branco": f'\033[1;30m{variavel}\033[m',
        "branco sublinhado": f'\033[4;30m{variavel}\033[m',
        "branco negatigo": f'\033[7;30m{variavel}\033[m',
        "branco fundo": f'\033[40m{variavel}\033[m',

        "verde": f'\033[1;32m{variavel}\033[m',
        "verde sublinhado": f'\033[4;32m{variavel}\033[m',
        "verde negatigo": f'\033[7;32m{variavel}\033[m',
        "verde fundo": f'\033[42m{variavel}\033[m',

        "amarelo": f'\033[1;33m{variavel}\033[m',
        "amarelo sublinhado": f'\033[4;33m{variavel}\033[m',
        "amarelo negatigo": f'\033[7;33m{variavel}\033[m',
        "amarelo fundo": f'\033[43m{variavel}\033[m',

        "azul": f'\033[1;34m{variavel}\033[m',
        "azul sublinhado": f'\033[4;34m{variavel}\033[m',
        "azul negatigo": f'\033[7;34m{variavel}\033[m',
        "azul fundo": f'\033[44m{variavel}\033[m',

        "roxo": f'\033[1;35m{variavel}\033[m',
        "roxo sublinhado": f'\033[4;35m{variavel}\033[m',
        "roxo negatigo": f'\033[7;35m{variavel}\033[m',
        "roxo fundo": f'\033[45m{variavel}\033[m',

        "cinza": f'\033[0;90m{variavel}\033[m',
        "cinza sublinhado": f'\033[4;90m{variavel}\033[m',
        "cinza negatigo": f'\033[7;90m{variavel}\033[m',
        "cinza fundo": f'\033[90m{variavel}\033[m',

        "ciano": f'\033[1;36m{variavel}\033[m',
        "ciano sublinhado": f'\033[4;36m{variavel}\033[m',
        "ciano negatigo": f'\033[7;36m{variavel}\033[m',
        "ciano fundo": f'\033[46m{variavel}\033[m',

        "italico": f'\033[3m{variavel}\033[m',
    }

    return cor.get(nome.lower(), "Cor não encontrada")
