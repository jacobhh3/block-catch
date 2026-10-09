# Block Catch

Hit the falling blocks before they reach the ground.

- **Phones and browsers:** https://jacobhh3.github.io/block-catch/ (on a phone, use "Add to Home Screen")
- **Windows:** `Block Catch.exe`, built from the same `clawd_catch.py`

## Making changes

- Play the PC version: `.venv\Scripts\python clawd_catch.py`
  (set `BLOCKCATCH_TOUCH=1` first to see the phone buttons)
- Try the web version locally: `.venv\Scripts\python build_web.py --serve`, then open http://127.0.0.1:8000
- Release to both: `.venv\Scripts\python release.py "what changed"`

## Leaderboard

Scores go to dreamlo through a small Cloudflare Worker in `relay/` (dreamlo's free tier is HTTP only, which
browsers block). To change the relay: `cd relay`, then `npx wrangler deploy`.
