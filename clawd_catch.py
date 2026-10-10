"""Block Catch - hit the falling blocks before they reach the ground."""
import asyncio
import json
import math
import os
import random
import sys
import threading
import urllib.parse
import urllib.request

import pygame

WEB = sys.platform == "emscripten"  # running in a browser (built with pygbag)
if WEB:
    import platform  # pygbag's bridge to the page's JavaScript
TOUCH = WEB or os.environ.get("BLOCKCATCH_TOUCH") == "1"  # on-screen buttons; the env var tests them on PC

W, H, GROUND = 400, 560, 512
PAD = 170 if TOUCH else 0  # height of the touch controls strip under the game
PAD_KEYS = [("left", 10, 98), ("right", 114, 98), ("jump", 218, 172)]  # touch buttons: left edge and width
KEY_ROWS = ["1234567890", "QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"]  # on-screen keyboard for the name entry
NIGHT = (27, 26, 36)
PANEL = (36, 34, 47)
INK = (239, 230, 220)
DIM = (143, 134, 152)
DASH_SPEED = 560
DASH_TIME = 0.14
DASH_COOLDOWN = 0.35
DOUBLE_TAP = 0.25  # seconds between taps that count as a double tap
HEART_STREAK = 20  # hits in a row that drop a heart
MAX_LIVES = 3
PICKUP_GAP = 2.0  # minimum seconds between power-ups dropping, so two never arrive together
TOAST_TIME = 3.5  # seconds the "new hat" notification stays up
HEART_FALL = 45
BOLT_EVERY = 15  # blocks hit (in total) that drop a lightning bolt
BOLT_FALL = 55
BOLT_KILLS = 2  # blocks the bolt destroys at the start, nearest the ground first
BOLT_GROWTH = 30  # seconds of play per extra block the bolt destroys
BOLT_MAX = 6
BOLT_COLOR = (255, 226, 102)
COMBO_STEP = 10  # hits in a row per extra score multiplier
MAX_MULT = 4
BOMB_AFTER = 15  # seconds before bombs start falling
BOMB_RED = (232, 72, 72)
BOMB_BODY = (16, 15, 22)
JUMP_SPEED = 640  # upward speed of a jump, from the ground or off a block
BLOCK_BOUNCE = 260  # little hop when Clawd breaks a block in midair without jumping
JUMP_WINDOW = 0.15  # seconds a jump press counts before or after breaking a block, to jump off it
RESUME_COUNT = 3  # seconds of countdown after unpausing, while Clawd wakes up
DANCE_PRESSES = 4  # easter egg: press jump this many times quickly on the main menu and Clawd dances
DANCE_GAP = 0.45  # most seconds allowed between those presses
DANCE_TIME = 2.0
DANCE_BEAT = 0.25
GOLD_EVERY = (20, 35)  # seconds between gold blocks shooting across the screen
GOLD_WARN = 1.2  # seconds of warning at the screen edge before it appears
GOLD_SPEED = (260, 380)  # random per gold block
GOLD_HEIGHT = (150, 450)  # random top edge; a plain jump reaches about 360
WALL_JUMP = 600  # upward speed of a wall jump
WALL_KICK = 340  # sideways push away from the wall
WALL_SLIDE = 140  # max fall speed while holding into a wall
GOLD_POINTS = 10  # times the combo multiplier
MAGNET_EVERY = 25  # blocks hit (in total) that drop a magnet
MAGNET_TIME = 1.0
MAGNET_FALL = 50
MAGNET_PULL = 160  # sideways pull speed on blocks while the magnet is active
MAGNET_COLOR = (224, 92, 108)
MAGNET_TIP = (220, 220, 232)
SPEED_COOLDOWN = 30  # seconds after one speed boost drops before the next can
SPEED_RANDOM = 20  # plus up to this many random extra seconds
SPEED_TIME = 5.0
SPEED_FALL = 55
SPEED_MULT = 1.6  # run speed and acceleration while boosted
SPEED_COLOR = (102, 214, 196)
CLAWD = (217, 119, 87)
EARTH = (58, 51, 70)
GOLD = (232, 176, 75)
BLOCK_COLORS = [(111, 183, 168), (157, 139, 224), (224, 122, 154), (127, 166, 224)]  # no gold or yellow, so gold blocks stand out

# Clawd sprite, 13x9. X = body, E = eye. Legs alternate frames.
BODY = [
    "..XXXXXXXXX..",
    "..XXXXXXXXX..",
    "..XXEXXXEXX..",
    "XXXXEXXXEXXXX",
    "XXXXXXXXXXXXX",
    "..XXXXXXXXX..",
    "..XXXXXXXXX..",
]
LEGS = [
    ["..X.X...X.X..", "..X.X...X.X.."],
    ["...X.X...X.X.", "...X.X...X.X."],
    [".X.X...X.X...", ".X.X...X.X..."],
]
PX = 4
PW, PH = 13 * PX, 9 * PX

# Hats, unlocked by reaching a streak. Drawn 13 wide like Clawd and sat on top of his head.
HAT_COLORS = {
    # pinks
    "L": (255, 176, 200), "P": (224, 122, 154), "p": (168, 78, 112),
    # golds
    "w": (255, 236, 150), "Y": (232, 176, 75), "y": (170, 118, 48),
    # blues
    "l": (176, 206, 250), "B": (106, 150, 224), "b": (62, 92, 160),
    # browns
    "T": (204, 148, 96), "N": (150, 100, 66), "n": (100, 64, 42),
    # top hat purples
    "G": (132, 110, 176), "K": (82, 64, 116), "k": (50, 38, 74),
    # accents
    "W": (239, 230, 220), "R": (232, 72, 72), "r": (160, 40, 52),
    "C": (111, 210, 190), "U": (170, 140, 240),
}
HATS = [
    ("PARTY HAT", 20, ["......w......",
                       ".....LPp.....",
                       ".....CCC.....",
                       "....LPPPp....",
                       "....wYYYy....",
                       "...LPPPPPp..."]),
    ("BALL CAP", 40, ["......R......",
                      "....lBBBb....",
                      "...lBBWBBb...",
                      "..lBBBBBBBb..",
                      "..bbbbbbbbbbb"]),
    ("COWBOY HAT", 60, [".....TNn.....",
                        "....TNNNn....",
                        "....rRwRr....",
                        "T.TNNNNNNNn.n",
                        ".nnnnnnnnnnn."]),
    ("TOP HAT", 80, ["...GGGGGGG...",
                     "...GKKKKKk...",
                     "...GKKKKKk...",
                     "...GKKKKPk...",
                     "...RRRRPwP...",
                     ".GKKKKKKKKKk."]),
    ("CROWN", 100, ["..w...w...w..",
                    "..YY.YwY.YY..",
                    "..wYYYYYYYy..",
                    "..YRYYCYYUy..",
                    "..yyyyyyyyy.."]),
]

HEART = [".XX.XX.", "XXXXXXX", "XXXXXXX", ".XXXXX.", "..XXX..", "...X..."]
BOLT = ["...XXX", "..XXX.", ".XXX..", "XXXXXX", "..XXX.", ".XXX..", "XXX...", "X....."]
SPEED = ["XX..XX..", ".XX..XX.", "..XX..XX", ".XX..XX.", "XX..XX.."]
# speaker icons for the sound button, one per SOUND_MODES entry
SPEAKERS = [
    ["...X...X..", "..XX....X.", "XXXX..X..X", "XXXX..X..X", "XXXX..X..X", "..XX....X.", "...X...X.."],
    ["...X......", "..XX......", "XXXX..X...", "XXXX..X...", "XXXX..X...", "..XX......", "...X......"],
    ["...X......", "..XX......", "XXXX.X.X..", "XXXX..X...", "XXXX.X.X..", "..XX......", "...X......"],
]
SHARE = ["...X...", "..XXX..", ".X.X.X.", "...X...", "XX.X.XX", "X.....X", "X.....X", "XXXXXXX"]  # iPhone share
MENU = ["X", ".", "X", ".", "X"]  # Android Chrome's menu (three dots)
MAGNET = ["TT...TT", "TT...TT", "XX...XX", "XX...XX", "XXX.XXX", ".XXXXX.", "..XXX.."]


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def resource(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def read_build():
    """This build's "commit-time commit-id", stamped in by build_web.py / release.py; empty when run from source."""
    try:
        with open(resource("version.txt"), encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return ""


def build_time(stamp):
    try:
        return int(stamp.split()[0])
    except (ValueError, IndexError):
        return 0


SAVE_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "ClawdCatch")  # old name kept so existing scores and hats carry over
SCORES_FILE = os.path.join(SAVE_DIR, "scores.json")
OLD_BEST_FILE = os.path.join(SAVE_DIR, "best.txt")
HATS_FILE = os.path.join(SAVE_DIR, "hats.json")
SETTINGS_FILE = os.path.join(SAVE_DIR, "settings.json")
SITE_URL = "https://jacobhh3.github.io/block-catch/"
VERSION_CHECK = 300  # seconds between checks for a newer build on the website
SOUND_MODES = ["ON", "EFFECTS ONLY", "OFF"]  # M key / speaker button cycles through these
MUSIC_VOLUME = {"play": 0.45, "paused": 0.0}  # every other screen: 0.2
TOP_N = 10
NAME_LEN = 10


# Shared online leaderboard (dreamlo.com), reached through a small Cloudflare relay (see relay/) because
# dreamlo's free tier is HTTP only and browsers refuse that. The relay holds dreamlo's private code.
LB_URL = "https://block-catch-lb.jacobhh3.workers.dev/"


def display_name(key):
    """Online keys are NAME_xxxx so two players can share a name; show just NAME."""
    return key.rsplit("_", 1)[0] if "_" in key else key


def load_save(path):
    """Reads a save file. The web version keeps them in the browser's localStorage instead of files."""
    if WEB:
        try:
            text = platform.window.localStorage.getItem("blockcatch/" + os.path.basename(path))
        except Exception as e:
            raise OSError(e)
        if not text:
            raise OSError("no save")
        return json.loads(str(text))
    with open(path) as f:
        return json.load(f)


def write_save(path, data):
    text = json.dumps(data, indent=2)
    if WEB:
        try:
            platform.window.localStorage.setItem("blockcatch/" + os.path.basename(path), text)
        except Exception as e:
            raise OSError(e)
        return
    os.makedirs(SAVE_DIR, exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


# In the browser, requests go through fetch(); Python polls for the answer so the game keeps running.
WEB_FETCH_JS = """
window.bc_net = {};
window.bc_get = function (id, url) {
    window.bc_net[id] = "";
    fetch(url, {cache: "no-store"}).then(r => r.text())
        .then(t => { window.bc_net[id] = "1" + t; })
        .catch(e => { window.bc_net[id] = "0" + e; });
};
window.bc_update = function () {
    var files = ["block-catch.apk", "index.html"];
    Promise.all(files.map(u => fetch(u, {cache: "reload"}).catch(() => 0))).then(() => location.reload());
};
window.bc_take = function (id) {
    var v = window.bc_net[id] || "";
    if (v) delete window.bc_net[id];
    return v;
};
"""


class Leaderboard:
    """Online top 10 with a local cache, so the table still shows when offline.
    Scores that fail to upload are kept and retried on the next launch."""

    def __init__(self):
        self.lock = threading.Lock()
        self.status = "connecting"  # connecting | online | offline
        self.scores, self.pending, self.name, self.player_id = [], [], "", ""
        self.syncing, self.again, self.requests = False, False, 0
        if WEB:
            platform.window.eval(WEB_FETCH_JS)
        try:
            data = load_save(SCORES_FILE)
            if "player_id" in data:
                self.scores = [s for s in data.get("scores", []) if isinstance(s.get("score"), int)]
                self.pending = data.get("pending", [])
            else:
                # first run after going online: upload the scores this PC already had
                self.pending = [dict(name=s["name"], score=s["score"]) for s in data.get("scores", [])
                                if s.get("name") not in (None, "???") and isinstance(s.get("score"), int)]
            self.name = str(data.get("last_name", ""))
            self.player_id = str(data.get("player_id", ""))
        except (OSError, ValueError, AttributeError, KeyError, TypeError):
            pass
        if not self.player_id:
            self.player_id = "%04x" % random.randrange(16 ** 4)
        for s in self.scores:
            s.setdefault("key", s["name"])
        self.save()
        self.refresh()

    def save(self):
        try:
            write_save(SCORES_FILE, dict(scores=self.scores, pending=self.pending, last_name=self.name,
                                         player_id=self.player_id))
        except OSError:
            pass

    def snapshot(self):
        with self.lock:
            return list(self.scores)

    def key_for(self, name):
        return f"{name}_{self.player_id}"

    def submit(self, name, score):
        """Shows the score in the table right away, then uploads it in the background."""
        key = self.key_for(name)
        with self.lock:
            self.name = name
            self.pending.append(dict(name=name, score=score))
            self.merge(dict(key=key, name=name, score=score))
            self.save()
        self.refresh()
        return key

    def merge(self, entry):
        # dreamlo keeps only the higher score per key, so do the same here
        for s in self.scores:
            if s["key"] == entry["key"]:
                s["score"] = max(s["score"], entry["score"])
                break
        else:
            self.scores.append(entry)
        self.scores.sort(key=lambda s: -s["score"])
        del self.scores[TOP_N:]

    def refresh(self):
        if WEB:
            asyncio.ensure_future(self._web_refresh())
        else:
            threading.Thread(target=self._thread_refresh, daemon=True).start()

    def _thread_refresh(self):
        with _sync_lock:
            asyncio.run(self._sync())

    async def _web_refresh(self):
        # no threads in the browser: one sync at a time, and another round if more was asked for meanwhile
        if self.syncing:
            self.again = True
            return
        self.syncing = True
        try:
            self.again = True
            while self.again:
                self.again = False
                await self._sync()
        finally:
            self.syncing = False

    async def _get(self, url):
        if not WEB:
            req = urllib.request.Request(url, headers={"User-Agent": "ClawdCatch"})
            with urllib.request.urlopen(req, timeout=8) as r:
                return r.read().decode("utf-8", "replace")
        self.requests += 1
        rid = str(self.requests)
        platform.window.bc_get(rid, url)
        for _ in range(160):  # about 8 seconds
            reply = str(platform.window.bc_take(rid) or "")
            if reply:
                if reply[0] != "1":
                    raise OSError(reply[1:])
                return reply[1:]
            await asyncio.sleep(0.05)
        raise OSError("timed out")

    async def _sync(self):
        try:
            with self.lock:
                todo = list(self.pending)
            for p in todo:
                key = urllib.parse.quote(self.key_for(p["name"]), safe="")
                reply = await self._get(f"{LB_URL}add/{key}/{int(p['score'])}")
                if not reply.startswith("OK"):
                    raise OSError(reply)
                with self.lock:
                    self.pending.remove(p)
                    self.save()
            data = json.loads(await self._get(f"{LB_URL}json/{TOP_N}"))
            rows = (data.get("dreamlo", {}).get("leaderboard") or {}).get("entry") or []
            if isinstance(rows, dict):
                rows = [rows]
            online = [dict(key=r["name"], name=display_name(r["name"]), score=int(r["score"]))
                      for r in rows]
            with self.lock:
                self.scores = sorted(online, key=lambda s: -s["score"])[:TOP_N]
                for p in self.pending:  # anything still waiting stays visible locally
                    self.merge(dict(key=self.key_for(p["name"]), name=p["name"], score=p["score"]))
                self.status = "online"
                self.save()
        except Exception:
            with self.lock:
                self.status = "offline"


_sync_lock = threading.Lock()


def make_hat(rows, color=None, px=PX):
    """A hat sprite; pass a color to get a flat silhouette (used for locked hats)."""
    surf = pygame.Surface((len(rows[0]) * px, len(rows) * px), pygame.SRCALPHA)
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch != ".":
                surf.fill(color or HAT_COLORS[ch], (c * px, r * px, px, px))
    return surf


def make_clawd(frame, blink):
    surf = pygame.Surface((PW, PH), pygame.SRCALPHA)
    rows = BODY + LEGS[frame]
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch == ".":
                continue
            color = CLAWD
            if ch == "E":
                color = (CLAWD if r == 2 else NIGHT) if blink else NIGHT
            surf.fill(color, (c * PX, r * PX, PX, PX))
    return surf


class Game:
    def __init__(self):
        if not WEB:
            pygame.mixer.pre_init(22050, -16, 1, 512)  # small buffer, so sounds play without delay
        pygame.init()
        pygame.display.set_caption("Block Catch")
        icon = pygame.Surface((64, 64), pygame.SRCALPHA)
        icon.blit(make_clawd(0, False), ((64 - PW) // 2, (64 - PH) // 2))
        pygame.display.set_icon(icon)
        # the browser page scales the canvas itself, so the web version skips SCALED
        self.screen = pygame.display.set_mode((W, H + PAD), 0 if WEB else pygame.SCALED | pygame.RESIZABLE)
        self.canvas = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()
        self.fonts = {}
        self.sprites = {(f, b): make_clawd(f, b) for f in range(3) for b in (False, True)}
        self.board = Leaderboard()
        self.hat_art = [make_hat(rows) for _, _, rows in HATS]
        self.hat_shadow = [a.copy() for a in self.hat_art]  # locked hats: full color, dimmed
        for a in self.hat_shadow:
            a.fill((150, 145, 160, 255), special_flags=pygame.BLEND_RGBA_MULT)
        self.hat_icons = [make_hat(rows, px=3) for _, _, rows in HATS]
        self.unlocked, self.worn = set(), -1  # hat indexes; -1 is no hat
        try:
            data = load_save(HATS_FILE)
            self.unlocked = {i for i in data.get("unlocked", []) if isinstance(i, int) and 0 <= i < len(HATS)}
            self.worn = data.get("worn", -1) if data.get("worn", -1) in self.unlocked else -1
        except (OSError, ValueError, AttributeError, TypeError):
            pass
        self.viewing = self.worn  # hat shown in the title screen picker
        self.on_home_screen = False  # opened from a home screen icon: no need for the how-to
        if WEB:
            try:
                platform.window.eval("window.bc_home = (matchMedia('(display-mode: standalone)').matches"
                                     " || navigator.standalone === true) ? 'yes' : 'no'")
                self.on_home_screen = str(platform.window.bc_home) == "yes"
            except Exception:
                pass
        self.sound = 0  # index into SOUND_MODES
        try:
            self.sound = int(load_save(SETTINGS_FILE).get("sound", 0)) % len(SOUND_MODES)
        except (OSError, ValueError, AttributeError, TypeError):
            pass
        self.sfx, self.music_volume, self.notice = {}, None, None
        try:
            pygame.mixer.set_num_channels(16)
            folder = resource("sounds")
            for f in os.listdir(folder):
                if f.endswith(".ogg") and f != "music.ogg":
                    self.sfx[f[:-4]] = pygame.mixer.Sound(os.path.join(folder, f))
            pygame.mixer.music.load(os.path.join(folder, "music.ogg"))
            pygame.mixer.music.play(-1)
        except (pygame.error, OSError):
            pass  # no audio device or no sound files: play on silently
        self.toast = None  # "new hat" notification
        self.name = self.board.name
        self.last_key = None  # online key of the score just entered, for highlighting
        self.pointers = {}  # touch fingers (and the mouse) currently down: id -> (x, y)
        self.buttons = []  # tappable menu buttons drawn this frame: (rect, action)
        self.pad = {name: pygame.Rect(x, H + 16, w, PAD - 32) for name, x, w in PAD_KEYS}
        self.build, self.update_ready, self.check_in = read_build(), False, 0.0
        self.stars = [((i * 97) % W, (i * 53) % 420, 2 if i % 3 == 0 else 1, i) for i in range(40)]
        self.reset("title")

    def font(self, size):
        if size not in self.fonts:
            try:
                self.fonts[size] = pygame.font.Font(resource("Silkscreen-Bold.ttf"), size)
            except (OSError, FileNotFoundError):
                self.fonts[size] = pygame.font.SysFont("consolas", size, bold=True)
        return self.fonts[size]

    @property
    def scores(self):
        return self.board.snapshot()

    @property
    def best(self):
        return max([s["score"] for s in self.scores] + [self.score if self.mode != "title" else 0])

    def qualifies(self):
        return self.score > 0 and (len(self.scores) < TOP_N or self.score > self.scores[-1]["score"])

    def game_over(self):
        self.last_key = None
        self.play("gameover")
        if self.qualifies():
            self.mode = "entry"
            self.entry_ready = pygame.time.get_ticks() + 500  # ignore keys still held from play
            pygame.key.start_text_input()
        else:
            self.mode = "over"
            self.board.refresh()

    def submit_name(self):
        name = self.name.strip() or "CLAWD"
        self.name = name
        self.last_key = self.board.submit(name, self.score)
        pygame.key.stop_text_input()
        self.mode = "over"

    def reset(self, mode):
        self.mode = mode  # title | help | board | home | play | paused | resume | entry | over
        self.t = 0.0
        self.score = 0
        self.lives = 3
        self.streak = 0
        self.hearts = []
        self.p = dict(x=W / 2 - PW / 2, y=GROUND - PH, vx=0.0, vy=0.0, on_ground=True,
                      walk=0.0, blink=0.0, chain=0, jump_buffer=0.0, block_grace=0.0,
                      dash=0.0, dash_dir=0, dash_cd=0.0, dance=0.0, taps=0, tap_gap=0.0)
        self.countdown, self.wake = 0.0, 0.0  # seconds left before play resumes; "!" after waking
        self.last_tap = (0, -1.0)
        self.ghosts = []
        self.blocks, self.parts, self.pops = [], [], []
        self.hits = 0
        self.bolts, self.strikes = [], []
        self.magnets, self.magnet = [], 0.0  # pickups falling, seconds of pull left
        self.boosts, self.speed = [], 0.0  # pickups falling, seconds of speed left
        self.speed_in = SPEED_COOLDOWN + random.random() * SPEED_RANDOM
        self.runners, self.gold_in = [], random.uniform(*GOLD_EVERY)  # gold blocks crossing the screen
        self.pickup_queue, self.pickup_wait = [], 0.0  # power-ups waiting their turn to drop
        self.trail, self.rings, self.dust = [], [], []
        self.flash = 0.0
        self.spawn_in = 1.0
        self.shake = 0.0

    def start(self):
        if self.mode == "paused":
            self.resume()
        else:
            self.reset("play")

    def pause(self):
        if self.mode in ("play", "resume"):
            self.mode = "paused"
            self.play("snore")

    def resume(self):
        """Leaving the pause screen: a short countdown while Clawd wakes up, then play goes on."""
        self.mode, self.countdown = "resume", RESUME_COUNT
        self.play("tick")

    def show_board(self):
        self.last_key = None
        self.board.refresh()
        self.mode = "board"

    def go(self, mode):
        """A button action that just switches screens."""
        return lambda: setattr(self, "mode", mode)

    def type_letter(self, ch):
        self.name = (self.name + ch)[:NAME_LEN]

    def erase_letter(self):
        self.name = self.name[:-1]

    # ---------- updates ----------
    def check_version(self):
        """Asks the website which build is live; a newer one shows the update banner on the main menu."""
        if not self.build or self.update_ready:
            return

        async def check():
            try:
                live = await self.board._get(f"{SITE_URL}version.txt?t={random.randrange(10 ** 9)}")
            except Exception:
                return  # offline: try again next time
            if build_time(live) > build_time(self.build):
                self.update_ready = True

        if WEB:
            asyncio.ensure_future(check())
        else:
            threading.Thread(target=lambda: asyncio.run(check()), daemon=True).start()

    def update_now(self):
        if WEB:
            self.notice = dict(txt="UPDATING", life=10)
            platform.window.bc_update()

    # ---------- sound ----------
    def play(self, name):
        if self.sound < 2 and name in self.sfx:
            self.sfx[name].play()

    def update_music(self):
        """Music is full while playing, softer on the menus, silent while paused."""
        vol = 0.0 if self.sound else MUSIC_VOLUME.get(self.mode, 0.2)
        if vol != self.music_volume:
            self.music_volume = vol
            try:
                pygame.mixer.music.set_volume(vol)
            except pygame.error:
                pass

    def toggle_sound(self):
        self.sound = (self.sound + 1) % len(SOUND_MODES)
        try:
            write_save(SETTINGS_FILE, dict(sound=self.sound))
        except OSError:
            pass
        self.notice = dict(txt="SOUND " + SOUND_MODES[self.sound], life=1.4)

    def sound_button(self, x, y):
        self.button("", x, y, 44, 32, self.toggle_sound, color=DIM)
        self.pixel_sprite(SPEAKERS[self.sound], x - 15, y - 10, 3, DIM)

    # ---------- touch ----------
    def pad_at(self, pos):
        return next((name for name, r in self.pad.items() if pos and r.collidepoint(pos)), None)

    def held(self):
        return {self.pad_at(pos) for pos in self.pointers.values()} - {None}

    def controls(self):
        """Left, right, jump: from the keyboard or the touch buttons."""
        k = pygame.key.get_pressed()
        held = self.held()
        return (k[pygame.K_LEFT] or k[pygame.K_a] or "left" in held,
                k[pygame.K_RIGHT] or k[pygame.K_d] or "right" in held,
                k[pygame.K_UP] or k[pygame.K_w] or k[pygame.K_SPACE] or "jump" in held)

    def pointer(self, kind, pid, pos):
        """A finger (or the mouse) went down, moved or lifted. kind: down | move | up"""
        if kind == "up":
            self.pointers.pop(pid, None)
            return
        before = self.pad_at(self.pointers.get(pid))
        self.pointers[pid] = pos
        now = self.pad_at(pos)
        if now in ("left", "right") and now != before:  # pressing, or sliding onto, an arrow counts as a tap
            self.tap_direction(-1 if now == "left" else 1)
        if kind == "down":
            if self.mode == "entry" and pygame.time.get_ticks() < self.entry_ready:
                return
            for r, action in self.buttons:
                if r.collidepoint(pos):
                    self.play("click")
                    action()
                    break

    def tap_direction(self, d):
        """Called on each left/right key press; a quick second tap in the same direction dashes."""
        if self.mode != "play":
            return
        p = self.p
        last_dir, last_t = self.last_tap
        if d == last_dir and self.t - last_t <= DOUBLE_TAP and p["dash_cd"] <= 0:
            p["dash"], p["dash_dir"], p["dash_cd"] = DASH_TIME, d, DASH_COOLDOWN
            p["vx"] = d * DASH_SPEED
            if not p["on_ground"]:
                p["vy"] = min(p["vy"], 0.0)
            self.play("dash")
            self.burst(p["x"] + PW / 2 - d * PW / 2, p["y"] + PH - 4, DIM, 6, 90)
            self.last_tap = (0, -1.0)
        else:
            self.last_tap = (d, self.t)

    # ---------- update ----------
    def dance_check(self, dt, controls):
        """Easter egg: a few quick jump presses on the main menu and Clawd does a little dance."""
        p = self.p
        jump = controls[2]
        pressed = jump and not p.get("dance_held")
        p["dance_held"] = jump
        p["tap_gap"] += dt
        if self.mode != "title":
            p["taps"], p["dance"] = 0, 0.0
            return
        if p["dance"] > 0:
            p["dance"] -= dt
            if p["dance"] <= 0:
                self.burst(p["x"] + PW / 2, GROUND - PH, GOLD, 14, 160)
            return
        if pressed:
            p["taps"] = p["taps"] + 1 if p["tap_gap"] <= DANCE_GAP else 1
            p["tap_gap"] = 0.0
            if p["taps"] >= DANCE_PRESSES:
                p["taps"], p["dance"] = 0, DANCE_TIME
                self.play("hat")

    def difficulty(self):
        d = min(1.0, self.t / 120)  # ramps over roughly 2 minutes
        return 38 + d * 70 + random.random() * 14, 1.9 - d * 1.15

    def save_hats(self):
        try:
            write_save(HATS_FILE, dict(unlocked=sorted(self.unlocked), worn=self.worn))
        except OSError:
            pass

    def check_hats(self):
        """Unlock any hat whose streak has just been reached, with a notification the first time."""
        for i, (name, need, _) in enumerate(HATS):
            if self.streak >= need and i not in self.unlocked:
                self.unlocked.add(i)
                self.save_hats()
                self.toast = dict(hat=i, life=TOAST_TIME)
                self.play("hat")

    def pick_hat(self, d):
        """Title screen: cycle through no hat and every hat. Locked ones can be looked at but not worn."""
        self.viewing = (self.viewing + 1 + d) % (len(HATS) + 1) - 1
        if self.viewing == -1 or self.viewing in self.unlocked:
            self.worn = self.viewing
            self.save_hats()

    def queue_pickup(self, kind):  # kind: "hearts", "bolts", "magnets" or "boosts"
        """Power-ups drop one at a time; earned ones wait in line."""
        self.pickup_queue.append(kind)

    @property
    def multiplier(self):
        return min(MAX_MULT, 1 + self.streak // COMBO_STEP)

    def spawn(self):
        fall, _ = self.difficulty()
        d = min(1.0, self.t / 120)
        if self.t > BOMB_AFTER and random.random() < 0.1 + d * 0.08:
            size = 20
            self.blocks.append(dict(x=12 + random.random() * (W - 24 - size), y=-size, s=size, vy=fall * 0.9,
                                    c=BOMB_RED, rot=0.0, spin=0.0, dead=False, bomb=True))
            return
        size = 16 + random.randrange(3) * 4
        self.blocks.append(dict(x=12 + random.random() * (W - 24 - size), y=-size, s=size, vy=fall,
                                c=random.choice(BLOCK_COLORS), rot=0.0, spin=(random.random() - 0.5) * 70,
                                dead=False))

    def hit_block(self, b, air=False, value=1):
        """Score a destroyed block: combo multiplier, air chain bonus, and pickup drops."""
        b["dead"] = True
        self.streak += 1
        self.check_hats()
        self.hits += 1
        pts = value * self.multiplier
        bx, by = b["x"] + b["s"] / 2, b["y"] + b["s"] / 2
        if air:
            self.p["chain"] += 1
            if self.p["chain"] >= 2:
                pts += self.p["chain"] - 1
                self.pops.append(dict(x=bx, y=by - 26, life=0.9, txt=f"AIR x{self.p['chain']}",
                                      c=(111, 183, 168), size=11))
        self.score += pts
        chain = air and self.p["chain"] >= 2
        self.play("gold" if value == GOLD_POINTS else "air" if chain else f"hit{self.multiplier}")
        if self.hits % BOLT_EVERY == 0:
            self.queue_pickup("bolts")
        if self.hits % MAGNET_EVERY == 0:
            self.queue_pickup("magnets")
        self.burst(bx, by, b["c"], 14, 220)
        self.pops.append(dict(x=bx, y=b["y"], life=0.8, txt=f"+{pts}", c=INK if pts == 1 else GOLD, size=16))
        if self.streak % COMBO_STEP == 0 and self.multiplier > 1 and self.streak <= COMBO_STEP * (MAX_MULT - 1):
            self.pops.append(dict(x=W / 2, y=140, life=1.4, txt=f"COMBO x{self.multiplier}", c=GOLD, size=18))
            self.play("combo")
        if self.streak % HEART_STREAK == 0:
            self.queue_pickup("hearts")
            self.pops.append(dict(x=W / 2, y=110, life=1.6, txt=f"{self.streak} IN A ROW", c=GOLD))

    def lose_life(self):
        self.lives -= 1
        self.streak = 0
        if self.lives <= 0:
            self.game_over()

    def explode(self, b):
        """Clawd touched a bomb."""
        b["dead"] = True
        self.play("boom")
        bx, by = b["x"] + b["s"] / 2, b["y"] + b["s"] / 2
        self.burst(bx, by, BOMB_RED, 24, 280)
        self.burst(bx, by, GOLD, 14, 220)
        self.burst(bx, by, BOMB_BODY, 10, 180, size=5)
        self.rings.append(dict(x=bx, y=by, r=8.0, life=0.4, c=BOMB_RED))
        self.pops.append(dict(x=bx, y=by - 16, life=1.0, txt="BOOM", c=BOMB_RED, size=18))
        self.shake = 10
        self.p["vy"] = min(self.p["vy"], -380)
        self.p["on_ground"] = False
        self.lose_life()

    def fizzle(self, b):
        """A bomb that lands just puffs out."""
        b["dead"] = True
        self.play("fizzle")
        bx = b["x"] + b["s"] / 2
        self.burst(bx, min(b["y"] + b["s"] / 2, GROUND - 4), (90, 82, 102), 10, 90)
        self.dust.append(dict(x=bx, y=GROUND - 6, vx=0.0, r=6.0, life=0.8))

    def block_jump(self, x, y, color):
        """Jump off a block Clawd just broke in midair."""
        p = self.p
        p["vy"], p["jump_buffer"], p["block_grace"], p["dash"] = -JUMP_SPEED, 0.0, 0.0, 0.0
        self.play("blockjump")
        self.burst(x, y, color, 10, 160)
        self.rings.append(dict(x=x, y=y, r=6.0, life=0.3, c=color))
        self.ghosts.append([p["x"], p["y"], 0.18])

    def broke_in_air(self, x, y, color):
        """After a midair hit: jump off the block if jump was just pressed, otherwise a little bounce
        (and a short moment where pressing jump still counts)."""
        p = self.p
        if p["jump_buffer"] > 0:
            self.block_jump(x, y, color)
        else:
            p["vy"] = min(p["vy"], -BLOCK_BOUNCE)  # so air chains are possible
            p["block_grace"] = JUMP_WINDOW
            p["grace_at"] = (x, y, color)

    def burst(self, x, y, color, n, power, size=3):
        for _ in range(n):
            a = random.random() * math.tau
            v = power * (0.4 + random.random() * 0.8)
            self.parts.append(dict(x=x, y=y, vx=math.cos(a) * v, vy=math.sin(a) * v - power * 0.4,
                                   life=0.6 + random.random() * 0.4, c=color, s=size + random.random() * 3))

    def crash(self, x, color):
        """A block hitting the ground: debris, a shockwave ring and a dust cloud."""
        self.play("crash")
        self.burst(x, GROUND - 4, color, 18, 180)
        self.burst(x, GROUND - 4, color, 5, 140, size=6)  # a few big chunks
        self.burst(x, GROUND - 4, (90, 82, 102), 8, 120)
        self.rings.append(dict(x=x, y=GROUND, r=4.0, life=0.4, c=color))
        for _ in range(6):
            self.dust.append(dict(x=x + random.uniform(-14, 14), y=GROUND - random.uniform(2, 8),
                                  vx=random.uniform(-40, 40), r=random.uniform(4, 8), life=0.8))

    @property
    def bolt_power(self):
        """The bolt destroys more blocks the longer the match goes on."""
        return min(BOLT_MAX, BOLT_KILLS + int(self.t / BOLT_GROWTH))

    def zap(self):
        """Lightning: destroy the blocks closest to the ground."""
        self.play("zap")
        safe = [b for b in self.blocks if not b.get("bomb")]
        targets = sorted(safe, key=lambda b: -(b["y"] + b["s"]))[:self.bolt_power]
        if targets and self.bolt_power > BOLT_KILLS:
            self.pops.append(dict(x=W / 2, y=140, life=1.0, txt=f"ZAP x{self.bolt_power}", c=BOLT_COLOR, size=18))
        for b in targets:
            b["dead"] = True
            bx, by = b["x"] + b["s"] / 2, b["y"] + b["s"] / 2
            # jagged bolt from the sky down to the block
            pts, y = [(bx + random.uniform(-20, 20), -10)], -10
            while y < by - 30:
                y += random.uniform(24, 44)
                pts.append((bx + random.uniform(-18, 18), min(y, by)))
            pts.append((bx, by))
            self.strikes.append(dict(pts=pts, life=0.35))
            self.burst(bx, by, BOLT_COLOR, 16, 240)
            self.burst(bx, by, b["c"], 12, 200)
            self.rings.append(dict(x=bx, y=by, r=6.0, life=0.35, c=BOLT_COLOR))
            self.score += 1
            self.pops.append(dict(x=bx, y=by - 10, life=0.9, txt="+1", c=BOLT_COLOR))
        self.blocks = [b for b in self.blocks if not b["dead"]]
        self.flash = 0.18
        self.shake = max(self.shake, 6)
        if not targets:
            self.pops.append(dict(x=W / 2, y=140, life=1.0, txt="ZAP!", c=BOLT_COLOR))

    def update(self, dt, controls):
        for q in self.parts:
            q["life"] -= dt
            q["vy"] += 900 * dt
            q["x"] += q["vx"] * dt
            q["y"] += q["vy"] * dt
            if q["y"] > GROUND:
                q["y"] = GROUND
                q["vy"] *= -0.3
                q["vx"] *= 0.7
        self.parts = [q for q in self.parts if q["life"] > 0]
        if self.notice:
            self.notice["life"] -= dt
            if self.notice["life"] <= 0:
                self.notice = None
        if self.toast:
            self.toast["life"] -= dt
            if self.toast["life"] <= 0:
                self.toast = None
        for q in self.pops:
            q["life"] -= dt
            q["y"] -= 40 * dt
        self.pops = [q for q in self.pops if q["life"] > 0]
        self.shake = max(0.0, self.shake - dt * 30)
        self.flash = max(0.0, self.flash - dt)
        for q in self.trail:
            q["life"] -= dt
            q["x"] += q["vx"] * dt
            q["y"] += q["vy"] * dt
        self.trail = [q for q in self.trail if q["life"] > 0]
        for q in self.rings:
            q["life"] -= dt
            q["r"] += 140 * dt
        self.rings = [q for q in self.rings if q["life"] > 0]
        for q in self.dust:
            q["life"] -= dt
            q["x"] += q["vx"] * dt
            q["vx"] *= 0.94
            q["y"] -= 14 * dt
            q["r"] += 10 * dt
        self.dust = [q for q in self.dust if q["life"] > 0]
        for q in self.strikes:
            q["life"] -= dt
        self.strikes = [q for q in self.strikes if q["life"] > 0]

        p = self.p
        p["blink"] -= dt
        if p["blink"] < -3 - random.random() * 3:
            p["blink"] = 0.12

        self.dance_check(dt, controls)
        self.check_in -= dt
        if self.check_in <= 0:
            self.check_in = VERSION_CHECK
            self.check_version()
        self.wake = max(0.0, self.wake - dt)
        if self.mode == "resume":
            before = math.ceil(self.countdown)
            self.countdown -= dt
            if self.countdown <= 0:
                self.mode, self.wake = "play", 0.6
                self.play("wake")
                self.pops.append(dict(x=W / 2, y=240, life=0.7, txt="GO!", c=GOLD, size=30))
            elif math.ceil(self.countdown) < before:
                self.play("tick")
        if self.mode != "play":
            return
        self.t += dt

        left, right, jump = controls

        accel, top = (2600 if p["on_ground"] else 1800), 230
        if self.speed:
            accel, top = accel * SPEED_MULT, top * SPEED_MULT
            if p["vx"] and int(self.t * 60) % 3 == 0:
                self.ghosts.append([p["x"], p["y"], 0.18])  # afterimages while boosted
        direction = right - left
        p["dash_cd"] -= dt
        for g in self.ghosts:
            g[2] -= dt
        self.ghosts = [g for g in self.ghosts if g[2] > 0]
        if p["dash"] > 0:
            p["dash"] -= dt
            p["vx"] = p["dash_dir"] * DASH_SPEED
            if not p["on_ground"]:
                p["vy"] = min(p["vy"], 0.0)  # brief hang in the air while dashing
            self.ghosts.append([p["x"], p["y"], 0.18])
        elif direction:
            p["vx"] += direction * accel * dt
        else:
            f = (2200 if p["on_ground"] else 700) * dt
            p["vx"] = 0.0 if abs(p["vx"]) <= f else p["vx"] - math.copysign(f, p["vx"])
        if p["dash"] <= 0:
            p["vx"] = max(-top, min(top, p["vx"]))

        pressed = jump and not p.get("jump_held")
        p["jump_held"] = jump
        p["jump_buffer"] = JUMP_WINDOW if pressed else max(0.0, p["jump_buffer"] - dt)
        p["block_grace"] = max(0.0, p["block_grace"] - dt)
        wall = -1 if p["x"] <= 2 else (1 if p["x"] >= W - PW - 2 else 0)
        if jump and p["on_ground"]:
            p["vy"], p["on_ground"], p["jump_buffer"] = -JUMP_SPEED, False, 0.0
            self.play("jump")
        elif pressed and p["block_grace"] > 0 and not p["on_ground"]:
            self.block_jump(*p["grace_at"])  # jump pressed just after breaking a block
        elif pressed and wall and not p["on_ground"]:
            # wall jump: kick off the screen edge, up and away
            p["vy"], p["vx"], p["jump_buffer"] = -WALL_JUMP, -wall * WALL_KICK, 0.0
            self.play("walljump")
            p["dash"] = 0.0
            wx = 0 if wall < 0 else W
            for _ in range(10):
                self.parts.append(dict(x=wx, y=p["y"] + PH / 2 + random.uniform(-12, 12),
                                       vx=-wall * random.uniform(60, 200), vy=random.uniform(-120, 60),
                                       life=0.35 + random.random() * 0.25, c=random.choice((DIM, INK, EARTH)),
                                       s=random.choice((2, 3, 4))))
            self.ghosts.append([p["x"], p["y"], 0.18])
        elif wall and wall == direction and not p["on_ground"] and p["vy"] > WALL_SLIDE:
            # wall slide: holding into the wall slows the fall
            p["vy"] = WALL_SLIDE
            if random.random() < 0.5:
                self.parts.append(dict(x=0 if wall < 0 else W, y=p["y"] + PH - 6, vx=-wall * random.uniform(10, 40),
                                       vy=random.uniform(-40, 0), life=0.3, c=DIM, s=2))
        if not p["on_ground"] and not jump and p["vy"] < -200:
            p["vy"] = -200  # short hop on early release

        p["vy"] += 1500 * dt
        p["x"] += p["vx"] * dt
        p["y"] += p["vy"] * dt
        if p["x"] < 0:
            p["x"], p["vx"] = 0, 0.0
        if p["x"] > W - PW:
            p["x"], p["vx"] = W - PW, 0.0
        if p["y"] < 64:  # keep Clawd under the HUD
            p["y"], p["vy"] = 64, max(p["vy"], 0.0)
        if p["y"] >= GROUND - PH:
            p["y"], p["vy"], p["on_ground"], p["chain"], p["block_grace"] = GROUND - PH, 0.0, True, 0, 0.0
        if p["on_ground"] and p["vx"]:
            p["walk"] += abs(p["vx"]) * dt

        # gold block: every so often one shoots sideways across the screen, at a random height
        # (the high ones need wall jumps to reach)
        self.gold_in -= dt
        if self.gold_in <= 0:
            self.gold_in = random.uniform(*GOLD_EVERY)
            d = random.choice((-1, 1))
            self.runners.append(dict(d=d, x=-20.0 if d > 0 else W + 2.0, y=random.uniform(*GOLD_HEIGHT),
                                     v=random.uniform(*GOLD_SPEED), s=18, warn=GOLD_WARN, rot=0.0, emit=0.0))
            self.play("warn")
        for r in self.runners:
            if r["warn"] > 0:
                r["warn"] -= dt
                continue
            r["x"] += r["d"] * r["v"] * dt
            r["rot"] += r["d"] * -540 * dt
            r["emit"] -= dt
            if r["emit"] <= 0:
                r["emit"] = 0.015
                self.trail.append(dict(x=r["x"] + r["s"] / 2 - r["d"] * 8, y=r["y"] + random.random() * r["s"],
                                       vx=-r["d"] * random.uniform(20, 60), vy=random.uniform(-20, 20),
                                       life=0.5, max=0.5, c=random.choice((GOLD, BOLT_COLOR, INK)), s=random.choice((2, 3))))
            if (r["x"] < p["x"] + PW - 4 and r["x"] + r["s"] > p["x"] + 4
                    and r["y"] < p["y"] + PH - 6 and r["y"] + r["s"] > p["y"]):
                r["dead"] = True
                self.hit_block(dict(r, c=GOLD), air=not p["on_ground"], value=GOLD_POINTS)
                if not p["on_ground"]:
                    self.broke_in_air(r["x"] + r["s"] / 2, r["y"] + r["s"] / 2, GOLD)
                self.burst(r["x"] + r["s"] / 2, r["y"] + r["s"] / 2, BOLT_COLOR, 20, 260)
                self.rings.append(dict(x=r["x"] + r["s"] / 2, y=r["y"] + r["s"] / 2, r=6.0, life=0.4, c=GOLD))
                self.shake = max(self.shake, 4)
            elif r["x"] < -30 or r["x"] > W + 10:
                r["dead"] = True  # got away, no penalty
        self.runners = [r for r in self.runners if not r.get("dead")]
        self.magnet = max(0.0, self.magnet - dt)
        self.speed = max(0.0, self.speed - dt)

        self.spawn_in -= dt
        if self.spawn_in <= 0:
            self.spawn()
            self.spawn_in = self.difficulty()[1] * (0.75 + random.random() * 0.5)

        pcx = p["x"] + PW / 2
        for b in self.blocks:
            b["y"] += b["vy"] * dt
            if self.magnet and not b.get("bomb"):
                pull = pcx - (b["x"] + b["s"] / 2)
                b["x"] += max(-MAGNET_PULL * dt, min(MAGNET_PULL * dt, pull))
            b["rot"] += b["spin"] * dt
            b["emit"] = b.get("emit", 0.0) - dt
            if b["emit"] <= 0 and b["y"] > 0:
                b["emit"] = 0.03
                self.trail.append(dict(x=b["x"] + random.random() * b["s"], y=b["y"] + random.random() * 4,
                                       vx=random.uniform(-8, 8), vy=random.uniform(-14, 4),
                                       life=0.8, max=0.8, c=b["c"], s=random.choice((2, 3, 3))))
            hit = (b["x"] < p["x"] + PW - 4 and b["x"] + b["s"] > p["x"] + 4
                   and b["y"] < p["y"] + PH - 6 and b["y"] + b["s"] > p["y"])
            if hit and b.get("bomb"):
                self.explode(b)
                if self.lives <= 0:
                    break
            elif hit:
                self.hit_block(b, air=not p["on_ground"])
                if not p["on_ground"]:
                    self.broke_in_air(b["x"] + b["s"] / 2, b["y"] + b["s"] / 2, b["c"])
            elif b["y"] + b["s"] >= GROUND:
                if b.get("bomb"):
                    self.fizzle(b)
                    continue
                b["dead"] = True
                self.crash(b["x"] + b["s"] / 2, b["c"])
                self.shake = 8
                self.lose_life()
                if self.lives <= 0:
                    break
        self.blocks = [b for b in self.blocks if not b["dead"]]

        # heart pickups drift down with a gentle sway; missing one costs nothing
        for h in self.hearts:
            h["t"] += dt
            h["y"] += HEART_FALL * dt
            hx = h["x"] + math.sin(h["t"] * 2) * 14
            if hx - 10 < p["x"] + PW - 4 and hx + 10 > p["x"] + 4 and h["y"] - 9 < p["y"] + PH - 6 and h["y"] + 9 > p["y"]:
                h["dead"] = True
                self.burst(hx, h["y"], CLAWD, 20, 200)
                self.play("heart")
                if self.lives < MAX_LIVES:
                    self.lives += 1
                    self.pops.append(dict(x=hx, y=h["y"] - 10, life=1.0, txt="+1 LIFE", c=CLAWD))
                else:
                    self.score += 5
                    self.pops.append(dict(x=hx, y=h["y"] - 10, life=1.0, txt="+5", c=GOLD))
            elif h["y"] + 9 >= GROUND:
                h["dead"] = True
                self.burst(hx, GROUND - 4, EARTH, 8, 100)
        self.hearts = [h for h in self.hearts if not h["dead"]]

        # lightning bolt pickups: catching one strikes the blocks nearest the ground
        for o in self.bolts:
            o["t"] += dt
            o["y"] += BOLT_FALL * dt
            bx = o["x"] + math.sin(o["t"] * 2.6) * 10
            if bx - 9 < p["x"] + PW - 4 and bx + 9 > p["x"] + 4 and o["y"] - 12 < p["y"] + PH - 6 and o["y"] + 12 > p["y"]:
                o["dead"] = True
                self.burst(bx, o["y"], BOLT_COLOR, 18, 200)
                self.zap()
            elif o["y"] + 12 >= GROUND:
                o["dead"] = True
                self.burst(bx, GROUND - 4, BOLT_COLOR, 8, 100)
        self.bolts = [o for o in self.bolts if not o["dead"]]

        # magnet pickups: catching one pulls blocks toward Clawd for a few seconds
        for m in self.magnets:
            m["t"] += dt
            m["y"] += MAGNET_FALL * dt
            mx = m["x"] + math.sin(m["t"] * 2.2) * 12
            if mx - 11 < p["x"] + PW - 4 and mx + 11 > p["x"] + 4 and m["y"] - 11 < p["y"] + PH - 6 and m["y"] + 11 > p["y"]:
                m["dead"] = True
                self.magnet = MAGNET_TIME
                self.play("magnet")
                self.burst(mx, m["y"], MAGNET_COLOR, 18, 200)
                self.rings.append(dict(x=pcx, y=p["y"] + PH / 2, r=8.0, life=0.4, c=MAGNET_COLOR))
                self.pops.append(dict(x=mx, y=m["y"] - 14, life=1.0, txt="MAGNET", c=MAGNET_COLOR, size=14))
            elif m["y"] + 11 >= GROUND:
                m["dead"] = True
                self.burst(mx, GROUND - 4, MAGNET_COLOR, 8, 100)
        self.magnets = [m for m in self.magnets if not m["dead"]]

        # speed pickups drop at random times, at least SPEED_COOLDOWN seconds apart
        if "boosts" not in self.pickup_queue:
            self.speed_in -= dt
            if self.speed_in <= 0:
                self.queue_pickup("boosts")
        self.pickup_wait -= dt
        if self.pickup_queue and self.pickup_wait <= 0:
            self.pickup_wait = PICKUP_GAP
            kind = self.pickup_queue.pop(0)
            if kind == "boosts":  # the cooldown counts from when it actually drops
                self.speed_in = SPEED_COOLDOWN + random.random() * SPEED_RANDOM
            getattr(self, kind).append(dict(x=40 + random.random() * (W - 80), y=-24.0, t=0.0, dead=False))

        # speed pickups: catching one makes Clawd run faster for a few seconds
        for o in self.boosts:
            o["t"] += dt
            o["y"] += SPEED_FALL * dt
            ox = o["x"] + math.sin(o["t"] * 2.4) * 12
            if ox - 12 < p["x"] + PW - 4 and ox + 12 > p["x"] + 4 and o["y"] - 9 < p["y"] + PH - 6 and o["y"] + 9 > p["y"]:
                o["dead"] = True
                self.speed = SPEED_TIME
                self.play("speed")
                self.burst(ox, o["y"], SPEED_COLOR, 18, 200)
                self.rings.append(dict(x=pcx, y=p["y"] + PH / 2, r=8.0, life=0.4, c=SPEED_COLOR))
                self.pops.append(dict(x=ox, y=o["y"] - 14, life=1.0, txt="SPEED", c=SPEED_COLOR, size=14))
            elif o["y"] + 9 >= GROUND:
                o["dead"] = True
                self.burst(ox, GROUND - 4, SPEED_COLOR, 8, 100)
        self.boosts = [o for o in self.boosts if not o["dead"]]

    # ---------- draw ----------
    def text(self, s, x, y, size, color, align="center", surf=None):
        f = self.font(size)
        img, shadow = f.render(s, False, color), f.render(s, False, NIGHT)
        r = img.get_rect()
        if align == "right":
            r.midright = (x, y)
        elif align == "left":
            r.midleft = (x, y)
        else:
            r.center = (x, y)
        surf = surf or self.canvas
        surf.blit(shadow, r.move(2, 2))
        surf.blit(img, r)

    def button(self, label, x, y, w, h, action, size=12, color=INK, surf=None):
        """A tappable box centered on x, y (touch version). Taps are matched against these on the next frame."""
        surf = surf or self.canvas
        r = pygame.Rect(0, 0, w, h)
        r.center = (x, y)
        down = any(r.collidepoint(pos) for pos in self.pointers.values())
        surf.fill(EARTH if down else NIGHT, r)
        pygame.draw.rect(surf, color, r, 2)
        self.text(label, x, y, size, color, surf=surf)
        self.buttons.append((r, action))

    def draw_pad(self):
        """The touch controls under the game, or a keyboard while typing a name."""
        s = self.screen
        s.fill(NIGHT, (0, H, W, PAD))
        if self.mode == "entry":
            pitch = 39
            for i, row in enumerate(KEY_ROWS):
                x0 = (W - (10 if i == 3 else len(row)) * pitch) / 2 + 1.5
                y = H + 28 + i * 40
                for k, ch in enumerate(row):
                    self.button(ch, x0 + k * pitch + 18, y, 36, 36, lambda ch=ch: self.type_letter(ch), 14, surf=s)
            wide = pitch * 1.5 - 3
            x = x0 + 7 * pitch + wide / 2
            self.button("DEL", x, y, wide, 36, self.erase_letter, 11, DIM, surf=s)
            self.button("OK", x + pitch * 1.5, y, wide, 36, self.submit_name, 13, CLAWD, surf=s)
            return
        held, live = self.held(), self.mode == "play"
        for name, r in self.pad.items():
            on = live and name in held
            col = INK if on else (DIM if live else EARTH)
            s.fill(EARTH if on else PANEL, r)
            pygame.draw.rect(s, col, r, 2)
            cx, cy = r.center
            if name in ("left", "right"):
                d = -1 if name == "left" else 1
                pygame.draw.polygon(s, col, [(cx - d * 14, cy - 22), (cx + d * 16, cy), (cx - d * 14, cy + 22)])
            else:
                pygame.draw.polygon(s, col, [(cx, cy - 32), (cx - 20, cy - 6), (cx + 20, cy - 6)])
                self.text("JUMP", cx, cy + 22, 12, col, surf=s)

    def pixel_sprite(self, rows, x, y, size, color):
        for r, row in enumerate(rows):
            for k, ch in enumerate(row):
                if ch != ".":
                    self.canvas.fill(color, (x + k * size, y + r * size, size, size))

    def pixel_heart(self, x, y, size, color):
        for r, row in enumerate(HEART):
            for k, ch in enumerate(row):
                if ch == "X":
                    self.canvas.fill(color, (x + k * size, y + r * size, size, size))

    def draw_table(self, top):
        self.text("HIGH SCORES", W / 2, top, 18, GOLD)
        status = {"online": ("ONLINE  EVERYONE'S SCORES", (111, 183, 168)),
                  "offline": ("OFFLINE  SHOWING SAVED LIST", DIM),
                  "connecting": ("CONNECTING...", DIM)}[self.board.status]
        self.text(status[0], W / 2, top + 20, 9, status[1])
        top += 14
        scores = self.scores
        if not scores:
            self.text("no scores yet", W / 2, top + 40, 12, DIM)
            return
        for i, s in enumerate(scores):
            y = top + 32 + i * 22
            mine = self.mode == "over" and s.get("key") == self.last_key
            col = CLAWD if mine else INK
            self.text(f"{i + 1}.", 92, y, 13, col if mine else DIM, "right")
            self.text(s["name"], 104, y, 13, col, "left")
            self.text(str(s["score"]), W - 80, y, 13, col, "right")

    def draw_help(self):
        c = self.canvas
        self.text("HOW TO PLAY", W / 2, 60, 20, GOLD)
        sections = [
            ("CONTROLS", [("ARROWS", "move"), ("JUMP" if TOUCH else "UP", "jump"),
                          ("BLOCKS", "jump as you hit one"),
                          ("TAP TAP", "dash left or right"), ("WALL", "jump again off the edge")]),
            ("SCORING", [("COMBO", "every 10 in a row adds x1"), ("AIR CHAIN", "hit more before landing"),
                         ("GOLD", "jump to catch it  +10")]),
            ("WATCH OUT", [("BOMBS", "never touch them"), ("3 MISSES", "and you are out")]),
        ]
        y = 92
        for title, rows in sections:
            self.text(title, 52, y, 11, CLAWD, "left")
            y += 18
            for key, desc in rows:
                self.text(key, 64, y, 10, {"BOMBS": BOMB_RED, "GOLD": GOLD}.get(key, INK), "left")
                self.text(desc, 160, y, 10, DIM, "left")
                y += 16
            y += 6
        # pickups, drawn with their in-game sprites
        self.text("PICKUPS", 52, y, 11, CLAWD, "left")
        y += 20
        self.pixel_heart(64, y - 9, 3, CLAWD)
        self.text("extra life", 96, y, 10, DIM, "left")
        y += 22
        for r, row in enumerate(BOLT):
            for k, ch in enumerate(row):
                if ch == "X":
                    c.fill(BOLT_COLOR, (66 + k * 3, y - 12 + r * 3, 3, 3))
        self.text("zaps low blocks  stronger over time", 96, y, 10, DIM, "left")
        y += 22
        for r, row in enumerate(MAGNET):
            for k, ch in enumerate(row):
                if ch != ".":
                    c.fill(MAGNET_TIP if ch == "T" else MAGNET_COLOR, (64 + k * 3, y - 10 + r * 3, 3, 3))
        self.text("pulls blocks to you", 96, y, 10, DIM, "left")
        y += 22
        self.pixel_sprite(SPEED, 64, y - 7, 3, SPEED_COLOR)
        self.text("run faster for a while", 96, y, 10, DIM, "left")

    def draw_zzz(self, body, now):
        """Little Zs drifting up from a sleeping Clawd."""
        for i in range(3):
            k = (now / 1800 + i / 3) % 1  # 0 to 1 as each Z rises
            x = body.right - 4 + k * 26 + math.sin(k * 6) * 3
            y = body.top - 8 - k * 60
            self.text("Z", x, y, int(12 + k * 12), lerp(INK, PANEL, k ** 3))

    def draw_home_help(self):
        """How to put the game on a phone's home screen, so it opens full screen like an app."""
        self.text("ADD TO HOME SCREEN", W / 2, 70, 18, GOLD)
        self.text("open it full screen, like an app", W / 2, 94, 10, DIM)
        y = 134
        for title, steps, note in (
            ("IPHONE  (SAFARI)", [("tap the share button", SHARE), ("scroll down, tap ADD TO HOME SCREEN", None),
                                 ("tap ADD", None)], "no share button? tap ... first"),
            ("ANDROID  (CHROME)", [("tap the menu at the top right", MENU), ("tap ADD TO HOME SCREEN", None),
                                  ("or INSTALL APP, then tap ADD", None)], None),
        ):
            self.text(title, 40, y, 12, CLAWD, "left")
            y += 26
            for i, (step, icon) in enumerate(steps):
                self.text(f"{i + 1}.", 52, y, 11, GOLD, "left")
                self.text(step, 74, y, 10, INK, "left")
                if icon:
                    x = 74 + self.font(10).size(step)[0] + 10
                    self.pixel_sprite(icon, x, y - len(icon) * 3 // 2, 3, GOLD)
                y += 24
            if note:
                self.text(note, 74, y - 4, 9, DIM, "left")
                y += 18
            y += 18
        self.text("then open Block Catch from your home screen", W / 2, y + 4, 10, DIM)

    def draw(self, now):
        c = self.canvas
        c.fill(PANEL)
        self.buttons = []
        ox = int((random.random() - 0.5) * self.shake)
        oy = int((random.random() - 0.5) * self.shake)

        for x, y, s, ph in self.stars:
            a = 0.25 + 0.25 * math.sin(now / 900 + ph)
            col = tuple(int(PANEL[i] + (DIM[i] - PANEL[i]) * a) for i in range(3))
            c.fill(col, (x + ox, y + oy, s, s))

        c.fill(EARTH, (0, GROUND + oy, W, H - GROUND))
        for x in range(0, W, 16):
            c.fill(DIM, (x + 4 + ox, GROUND + 6 + oy, 6, 2))

        for q in self.trail:
            c.fill(lerp(PANEL, q["c"], q["life"] / q["max"] * 0.9), (q["x"] + ox, q["y"] + oy, q["s"], q["s"]))

        p = self.p
        for b in self.blocks:
            danger = max(0.0, (b["y"] - 250) / (GROUND - 250))
            a = 0.15 + danger * 0.5
            mark = tuple(int(EARTH[i] + (b["c"][i] - EARTH[i]) * a) for i in range(3))
            c.fill(mark, (b["x"] + ox, GROUND - 3 + oy, b["s"], 3))
            s = b["s"]
            cx, cy = b["x"] + s / 2 + ox, b["y"] + s / 2 + oy
            if b.get("bomb"):
                lit = int(now / (90 if danger > 0.5 else 180)) % 2 == 0
                glow = pygame.Surface((s * 2 + 8, s * 2 + 8), pygame.SRCALPHA)
                pygame.draw.circle(glow, (*BOMB_RED, 70 if lit else 35), (s + 4, s + 4), s)
                c.blit(glow, (cx - s - 4, cy - s - 4))
                pygame.draw.circle(c, BOMB_RED if lit else (176, 54, 62), (cx, cy), s / 2 + 3)
                pygame.draw.circle(c, BOMB_BODY, (cx, cy), s / 2)
                c.fill((70, 66, 84), (cx - 5, cy - 5, 3, 3))  # shine
                c.fill(DIM, (cx - 1, cy - s / 2 - 5, 3, 5))  # fuse
                spark = GOLD if int(now / 60) % 2 else (255, 250, 220)
                c.fill(spark, (cx - 2 + random.randint(-1, 1), cy - s / 2 - 9 + random.randint(-1, 1), 4, 4))
                continue
            if self.magnet:
                # dotted pull line from the block to Clawd
                tx, ty = p["x"] + PW / 2 + ox, p["y"] + PH / 2 + oy
                n = max(1, int(math.hypot(tx - cx, ty - cy) / 14))
                for k in range(1, n):
                    f = (k + (now / 120) % 1) / n
                    c.fill(lerp(PANEL, MAGNET_COLOR, 0.5), (cx + (tx - cx) * f - 1, cy + (ty - cy) * f - 1, 2, 2))
            blk = pygame.Surface((s, s), pygame.SRCALPHA)
            blk.fill(b["c"])
            blk.fill(tuple(min(255, v + 50) for v in b["c"]), (0, 0, s, 4))
            blk.fill(tuple(int(v * 0.78) for v in b["c"]), (0, s - 4, s, 4))
            rot = pygame.transform.rotate(blk, b["rot"])
            c.blit(rot, rot.get_rect(center=(b["x"] + s / 2 + ox, b["y"] + s / 2 + oy)))

        p = self.p
        if self.mode == "title" and not p["dance"] > 0:
            p["y"] = GROUND - PH - abs(math.sin(now / 300)) * 18
        frame = 0 if not p["on_ground"] or not p["vx"] else 1 + int(p["walk"] / 18) % 2
        hop = sway = 0
        if p["dance"] > 0:
            p["y"] = GROUND - PH
            into = DANCE_TIME - p["dance"]
            beat, phase = divmod(into / DANCE_BEAT, 1)
            beat = int(beat)
            frame = 1 + beat % 2  # step side to side
            hop = -abs(math.sin(phase * math.pi)) * (16 if p["dance"] < DANCE_BEAT * 2 else 7)
            sway = (3 if beat % 2 else -3)
        asleep = self.mode in ("paused", "resume")
        sprite = self.sprites[(frame, p["blink"] > 0 or asleep)]
        squash = -0.05 if not p["on_ground"] else 0
        if asleep:
            squash = 0.04 * math.sin(now / 700)  # slow breathing
        if squash:
            sprite = pygame.transform.scale(sprite, (int(PW * (1 + squash)), int(PH * (1 - squash))))
        if p["dance"] > 0:
            sprite = pygame.transform.rotate(sprite, 12 if beat % 2 else -12)  # wiggle with the beat
        for gx, gy, life in self.ghosts:
            ghost = self.sprites[(0, False)].copy()
            ghost.set_alpha(int(255 * life / 0.18 * 0.4))
            c.blit(ghost, (round(gx) + ox, round(gy) + oy))
        if self.magnet:
            r = int(36 + 4 * math.sin(now / 80))
            aura = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(aura, (*MAGNET_COLOR, 40), (r, r), r)
            pygame.draw.circle(aura, (*MAGNET_COLOR, 120), (r, r), r, 2)
            c.blit(aura, (p["x"] + PW / 2 - r + ox, p["y"] + PH / 2 - r + oy))
        shadow = pygame.Surface((PW - 12, 4), pygame.SRCALPHA)
        shadow.fill((*NIGHT, 64))
        c.blit(shadow, (p["x"] + 6 + ox, GROUND - 2 + oy))
        body = sprite.get_rect(midbottom=(round(p["x"] + PW / 2 + sway) + ox, round(p["y"] + PH + hop) + oy))
        clawd = [(sprite, body)]
        hat = self.viewing if self.mode == "title" else self.worn
        if hat >= 0:
            art = self.hat_art[hat] if hat in self.unlocked else self.hat_shadow[hat]
            clawd.append((art, art.get_rect(midbottom=(body.centerx, body.top))))
        c.blits(clawd)

        for q in self.dust:
            r = int(q["r"])
            puff = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(puff, (*DIM, int(90 * q["life"] / 0.8)), (r, r), r)
            c.blit(puff, (q["x"] - r + ox, q["y"] - r + oy))
        for q in self.rings:
            col = lerp(PANEL, q["c"], q["life"] / 0.4)
            rect = pygame.Rect(0, 0, int(q["r"] * 2), max(4, int(q["r"] * 0.7)))
            rect.center = (q["x"] + ox, q["y"] + oy)
            pygame.draw.ellipse(c, col, rect, 2)
        for q in self.parts:
            c.fill(q["c"], (q["x"] + ox, q["y"] + oy, q["s"], q["s"]))
        for q in self.strikes:
            pts = [(x + ox, y + oy) for x, y in q["pts"]]
            k = q["life"] / 0.35
            pygame.draw.lines(c, lerp(PANEL, q.get("c", BOLT_COLOR), k), False, pts, 6)
            pygame.draw.lines(c, lerp(PANEL, (255, 255, 240), k), False, pts, 2)
        for o in self.bolts:
            bx = o["x"] + math.sin(o["t"] * 2.6) * 10
            pulse = 1 + 0.15 * math.sin(o["t"] * 9)
            glow = pygame.Surface((44, 44), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*BOLT_COLOR, 55), (22, 22), int(17 * pulse))
            c.blit(glow, (bx - 22 + ox, o["y"] - 22 + oy))
            for r, row in enumerate(BOLT):
                for k, ch in enumerate(row):
                    if ch == "X":
                        c.fill(BOLT_COLOR, (bx - 9 + k * 3 + ox, o["y"] - 12 + r * 3 + oy, 3, 3))
        for r in self.runners:
            cy = r["y"] + r["s"] / 2 + oy
            if r["warn"] > 0:
                if int(now / 110) % 2 == 0:  # blinking arrow at the edge it will come from
                    ex = 14 if r["d"] > 0 else W - 14
                    pygame.draw.polygon(c, GOLD, [(ex - r["d"] * 6, cy - 9), (ex + r["d"] * 8, cy), (ex - r["d"] * 6, cy + 9)])
                    self.text("!", ex + r["d"] * 18, cy, 16, GOLD)
                continue
            s = r["s"]
            cx = r["x"] + s / 2 + ox
            glow = pygame.Surface((s * 3, s * 3), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*GOLD, 60), (s * 1.5, s * 1.5), s * 1.3)
            c.blit(glow, (cx - s * 1.5, cy - s * 1.5))
            blk = pygame.Surface((s, s), pygame.SRCALPHA)
            blk.fill(GOLD)
            blk.fill(BOLT_COLOR, (0, 0, s, 4))
            blk.fill((176, 128, 52), (0, s - 4, s, 4))
            blk.fill((255, 250, 220), (3, 6, 3, 3))  # glint
            rot = pygame.transform.rotate(blk, r["rot"])
            c.blit(rot, rot.get_rect(center=(cx, cy)))
        for m in self.magnets:
            mx = m["x"] + math.sin(m["t"] * 2.2) * 12
            pulse = 1 + 0.15 * math.sin(m["t"] * 9)
            glow = pygame.Surface((44, 44), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*MAGNET_COLOR, 55), (22, 22), int(17 * pulse))
            c.blit(glow, (mx - 22 + ox, m["y"] - 22 + oy))
            for r, row in enumerate(MAGNET):
                for k, ch in enumerate(row):
                    if ch != ".":
                        col = MAGNET_TIP if ch == "T" else MAGNET_COLOR
                        c.fill(col, (mx - 10 + k * 3 + ox, m["y"] - 10 + r * 3 + oy, 3, 3))
        for o in self.boosts:
            bx = o["x"] + math.sin(o["t"] * 2.4) * 12
            pulse = 1 + 0.15 * math.sin(o["t"] * 9)
            glow = pygame.Surface((44, 44), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*SPEED_COLOR, 55), (22, 22), int(17 * pulse))
            c.blit(glow, (bx - 22 + ox, o["y"] - 22 + oy))
            self.pixel_sprite(SPEED, bx - 12 + ox, o["y"] - 7 + oy, 3, SPEED_COLOR)
        for h in self.hearts:
            hx = h["x"] + math.sin(h["t"] * 2) * 14
            pulse = 1 + 0.12 * math.sin(h["t"] * 8)
            glow = pygame.Surface((40, 40), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*CLAWD, 50), (20, 20), int(16 * pulse))
            c.blit(glow, (hx - 20 + ox, h["y"] - 20 + oy))
            self.pixel_heart(hx - 10 + ox, h["y"] - 9 + oy, 3, CLAWD)

        for q in self.pops:
            self.text(q["txt"], q["x"] + ox, q["y"] + oy, q.get("size", 14), q["c"])
        if self.wake > 0 and self.mode == "play":
            self.text("!", body.centerx, body.top - 18 - (8 if self.worn >= 0 else 0), 20, GOLD)

        if self.flash > 0:
            veil = pygame.Surface((W, H), pygame.SRCALPHA)
            veil.fill((255, 250, 220, int(90 * self.flash / 0.18)))
            c.blit(veil, (0, 0))

        for i in range(max(3, self.lives)):
            self.pixel_heart(14 + i * 26, 16, 3, CLAWD if i < self.lives else EARTH)
        # streak meter: fills toward the next heart drop
        if self.mode in ("play", "paused"):
            fill = (self.streak % HEART_STREAK) / HEART_STREAK
            c.fill(EARTH, (14, 40, 124, 4))
            c.fill(GOLD, (14, 40, int(124 * fill), 4))
            if self.streak:
                label = f"STREAK {self.streak}" + (f"  x{self.multiplier}" if self.multiplier > 1 else "")
                self.text(label, 14, 54, 10, GOLD if self.streak >= 10 else DIM, "left")
            bar_y = 66
            for left, total, col in ((self.magnet, MAGNET_TIME, MAGNET_COLOR), (self.speed, SPEED_TIME, SPEED_COLOR)):
                if left:
                    c.fill(EARTH, (14, bar_y, 124, 4))
                    c.fill(col, (14, bar_y, int(124 * left / total), 4))
                    bar_y += 8
        self.text(str(self.score), W - 16, 26, 22, INK, "right")
        self.text(f"BEST {self.best}", W - 16, 48, 10, DIM, "right")

        if self.mode != "play":
            veil = pygame.Surface((W, H), pygame.SRCALPHA)
            veil.fill((*NIGHT, 160))
            c.blit(veil, (0, 0))
            blink_on = int(now / 500) % 2 == 0
            if self.mode == "title":
                up = 36 if TOUCH else 0
                self.text("BLOCK", W / 2, 170 - up, 52, CLAWD)
                self.text("CATCH", W / 2, 222 - up, 52, INK)
                self.text("hit the blocks before they land", W / 2, 272 - up, 12, DIM)
                if TOUCH:
                    self.button("PLAY", W / 2, 282, 150, 44, self.start, 18, CLAWD)
                    self.button("HOW TO PLAY", W / 2 - 92, 328, 170, 30, self.go("help"), 10)
                    self.button("HIGH SCORES", W / 2 + 92, 328, 170, 30, self.show_board, 10)
                    if not self.on_home_screen:
                        self.button("ADD TO HOME SCREEN", W / 2, 366, 354, 30, self.go("home"), 10, GOLD)
                else:
                    if blink_on:
                        self.text("PRESS SPACE", W / 2, 330, 16, INK)
                    self.text("I  HELP     H  SCORES     M  SOUND", W / 2, 362, 10, DIM)
                if self.update_ready:
                    if TOUCH:
                        self.button("NEW VERSION  TAP TO UPDATE", W / 2, 80, 300, 28, self.update_now, 10, GOLD)
                    else:
                        self.text("A NEW VERSION IS OUT", W / 2, 80, 11, GOLD)
                if self.viewing == -1:
                    name, col = "NO HAT", DIM
                elif self.viewing in self.unlocked:
                    name, col = HATS[self.viewing][0], GOLD
                else:
                    name, col = f"LOCKED  {HATS[self.viewing][1]} IN A ROW", DIM
                if TOUCH:
                    self.button("<", 30, 406, 44, 36, lambda: self.pick_hat(-1), 14, DIM)
                    self.button(">", W - 30, 406, 44, 36, lambda: self.pick_hat(1), 14, DIM)
                    self.text(name, W / 2, 400, 11, col)
                    self.text(f"HATS {len(self.unlocked)}/{len(HATS)}", W / 2, 416, 9, DIM)
                else:
                    self.text(f"<  {name}  >", W / 2, 398, 11, col)
                    self.text(f"HATS {len(self.unlocked)}/{len(HATS)}", W / 2, 414, 9, DIM)
                c.blits(clawd)  # Clawd stays bright on the title so the hat picker is easy to see
            elif self.mode == "home":
                self.draw_home_help()
                self.button("BACK", W / 2, 454, 140, 34, self.go("title"), 12, DIM)
            elif self.mode == "help":
                self.draw_help()
                if TOUCH:
                    self.button("BACK", W / 2 - 76, 454, 140, 34, self.go("title"), 12, DIM)
                    self.button("PLAY", W / 2 + 76, 454, 140, 34, self.start, 12, CLAWD)
                elif blink_on:
                    self.text("SPACE TO PLAY   ESC TO GO BACK", W / 2, 446, 11, DIM)
            elif self.mode == "board":
                self.draw_table(110)
                if TOUCH:
                    self.button("BACK", W / 2 - 76, 404, 140, 34, self.go("title"), 12, DIM)
                    self.button("PLAY", W / 2 + 76, 404, 140, 34, self.start, 12, CLAWD)
                elif blink_on:
                    self.text("SPACE TO PLAY   ESC TO GO BACK", W / 2, 400, 11, DIM)
            elif self.mode in ("paused", "resume"):
                c.blits(clawd)  # Clawd stays bright while napping
                self.draw_zzz(body, now)
                if self.mode == "resume":
                    n = math.ceil(self.countdown)
                    grow = 1 + 0.4 * (self.countdown - n + 1) ** 3  # each number pops in, then settles
                    self.text(str(n), W / 2, 220, int(56 * grow), GOLD)
                    self.text("WAKING UP", W / 2, 280, 13, DIM)
                else:
                    self.text("PAUSED", W / 2, 220, 40, INK)
                    if TOUCH:
                        self.button("RESUME", W / 2, 290, 170, 44, self.resume, 16, CLAWD)
                    elif blink_on:
                        self.text("PRESS SPACE TO RESUME", W / 2, 280, 13, DIM)
            elif self.mode == "entry":
                top_before = max([s["score"] for s in self.scores] + [0])
                self.text("GAME OVER", W / 2, 150, 40, CLAWD)
                self.text(f"{self.score} POINT{'' if self.score == 1 else 'S'}", W / 2, 200, 22, INK)
                self.text("NEW HIGH SCORE" if self.score > top_before else "YOU MADE THE TOP 10", W / 2, 246, 14, GOLD)
                self.text("TYPE YOUR NAME", W / 2, 290, 11, DIM)
                box = pygame.Rect(W / 2 - 120, 306, 240, 36)
                c.fill(NIGHT, box)
                pygame.draw.rect(c, CLAWD, box, 2)
                self.text(self.name + ("_" if blink_on and len(self.name) < NAME_LEN else " "), W / 2, 324, 18, INK)
                self.text("TAP OK TO SAVE" if TOUCH else "ENTER TO SAVE", W / 2, 362, 11, DIM)
            else:
                self.text("GAME OVER", W / 2, 70, 34, CLAWD)
                self.text(f"{self.score} POINT{'' if self.score == 1 else 'S'}", W / 2, 110, 18, INK)
                self.draw_table(150)
                if TOUCH:
                    self.button("MENU", W / 2 - 76, 432, 140, 34, lambda: self.reset("title"), 12, DIM)
                    self.button("PLAY AGAIN", W / 2 + 76, 432, 140, 34, self.start, 12, CLAWD)
                else:
                    if blink_on:
                        self.text("SPACE TO PLAY AGAIN", W / 2, 420, 13, DIM)
                    self.text("ESC  MAIN MENU", W / 2, 440, 10, DIM)

        if TOUCH and self.mode != "entry":
            if self.mode == "play":
                self.button("II", W / 2 - 24, 26, 40, 32, self.pause, 12, DIM)
            self.sound_button(W / 2 + 24 if self.mode == "play" else W / 2, 26)
        if self.notice:
            self.text(self.notice["txt"], W / 2, 64, 12, INK)

        if self.toast:
            t = self.toast
            slide = min(1.0, (TOAST_TIME - t["life"]) / 0.25, t["life"] / 0.25)  # slide in, slide out
            box = pygame.Rect(0, 0, 250, 56)
            box.midtop = (W / 2, int(-60 + 140 * slide))
            c.fill(NIGHT, box)
            pygame.draw.rect(c, GOLD, box, 2)
            icon = self.hat_icons[t["hat"]]
            c.blit(icon, icon.get_rect(center=(box.left + 34, box.centery)))
            self.text("NEW HAT UNLOCKED", box.left + 66, box.top + 18, 11, GOLD, "left")
            self.text(HATS[t["hat"]][0], box.left + 66, box.top + 38, 13, INK, "left")

        self.screen.blit(c, (0, 0))
        if TOUCH:
            self.draw_pad()
        pygame.display.flip()

    async def run(self):
        while True:
            ms = self.clock.tick(60 if WEB else 120)
            if ms > 400 and self.mode in ("play", "resume"):
                self.pause()  # the game was frozen a while, e.g. the phone switched apps
            dt = min(0.033, ms / 1000)
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    return
                if e.type in (pygame.WINDOWFOCUSLOST, pygame.WINDOWHIDDEN, pygame.WINDOWMINIMIZED):
                    self.pause()
                if e.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
                    pid = (e.touch_id, e.finger_id)
                    kind = {pygame.FINGERDOWN: "down", pygame.FINGERMOTION: "move", pygame.FINGERUP: "up"}[e.type]
                    if kind == "down" or pid in self.pointers:
                        w, h = self.screen.get_size()
                        self.pointer(kind, pid, (e.x * w, e.y * h))
                    continue
                if e.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP):
                    if not getattr(e, "touch", False):  # touches also arrive as mouse events; handled above
                        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                            self.pointer("down", "mouse", e.pos)
                        elif e.type == pygame.MOUSEMOTION and "mouse" in self.pointers:
                            self.pointer("move", "mouse", e.pos)
                        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                            self.pointer("up", "mouse", e.pos)
                    continue
                if self.mode == "entry":
                    if pygame.time.get_ticks() < self.entry_ready:
                        continue
                    if e.type == pygame.TEXTINPUT:
                        typed = "".join(ch for ch in e.text.upper() if ch.isalnum() or ch in " -_.!")
                        self.name = (self.name + typed)[:NAME_LEN]
                    elif e.type == pygame.KEYDOWN:
                        if e.key == pygame.K_BACKSPACE:
                            self.name = self.name[:-1]
                        elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            self.submit_name()
                    continue
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_m:
                        self.toggle_sound()
                        continue
                    if e.key == pygame.K_h and self.mode in ("title", "over"):
                        self.last_key = None
                        self.board.refresh()
                        self.mode = "board"
                        continue
                    if e.key == pygame.K_i and self.mode == "title":
                        self.mode = "help"
                        continue
                    if e.key == pygame.K_ESCAPE and self.mode == "over":
                        self.reset("title")
                        continue
                    if e.key == pygame.K_ESCAPE and self.mode in ("board", "help"):
                        self.mode = "title"
                        continue
                    if self.mode == "title" and e.key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
                        self.pick_hat(-1 if e.key in (pygame.K_LEFT, pygame.K_a) else 1)
                        continue
                    if e.key in (pygame.K_LEFT, pygame.K_a):
                        self.tap_direction(-1)
                    elif e.key in (pygame.K_RIGHT, pygame.K_d):
                        self.tap_direction(1)
                    if e.key in (pygame.K_p, pygame.K_ESCAPE):
                        if self.mode in ("play", "resume"):
                            self.pause()
                        elif self.mode == "paused":
                            self.resume()
                    elif e.key in (pygame.K_SPACE, pygame.K_RETURN) and self.mode not in ("play", "resume"):
                        self.start()
            self.update(dt, self.controls())
            self.update_music()
            self.draw(pygame.time.get_ticks())
            await asyncio.sleep(0)  # lets the browser run between frames


async def main():
    await Game().run()
    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
