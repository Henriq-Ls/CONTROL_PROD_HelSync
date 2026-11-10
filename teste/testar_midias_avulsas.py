"""Testes isolados para destinos avulsos e detecção de medidas.

Execute da raiz de hen-place-control:
    python teste/testar_midias_avulsas.py

Os processadores de imagem/vídeo e a UI não são iniciados. Dependências externas
são substituídas por doubles para validar caminhos e fallback.
"""

from __future__ import annotations

import ast
import importlib.util
import io
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


PROJETO = Path(__file__).resolve().parents[1]
PROCESSOR_PATH = (
    PROJETO
    / "_APP_"
    / "Cadastro"
    / "Medidas_Avulsas"
    / "processor.py"
)
MEDIDAS_PATH = PROJETO / "Tratar_midias" / "f__Medidas_Graficos.py"


def _carregar_processor():
    spec = importlib.util.spec_from_file_location(
        "_processor_midias_avulsas_test",
        PROCESSOR_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Não foi possível carregar {PROCESSOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _modulo_pacote(nome: str) -> types.ModuleType:
    module = types.ModuleType(nome)
    module.__path__ = []
    return module


class _ImagemFake:
    def __init__(self, caminho: str | Path):
        self.caminho = Path(caminho)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def convert(self, _modo: str):
        return self

    def save(self, caminho: str | Path):
        Path(caminho).write_bytes(b"imagem-de-teste")


def _modulos_pil_falsos():
    pil = _modulo_pacote("PIL")
    image = types.ModuleType("PIL.Image")
    image.open = lambda caminho: _ImagemFake(caminho)
    image_ops = types.ModuleType("PIL.ImageOps")
    image_ops.exif_transpose = lambda imagem: imagem
    pil.Image = image
    pil.ImageOps = image_ops
    return {
        "PIL": pil,
        "PIL.Image": image,
        "PIL.ImageOps": image_ops,
    }


def _modulos_tratar_falsos():
    pacote = _modulo_pacote("Tratar_midias")

    ajuste = types.ModuleType("Tratar_midias.b__Ajuste_Geral_IMG")

    def ajustar(entrada: str, saida: str):
        for source in Path(entrada).iterdir():
            shutil.copy2(source, Path(saida) / source.name)

    ajuste.Ajuste_IMG = ajustar

    remove = types.ModuleType("Tratar_midias.c__Remove_Refina_IMG")

    def remover(entrada: str, saida: str, progress=None):
        for source in Path(entrada).iterdir():
            (Path(saida) / f"{source.stem}.png").write_bytes(b"sem-fundo")

    remove.Remove_IMG = remover

    medidas = types.ModuleType("Tratar_midias.f__Medidas_Graficos")

    def colocar_medidas(entrada: str, saida: str, _kit, _tipo, progress=None):
        for source in Path(entrada).iterdir():
            (Path(saida) / f"{source.stem}.jpg").write_bytes(b"com-medidas")

    medidas.Colocar_medidas = colocar_medidas
    return {
        "Tratar_midias": pacote,
        "Tratar_midias.b__Ajuste_Geral_IMG": ajuste,
        "Tratar_midias.c__Remove_Refina_IMG": remove,
        "Tratar_midias.f__Medidas_Graficos": medidas,
    }


def _carregar_funcoes_bbox(namespace: dict):
    tree = ast.parse(MEDIDAS_PATH.read_text(encoding="utf-8"))
    nomes = {
        "_sessao_cpu_medidas",
        "_erro_memoria_gpu",
        "_mascara_para_bbox",
        "detectar_bbox",
    }
    funcoes = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in nomes
    ]
    if {node.name for node in funcoes} != nomes:
        raise RuntimeError("Funções de detecção de medidas ausentes.")
    module = ast.Module(body=funcoes, type_ignores=[])
    ast.fix_missing_locations(module)
    exec(compile(module, str(MEDIDAS_PATH), "exec"), namespace)
    return namespace


class TestarMidiasAvulsas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.processor = _carregar_processor()

    def test_imagens_sao_separadas_na_pasta_h_avulsas(self):
        with tempfile.TemporaryDirectory() as temporary:
            raiz = Path(temporary)
            destino = raiz / "produto"
            destino.mkdir()
            imagem = raiz / "foto.jpg"
            imagem.write_bytes(b"original-intacto")

            with (
                patch.dict(
                    sys.modules,
                    {
                        **_modulos_pil_falsos(),
                        **_modulos_tratar_falsos(),
                    },
                ),
                patch.object(
                    self.processor,
                    "_compor_fundo_branco",
                    side_effect=lambda source, target: Path(target).write_bytes(
                        Path(source).read_bytes()
                    ),
                ),
            ):
                saidas = self.processor.processar_imagens_avulsas(
                    [str(imagem)],
                    str(destino),
                    "30",
                    "20",
                    "2",
                    "400",
                    "alt x larg x esp",
                )

            raiz_avulsas = destino / "H_Arq_avulsas"
            self.assertEqual(len(saidas), 3)
            self.assertTrue(all(Path(path).is_file() for path in saidas))
            self.assertTrue(
                all(raiz_avulsas in Path(path).parents for path in saidas)
            )
            self.assertEqual(imagem.read_bytes(), b"original-intacto")
            self.assertEqual(
                {Path(path).parent.name for path in saidas},
                {"b_sem_fundo", "c_fundo_branco", "d_medidas"},
            )

    def test_video_fica_em_h_avulsas_e_nao_substitui_arquivo_existente(self):
        with tempfile.TemporaryDirectory() as temporary:
            raiz = Path(temporary)
            destino = raiz / "produto"
            destino.mkdir()
            video = raiz / "video original.mp4"
            video.write_bytes(b"video-original")

            appdata = types.SimpleNamespace(
                inicializar=lambda: None,
                listar_midias=lambda _categoria: [],
                ler_config=lambda: {},
            )
            appdata_module = types.ModuleType("_APPDATA_")
            appdata_module.appdata = appdata

            conversor = types.ModuleType("Tratar_midias.v__Converter_video")

            def converter(**kwargs):
                saida = Path(kwargs["pasta_video"]) / (
                    f"video_{kwargs['ref']}.mp4"
                )
                saida.write_bytes(b"video-convertido")
                return True

            conversor.Converte_Video_Completo = converter
            modules = {
                **_modulos_tratar_falsos(),
                "_APPDATA_": appdata_module,
                "Tratar_midias.v__Converter_video": conversor,
            }

            with patch.dict(sys.modules, modules):
                primeira = Path(
                    self.processor.converter_video_avulso(
                        str(video),
                        str(destino),
                        music_volume=0,
                    )
                )
                segunda = Path(
                    self.processor.converter_video_avulso(
                        str(video),
                        str(destino),
                        music_volume=0,
                    )
                )

            raiz_avulsas = destino / "H_Arq_avulsas"
            self.assertEqual(
                primeira.parent,
                raiz_avulsas / "F_video_shopee",
            )
            self.assertTrue(primeira.is_file())
            self.assertTrue(segunda.is_file())
            self.assertNotEqual(primeira, segunda)
            self.assertEqual(video.read_bytes(), b"video-original")

    def test_png_transparente_usa_alfa_sem_chamar_onnx(self):
        class AlphaFake:
            def getextrema(self):
                return (0, 255)

            def getbbox(self):
                return (12, 18, 80, 95)

        class ImagemTransparenteFake:
            width = 100
            height = 120

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def convert(self, _modo):
                return self

            def getchannel(self, _canal):
                return AlphaFake()

        image_module = types.SimpleNamespace(
            open=lambda _path: ImagemTransparenteFake()
        )
        namespace = _carregar_funcoes_bbox(
            {
                "Image": image_module,
                "BytesIO": io.BytesIO,
                "sys": sys,
                "remove": lambda *_args, **_kwargs: self.fail(
                    "Não deveria executar outra inferência ONNX."
                ),
                "new_session": self.fail,
                "MODELO_REMBG_MEDIDAS": "isnet-general-use",
                "_SESSAO_CPU_MEDIDAS": None,
            }
        )

        imagem, bbox = namespace["detectar_bbox"]("imagem-transparente.png")
        self.assertEqual(bbox, (12, 18, 80, 95))
        self.assertEqual((imagem.width, imagem.height), (100, 120))

    def test_falta_de_memoria_gpu_refaz_deteccao_na_cpu(self):
        sessao_gpu = object()
        sessao_cpu = object()
        modulo_remocao = types.ModuleType(
            "Tratar_midias.c__Remove_Refina_IMG"
        )
        modulo_remocao.sessao = sessao_gpu
        modulo_remocao.MODO_GPU = True
        remove = unittest.mock.Mock(
            side_effect=[
                RuntimeError("CUDA failure 2: out of memory"),
                b"mascara-cpu",
            ]
        )
        new_session = unittest.mock.Mock(return_value=sessao_cpu)
        namespace = _carregar_funcoes_bbox(
            {
                "Image": None,
                "BytesIO": io.BytesIO,
                "sys": sys,
                "remove": remove,
                "new_session": new_session,
                "MODELO_REMBG_MEDIDAS": "isnet-general-use",
                "_SESSAO_CPU_MEDIDAS": None,
            }
        )

        with patch.dict(
            sys.modules,
            {"Tratar_midias.c__Remove_Refina_IMG": modulo_remocao},
        ):
            result = namespace["_mascara_para_bbox"](b"imagem")

        self.assertEqual(result, b"mascara-cpu")
        self.assertEqual(remove.call_count, 2)
        self.assertIs(remove.call_args_list[0].kwargs["session"], sessao_gpu)
        self.assertIs(remove.call_args_list[1].kwargs["session"], sessao_cpu)
        new_session.assert_called_once_with(
            "isnet-general-use",
            providers=["CPUExecutionProvider"],
        )


if __name__ == "__main__":
    unittest.main()
