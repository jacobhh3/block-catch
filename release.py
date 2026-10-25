r"""Releases a new version of Block Catch, for PC and phones, in one go.

    .venv\Scripts\python release.py "what changed"

Every update gets its own name, like V1.0: set VERSION at the top of clawd_catch.py first (it won't release a
version that's already out).
1. Commits the changes, as "V1.0: what changed".
2. Builds Block Catch.exe, stamped with that commit, and copies it to the Desktop.
3. Tags the commit v1.0 and pushes both to GitHub, which rebuilds the web version and puts it live (takes a couple
   of minutes).
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
version = re.search(r'^VERSION = "([^"]+)"', (ROOT / "clawd_catch.py").read_text(encoding="utf-8"), re.M).group(1)
tag = f"v{version}"
if subprocess.run(["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag}"], cwd=ROOT, capture_output=True).returncode == 0:
    sys.exit(f"V{version} is already out: raise VERSION at the top of clawd_catch.py first")
message = f"V{version}: " + (" ".join(sys.argv[1:]) or "Update Block Catch")

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

subprocess.run(["git", "tag", tag], cwd=ROOT, check=True)
subprocess.run(["git", "push"], cwd=ROOT, check=True)
subprocess.run(["git", "push", "origin", tag], cwd=ROOT, check=True)
print(f"V{version} pushed: the phone version updates in a couple of minutes at https://jacobhh3.github.io/block-catch/")
