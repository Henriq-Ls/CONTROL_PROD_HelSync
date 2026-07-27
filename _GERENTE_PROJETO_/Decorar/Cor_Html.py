from typing import Optional, Literal

Cor = Literal[
	"cinza_fosco",
	"cinza",
	"branco",
	"laranja_fosco",
	"preto",
	"preto_fosco",
	"verde_fosco",
	"azul_escuro",
	"laranja",
	"texto_secundario",
	"vermelho_fosco",
	"amarelo"
]


def Cores(
		nome: Cor = "",
		texto: Optional[str] = None,
		quantidade: Optional[int] = None,
		help: Optional[str] = None,
) -> str:
	cores = {
		"cinza_fosco": "#1A1A1A",
		"branco": "#EAEAEA",
		"laranja_fosco": "#C68642",
		"preto_fosco": "#080808",
		"verde_fosco": "#1FA36B",
		"preto": "#000000",
		"azul_escuro": "#000016",
		"laranja": "#984E00",
		"cinza": "#5E5E5E",
		"texto_secundario": "#9A9A9A",
		"vermelho_fosco": "#B04A4A",
		"amarelo": "#4C3B02",
	}

	ret = []

	if nome:
		cor = cores.get(nome.lower())

		if cor:
			if texto:
				ret.append(texto)
			if quantidade:
				ret.append(cor * quantidade)
			else:
				ret.append(cor)

			return ''.join(ret)
		else:
			return "Cor não encontrada"
	else:
		return "Nome da cor não informado"


def eccor(st):
	col1, col2, col3 = st.columns(3)

	with col1:
		st.color_picker("cinza", Cores("cinza"))
		st.color_picker("branco", Cores("branco"))
		st.color_picker("laranja_fosco", Cores("laranja_fosco"))
		st.color_picker("preto_fosco", Cores("preto_fosco"))

	with col2:
		st.color_picker("preto", Cores("preto"))
		st.color_picker("azul_escuro", Cores("azul_escuro"))
		st.color_picker("laranja", Cores("laranja"))
	with col3:
		st.color_picker("cinza_fosco", Cores("cinza_fosco"))
		st.color_picker("vermelho_fosco", Cores("vermelho_fosco"))
		st.color_picker("amarelo_fosco", Cores("amarelo"))
		st.color_picker("verde_fosco", Cores("verde_fosco"))
