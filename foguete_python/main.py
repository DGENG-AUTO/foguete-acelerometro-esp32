"""MÓDULO PRINCIPAL do sistema.
    Inicia a execução da lógica dos arquivos Python.
"""
from rocket_simulator import FogueteApp


if __name__ == "__main__":
    app = FogueteApp()
    app.run()