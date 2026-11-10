"""Área Configuração da interface principal."""

from .workspace import ConfiguracaoWorkspace
from .Configuracoes import ConfiguracoesTab
from .Banco_Dados import DatabaseMigrationPage

__all__ = [
    "ConfiguracaoWorkspace",
    "ConfiguracoesTab",
    "DatabaseMigrationPage",
]
