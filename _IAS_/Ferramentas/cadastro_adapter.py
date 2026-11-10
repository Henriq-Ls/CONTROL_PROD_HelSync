"""Adaptador seguro entre as ferramentas e os widgets do Cadastro.

O adaptador conhece somente os widgets autorizados no contrato de campos. Ele
nao permite que a IA escolha um atributo arbitrario da janela.
"""

from __future__ import annotations

from typing import Any, Mapping

from .campos_cadastro import CampoCadastro, campo_por_id


class AdaptadorCadastro:
    """Le e altera apenas campos declarados em campos_cadastro.py."""

    def __init__(self, cadastro: Any):
        self._cadastro = cadastro

    def ler_valor(self, campo_id: str) -> Any:
        campo = self._campo_editavel_ou_legivel(campo_id)
        if campo.widget is None:
            return self._valor_do_snapshot(campo)
        widget = getattr(self._cadastro, campo.widget, None)
        if widget is None:
            raise AttributeError(f"Widget ausente para o campo: {campo_id}")
        return self._ler_widget(widget, campo)

    def aplicar_valor(self, campo_id: str, valor: Any) -> Any:
        campo = self._campo_editavel_ou_legivel(campo_id)
        if not campo.editavel or campo.widget is None:
            raise ValueError(f"Campo não editável: {campo_id}")
        widget = getattr(self._cadastro, campo.widget, None)
        if widget is None:
            raise AttributeError(f"Widget ausente para o campo: {campo_id}")
        self._escrever_widget(widget, campo, valor)
        agendar = getattr(self._cadastro, "_schedule_ai_context", None)
        if callable(agendar):
            agendar()
        return self.ler_valor(campo_id)

    def snapshot_atual(self) -> dict[str, Any]:
        capturar = getattr(self._cadastro, "_snapshot_ai_context", None)
        if callable(capturar):
            return dict(capturar())
        return {
            campo.chave_snapshot: self.ler_valor(campo.id)
            for campo in self._campos_com_widget()
        }

    def _campo_editavel_ou_legivel(self, campo_id: str) -> CampoCadastro:
        campo = campo_por_id(campo_id)
        if campo is None:
            raise KeyError(f"Campo desconhecido: {campo_id}")
        return campo

    def _campos_com_widget(self) -> tuple[CampoCadastro, ...]:
        from .campos_cadastro import CAMPOS_CADASTRO

        return tuple(campo for campo in CAMPOS_CADASTRO if campo.widget)

    def _valor_do_snapshot(self, campo: CampoCadastro) -> Any:
        snapshot = self.snapshot_atual()
        return snapshot.get(campo.chave_snapshot, "")

    @staticmethod
    def _ler_widget(widget: Any, campo: CampoCadastro) -> Any:
        if campo.tipo == "multiseleção" and hasattr(widget, "checked_text"):
            return str(widget.checked_text())
        if hasattr(widget, "toPlainText"):
            return str(widget.toPlainText())
        if hasattr(widget, "currentText"):
            return str(widget.currentText())
        if hasattr(widget, "text"):
            return str(widget.text())
        raise TypeError(f"Widget sem leitura suportada: {campo.id}")

    @staticmethod
    def _escrever_widget(widget: Any, campo: CampoCadastro, valor: Any) -> None:
        if campo.tipo == "multiseleção":
            AdaptadorCadastro._escrever_multiseleção(widget, valor)
            return
        texto = str(valor)
        if hasattr(widget, "setPlainText"):
            widget.setPlainText(texto)
            return
        if hasattr(widget, "setCurrentText"):
            widget.setCurrentText(texto)
            return
        if hasattr(widget, "setText"):
            widget.setText(texto)
            return
        raise TypeError(f"Widget sem escrita suportada: {campo.id}")

    @staticmethod
    def _escrever_multiseleção(widget: Any, valor: Any) -> None:
        desejados = {
            item.strip()
            for item in (
                valor if isinstance(valor, (list, tuple, set)) else str(valor).split(",")
            )
            if str(item).strip()
        }
        modelo = widget.model()
        try:
            from PySide6.QtCore import Qt

            marcado = Qt.CheckState.Checked
            desmarcado = Qt.CheckState.Unchecked
        except ImportError:
            marcado = 2
            desmarcado = 0
        for indice in range(modelo.rowCount()):
            item = modelo.item(indice)
            item.setCheckState(marcado if item.text() in desejados else desmarcado)
        refresh = getattr(widget, "_refresh_text", None)
        if callable(refresh):
            refresh()