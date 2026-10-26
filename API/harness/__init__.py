from pathlib import Path


def log(file: str, msg: str) -> None:
    """Every runtime action is printed with the name of the file that did it."""
    print(f"[{Path(file).name}] {msg}", flush=True)
