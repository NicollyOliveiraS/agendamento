"""Copia os arquivos estáticos para a CDN da Vercel durante o build."""

from pathlib import Path
from shutil import copytree


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    copytree(root / "app" / "static", root / "public" / "static", dirs_exist_ok=True)
