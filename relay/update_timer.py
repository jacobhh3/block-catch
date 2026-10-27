r"""Starts the "UPDATE IN" countdown every copy of the game shows (from V1.1 on), through the relay.

    python relay\update_timer.py MINUTES     start (or restart) a countdown of that many minutes
    python relay\update_timer.py 0           cancel it
    python relay\update_timer.py             show the current one

Games check about once a minute, so the countdown shows up within a minute everywhere. When it runs out,
players see "UPDATE OUT" (a banner even mid-game, and the update button on the menus). It asks for the admin
password (the ADMIN_KEY secret, the same one delete_score.py uses) without showing it.
"""
import datetime
import getpass
import json
import os
import sys
import urllib.error
import urllib.request

RELAY = os.environ.get("BLOCKCATCH_RELAY") or "https://block-catch-lb.jacobhh3.workers.dev/"  # env var: test relay


def get(path, key=None):
    req = urllib.request.Request(RELAY + path, headers={"User-Agent": "ClawdCatch"})
    if key:
        req.add_header("X-Admin-Key", key)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def show(t):
    if not t["at"]:
        print("no countdown running")
    elif t["at"] <= t["now"]:
        print("the countdown has run out: games show UPDATE OUT")
    else:
        left = (t["at"] - t["now"]) // 1000
        ends = datetime.datetime.fromtimestamp(t["at"] / 1000).strftime("%I:%M %p")
        print(f"countdown running: {left // 60}:{left % 60:02d} left (ends {ends})")


if len(sys.argv) < 2:
    show(get("update"))
    sys.exit()
if not sys.argv[1].isdigit() or int(sys.argv[1]) > 9999:
    sys.exit("give the countdown in whole minutes (0 cancels it)")
key = getpass.getpass("admin password: ")
try:
    show(get(f"update/set/{int(sys.argv[1])}", key))
except urllib.error.HTTPError as e:
    sys.exit(f"{e.code} {e.read().decode('utf-8', 'replace')}")
