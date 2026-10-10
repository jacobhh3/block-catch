r"""Releases a new version of Block Catch, for PC and phones, in one go.

    .venv\Scripts\python release.py "what changed"

1. Commits the changes.
2. Builds Block Catch.exe, stamped with that commit, and copies it to the Desktop.
3. Pushes to GitHub, which rebuilds the web version and puts it live (takes a couple of minutes).
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
message = " ".join(sys.argv[1:]) or "Update Block Catch"

subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode:
    subprocess.run(["git", "commit", "-m", message], cwd=ROOT, check=True)

stamp = subprocess.run(["git", "log", "-1", "--format=%ct %h"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
(ROOT / "version.txt").write_text(stamp)  # bundled into the exe for the in-game update check
subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "Block Catch.spec"], cwd=ROOT, check=True)
desktop = Path.home() / "Desktop"
if desktop.is_dir():
    shutil.copy(ROOT / "dist" / "Block Catch.exe", desktop)
    print(f"copied Block Catch.exe to {desktop}")

subprocess.run(["git", "push"], cwd=ROOT, check=True)
print("pushed: the phone version updates in a couple of minutes at https://jacobhh3.github.io/block-catch/")
