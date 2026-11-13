"""Chrome "de verdade" para a LATAM, sem modo de automação.

O Chrome é aberto como um navegador comum (perfil próprio do projeto em
flight-watch/.latam-profile) com uma porta de depuração local. O login no
LATAM Pass é feito à mão nessa janela; o coletor se conecta à mesma janela via
CDP, o que evita as marcas de automação que o anti-bot do login rejeita.

Uso: python -m flightwatch.latam_browser [url]
"""
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

PROFILE = Path(__file__).resolve().parent.parent / ".latam-profile"
PORT = int(os.environ.get("LATAM_CDP_PORT", "9333"))
CDP_URL = f"http://127.0.0.1:{PORT}"
HOME = "https://www.latamairlines.com/br/pt"

CHROME_CANDIDATES = [
    os.environ.get("LATAM_CHROME", ""),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
]


def chrome_path() -> str:
    for c in CHROME_CANDIDATES:
        if c and Path(c).exists():
            return c
    raise FileNotFoundError("Chrome não encontrado; defina LATAM_CHROME")


def is_running() -> bool:
    try:
        urllib.request.urlopen(f"{CDP_URL}/json/version", timeout=2).read()
        return True
    except Exception:
        return False


def ensure_running(url: str = HOME, minimized: bool = False) -> None:
    """Abre o Chrome do projeto se ainda não estiver aberto."""
    if is_running():
        return
    PROFILE.mkdir(exist_ok=True)
    args = [chrome_path(), f"--user-data-dir={PROFILE}", f"--remote-debugging-port={PORT}",
            "--no-first-run", "--no-default-browser-check", "--lang=pt-BR"]
    if minimized:
        args.append("--start-minimized")
    flags = 0
    if os.name == "nt":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(args + [url], creationflags=flags, close_fds=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(30):
        if is_running():
            return
        time.sleep(1)
    raise RuntimeError("Chrome não respondeu na porta de depuração")


def connect(pw):
    """Conecta o Playwright ao Chrome do projeto e devolve uma aba de trabalho."""
    browser = pw.chromium.connect_over_cdp(CDP_URL)
    ctx = browser.contexts[0]
    for p in ctx.pages:
        if "latamairlines.com" in p.url:
            return p
    return ctx.new_page()


if __name__ == "__main__":
    ensure_running(sys.argv[1] if len(sys.argv) > 1 else HOME)
    print(f"Chrome do projeto aberto ({CDP_URL}). Faça login no LATAM Pass nessa janela.")
