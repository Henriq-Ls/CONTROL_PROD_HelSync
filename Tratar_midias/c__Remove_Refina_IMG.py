# 📁 Tratar_midias/c__Remove_Refina_IMG.py
import concurrent.futures
import os
from pathlib import Path
import time

import cv2
import numpy as np
from rembg import remove, new_session
import torch
import torch.nn.functional as F
import torchvision.transforms.functional as TF
EXTENSOES = (".jpg", ".jpeg", ".png", ".webp")
MAX_RESOLUCAO = 2000
MODELO_REMBG = "isnet-general-use"
WORKERS = 4

if not torch.cuda.is_available():

    raise RuntimeError("PyTorch não achou o CUDA! Instalação do torch está só para CPU.")

device = torch.device("cuda")

print("Carregando ONNX na GPU...")
provedores_gpu = ["CUDAExecutionProvider", "CPUExecutionProvider"]
sessao = new_session(MODELO_REMBG, providers=provedores_gpu)

def refinar_borda_gpu_pytorch(alpha_numpy, erode_kernel=7, blur_kernel=5):
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
        cv2.imwrite(caminho_salvar, img_final_bgra, [cv2.IMWRITE_PNG_COMPRESSION, 1])

        return f"✅ {nome_png}"

    except Exception as e:

        return f"❌ Erro em {caminho.name}: {e}"

def Remove_IMG(pasta_entrada, pasta_saida):
    pasta_entrada = Path(pasta_entrada)
    pasta_saida = Path(pasta_saida)
    pasta_saida.mkdir(parents=True, exist_ok=True)

    arquivos = sorted([a for a in os.listdir(pasta_entrada) if a.lower().endswith(EXTENSOES)])
    caminhos = [pasta_entrada / arq for arq in arquivos]

    print(f"\n{'='*60}")
    print(f"🔥 MODO EXTREME GPU (PyTorch+ONNX+OpenCV) — {len(arquivos)} imgs")
    print(f"{'='*60}")

    tempo_inicio = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futuros = {executor.submit(processar_imagem, cam, pasta_saida): cam for cam in caminhos}
        for futuro in concurrent.futures.as_completed(futuros):
            print(futuro.result())

    tempo_total = time.time() - tempo_inicio
    print(f"\n⚡ FINALIZADO! {len(arquivos)} imagens em {tempo_total:.2f} segundos.")
    if len(arquivos) > 0:
        print(f"Média: {tempo_total / len(arquivos):.3f}s por imagem.")

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
