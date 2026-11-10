# 📁 Tratar_midias/c__Remove_Refina_IMG.py
import os
from pathlib import Path
import time
from typing import Callable

import cv2
import numpy as np
from rembg import remove, new_session

try:
    import torch
    import torch.nn.functional as F
    import torchvision.transforms.functional as TF
except Exception as exc:
    torch = None
    F = None
    TF = None
    TORCH_IMPORT_ERROR = exc
else:
    TORCH_IMPORT_ERROR = None

EXTENSOES = (".jpg", ".jpeg", ".png", ".webp")
MAX_RESOLUCAO = 2000
MODELO_REMBG = "isnet-general-use"

MODO_GPU = False
device = None
sessao = None

if torch is not None:
    try:
        if torch.cuda.is_available():
            device = torch.device("cuda")
            print("Carregando ONNX na GPU...")
            provedores_gpu = ["CUDAExecutionProvider", "CPUExecutionProvider"]
            sessao = new_session(MODELO_REMBG, providers=provedores_gpu)
            MODO_GPU = True
    except Exception as exc:
        print(f"GPU indisponível; usando CPU para remover fundos: {exc}")
elif TORCH_IMPORT_ERROR is not None:
    print(
        "PyTorch/CUDA indisponível; usando CPU para remover fundos: "
        f"{TORCH_IMPORT_ERROR}"
    )

if sessao is None:
    print("Carregando ONNX na CPU...")
    sessao = new_session(MODELO_REMBG, providers=["CPUExecutionProvider"])

def refinar_borda_gpu_pytorch(alpha_numpy, erode_kernel=7, blur_kernel=5):
    if not MODO_GPU:
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (erode_kernel, erode_kernel),
        )
        refinada = cv2.erode(alpha_numpy, kernel, iterations=1)
        return cv2.GaussianBlur(
            refinada,
            (blur_kernel, blur_kernel),
            0,
        )

    with torch.no_grad():
        alpha_tensor = torch.from_numpy(alpha_numpy).float().to(device) / 255.0
        alpha_tensor = alpha_tensor.unsqueeze(0).unsqueeze(0)
        pad = erode_kernel // 2
        alpha_tensor = -F.max_pool2d(-alpha_tensor, kernel_size=erode_kernel, stride=1, padding=pad)
        alpha_tensor = TF.gaussian_blur(alpha_tensor, kernel_size=[blur_kernel, blur_kernel])
        alpha_tensor = alpha_tensor.squeeze()

        return (alpha_tensor.cpu().numpy() * 255).clip(0, 255).astype(np.uint8)

def processar_imagem(caminho, pasta_saida):
    try:
        img = cv2.imread(str(caminho))
        if img is None:

            return f"❌ Imagem corrompida: {caminho.name}"

        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w = img.shape[:2]

        if max(h, w) > MAX_RESOLUCAO:
            escala = MAX_RESOLUCAO / float(max(h, w))
            novo_w, novo_h = int(w * escala), int(h * escala)
            img = cv2.resize(img, (novo_w, novo_h), interpolation=cv2.INTER_AREA)

        img_sem_fundo = remove(img, session=sessao, alpha_matting=False)

        rgb_channels = img_sem_fundo[:, :, :3]
        alpha_channel = img_sem_fundo[:, :, 3]
        alpha_channel = refinar_borda_gpu_pytorch(alpha_channel, erode_kernel=9, blur_kernel=5)

        img_final = np.dstack((rgb_channels, alpha_channel))
        img_final_bgra = cv2.cvtColor(img_final, cv2.COLOR_RGBA2BGRA)

        nome_png = caminho.stem + ".png"
        caminho_salvar = str(pasta_saida / nome_png)
        if not cv2.imwrite(
            caminho_salvar,
            img_final_bgra,
            [cv2.IMWRITE_PNG_COMPRESSION, 1],
        ):
            return f"❌ Não foi possível salvar: {nome_png}"

        return f"✅ {nome_png}"

    except Exception as e:

        return f"❌ Erro em {caminho.name}: {e}"

def Remove_IMG(
    pasta_entrada,
    pasta_saida,
    progress: Callable[[str], None] | None = None,
):
    pasta_entrada = Path(pasta_entrada)
    pasta_saida = Path(pasta_saida)

    arquivos = sorted(
        arquivo
        for arquivo in os.listdir(pasta_entrada)
        if arquivo.lower().endswith(EXTENSOES)
        and (pasta_entrada / arquivo).is_file()
    )
    caminhos = [pasta_entrada / arq for arq in arquivos]
    if not caminhos:
        mensagem = (
            f"Nenhuma imagem válida encontrada em {pasta_entrada}; "
            "a remoção de fundo foi interrompida."
        )
        if progress:
            progress(f"AVISO: {mensagem}")
        raise ValueError(mensagem)

    pasta_saida.mkdir(parents=True, exist_ok=True)

    if progress:
        progress(f"Pasta sem fundo pronta: {pasta_saida}")
        progress(f"Removendo fundo de {len(arquivos)} imagem(ns)...")

    print(f"\n{'='*60}")
    print(f"Remoção com rembg/ONNX — {len(arquivos)} imagem(ns)")
    print(f"{'='*60}")

    tempo_inicio = time.time()
    falhas = 0
    # A sessão ONNX é compartilhada; uma imagem por vez evita concorrência
    # na inferência e permite informar qual arquivo está sendo processado.
    for indice, caminho in enumerate(caminhos, start=1):
        destino = pasta_saida / f"{caminho.stem}.png"
        if destino.is_file():
            resultado = f"⏭️ {destino.name} já existe; arquivo mantido sem sobrescrever."
            print(resultado)
            if progress:
                progress(f"Sem fundo {indice}/{len(caminhos)}: {resultado}")
            continue

        if progress:
            progress(
                f"Processando imagem {indice}/{len(caminhos)}: {caminho.name}"
            )
        inicio_imagem = time.time()
        resultado = processar_imagem(caminho, pasta_saida)
        duracao = time.time() - inicio_imagem
        print(resultado)
        if resultado.startswith("❌"):
            falhas += 1
        if progress:
            progress(
                f"Sem fundo {indice}/{len(caminhos)} "
                f"({duracao:.1f}s): {resultado}"
            )

    tempo_total = time.time() - tempo_inicio
    print(f"\n⚡ FINALIZADO! {len(arquivos)} imagens em {tempo_total:.2f} segundos.")
    if len(arquivos) > 0:
        print(f"Média: {tempo_total / len(arquivos):.3f}s por imagem.")
    if progress:
        if falhas:
            progress(
                f"Remoção de fundo encerrada com {falhas} erro(s); "
                f"confira as mensagens por imagem. Pasta: {pasta_saida}"
            )
        else:
            progress(f"Pasta sem fundo concluída: {pasta_saida}")

    return str(pasta_saida)

r'''if __name__ == "__main__":
    pasta_in = r"C:\Users\henri\Downloads\PRODUTOS\CANETAS\Ajuste_Geral"
    pasta_out = r"C:\Users\henri\Downloads\PRODUTOS\CANETAS\03 - Sem Fundo"
    Remove_IMG(
        pasta_in,
        pasta_out
    )'''

'''
python .\Tratar_midias\c__Remove_Refina_IMG.py
'''
