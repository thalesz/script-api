import json
from pathlib import Path


def load_checkpoint(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_checkpoint(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp.replace(path)


class CheckpointManager:
    """Classe para gerenciar leitura/escrita de checkpoint.

    Mantém compatibilidade com as funções `load_checkpoint` e `save_checkpoint`.
    """

    def __init__(self, path: Path):
        self.path = path

    def exists(self) -> bool:
        return self.path.exists()

    def load(self) -> dict:
        return load_checkpoint(self.path)

    def save(self, data: dict) -> None:
        return save_checkpoint(self.path, data)
