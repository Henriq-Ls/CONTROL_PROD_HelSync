from typing import Optional,Literal
# def Emoj2(nome: object = 'alerta') -> object:

EmojNome = Literal["alerta", "emergencia", "proibido","escudo","inseto","bosta","merda", "erro", "aviso","arvore" ,"parar", "perigo", "chama", "beijo","folhas", "chorando", "feliz", "olho", "raiva", "rindo", "triste", "arco-íris", "borboleta", "flor", "galinha", "gato", "boi", "cachorro", "leão", "peixe", "rosa", "plantação", "vento", "bolo", "café", "cerveja", "coquetel", "hambúrguer", "pizza", "queijo", "refrigerante", "salada", "sopa", "vinho", "avião", "carro", "ônibus", "trator", "foguete", "computador", "tv", "mouse", "teclado", "celular", "internet", "link", "satélite", "servidor", "terminal", "etiqueta", "robô", "cerebro", "engrenagem", "escrita", "lápis", "pasta", "caneta", "documento", "papel", "impressora", "prancheta", "trabalho", "calculadora", "detetive", "lupa", "ferramentas", "chave inglesa", "manutenção", "martelo", "extintor", "luz", "lampada", "deploy", "pacote", "pergaminho", "atualizar", "reiniciar", "bailarina", "bola futebol", "bola vôlei", "bola basquete", "bola futebolamericano", "bola 8", "neve", "nuvem", "trovoada", "correto", "verificado", "selecionado", "positivo", "ok", "100", "alvo", "circulo branca", "circulo azul", "circulo verde", "circulo roxa", "circulo preta", "circulo amarela", "circulo vermelha", "circulo laranja", "circulo marrom"]

# Literal["choro", "sorriso", "amor",'raiva'] = "",
# ⚠️  função grande (157 linhas)
def Emoj( nome: EmojNome = "", texto: Optional[str] = None, quantidade: Optional[int] = None, help: Optional[str] = None, ) -> str:
	emojis = {
		# Alertas e Segurança
		"alerta": "⚠️",
		"emergencia": "🚑",
		"proibido": "🚫",
		"erro": "❌",
		"aviso": "⛔",
		"parar": "🛑",
		"perigo": "⚡",
		"chama": "🔥",
		"escudo":"🛡️",

		# Emoções e Expressões
		"beijo": "💋",
		"chorando": "😭",
		"feliz": "😄",
		"olho": "👀",
		"raiva": "😡",
		"rindo": "😆",
		"triste": "😔",
		"merda":"💩",
		"bosta":"💩",

		# Natureza
		"flor": "🌻",
		"rosa": "🌹",
		"plantação": "🌾",
		"folhas": "🌿",
		"arvore": "🌳",

		# Clima
		"neve": "❄",
		"nuvem": "☁️",
		"trovoada": "⛈️",
		"vento": "💨",
		"arco-íris": "🌈",

		# Animais
		"borboleta": "🦋",
		"galinha": "🐔",
		"gato": "🐱",
		"boi": "🐄",
		"cachorro": "🐕",
		"leão": "🦁",
		"peixe": "🐠",
		"inseto": "🐜",

		# Comidas e Bebidas
		"bolo": "🍰",
		"café": "☕",
		"cerveja": "🍺",
		"coquetel": "🍹",
		"hambúrguer": "🍔",
		"pizza": "🍕",
		"queijo": "🧀",
		"refrigerante": "🥤",
		"salada": "🥗",
		"sopa": "🍲",
		"vinho": "🍷",

		# Transporte e Viagem
		"avião": "🛫",
		"carro": "🚗",
		"ônibus": "🚌",
		"trator": "🚜",
		"foguete": "🚀",

		# Objetos e Tecnologia
		"computador": "💻",
		"tv": "🖥️",
		"mouse": "🖱️",
		"teclado": "⌨️",
		"celular": "📱",
		"internet": "🌐",
		"link": "🔗",
		"satélite": "🛰️",
		"servidor": "🗄️",
		"terminal": "📟",
		"etiqueta": "🏷️",
		"robô": "🤖",
		"cerebro": "🧠",
		"engrenagem": "⚙️",

		# Escritorio
		"escrita": "📝",
		"lápis": "✏️",
		"pasta": "📁",
		"caneta": "🖊️",
		"documento": "📄",
		"papel": "📃",
		"impressora": "🖨️",
		"prancheta": "📋",
		"trabalho": "💼",
		"calculadora": "🧮",

		# Código e Depuração
		"detetive": "🕵️‍♂️",
		"lupa": "🔍",
		"ferramentas": "🛠️",
		"chave inglesa": "🔧",
		"manutenção": "🏗️",
		"martelo": "🔨",
		"extintor": "🧯",
		"luz": "💡",
		"lampada": "💡",

		# Controle de Versão e Deploy
		"deploy": "🚀",
		"pacote": "📦",
		"pergaminho": "📜",
		"atualizar": "🔄",
		"reiniciar": "♻️",

		# Esportes e Atividades
		"bailarina": "💃",
		"bola futebol": "⚽",
		"bola vôlei": "🏐",
		"bola basquete": "🏀",
		"bola futebolamericano": "🏈",
		"bola 8": "🎱",

		# Correto e Sucesso
		"correto": "✅",
		"verificado": "✔️",
		"selecionado": "☑️",
		"positivo": "👍",
		"ok": "🆗",
		"100": "💯",
		"alvo": "🎯",

		# circulos
	    "circulo branca" :  "⚪",
		"circulo azul" : "🔵",
		"circulo verde" : "🟢",
		"circulo roxa" : "🟣",
		"circulo preta" : "⚫",
		"circulo amarela" : "🟡",
		"circulo vermelha" :  "🔴",
		"circulo laranja" :  "🟠",
		"circulo marrom" :  "🟤",
	}
	ret = []

	if emojis:
		if nome in emojis:
			ret.append(emojis[nome])

		if quantidade:
			ret.append(emojis[nome] * (quantidade-1))

		if texto:
			ret.append(texto)
		return ''.join(ret)

	else:
		return emojis.get(nome.lower(), "Emoji não encontrado")
