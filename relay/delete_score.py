r"""Removes scores from the online leaderboard, through the relay.

    python relay\delete_score.py NAME_xxxx [NAME_xxxx ...]

Names are the full leaderboard keys: the player's name, an underscore and their 4-character device id
(e.g. BENCHEATS_44cb). Run it with no names to list every key. It asks for the admin password (the
ADMIN_KEY secret set with `npx wrangler secret put ADMIN_KEY`) without showing it.
"""
import getpass
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

RELAY = "https://block-catch-lb.jacobhh3.workers.dev/"


def get(path, key=None):
    req = urllib.request.Request(RELAY + path, headers={"User-Agent": "ClawdCatch"})
    if key:
        req.add_header("X-Admin-Key", key)
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.read().decode("utf-8", "replace")


board = json.loads(get("json/999"))["dreamlo"]["leaderboard"]
entries = (board or {}).get("entry", [])
entries = [entries] if isinstance(entries, dict) else entries
keys = {e["name"]: e["score"] for e in entries}
if len(sys.argv) < 2:
    for k, score in sorted(keys.items(), key=lambda kv: -int(kv[1])):
        print(f"{k:<24} {score:>6}")
    sys.exit()

missing = [k for k in sys.argv[1:] if k not in keys]
if missing:
    sys.exit(f"not on the leaderboard: {', '.join(missing)}  (run with no names to list them)")
key = getpass.getpass("admin password: ")
for name in sys.argv[1:]:
    try:
        get("delete/" + urllib.parse.quote(name, safe=""), key)
        print(f"deleted {name} ({keys[name]})")
    except urllib.error.HTTPError as e:
        sys.exit(f"{name}: {e.code} {e.read().decode('utf-8', 'replace')}")
