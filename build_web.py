"""Builds the browser version of Block Catch with pygbag.

    python build_web.py           build into build/block-catch/build/web
    python build_web.py --serve   build, then play it at http://127.0.0.1:8000

    --lan      serve it to the home network too, so a phone on the same Wi-Fi can open it (local tests only)
    --mirror   load pygbag's Python from the jsDelivr mirror of its GitHub repo, for when pygame-web.github.io
               can't be reached (local tests only: the live site keeps the usual address)
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STAGE = ROOT / "build" / "block-catch"  # pygbag names the bundle after this folder
SITE = STAGE / "build" / "web"

shutil.rmtree(STAGE, ignore_errors=True)
STAGE.mkdir(parents=True)
shutil.copy(ROOT / "clawd_catch.py", STAGE / "main.py")  # pygbag runs main.py
shutil.copy(ROOT / "Silkscreen-Bold.ttf", STAGE)
shutil.copy(ROOT / "favicon-web.png", STAGE / "favicon.png")
shutil.copytree(ROOT / "sounds", STAGE / "sounds")
stamp = subprocess.run(["git", "log", "-1", "--format=%ct %h"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
(STAGE / "version.txt").write_text(stamp)  # the game compares this with the website's copy

# pygame-web.github.io/cdn/ is published from the pygame-web/cdn repo on GitHub, which jsDelivr mirrors
PYGBAG = subprocess.run([sys.executable, "-c", "import pygbag; print(pygbag.VERSION)"], capture_output=True,
                        text=True).stdout.strip()
mirror = ["--cdn", f"https://cdn.jsdelivr.net/gh/pygame-web/cdn@main/{PYGBAG}/"] if "--mirror" in sys.argv else []
subprocess.run([sys.executable, "-m", "pygbag", "--build", "--ume_block", "1", "--title", "Block Catch", *mirror,
                "--template", str(ROOT / "web.tmpl"), str(STAGE)], check=True)
for name in ("apple-touch-icon.png", "icon-192.png", "icon-512.png", "manifest.webmanifest"):
    shutil.copy(ROOT / name, SITE)  # home screen icons, and the app details Android uses
shutil.copy(STAGE / "version.txt", SITE)  # which build is live, for the in-game update check
print(f"\nweb build ready: {SITE}")

if "--serve" in sys.argv:
    lan = "--lan" in sys.argv
    if lan:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("192.168.0.1", 9))  # no traffic is sent: this just picks the Wi-Fi address
            print(f"on a phone on the same Wi-Fi: http://{probe.getsockname()[0]}:8000")
    print("playing at http://127.0.0.1:8000  (Ctrl+C to stop)", flush=True)
    subprocess.run([sys.executable, "-m", "http.server", "8000", "--bind", "0.0.0.0" if lan else "127.0.0.1",
                    "-d", str(SITE)])
