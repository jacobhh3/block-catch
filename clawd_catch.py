"""Block Catch - hit the falling blocks before they reach the ground."""
import asyncio
import colorsys
import datetime
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
PAD = 214 if TOUCH else 0  # height of the touch controls strip under the game
# touch buttons: left edge, top (down from the top of the strip), width, height. ZAP is a short bar above JUMP;
# the arrows run the full height.
PAD_KEYS = [("left", 10, 16, 98, 182), ("right", 114, 16, 98, 182), ("zap", 218, 16, 172, 38),
            ("jump", 218, 60, 172, 138)]
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
BOLT_KILLS = 2  # blocks a zap destroys from one bolt, nearest the ground first
ZAP_MAX = 5  # each extra bolt caught before using the zap makes it destroy one more, up to this many
BOLT_COLOR = (255, 226, 102)
COMBO_STEP = 10  # hits in a row per extra score multiplier
MAX_MULT = 4
BOMB_AFTER = 15  # seconds before bombs start falling
BOMB_RED = (232, 72, 72)
BOMB_BODY = (16, 15, 22)
DIZZY_TIME = 1.0  # seconds of stars after bonking a bomb with his head
HOTFOOT_TIME = 0.5  # seconds of kicking legs and a fiery behind after landing on a bomb (or until he lands)
JUMP_SPEED = 640  # upward speed of a jump, from the ground or off a block
BLOCK_BOUNCE = 260  # little hop when Clawd breaks a block in midair without jumping
JUMP_WINDOW = 0.15  # seconds a jump press counts before or after breaking a block, to jump off it
RESUME_COUNT = 3  # seconds of countdown after unpausing, while Clawd wakes up
LEAVE_COUNT = 3  # seconds to change your mind after choosing MAIN MENU on the pause screen
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
FLIP_SPEED = 120  # sideways speed that turns a block jump into a front flip (slower: a springy stretch)
SLIDE_LEAN = 27  # degrees Clawd tilts on a wall slide, so his arm and legs both touch the wall
SLIDE_PANIC = 0.12  # chance a wall slide is a panicky scramble instead of a cool lean
GOLD_POINTS = 10  # times the combo multiplier
JACKPOT_TIME = 0.9  # how long the JACKPOT! text shows after catching a gold block
MAGNET_EVERY = 25  # blocks hit (in total) that drop a magnet
MAGNET_TIME = 1.0
MAGNET_FALL = 50
MAGNET_PULL = 160  # sideways pull speed on blocks while the magnet is active
FALL_GAP = 6  # min space kept between falling blocks and bombs
MAGNET_COLOR = (224, 92, 108)
MAGNET_TIP = (220, 220, 232)
SHIELD_COOLDOWN = 30  # seconds after one shield drops before the next can
SHIELD_RANDOM = 20  # plus up to this many random extra seconds
SHIELD_FALL = 55
SHIELD_COLOR = (127, 200, 255)
SHIELD_PIXELS = {"X": SHIELD_COLOR, "W": (230, 246, 255)}
SHIELD_STYLE = "glow"  # how the shield outline looks: "glow" (breathing) or "sparkles"
CLAWD = (217, 119, 87)
EARTH = (58, 51, 70)
GOLD = (232, 176, 75)
FIRE = (BOMB_RED, GOLD, (255, 150, 60))  # flames off a hot foot
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

# Clawd's colors, picked on the main menu. Each one is unlocked by a challenge (see Game.unlock_color).
# A color is one RGB, or a list of them for a speckled look.
PURPLE = BLOCK_COLORS[1]
SKINS = [
    ("CLAWD", CLAWD, None),
    ("AIRTIME RICKY", (238, 236, 232), "air"),
    ("OBSESSED OSCAR", (150, 104, 222), "purple"),
    ("RAGING RYAN", (222, 58, 58), "bombs"),
    ("LIGHTNING LANGLEY", (246, 210, 72), "zaps"),
    ("EARTHQUAKE BEN", [(122, 112, 124), (122, 112, 124), (96, 86, 102), (150, 140, 144), (82, 73, 98)], "landings"),
    # added later: the third item is a challenge from COLOR_GOALS, and a word for a look is an animation (skin_pixel)
    ("FROSTY FRANK", [(170, 220, 250), (200, 235, 255), (140, 200, 240)], "december"),
    ("GOLDEN GABE", [(240, 190, 80), (255, 220, 120), (210, 150, 50)], "golds50"),
    ("MINTY MAYA", (140, 225, 190), "score1000"),
    ("SMOKY SAM", [(110, 104, 126), (92, 86, 108), (128, 122, 142)], "games50"),
    ("BUBBLEGUM BELLA", (250, 150, 200), "hearts100"),
    ("TOXIC TONY", [(150, 230, 60), (120, 200, 40), (180, 245, 90)], "bombs10"),
    ("LAVA LUKE", [(240, 90, 40), (255, 150, 50), (200, 50, 40)], "hotfoots50"),
    ("OCEAN OLIVIA", [(40, 130, 170), (60, 160, 200), (30, 100, 150)], "walljumps500"),
    ("PUMPKIN PETE", (240, 140, 50), "october"),
    ("CHERRY CHLOE", (176, 30, 72), "combo4"),
    ("SLIME STEVE", [(90, 190, 90), (60, 150, 70), (120, 210, 110)], "bounces500"),
    ("COTTON CANDY CARL", [(250, 170, 210), (160, 210, 250)], "dances50"),
    ("CAMO CODY", [(110, 130, 80), (80, 96, 60), (140, 120, 80), (60, 70, 50)], "time600"),
    ("ZEBRA ZACK", "zebra", "dashes1000"),
    ("TROPICAL TRISTEN", "tropical", "streak100"),
    ("NINJA NICK", "ninja", "dashhits100"),
    ("NEON NOAH", [(60, 240, 230), (240, 70, 220)], "air50"),
    ("PEACHY PAIGE", (252, 196, 170), "landings5000"),
    ("ROBO ROB", "robo", "zapped1000"),
    ("BLOCKBUSTER BRAD", "blocks", "blocks5000"),
    ("STARLIGHT STELLA", "stella", "days30"),
    ("GALAXY GRACE", "galaxy", "sky1000"),
    ("PLATINUM PARKER", "platinum", "score5000"),
    ("DIAMOND DANI", "diamond", "score10000"),
    ("COSMIC COLE", "cosmic", "score20000"),
    ("GUARDIAN GRANT", "guardian", "shields1000"),
    ("GHOST GARY", "ghost", "hats20"),
    ("THUNDER THEO", "thunder", "bolts1000"),
    ("HEARTFELT HOPE", "love", "hearts1000"),
    ("JACKPOT JACK", "jackpot", "golds1000"),
    ("KRYSTAL KAI", "krystal", "blocks20000"),
    ("KABOOM KEVIN", "kaboom", "bombs1000"),
    ("PHOENIX PHIL", "phoenix", "hotfoots1000"),
    ("ANCIENT ARCHIE", "archie", "days100"),
    ("OBSIDIAN OWEN", "obsidian", "hours50"),
    ("LEGENDARY LEO", "leo", "everything"),
    ("MAGNETIC MILO", "magnet", "magnets1000"),
]
# A color challenge: (what's counted, goal, what the menu says). See Game.stat_value for the counts.
COLOR_GOALS = {
    "december": ("month", 12, "PLAY IN DECEMBER"),
    "october": ("month", 10, "PLAY IN OCTOBER"),
    "golds50": ("golds_total", 50, "CATCH 50 GOLD BLOCKS"),
    "score1000": ("score", 1000, "SCORE 1000 IN ONE GAME"),
    "games50": ("games", 50, "PLAY 50 GAMES"),
    "hearts100": ("hearts", 100, "CATCH 100 HEARTS"),
    "bombs10": ("bombs_game", 10, "HIT 10 BOMBS IN ONE GAME"),
    "hotfoots50": ("hotfoots", 50, "GET 50 HOT FOOTS"),
    "walljumps500": ("walljumps", 500, "WALL JUMP 500 TIMES"),
    "combo4": ("combo4", 10, "REACH COMBO X4 10 TIMES"),
    "bounces500": ("block_bounces_total", 500, "BOUNCE OFF 500 BLOCKS"),
    "dances50": ("dances", 50, "DANCE 50 TIMES"),
    "time600": ("time", 600, "SURVIVE 10 MINUTES IN ONE GAME"),
    "dashes1000": ("dashes", 1000, "DASH 1000 TIMES"),
    "streak100": ("streak", 100, "BREAK 100 BLOCKS WITHOUT LOSING A LIFE"),
    "dashhits100": ("dash_hits", 100, "HIT 100 BLOCKS MID-DASH"),
    "air50": ("chain", 50, "50 IN A ROW IN THE AIR"),
    "landings5000": ("landings", 5000, "LAND 5000 TIMES"),
    "zapped1000": ("zapped", 1000, "ZAP 1000 BLOCKS"),
    "blocks5000": ("blocks", 5000, "BREAK 5000 BLOCKS"),
    "days30": ("days", 30, "PLAY ON 30 DIFFERENT DAYS"),
    "sky1000": ("sky_total", 1000, "TOUCH THE SKY 1000 TIMES"),
    "score5000": ("score", 5000, "SCORE 5000 IN ONE GAME"),
    "score10000": ("score", 10000, "SCORE 10000 IN ONE GAME"),
    "score20000": ("score", 20000, "SCORE 20000 IN ONE GAME"),
    "shields1000": ("shield_saves", 1000, "GET SAVED BY 1000 SHIELDS"),
    "hats20": ("hats", 20, "UNLOCK 20 HATS"),
    "bolts1000": ("bolts", 1000, "CATCH 1000 BOLTS"),
    "hearts1000": ("hearts", 1000, "CATCH 1000 HEARTS"),
    "golds1000": ("golds_total", 1000, "CATCH 1000 GOLD BLOCKS"),
    "blocks20000": ("blocks", 20000, "BREAK 20000 BLOCKS"),
    "bombs1000": ("bombs", 1000, "HIT 1000 BOMBS"),
    "hotfoots1000": ("hotfoots", 1000, "GET 1000 HOT FOOTS"),
    "days100": ("days", 100, "PLAY ON 100 DIFFERENT DAYS"),
    "hours50": ("playtime", 50 * 3600, "PLAY FOR 50 HOURS"),
    "magnets1000": ("magnets_total", 1000, "CATCH 1000 MAGNETS"),
    "everything": ("colors", 0, "UNLOCK EVERY OTHER COLOR"),  # goal filled in below
}
COLOR_GOALS["everything"] = ("colors", len(SKINS) - 1, "UNLOCK EVERY OTHER COLOR")
GAME_STATS = {"score", "streak", "chain", "time", "bombs_game", "month"}  # counted in one game, no progress shown
TIER_NAMES = ["COMMON", "UNCOMMON", "RARE", "VERY RARE", "LEGENDARY"]  # for colors and hats
# the color picker goes easiest to hardest (saves keep each color's place in SKINS); every animated
# color is harder than every still one. Names on the menu are colored by their tier.
COLOR_TIERS = [
    ((120, 210, 140), ["CLAWD", "PUMPKIN PETE", "FROSTY FRANK", "OBSESSED OSCAR", "RAGING RYAN", "AIRTIME RICKY",
                       "MINTY MAYA", "COTTON CANDY CARL"]),  # common
    ((127, 200, 255), ["TOXIC TONY", "GOLDEN GABE", "LAVA LUKE", "SMOKY SAM", "LIGHTNING LANGLEY", "EARTHQUAKE BEN",
                       "CHERRY CHLOE", "BUBBLEGUM BELLA", "OCEAN OLIVIA", "SLIME STEVE", "NINJA NICK"]),  # uncommon
    ((232, 176, 75), ["ZEBRA ZACK", "NEON NOAH", "CAMO CODY", "PEACHY PAIGE"]),  # rare
    ((240, 110, 90), ["TROPICAL TRISTEN", "PLATINUM PARKER", "BLOCKBUSTER BRAD", "GHOST GARY", "STARLIGHT STELLA",
                      "ROBO ROB", "DIAMOND DANI", "GALAXY GRACE", "KABOOM KEVIN", "PHOENIX PHIL", "THUNDER THEO",
                      "JACKPOT JACK", "HEARTFELT HOPE", "COSMIC COLE", "KRYSTAL KAI", "MAGNETIC MILO"]),  # very rare
    ((200, 140, 255), ["GUARDIAN GRANT", "ANCIENT ARCHIE", "OBSIDIAN OWEN", "LEGENDARY LEO"]),  # legendary
]
_SKIN_INDEX = {sk[0]: i for i, sk in enumerate(SKINS)}
COLOR_ORDER = [_SKIN_INDEX[name] for _, names in COLOR_TIERS for name in names]
TIER_COLOR = {_SKIN_INDEX[name]: col for col, names in COLOR_TIERS for name in names}
COLOR_TIER_NAME = {_SKIN_INDEX[name]: TIER_NAMES[t] for t, (_, names) in enumerate(COLOR_TIERS) for name in names}
assert sorted(COLOR_ORDER) == list(range(len(SKINS)))
AIR_STREAK = 10  # blocks broken in a row without touching the ground (lightning doesn't count)
PURPLE_GOAL = 50  # purple blocks broken in one game
BOMB_GOAL = 3  # bombs touched in one game
ZAP_GOAL = 100  # lightning bolts caught, over all games
LANDING_GOAL = 1000  # landings on the ground, over all games

# Hats, drawn 13 wide like Clawd and sat on top of his head. The second item is what unlocks it:
# a number is a streak to reach (blocks broken without losing a life), a word is a challenge from HAT_GOALS.
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
    # steel, horn, army green, visor
    "S": (190, 196, 210), "s": (120, 126, 146), "H": (240, 232, 210), "h": (196, 180, 150),
    "A": (118, 138, 84), "a": (76, 92, 56), "V": (110, 210, 245), "v": (50, 120, 180),
    # black and dark grey (light enough to see on the night sky), leaf greens
    "Z": (64, 60, 80), "z": (112, 106, 128), "E": (90, 200, 110), "e": (50, 130, 70),
    # welding glass, pale leaf vein
    "D": (34, 70, 48), "j": (170, 240, 160),
    # see-through helmet glass and UFO beam, flame orange
    "q": (170, 220, 255, 45), "x": (170, 255, 170, 70), "X": (210, 255, 210, 40), "O": (240, 140, 50),
}


def _with(rows, *changes):
    """A copy of a hat's rows with some swapped out: _with(rows, (row index, new row), ...)."""
    rows = list(rows)
    for i, row in changes:
        rows[i] = row
    return rows


def _ufo(k):
    """The UFO with its rim lights chased k steps round and its beam shimmering."""
    lights = "SYSSRSSYSSRSS"
    beam = ["....xxxxx....", "...xxxxxxx...", "..xxxxxxxxx.."]
    return [".....VVV.....", "....VwVVV....", "..SSSSSSSSS..", lights[-k:] + lights[:-k] if k else lights,
            ".sssssssssss."] + [b.replace("x", "X") if (i + k) % 2 else b for i, b in enumerate(beam)]


def _disco(k):
    """A mirror ball turning k steps, with sparkles flashing around it."""
    ball = [".....XXX.....", "....XXXXX....", "....XXXXX....", "....XXXXX....", ".....XXX.....", "............."]
    rows = [["SWsS"[(r + c + k) % 4] if ch == "X" else ch for c, ch in enumerate(row)] for r, row in enumerate(ball)]
    for n, (r, c) in enumerate([(0, 2), (1, 10), (3, 1), (4, 11), (5, 3), (5, 9)]):
        if (n + k) % 3 == 0:
            rows[r][c] = "w"
    return ["".join(r) for r in rows]


_PROPELLER = ["..BBBB.RRRR..", "......Y......", "....RYBRY....", "...BBRRRBB...", "..YYYYYYYYY.."]
_SPACE = ["......R......", "......W......", "....WWWWW....", "..WWqqqqqWW..", ".WqqqqqqqqqW.", ".WqWqqqqqqqW.",
          ".WqqqqqqqqqW.", ".WqqqqqqqqqW.", "..WWWWWWWWW.."]
_ARMY = ["....AAAAA....", "...AaAAAAAA..", "..AAzjzjzAA..", "..AazzzzzaA..", ".aaaaaaaaaaa."]
_KINGS = ["......w......", ".....wYw.....", "..Y...Y...Y..", "..YYRRYRRYY..", "..YRRRRRRRY..", "..YCYRYUYCY..",
          "..yyyyyyyyy..", ".WZWWWZWWWZW."]
_DRAGON = ["H...........H", "hH.........Hh", ".hH.eEEEe.Hh.", "..heeEeEeeh..", "..eEeeeeeEe..", "..eeeEeEeee..",
           "..ee.eee.ee..", "..ee.eee.ee..", "...W.W.W.W..."]
_FLAME = ["..R...R...R..", ".RO..ROR..OR.", ".ROY.RYO.YOR.", "..YYYYYYYYY..", "..yyyyyyyyy.."]
_SAMURAI = ["Y...........Y", ".Y.........Y.", "..Y...w...Y..", "...YrrYrrY...", "..rRRRRRRRr..", ".rRRRRRRRRRr.",
            "rrY.......Yrr"]
_CLOUD = ["....sSSs.....", "..sSSSSSSSs..", ".sSSSSSSSSSs.", ".zzzzzzzzzzz."]
_RAIN = [["..l...l...l..", "....l...l...."], ["....l...l....", "..l...l...l.."]]
_VALKYRIE = ["W...........W", "WW.........WW", ".WW.SSSSS.WW.", "..WSSSSSSSW..", "..SsSsSsSsS..", "..sssssssss.."]
_DEMOLITION = [".....OOO.....", ".....OOO.....", "....YYYYY....", "...YYwYYYY...", "..YYYYYYYYY..",
               "yyyyyyyyyyyyy"]
_HEART_CROWN = ["....RR.RR....", "....RLRRR....", "..Y..RRR..Y..", "..YY..R..YY..", "..YYYYYYYYY..",
                "..yLyyRyyLy.."]
_HEART_CROWN_BIG = ["...RRR.RRR...", "...RLRRRRR...", "..YRRRRRRRY..", "..YY.RRR.YY..", "..YYYYRYYYY..",
                    "..yLyyRyyLy.."]
_LIGHTNING_CROWN = ["...Y...Y...Y.", "..YY..YY..YY.", "..Y...Y...Y..", "..zzzzzzzzz..", "..zYzzYzzYz.."]
_SCRAP_CROWN = ["..s...S...s..", "..S..sSs..S..", "..RRRRBBBBB..", "..RRRRBBBBB..", "..rrrrbbbbb.."]
_SHIELD_CROWN = [".lll.lll.lll.", ".lWl.lWl.lWl.", "..l...l...l..", "..SSSSSSSSS..", "..sSsSsSsSs.."]


def _bright(rows, cols, a, b):
    """Rows with color a turned into b, only in the given columns (to light up one point of a crown)."""
    return ["".join(b if ch == a and c in cols else ch for c, ch in enumerate(row)) for row in rows]


_PHARAOH = [".....YYY.....", "...YYYwYYY...", "..BBBBBBBBB..", ".YYYYYYYYYYY.", ".BB.......BB.", ".YY.......YY.",
            ".BB.......BB.", ".YY.......YY."]

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
    ("VIKING HELMET", "bomb_bounces", ["H...........H", "hH..SSSSS..Hh", ".hHSSSSSSSHh.", "..SsSsSsSsS..",
                                       "..sssssssss..", "......s......"]),
    ("ARMY HELMET", "hour", _ARMY),
    ("SPACE HELMET", "airtime", _SPACE),
    ("PIRATE HAT", "golds", ["...ZZZZZZZ...", "..ZZZWZWZZZ..", "..ZZZZWZZZZ..", "ZZZZZZZZZZZZZ", ".zzzzzzzzzzz.",
                             ".......ZZZ...", ".......ZZZ...", "........Z...."]),
    ("CHEF HAT", "score500", ["...WW.WW.WW..", "..WWWWWWWWW..", "..WWWWWWWWW..", "...WWWWWWW...", "...zzzzzzz..."]),
    ("WIZARD HAT", "dances", ["......U......", ".....UUw.....", "....UUUUU....", "...UwUUUUU...", "..UUUUUwUUU..",
                              "KKKKKKKKKKKKK"]),
    ("BEANIE", "games", ["......W......", "....RRRRR....", "...RWRWRWR...", "..RRRRRRRRR..", "..rrrrrrrrr.."]),
    ("HARD HAT", "blocks", ["....YYYYY....", "...YYwYYYY...", "..YYYYYYYYY..", "yyyyyyyyyyyyy"]),
    ("FIREFIGHTER", "hotfoots", ["....RRRRR....", "...RRYYYRR...", "..RRRYRYRRR..", "rrrrrrrrrrrrr"]),
    ("KNIGHT HELMET", "shield_saves", [".....RRr.....", "....RR.......", "...SSSSSSS...", "..SsSSSSSsS..",
                                       "..SSSSSSSSS..", "..SZZZZZZZS..", "..SSsSsSsSS..", "...sssssss..."]),
    ("SOMBRERO", "walljumps", ["......T......", ".....TNT.....", "....TNNNT....", "...RYRYRYR...", "TNNNNNNNNNNNT",
                               ".nnnnnnnnnnn."]),
    ("HALO", "clean", ["...wwwwwww...", "..w.......w..", "...YYYYYYY...", "............."]),
    ("DEVIL HORNS", "bombs", ["..R.......R..", "..Rr.....rR..", "...rr...rr..."]),
    ("BUNNY EARS", "jumps", ["...W.....W...", "..WPW...WPW..", "..WPW...WPW..", "..WPW...WPW..", "...WW...WW..."]),
    ("CAT EARS", "flips", ["..N.......N..", "..NP.....PN..", "..NNN...NNN.."]),
    ("PROPELLER CAP", "air100", _PROPELLER),
    ("GRAD CAP", "score2000", [".ZZZZZZZZZZZ.", "ZZZZZZYZZZZZZ", "...zzzzzzzY..", "...zzzzzzzY.."]),
    ("HEADPHONES", "playtime", ["...zzzzzzz...", "..z.......z..", ".z.........z.", ".RR.......RR.", ".RR.......RR."]),
    ("FLOWER CROWN", "hearts", [".LP.wY.LP.wY.", ".PL.Yw.PL.Yw.", "eEeEeEeEeEeEe"]),
    ("ROBOT ANTENNA", "zapped", ["......R......", "......z......", "......z......", "....zzzzz....", "...zSSSSSz..."]),
    ("SANTA HAT", "december", ["..........W..", "........RRW..", ".....RRRRr...", "...RRRRRRR...", "..WWWWWWWWW.."]),
    ("WITCH HAT", "october", [".......K.....", "......KK.....", ".....KKKK....", "....KGGGGK...", "KKKKKKKKKKKKK"]),
    ("CAPTAIN HAT", "days", ["...WWWWWWW...", "..WWWWYWWWW..", "..ZZZZZZZZZ..", "..zzzzzzzzzz."]),
    ("MUSHROOM CAP", "block_bounces", ["....RRRRR....", "..RRWRRRWRR..", ".RRRRRWRRRRR.", ".WWWWWWWWWWW."]),
    ("NINJA BAND", "dashes", ["..RRRSSSRRRR.", "..rrrSsSrrrRR", "...........rR"]),
    ("JESTER HAT", "jester", ["R...........B", "rR.........Bb", ".RR..YYY..BB.", "..RRRBBBBBB..", "..YYYYYYYYY.."]),
    ("WELDING MASK", "magnets_total", ["...zzzzzzz...", "..zZZZZZZZz..", "..ZZZZZZZZZ..", "..ZDDDDDDDZ..",
                                       "..ZDeDDDDDZ..", "..ZDDDDDDDZ..", "...ZZZZZZZ..."]),
    ("USHANKA", "walljumps200", ["....nNNNn....", "...NNNNNNN...", "..NNNNNNNNN..", ".TTTTTRTTTTT.", ".TTTRRRRRTTT.",
                            ".TTTTRTRTTTT.", ".NN.......NN.", ".nN.......Nn."]),
    ("SPROUT", "sky_total", [".......EE....", "......EEje...", "......Ejee...", ".....EjEe....",
                                    ".....Eje.....", "......e......", "......e......", "......e......"]),
    ("KING'S CROWN", "allhats", _KINGS),
    ("DRAGON HELM", "score10000", _DRAGON),
    ("UFO", "sky500", _ufo(0)),
    ("FLAME CROWN", "hotfoots1000", _FLAME),
    ("SAMURAI HELMET", "playtime10", _SAMURAI),
    ("SUNGLASSES", "score1000", ["..zwZZzwZZz..", "...ZZZ.ZZZ..."]),
    ("BOW", "games25", [".....LP...PL.", ".....LPPpPPL.", ".....LP...PL."]),
    ("FEZ", "hearts50", ["....RRRRZ....", "....RRRRRZ...", "...RRRRRRRZ..", "...rrrrrrrZ.."]),
    ("STORM CLOUD", "zapped5000", _CLOUD + _RAIN[0]),
    ("VALKYRIE HELM", "walljumps5000", _VALKYRIE),
    ("DISCO BALL", "days30", _disco(0)),
    ("DEMOLITION HAT", "blocks25000", _DEMOLITION),
    ("PHARAOH", "golds500", _PHARAOH),
    ("HEART CROWN", "hearts2000", _HEART_CROWN),
    ("LIGHTNING CROWN", "bolts2000", _LIGHTNING_CROWN),
    ("SCRAP CROWN", "magnets2000", _SCRAP_CROWN),
    ("SHIELD CROWN", "shields250", _SHIELD_CROWN),
]
# animated hats: (frames per second, frames). The propeller only spins while he's in the air.
HAT_ANIM = {
    "PROPELLER CAP": (16, [_PROPELLER, _with(_PROPELLER, (0, ".....BRR.....")),
                           _with(_PROPELLER, (0, "..RRRR.BBBB..")), _with(_PROPELLER, (0, ".....RBB....."))]),
    "UFO": (8, [_ufo(k) for k in range(6)]),
    "FLAME CROWN": (8, [_FLAME, _with(_FLAME, (0, ".R....R....R."), (1, "..RO.RORO.RO."), (2, ".ORY.OYR.YRO.")),
                        _with(_FLAME, (0, "...R..R..R..."), (1, ".ROR.ROR.ROR."), (2, ".OYO.OYO.OYO."))]),
    "SPACE HELMET": (2, [_SPACE, _with(_SPACE, (0, "......r......"))]),  # blinking antenna
    "ARMY HELMET": (3, [_with(_ARMY, (2, f"..AAz{c}z{c}zAA..")) for c in "jEeE"]),  # night vision glowing
    "KING'S CROWN": (3, [_KINGS, _with(_KINGS, (5, "..YwYRYUYCY..")), _KINGS, _with(_KINGS, (5, "..YCYRYwYCY.."))]),
    "DRAGON HELM": (3, [_DRAGON] + [_with(_DRAGON, (6, f"..ee{c}eee{c}ee.."), (7, f"..ee{c}eee{c}ee.."))
                                    for c in "rRr"]),  # eyes glowing red
    "SAMURAI HELMET": (2, [_SAMURAI, _with(_SAMURAI, (0, "w...........w"), (2, "..Y...Y...Y.."))]),
    "STORM CLOUD": (6, [_CLOUD + _RAIN[k % 2] for k in range(6)] + [_CLOUD + ["......YY.....", ".....YY......"],
                                                                    _CLOUD + _RAIN[1]]),
    "VALKYRIE HELM": (6, [_VALKYRIE,
                          [".............", "W...........W", "WW..SSSSS..WW", ".WWSSSSSSSWW.", "..SsSsSsSsS..",
                           "..sssssssss.."],
                          [".............", ".............", "....SSSSS....", ".WWSSSSSSSWW.", "WWSsSsSsSsSWW",
                           "W.sssssssss.W"],
                          [".............", "W...........W", "WW..SSSSS..WW", ".WWSSSSSSSWW.", "..SsSsSsSsS..",
                           "..sssssssss.."]]),  # wings flapping
    "DISCO BALL": (6, [_disco(k) for k in range(12)]),
    "DEMOLITION HAT": (8, [_DEMOLITION, _with(_DEMOLITION, (0, "..w..wOO..w.."), (1, ".....wOO.....")),
                           _with(_DEMOLITION, (0, ".....OwO....."), (1, ".....OwO.....")),
                           _with(_DEMOLITION, (0, ".....OOw....."), (1, ".....OOw....."))]),  # warning light
    "HEART CROWN": (8, [_HEART_CROWN, _HEART_CROWN_BIG] * 2 + [_HEART_CROWN] * 4),  # lub-dub, pause
    "LIGHTNING CROWN": (6, [_bright(_LIGHTNING_CROWN, range(c, c + 3), "Y", "w") for c in (2, 6, 10)]
                        + [_LIGHTNING_CROWN, [r.replace("Y", "w") for r in _LIGHTNING_CROWN], _LIGHTNING_CROWN]),
    "SCRAP CROWN": (5, [_SCRAP_CROWN, [".....sSs.....", "..s...S...s.."] + _SCRAP_CROWN[2:]]),  # bits jiggling
    "SHIELD CROWN": (3, [_bright(_SHIELD_CROWN, range(c, c + 3), "l", "B") for c in (1, 5, 9)]),
    "PHARAOH": (3, [_PHARAOH, [row.translate(str.maketrans("YB", "BY")) for row in _PHARAOH]]),
}
HAT_AIR_ONLY = {"PROPELLER CAP"}
HAT_SPRING = {"SPROUT"}  # bends and wobbles as Clawd moves (see Game.swing_sprout)
HAT_BOB = {"UFO": 5, "STORM CLOUD": 3, "DISCO BALL": 3}  # floating hats drift up and down this many pixels
# hats that hang down over Clawd's head (rows below the top of his head), like a mask over his eyes
HAT_DROP = {"WELDING MASK": 5, "USHANKA": 3, "SPACE HELMET": 5, "KNIGHT HELMET": 5, "PIRATE HAT": 4,
            "HEADPHONES": 3, "NINJA BAND": 3, "VIKING HELMET": 2, "KING'S CROWN": 1, "DRAGON HELM": 5,
            "SAMURAI HELMET": 2, "SUNGLASSES": 4, "BOW": 1, "FEZ": 1,
            "VALKYRIE HELM": 1, "PHARAOH": 4, "DEMOLITION HAT": 1, "HEART CROWN": 1,
            "LIGHTNING CROWN": 1, "SCRAP CROWN": 1, "SHIELD CROWN": 1}
# brimmed hats sit one row down, resting on his head
HAT_DROP.update({n: 1 for n in ["BALL CAP", "COWBOY HAT", "TOP HAT", "ARMY HELMET", "CHEF HAT", "BEANIE", "HARD HAT",
                                "FIREFIGHTER", "SOMBRERO", "FLOWER CROWN", "GRAD CAP", "SANTA HAT", "WITCH HAT",
                                "CAPTAIN HAT", "MUSHROOM CAP"]})
# A hat challenge: (goal, where it's counted, what the menu says). "total" counts over all games (saved),
# "game" counts in one game, and "event" is a one-off that's either done or not.
HAT_GOALS = {
    "bomb_bounces": (25, "total", "BOUNCE OFF 25 BOMBS"),
    "hour": (3600, "game", "SURVIVE 1 HOUR IN ONE GAME"),
    "airtime": (300, "game", "STAY IN THE AIR FOR 5 MINUTES STRAIGHT"),
    "golds": (20, "game", "CATCH 20 GOLD IN ONE GAME"),
    "score500": (500, "game", "SCORE 500 IN ONE GAME"),
    "dances": (10, "total", "DANCE 10 TIMES"),
    "games": (10, "total", "PLAY 10 GAMES"),
    "blocks": (1000, "total", "BREAK 1000 BLOCKS"),
    "hotfoots": (100, "total", "GET 100 HOT FOOTS"),
    "shield_saves": (5, "total", "GET SAVED BY 5 SHIELDS"),
    "walljumps": (1000, "total", "WALL JUMP 1000 TIMES"),
    "clean": (240, "game", "4 MINUTES WITHOUT LOSING A LIFE"),
    "bombs": (50, "total", "HIT 50 BOMBS"),
    "jumps": (500, "total", "JUMP 500 TIMES"),
    "flips": (200, "game", "200 FRONT FLIPS IN ONE GAME"),
    "air100": (100, "game", "100 AIR CHAIN IN A ROW"),
    "score2000": (2000, "game", "SCORE 2000 IN ONE GAME"),
    "playtime": (3600, "total", "PLAY FOR 1 HOUR"),
    "hearts": (500, "total", "CATCH 500 HEARTS"),
    "zapped": (500, "total", "ZAP 500 BLOCKS"),
    "december": (12, "event", "PLAY IN DECEMBER"),
    "october": (10, "event", "PLAY IN OCTOBER"),
    "days": (7, "total", "PLAY ON 7 DIFFERENT DAYS"),
    "block_bounces": (50, "game", "BOUNCE OFF 50 BLOCKS IN ONE GAME"),
    "dashes": (200, "total", "DASH 200 TIMES"),
    "jester": (1, "game", "LOSE YOUR LAST LIFE RIGHT AFTER A SHIELD"),
    "magnets_total": (100, "total", "CATCH 100 MAGNETS"),
    "walljumps200": (200, "total", "WALL JUMP 200 TIMES"),
    "sky_total": (50, "total", "TOUCH THE SKY 50 TIMES"),
    "allhats": (0, "total", "UNLOCK EVERY OTHER HAT"),  # goal filled in below
    "score10000": (10000, "game", "SCORE 10000 IN ONE GAME"),
    "sky500": (500, "total", "TOUCH THE SKY 500 TIMES"),
    "playtime10": (10 * 3600, "total", "PLAY FOR 10 HOURS"),
    "score1000": (1000, "game", "SCORE 1000 IN ONE GAME"),
    "games25": (25, "total", "PLAY 25 GAMES"),
    "hearts50": (50, "total", "CATCH 50 HEARTS"),
    "zapped5000": (5000, "total", "ZAP 5000 BLOCKS"),
    "walljumps5000": (5000, "total", "WALL JUMP 5000 TIMES"),
    "days30": (30, "total", "PLAY ON 30 DIFFERENT DAYS"),
    "golds500": (500, "total", "CATCH 500 GOLD BLOCKS"),
    "blocks25000": (25000, "total", "BREAK 25000 BLOCKS"),
    "hearts2000": (2000, "total", "CATCH 2000 HEARTS"),
    "bolts2000": (2000, "total", "CATCH 2000 BOLTS"),
    "magnets2000": (2000, "total", "CATCH 2000 MAGNETS"),
    "shields250": (250, "total", "GET SAVED BY 250 SHIELDS"),
    "hotfoots1000": (1000, "total", "GET 1000 HOT FOOTS"),
}
HAT_GOALS["allhats"] = (len(HATS) - 1, "total", "UNLOCK EVERY OTHER HAT")
# challenges that read another challenge's counter (a second, bigger goal for the same thing)
HAT_STAT = {"walljumps200": "walljumps", "sky500": "sky_total", "playtime10": "playtime", "games25": "games",
            "hearts50": "hearts", "zapped5000": "zapped", "walljumps5000": "walljumps", "golds500": "golds_total",
            "blocks25000": "blocks", "hearts2000": "hearts", "magnets2000": "magnets_total",
            "shields250": "shield_saves", "hotfoots1000": "hotfoots"}
# everything counted over all games (saved with the hats)
TOTAL_STATS = [k for k, (_, scope, _) in HAT_GOALS.items() if scope == "total" and k not in ("days", "days30", "allhats", "bolts2000") and k not in HAT_STAT] + [
    "golds_total", "block_bounces_total", "combo4", "dash_hits", "best_score", "total_score"]
# hat tiers (TIER_NAMES), like the colors': the picker goes easiest to hardest and names are colored by tier
HAT_TIERS = [
    ((120, 210, 140), ["PARTY HAT", "BALL CAP", "COWBOY HAT", "TOP HAT"]),  # the original streak hats
    ((127, 200, 255), ["CROWN", "BEANIE", "CHEF HAT", "WIZARD HAT", "KNIGHT HELMET", "NINJA BAND", "SUNGLASSES", "BOW",
                       "FEZ"]),
    ((232, 176, 75), ["VIKING HELMET", "DEVIL HORNS", "BUNNY EARS", "SPROUT", "USHANKA", "HEADPHONES",
                      "CAPTAIN HAT", "SANTA HAT", "WITCH HAT", "FIREFIGHTER"]),
    ((240, 110, 90), ["PIRATE HAT", "HARD HAT", "FLOWER CROWN", "ROBOT ANTENNA", "MUSHROOM CAP", "WELDING MASK",
                      "CAT EARS", "GRAD CAP", "SOMBRERO", "PROPELLER CAP", "HALO", "JESTER HAT"]),
    ((200, 140, 255), ["ARMY HELMET", "SPACE HELMET", "DRAGON HELM", "UFO", "FLAME CROWN", "SAMURAI HELMET",
                       "STORM CLOUD", "VALKYRIE HELM", "DISCO BALL", "DEMOLITION HAT", "PHARAOH", "HEART CROWN",
                       "LIGHTNING CROWN", "SCRAP CROWN", "SHIELD CROWN", "KING'S CROWN"]),  # king's crown last: it needs every other hat
]
_HAT_INDEX = {h[0]: i for i, h in enumerate(HATS)}
HAT_ORDER = [_HAT_INDEX[name] for _, names in HAT_TIERS for name in names]
HAT_TIER_COLOR = {_HAT_INDEX[name]: col for col, names in HAT_TIERS for name in names}
HAT_TIER_NAME = {_HAT_INDEX[name]: TIER_NAMES[t] for t, (_, names) in enumerate(HAT_TIERS) for name in names}
assert sorted(HAT_ORDER) == list(range(len(HATS)))
GALLERY_COLS, GALLERY_ROWS, GALLERY_CELL = 6, 5, 58  # the gallery's grid of hats or colors, a page at a time
JESTER_WINDOW = 3.0  # seconds after a shield pops that losing your last life earns the jester hat

HEART = [".XX.XX.", "XXXXXXX", "XXXXXXX", ".XXXXX.", "..XXX..", "...X..."]
BOLT = ["...XXX", "..XXX.", ".XXX..", "XXXXXX", "..XXX.", ".XXX..", "XXX...", "X....."]
SHIELD_ICON = ["XXXXXXX", "XWXXXXX", "XWXXXXX", "XWXXXXX", ".XXXXX.", "..XXX..", "...X..."]  # W = shine
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


def build_label(stamp):
    """Short version text for the main menu, like "VERSION 78165AA"; "DEV" when run from source."""
    return f"VERSION {stamp.split()[-1].upper()}" if build_time(stamp) else "VERSION DEV"


def rainbow(t):
    """A bright color that cycles through the rainbow as t goes from 0 to 1 (and wraps)."""
    c = pygame.Color(0)
    c.hsva = (t % 1 * 360, 65, 100, 100)
    return c[:3]


SAVE_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "ClawdCatch")  # old name kept so existing scores and hats carry over
SCORES_FILE = os.path.join(SAVE_DIR, "scores.json")
OLD_BEST_FILE = os.path.join(SAVE_DIR, "best.txt")
HATS_FILE = os.path.join(SAVE_DIR, "hats.json")
COLORS_FILE = os.path.join(SAVE_DIR, "colors.json")
SETTINGS_FILE = os.path.join(SAVE_DIR, "settings.json")
SITE_URL = "https://jacobhh3.github.io/block-catch/"
VERSION_CHECK = 300  # seconds between checks for a newer build on the website
SOUND_MODES = ["ON", "EFFECTS ONLY", "OFF"]  # M key / speaker button cycles through these
MUSIC_VOLUME = {"play": 0.45, "paused": 0.0}  # every other screen: 0.2
# the song's layers (sounds/music_<name>.ogg, made by make_sounds.py). While playing, layer i joins at combo
# x(i+1): just bass and drums at first, the whole song at the top combo. The menus play all of them.
MUSIC_LAYERS = ["base", "beat", "melody", "lead"]
TOP_N = 10
LB_FETCH = 100  # scores fetched, so the top 10 can still be filled after keeping one per player
NAME_LEN = 10


# Shared online leaderboard (dreamlo.com), reached through a small Cloudflare relay (see relay/) because
# dreamlo's free tier is HTTP only and browsers refuse that. The relay holds dreamlo's private code.
LB_URL = "https://block-catch-lb.jacobhh3.workers.dev/"


def skin_number(text):
    """The color a leaderboard entry was set in (dreamlo's text field), or None if it has none or it's unknown."""
    try:
        n = int(str(text).strip())
    except (TypeError, ValueError):
        return None
    return n if 0 <= n < len(SKINS) else None


# Before this was fixed, every phone got this same player id (the browser's Python random starts out the same),
# so scores with it are told apart by name instead.
SHARED_ID = "44cb"


def new_player_id():
    """A random 4-hex-digit id for this device. In the browser, from the browser's own random numbers."""
    if WEB:
        try:
            platform.window.eval("window.bc_pid = crypto.getRandomValues(new Uint16Array(1))[0]"
                                 ".toString(16).padStart(4, '0')")
            pid = str(platform.window.bc_pid)
            if len(pid) == 4 and pid != SHARED_ID:
                return pid
        except Exception:
            pass
    return "%04x" % random.SystemRandom().randrange(16 ** 4)


def player_of(key):
    """Online keys are NAME_xxxx, where xxxx is the player (one per device). Old phone scores all share one id,
    so each of their names counts as its own player."""
    who = key.rsplit("_", 1)[1] if "_" in key else key
    return key if who == SHARED_ID else who


def best_per_player(entries):
    """Leaderboard protection: one spot per player, their best, so nobody can fill the board with many names.
    A player only moves up by beating their own best, and only moves down when someone passes them."""
    best = {}
    for e in entries:
        who = player_of(e["key"])
        if who not in best or e["score"] > best[who]["score"]:
            best[who] = e
    return sorted(best.values(), key=lambda s: -s["score"])[:TOP_N]


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
    var files = ["block-catch.tar.gz", "block-catch.apk", "index.html", location.pathname];
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
        if not self.player_id or (WEB and self.player_id == SHARED_ID):
            self.player_id = new_player_id()
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

    def submit(self, name, score, skin):
        """Shows the score in the table right away, then uploads it (with the color worn) in the background."""
        key = self.key_for(name)
        with self.lock:
            self.name = name
            self.pending.append(dict(name=name, score=score, skin=skin))
            self.merge(dict(key=key, name=name, score=score, skin=skin))
            self.save()
        self.refresh()
        return key

    def merge(self, entry):
        # dreamlo keeps only the higher score per key, so do the same here
        for s in self.scores:
            if s["key"] == entry["key"]:
                if entry["score"] >= s["score"]:
                    s["score"], s["skin"] = entry["score"], entry.get("skin")
                break
        else:
            self.scores.append(entry)
        self.scores = best_per_player(self.scores)

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
                add = f"{LB_URL}add/{key}/{int(p['score'])}"
                try:  # with the color they wore, so other players see their name in its tier color
                    reply = await self._get(f"{add}/{int(p.get('skin', 0))}")
                except OSError:
                    reply = await self._get(add)  # an older relay only takes name and score
                if not reply.startswith("OK"):
                    raise OSError(reply)
                with self.lock:
                    self.pending.remove(p)
                    self.save()
            data = json.loads(await self._get(f"{LB_URL}json/{LB_FETCH}"))
            rows = (data.get("dreamlo", {}).get("leaderboard") or {}).get("entry") or []
            if isinstance(rows, dict):
                rows = [rows]
            online = [dict(key=r["name"], name=display_name(r["name"]), score=int(r["score"]),
                           skin=skin_number(r.get("text"))) for r in rows]
            with self.lock:
                self.scores = best_per_player(online)
                for p in self.pending:  # anything still waiting stays visible locally
                    self.merge(dict(key=self.key_for(p["name"]), name=p["name"], score=p["score"],
                                    skin=p.get("skin")))
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


def apply_moves(surf, moves):
    """Squash and spin a sprite: moves are ("scale", x, y) and ("rotate", degrees), done in order."""
    for kind, *args in moves:
        if kind == "scale":
            surf = pygame.transform.scale(surf, (int(surf.get_width() * args[0]), int(surf.get_height() * args[1])))
        else:
            surf = pygame.transform.rotate(surf, args[0])
    return surf


def bend_hat(rows, bend):
    """A hat's rows bent sideways like a stalk: the base stays put and the top moves bend pixels."""
    pad = 5
    top = len(rows) - 1 or 1
    return ["." * pad + "." * s + row + "." * (pad - s) for row, s in
            ((row, max(-pad, min(pad, round(bend * ((top - r) / top) ** 2)))) for r, row in enumerate(rows))]


def hat_label(need):
    """What unlocks a hat, as the menu says it."""
    if isinstance(need, int):
        return f"BREAK {need} BLOCKS WITHOUT LOSING A LIFE"
    return HAT_GOALS[need][2]


def make_clawd(frame, blink, skin=CLAWD, px=PX):
    surf = pygame.Surface((13 * px, 9 * px), pygame.SRCALPHA)
    rows = BODY + LEGS[frame]
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch == ".":
                continue
            # speckled skins pick a shade per pixel, the same one every time
            body = skin if isinstance(skin, tuple) else skin[(r * 7 + c * 13 + r * c * 5) % len(skin)]
            color = body
            if ch == "E":
                color = (body if r == 2 else NIGHT) if blink else NIGHT
            surf.fill(color, (c * px, r * px, px, px))
    return surf


def hsv_rgb(h, s, v):
    return tuple(int(x * 255) for x in colorsys.hsv_to_rgb(h % 1, s, v))


SKY_STARS = {(0, 3), (1, 9), (4, 2), (5, 10), (6, 5), (3, 11), (0, 7)}
BOMB_SEAMS = {(2, 2), (2, 10), (3, 1), (3, 11), (4, 3), (4, 9), (5, 4), (5, 8), (6, 6), (0, 4), (0, 8)}
PHOENIX_FIRE = [(120, 20, 30), (200, 40, 30), (240, 90, 30), (255, 150, 40), (255, 210, 90), (255, 245, 200)]
LOVE_HEARTS = {(1, 3), (1, 5), (2, 4), (1, 8), (1, 10), (2, 9), (4, 5), (4, 7), (5, 6)}
SKIN_EYES = {"obsidian": (200, 120, 255), "ninja": (240, 236, 230), "stella": (240, 230, 220),
             "galaxy": (240, 230, 220), "kaboom": (240, 230, 220), "phoenix": (60, 20, 30), "magnet": (250, 240, 230)}


def skin_pixel(look, r, c, t):
    """The color of one of Clawd's pixels (row r, column c) in a patterned or animated look, t seconds in."""
    k = r * 7 + c * 13 + r * c * 5  # the same per-pixel pick as speckles
    if look == "zebra":
        return (240, 236, 230) if (c // 2) % 2 == 0 else (70, 66, 82)
    if look == "tropical":  # sunset, pink at the top to yellow-green at his feet, slowly shifting
        return hsv_rgb(0.93 + r * 0.03 + 0.04 * math.sin(t * 0.8 + c * 0.3), 0.6, 1.0 - r * 0.04)
    if look == "ninja":
        if r in (2, 3) and 2 <= c <= 10:
            return (210, 50, 60)  # headband across his eyes
        return (54, 50, 66) if k % 3 else (66, 62, 80)
    if look == "robo":  # steel, with a scanning line moving down him
        return (150, 240, 255) if abs(r - (t * 6) % 12 + 2) < 0.8 else ((180, 186, 200) if k % 3 else (150, 156, 172))
    if look == "blocks":  # little tiles in the four block colors, shuffling every so often
        col = BLOCK_COLORS[(c // 2 + r // 2 * 3 + int(t * 1.5)) % 4]
        return tuple(min(255, v + 40) for v in col) if r % 2 == 0 and c % 2 == 0 else col
    if look == "stella":  # night sky with twinkling stars
        if (r, c) in SKY_STARS:
            return (255, 250, 220) if math.sin(t * 4 + r * 3 + c) > 0 else (120, 110, 190)
        return (40, 44, 100) if k % 4 else (56, 50, 120)
    if look == "galaxy":  # drifting purple-pink nebula with stars
        if (r, c) in SKY_STARS or (r + 2, c - 1) in SKY_STARS:
            return (255, 250, 230) if math.sin(t * 4 + r * 3 + c) > 0.2 else (130, 100, 200)
        return hsv_rgb(0.76 + 0.08 * math.sin(c * 0.5 - t * 1.5 + r * 0.3), 0.6, 0.62 if k % 3 else 0.72)
    if look == "platinum":  # a shine sweeps across
        if 0 <= c + r * 0.5 - (t * 10) % 26 + 6 < 2:
            return (255, 255, 255)
        return (214, 218, 228) if k % 3 else (190, 196, 210)
    if look == "diamond":  # sparkling glints
        return (255, 255, 255) if (k + int(t * 6)) % 11 == 0 else ((150, 230, 250) if k % 3 else (120, 200, 240))
    if look == "cosmic":  # swirling purple and blue with gold sparks
        if (k + int(t * 3)) % 23 == 0:
            return (255, 230, 150)
        return hsv_rgb(0.72 + 0.12 * math.sin((math.atan2(r - 3.5, c - 6) + t * 1.2) * 2), 0.7, 0.9)
    if look == "guardian":  # shield-blue armor plates pulsing, with a shine sweeping across
        if 0 <= c + r * 0.5 - (t * 9) % 26 + 6 < 1.5:
            return (230, 246, 255)
        k2 = 0.5 + 0.5 * math.sin(t * 3 + c * 0.4 + r * 0.6)
        f = 0.62 + 0.2 * k2 if (c + r % 2) % 3 == 0 else 0.85
        return tuple(int(v * f) for v in SHIELD_COLOR)
    if look == "ghost":
        return (225, 235, 255) if k % 5 else (200, 215, 250)
    if look == "thunder":  # a storm cloud with zigzag lightning striking somewhere new each time
        strike = int(t * 3)
        bolt_on = (t * 3) % 1 < 0.35
        zig = (0, 1, 1, 0, -1, -1, 0, 1, 1) if strike % 2 else (0, -1, -1, 0, 1, 1, 0, -1, -1)
        x = 3 + (strike * 5) % 7 + zig[r]
        if bolt_on and c in (x, x + (1 if r in (3, 6) else 0)):
            return (255, 236, 110) if (t * 20) % 2 < 1 else (255, 255, 230)
        lift = 30 if bolt_on else 0
        return tuple(min(255, v + lift) for v in ((74, 80, 104) if k % 3 else (90, 96, 122)))
    if look == "love":  # pink, with little hearts that beat: lub-dub, pause
        beat = t % 1.0
        if (r, c) in LOVE_HEARTS:
            return (255, 90, 130) if beat < 0.1 or 0.2 < beat < 0.3 else (220, 60, 100)
        return (255, 170, 200) if k % 3 else (245, 150, 190)
    if look == "jackpot":  # rich gold, a sweeping shine and rainbow glints
        if 0 <= c + r * 0.5 - (t * 11) % 28 + 6 < 2:
            return (255, 250, 220)
        if (k + int(t * 5)) % 13 == 0:
            return hsv_rgb(t * 0.8 + c * 0.1, 0.5, 1)
        return ((232, 176, 75), (250, 204, 96), (206, 146, 52))[k % 3]
    if look == "krystal":  # pale crystal facets with rainbow glints
        if (k + int(t * 5)) % 12 == 0:
            return hsv_rgb(t * 0.5 + c * 0.08, 0.6, 1)
        return ((190, 220, 240), (160, 200, 235), (210, 235, 250))[(c // 3 + r // 2) % 3]
    if look == "kaboom":  # a lit bomb: fuse sparking, seams glowing hotter and faster
        if r == 0 and c == 6:
            return ((255, 230, 120), (255, 255, 255), (255, 150, 60))[int(t * 20) % 3]
        if (r, c) in BOMB_SEAMS:
            heat = (t % 2.4) / 2.4
            pulse = 0.5 + 0.5 * math.sin(t * (6 + 20 * heat))
            return (int(120 + 135 * pulse), int(30 + 60 * heat * pulse), 30)
        return (50, 46, 60) if k % 3 else (64, 58, 76)
    if look == "phoenix":  # living fire licking upward
        flick = math.sin(c * 1.7 + t * 9) + math.sin(c * 0.9 - t * 6 + r) + math.sin(r * 2.1 - t * 12)
        return PHOENIX_FIRE[max(0, min(len(PHOENIX_FIRE) - 1, int((r / 8) * 3.2 + flick * 0.6)))]
    if look == "archie":  # stone with moss creeping over him and pulling back
        if min(r, 8 - r) / 4 + ((k * 37) % 100) / 260 < 0.45 + 0.3 * math.sin(t * 0.7):
            if (k + int(t * 2)) % 29 == 0:
                return (230, 240, 170)  # dewdrop
            if (k + int(t)) % 41 == 0:
                return (250, 210, 230)  # tiny flower
            return ((86, 150, 70), (106, 172, 80), (70, 126, 62))[k % 3]
        return ((138, 134, 128), (118, 114, 110), (152, 148, 140))[k % 3]
    if look == "obsidian":  # black glass with purple glints sweeping across
        return (190, 150, 255) if (c + r - int(t * 8)) % 14 == 0 else ((40, 34, 54) if k % 3 else (54, 46, 72))
    if look == "magnet":  # red and blue poles glowing, with a crackling seam down his middle
        if c == 6:
            return (240, 240, 250) if (r + int(t * 10)) % 3 == 0 else (170, 160, 190)
        glow = 0.5 + 0.5 * math.sin(t * 4 - abs(c - 6) * 0.8)
        return tuple(min(255, int(v * (0.75 + 0.35 * glow))) for v in (MAGNET_COLOR if c < 6 else (90, 130, 230)))
    if look == "leo":  # shimmering rainbow
        return hsv_rgb((c + r) / 18 - t * 0.4, 0.55, 1)
    return CLAWD


def make_skin(look, frame, blink, t, px=PX):
    """Clawd in a patterned or animated look, drawn fresh (t seconds in)."""
    surf = pygame.Surface((13 * px, 9 * px), pygame.SRCALPHA)
    eye = SKIN_EYES.get(look, NIGHT)
    rows = BODY + ([] if look == "ghost" else LEGS[frame])
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch == ".":
                continue
            body = skin_pixel(look, r, c, t)
            color = ((body if r == 2 else eye) if blink else eye) if ch == "E" else body
            surf.fill(color, (c * px, r * px, px, px))
    if look == "ghost":  # a wavy tail instead of legs, and see-through, fading in and out
        for c in range(2, 11):
            surf.fill((210, 222, 252), (c * px, 7 * px, px, (1 + (math.sin(c * 1.3 - t * 7) > 0)) * px))
        surf.set_alpha(int(165 + 75 * math.sin(t * 2.2)))
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
        # plain and speckled colors are drawn once; patterned and animated ones (a word) every frame
        self.skin_sprites = [None if isinstance(skin, str) else
                             {(f, b): make_clawd(f, b, skin) for f in range(3) for b in (False, True)}
                             for _, skin, _ in SKINS]
        self.skin_icons = [make_skin(skin, 0, False, 0.0, px=3) if isinstance(skin, str) else
                           make_clawd(0, False, skin, px=3) for _, skin, _ in SKINS]
        self.skins, self.skin = {0}, 0  # unlocked color indexes, and the one Clawd wears
        self.gallery, self.gallery_icons = dict(tab="hats", pick=0), {}  # the gallery screen, and its little pictures
        self.zaps = self.landings = 0  # progress toward the colors that count over all games
        try:
            data = load_save(COLORS_FILE)
            self.skins |= {i for i in data.get("unlocked", []) if isinstance(i, int) and 0 <= i < len(SKINS)}
            self.skin = data.get("worn", 0) if data.get("worn", 0) in self.skins else 0
            self.zaps, self.landings = int(data.get("zaps", 0)), int(data.get("landings", 0))
        except (OSError, ValueError, AttributeError, TypeError):
            pass
        self.skin_viewing = self.skin  # color shown in the title screen picker
        self.board = Leaderboard()
        # every frame of every hat (most have just one)
        self.hat_art = [[make_hat(f) for f in HAT_ANIM[name][1]] if name in HAT_ANIM else [make_hat(rows)]
                        for name, _, rows in HATS]
        self.hat_shadow = [[a.copy() for a in frames] for frames in self.hat_art]  # locked hats: full color, dimmed
        self.sprout = dict(bend=0.0, speed=0.0, px=0.0, py=0.0, vx=0.0, vy=0.0)  # the sprout's springy stem
        self.bent = {}  # bent sprout art, by (bend, locked)
        for frames in self.hat_shadow:
            for a in frames:
                a.fill((150, 145, 160, 255), special_flags=pygame.BLEND_RGBA_MULT)
        self.hat_icons = [make_hat(rows, px=3) for _, _, rows in HATS]
        self.unlocked, self.worn = set(), -1  # hat indexes; -1 is no hat
        # progress toward the hats that count over all games (play time in seconds; days as dates)
        self.hat_stats = {k: 0.0 for k in TOTAL_STATS}
        self.hat_stats["days"] = []
        try:
            data = load_save(HATS_FILE)
            self.unlocked = {i for i in data.get("unlocked", []) if isinstance(i, int) and 0 <= i < len(HATS)}
            self.worn = data.get("worn", -1) if data.get("worn", -1) in self.unlocked else -1
            stats = data.get("stats", {})
            for key in TOTAL_STATS:
                self.hat_stats[key] = float(stats.get(key, 0))
            self.hat_stats["days"] = [d for d in stats.get("days", []) if isinstance(d, str)]
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
        self.sound, self.fullscreen = 0, False  # index into SOUND_MODES; F11 full screen on PC
        try:
            settings = load_save(SETTINGS_FILE)
            self.sound = int(settings.get("sound", 0)) % len(SOUND_MODES)
            if settings.get("fullscreen") and not WEB:
                pygame.display.toggle_fullscreen()
                self.fullscreen = True
        except (OSError, ValueError, AttributeError, TypeError, pygame.error):
            pass
        self.sfx, self.notice = {}, None
        self.layers, self.layer_vol = [], [0.0] * len(MUSIC_LAYERS)  # (channel, sound) per music layer, and its volume
        try:
            pygame.mixer.set_num_channels(16)
            folder = resource("sounds")
            for f in os.listdir(folder):
                if f.endswith(".ogg") and not f.startswith("music_"):
                    self.sfx[f[:-4]] = pygame.mixer.Sound(os.path.join(folder, f))
            # each music layer loops on its own channel (kept away from the sound effects); all start
            # together and are the same length, so they stay in step
            pygame.mixer.set_reserved(len(MUSIC_LAYERS))
            self.layers = [(pygame.mixer.Channel(i), pygame.mixer.Sound(os.path.join(folder, f"music_{name}.ogg")))
                           for i, name in enumerate(MUSIC_LAYERS)]
            for channel, sound in self.layers:
                channel.set_volume(0.0)
                channel.play(sound, loops=-1)
        except (pygame.error, OSError):
            pass  # no audio device or no sound files: play on silently
        self.toast, self.toasts = None, []  # "new hat" / "new color" notification, and ones waiting their turn
        self.name = self.board.name
        self.last_key = None  # online key of the score just entered, for highlighting
        self.pointers = {}  # touch fingers (and the mouse) currently down: id -> (x, y)
        self.buttons = []  # tappable menu buttons drawn this frame: (rect, action)
        self.pad = {name: pygame.Rect(x, H + y, w, h) for name, x, y, w, h in PAD_KEYS}
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

    def personal_best(self):
        """This player's own best score: kept since stats began, plus their own leaderboard entries from before."""
        mine = [e["score"] for e in self.scores if str(e.get("key", "")).endswith(f"_{self.board.player_id}")]
        playing = self.score if self.mode in ("play", "paused", "resume", "entry", "over") else 0
        return int(max([self.hat_stats["best_score"], playing] + mine))

    def qualifies(self):
        mine = [s["score"] for s in self.scores if player_of(s["key"]) == self.board.player_id]
        if mine and self.score <= mine[0]:
            return False  # already on the board with a better score: that spot stays
        return self.score > 0 and (len(self.scores) < TOP_N or self.score > self.scores[-1]["score"])

    def game_over(self):
        self.hat_stats["best_score"] = max(self.hat_stats["best_score"], self.score)
        self.hat_stats["total_score"] += self.score
        self.save_progress()
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
        self.last_key = self.board.submit(name, self.score, self.skin)
        pygame.key.stop_text_input()
        self.mode = "over"

    def reset(self, mode):
        self.mode = mode  # title | help | board | stats | home | play | paused | resume | entry | over
        self.t = 0.0
        self.score = 0
        self.lives = 3
        self.streak = 0
        self.hearts = []
        self.p = dict(x=W / 2 - PW / 2, y=GROUND - PH, vx=0.0, vy=0.0, on_ground=True,
                      walk=0.0, blink=0.0, chain=0, jump_buffer=0.0, block_grace=0.0, sliding=0, slide_t=0.0, slide_panic=False, bj_t=9.0, bj_flip=False, bomb_fx=None, bomb_t=0.0,
                      dash=0.0, dash_dir=0, dash_cd=0.0, dance=0.0, taps=0, tap_gap=0.0, air_t=0.0)
        self.countdown, self.wake = 0.0, 0.0  # seconds left before play resumes; "!" after waking
        self.leave_in = None  # seconds left before quitting to the main menu, once MAIN MENU is chosen
        self.purples, self.bombs_hit = 0, 0  # this game's progress toward the purple and red colors
        self.game_counts = dict(last_loss=0.0, shield_pop_t=-99.0)  # this game's progress toward hats
        self.last_tap = (0, -1.0)
        self.ghosts = []
        self.blocks, self.parts, self.pops = [], [], []
        self.hits = 0
        self.bolts, self.strikes = [], []
        self.charge = 0  # blocks the stored zap will destroy (0: none), used with E or the ZAP button
        self.magnets, self.magnet = [], 0.0  # pickups falling, seconds of pull left
        self.shields, self.shielded = [], False  # pickups falling; a shield saves the next lost life
        self.shield_in = SHIELD_COOLDOWN + random.random() * SHIELD_RANDOM
        self.shield_pop, self.shield_edge = None, []  # the outline bursting after a save; its points last frame
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
            today = datetime.date.today().isoformat()
            if today not in self.hat_stats["days"]:
                self.hat_stats["days"].append(today)
            self.count("games")
            self.save_hats()

    def pause(self):
        if self.mode in ("play", "resume"):
            self.mode = "paused"
            self.play("snore")
            self.save_progress()

    def resume(self):
        """Leaving the pause screen: a short countdown while Clawd wakes up, then play goes on."""
        self.leave_in = None
        self.mode, self.countdown = "resume", RESUME_COUNT
        self.play("tick")

    def ask_leave(self):
        """MAIN MENU on the pause screen: counts down first, so a slip of the finger can be cancelled."""
        if self.mode == "paused" and self.leave_in is None:
            self.leave_in = LEAVE_COUNT
            self.play("tick")

    def cancel_leave(self):
        self.leave_in = None
        self.play("click")

    def leave_to_menu(self):
        """Quit this game for the main menu. Its stats and best score still count; it isn't posted as a high score."""
        self.leave_in = None
        self.hat_stats["best_score"] = max(self.hat_stats["best_score"], self.score)
        self.hat_stats["total_score"] += self.score
        self.save_progress()
        self.reset("title")

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

    def update_music(self, dt):
        """Music is full while playing, softer on the menus, silent while paused. While playing, the layers
        fade in one by one as the combo climbs, and fade back out when the streak ends."""
        vol = 0.0 if self.sound else MUSIC_VOLUME.get(self.mode, 0.2)
        building = self.mode in ("play", "resume")
        for i, (channel, _) in enumerate(self.layers):
            target = vol if not building or self.multiplier > i else 0.0
            now = self.layer_vol[i]
            if now < target:
                now = min(target, now + dt * 0.9)  # joins over about half a second
            elif now > target:
                now = max(target, now - dt * 0.45)  # drops out a bit slower
            if now != self.layer_vol[i]:
                self.layer_vol[i] = now
                try:
                    channel.set_volume(now)
                except pygame.error:
                    pass

    def save_settings(self):
        try:
            write_save(SETTINGS_FILE, dict(sound=self.sound, fullscreen=self.fullscreen))
        except OSError:
            pass

    def toggle_sound(self):
        self.sound = (self.sound + 1) % len(SOUND_MODES)
        self.save_settings()
        self.notice = dict(txt="SOUND " + SOUND_MODES[self.sound], life=1.4)

    def toggle_fullscreen(self):
        """F11 on PC: the game scaled up to fill the screen (keeping its shape), or back to a window. Remembered."""
        if WEB:
            return
        try:
            pygame.display.toggle_fullscreen()
        except pygame.error:
            return
        self.fullscreen = not self.fullscreen
        self.save_settings()

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
        if now == "zap" and now != before:
            self.use_charge()
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
            self.count("dashes")
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
                self.count("dances")
                self.save_hats()

    def difficulty(self):
        d = min(1.0, self.t / 120)  # ramps over roughly 2 minutes
        return 38 + d * 70 + random.random() * 14, 1.9 - d * 1.15

    def hat_sprite(self, i, now):
        """Hat i as drawn at now (milliseconds): its animation frame."""
        name = HATS[i][0]
        if name in HAT_SPRING:
            key = (round(self.sprout["bend"]), i in self.unlocked)
            if key not in self.bent:
                self.bent[key] = make_hat(bend_hat(HATS[i][2], key[0]))
                if not key[1]:
                    self.bent[key].fill((150, 145, 160, 255), special_flags=pygame.BLEND_RGBA_MULT)
            return self.bent[key]
        frames = self.hat_art[i] if i in self.unlocked else self.hat_shadow[i]
        k = 0
        if name in HAT_ANIM and (name not in HAT_AIR_ONLY or not self.p["on_ground"]):
            k = int(now / 1000 * HAT_ANIM[name][0]) % len(frames)  # now is in milliseconds
        return frames[k]

    def swing_sprout(self, dt):
        """The sprout's stem is a spring: it lags behind when Clawd speeds up or stops, bounces when he lands
        or jumps, then wobbles back upright. bend is how many pixels the leaf is pushed sideways."""
        s, p = self.sprout, self.p
        if dt <= 0:
            return
        vx, vy = (p["x"] - s["px"]) / dt, (p["y"] - s["py"]) / dt
        ax = max(-8000.0, min(8000.0, (vx - s["vx"]) / dt))
        ay = max(-8000.0, min(8000.0, (vy - s["vy"]) / dt))
        s["px"], s["py"], s["vx"], s["vy"] = p["x"], p["y"], vx, vy
        push = -ax * 0.15 + abs(ay) * 0.04 * (1 if s["bend"] >= 0 else -1)  # up and down jolts make it flop
        s["speed"] += (push - 60 * s["bend"] - 5 * s["speed"]) * dt
        s["bend"] = max(-4.0, min(4.0, s["bend"] + s["speed"] * dt))

    def save_hats(self):
        try:
            write_save(HATS_FILE, dict(unlocked=sorted(self.unlocked), worn=self.worn, stats=self.hat_stats))
        except OSError:
            pass

    def hat_progress(self, need):
        """How far along a hat's challenge is, and its goal."""
        if isinstance(need, int):
            return self.streak, need
        goal, scope, _ = HAT_GOALS[need]
        if need in ("days", "days30"):
            return len(self.hat_stats["days"]), goal
        if need in HAT_STAT:
            return self.hat_stats[HAT_STAT[need]], goal
        if need == "allhats":
            return len(self.unlocked - {_HAT_INDEX["KING'S CROWN"]}), goal
        if need == "airtime":
            return self.p["air_t"], goal
        if need == "bolts2000":
            return self.zaps, goal  # bolts are counted with the colors
        if scope == "total":
            return self.hat_stats[need], goal
        if need == "hour":
            return self.t, goal
        if need == "clean":
            return self.t - self.game_counts["last_loss"], goal
        if need == "air100":
            return self.p["chain"], goal
        if need.startswith("score"):
            return self.score, goal
        if scope == "event":
            return (goal if self.mode in ("play", "paused", "resume") and datetime.date.today().month == goal else 0), goal
        return self.game_counts.get(need, 0), goal

    def count(self, stat, n=1):
        """Add to a hat challenge's counter (this game's, or the all-games one) and check for unlocks."""
        if stat in TOTAL_STATS:
            self.hat_stats[stat] += n
        else:
            self.game_counts[stat] = self.game_counts.get(stat, 0) + n
        self.check_hats()

    def check_hats(self):
        """Unlock any hat whose challenge has just been met, with a notification the first time."""
        for i, (name, need, _) in enumerate(HATS):
            if i not in self.unlocked:
                have, goal = self.hat_progress(need)
                if have >= goal:
                    self.unlocked.add(i)
                    self.save_hats()
                    self.show_toast(dict(hat=i))
                    self.play("hat")
        self.check_colors()

    def hat_status(self, i):
        """The line under a hat's name on the menu: what unlocks it (and progress so far) while it's locked."""
        if i == -1:
            return f"HATS {len(self.unlocked)}/{len(HATS)}"
        if i in self.unlocked:
            return f"{HAT_TIER_NAME[i]}  HATS {len(self.unlocked)}/{len(HATS)}"
        need = HATS[i][1]
        if isinstance(need, int):
            return f"LOCKED  {hat_label(need)}"
        goal, scope, label = HAT_GOALS[need]
        if scope != "total":
            return f"LOCKED  {label}"
        have, goal = self.hat_progress(need)
        if need == "playtime":
            return f"LOCKED  {label}  {int(have // 60)}/{goal // 60} MIN"
        if need == "playtime10":
            return f"LOCKED  {label}  {have / 3600:.1f}/{goal // 3600} HRS"
        return f"LOCKED  {label}  {int(min(have, goal))}/{goal}"

    def save_progress(self):
        self.save_colors()
        self.save_hats()

    def save_colors(self):
        try:
            write_save(COLORS_FILE, dict(unlocked=sorted(self.skins), worn=self.skin,
                                         zaps=self.zaps, landings=self.landings))
        except OSError:
            pass

    def unlock_color(self, key):
        """A color's challenge was just met: unlock it, with a notification the first time."""
        i = next(k for k, (_, _, need) in enumerate(SKINS) if need == key)
        if i not in self.skins:
            self.skins.add(i)
            self.save_colors()
            self.show_toast(dict(color=i))
            self.play("hat")

    def show_toast(self, t):
        t["life"] = TOAST_TIME
        if self.toast:
            self.toasts.append(t)
        else:
            self.toast = t

    def skin_sprite(self, i, frame, blink, now):
        look = SKINS[i][1]
        if isinstance(look, str):
            return make_skin(look, frame, blink, now / 1000)
        return self.skin_sprites[i][(frame, blink)]

    def stat_value(self, stat):
        """How much of something has been done, for the color challenges."""
        if stat == "month":
            return datetime.date.today().month if self.mode in ("play", "paused", "resume") else 0
        if stat in ("score", "streak", "time"):
            return {"score": self.score, "streak": self.streak, "time": self.t}[stat]
        if stat == "chain":
            return self.p["chain"]
        if stat == "bombs_game":
            return self.bombs_hit
        if stat == "bolts":
            return self.zaps
        if stat == "landings":
            return self.landings
        if stat == "hats":
            return len(self.unlocked)
        if stat == "colors":
            return len(self.skins)
        if stat == "days":
            return len(self.hat_stats["days"])
        return self.hat_stats[stat]

    def check_colors(self):
        for i, (_, _, key) in enumerate(SKINS):
            if key in COLOR_GOALS and i not in self.skins:
                stat, goal, _ = COLOR_GOALS[key]
                if (self.stat_value(stat) == goal) if stat == "month" else (self.stat_value(stat) >= goal):
                    self.unlock_color(key)

    def color_status(self, i):
        """The second line under a color's name on the menu: progress if it's locked."""
        if i in self.skins:
            return f"{COLOR_TIER_NAME[i]}  COLORS {len(self.skins)}/{len(SKINS)}"
        key = SKINS[i][2]
        if key in COLOR_GOALS:
            stat, goal, label = COLOR_GOALS[key]
            if stat in GAME_STATS:
                return f"LOCKED  {label}"
            have = self.stat_value(stat)
            if stat == "playtime":
                return f"LOCKED  {label}  {have / 3600:.1f}/{goal // 3600} HRS"
            return f"LOCKED  {label}  {int(min(have, goal))}/{goal}"
        return "LOCKED  " + {
            "air": f"{AIR_STREAK} IN A ROW IN THE AIR",
            "purple": f"{PURPLE_GOAL} PURPLE IN ONE GAME",
            "bombs": f"HIT {BOMB_GOAL} BOMBS IN ONE GAME",
            "zaps": f"CATCH {ZAP_GOAL} BOLTS  {min(self.zaps, ZAP_GOAL)}/{ZAP_GOAL}",
            "landings": f"LAND {LANDING_GOAL} TIMES  {min(self.landings, LANDING_GOAL)}/{LANDING_GOAL}",
        }[SKINS[i][2]]

    def pick_color(self, d):
        """Title screen: cycle through the colors. Locked ones can be looked at but not worn."""
        spot = (COLOR_ORDER.index(self.skin_viewing) + d) % len(SKINS)  # easiest to hardest
        self.skin_viewing = COLOR_ORDER[spot]
        if self.skin_viewing in self.skins:
            self.skin = self.skin_viewing
            self.save_colors()

    # ---------- gallery ----------
    def open_gallery(self):
        """Every hat or color on one screen, easiest to hardest, starting on what's being worn."""
        self.mode = "gallery"
        self.gallery = dict(tab="hats", pick=0)
        self.gallery_tab("hats")

    def gallery_items(self):
        return HAT_ORDER if self.gallery["tab"] == "hats" else COLOR_ORDER

    def gallery_tab(self, tab):
        self.gallery["tab"] = tab
        worn = self.worn if tab == "hats" else self.skin
        items = self.gallery_items()
        self.gallery["pick"] = items.index(worn) if worn in items else 0

    def gallery_move(self, d):
        self.gallery["pick"] = (self.gallery["pick"] + d) % len(self.gallery_items())

    def gallery_page(self, d):
        per, n = GALLERY_COLS * GALLERY_ROWS, len(self.gallery_items())
        page = (self.gallery["pick"] // per + d) % -(-n // per)
        self.gallery["pick"] = min(n - 1, page * per)

    def gallery_tap(self, k):
        """Touch: the first tap picks a cell, a second tap on it wears it."""
        if k == self.gallery["pick"]:
            self.gallery_wear()
        else:
            self.gallery["pick"] = k

    def gallery_wear(self):
        """Wear the picked hat or color (if it's unlocked); a worn hat picked again comes off."""
        i = self.gallery_items()[self.gallery["pick"]]
        if self.gallery["tab"] == "hats":
            if i in self.unlocked:
                self.worn = self.viewing = -1 if self.worn == i else i
                self.save_hats()
                self.play("click")
        elif i in self.skins:
            self.skin = self.skin_viewing = i
            self.save_colors()
            self.play("click")

    def gallery_key(self, key):
        if key == pygame.K_ESCAPE:
            self.mode = "title"
        elif key == pygame.K_TAB:
            self.gallery_tab("colors" if self.gallery["tab"] == "hats" else "hats")
        elif key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
            self.gallery_move(-1 if key in (pygame.K_LEFT, pygame.K_a) else 1)
        elif key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
            self.gallery_move(-GALLERY_COLS if key in (pygame.K_UP, pygame.K_w) else GALLERY_COLS)
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.gallery_wear()

    def gallery_icon(self, i, hats, owned):
        """A small Clawd (in the worn color) with hat i on, or Clawd in color i; dimmed while locked."""
        key = (hats, i, owned, self.skin)
        if key not in self.gallery_icons:
            if hats:
                body, (name, _, rows) = self.skin_icons[self.skin], HATS[i]
                hat, drop = make_hat(rows, px=3), HAT_DROP.get(name, 0) * 3
                lift = max(0, hat.get_height() - drop)
                art = pygame.Surface((max(body.get_width(), hat.get_width()), body.get_height() + lift), pygame.SRCALPHA)
                mid = art.get_width() // 2
                art.blit(body, body.get_rect(midtop=(mid, lift)))
                art.blit(hat, hat.get_rect(midbottom=(mid, lift + drop)))
            else:
                art = self.skin_icons[i].copy()
            if not owned:
                art.fill((110, 105, 120, 255), special_flags=pygame.BLEND_RGBA_MULT)
            self.gallery_icons[key] = art
        return self.gallery_icons[key]

    def dressed(self, skin, hat, now):
        """Clawd at full size in a color and hat (hat -1: none), animated, for the gallery's preview."""
        body = self.skin_sprite(skin, 0, False, now)
        if hat < 0:
            return body
        art, name = self.hat_sprite(hat, now), HATS[hat][0]
        drop = HAT_DROP.get(name, 0) * PX
        lift = max(0, art.get_height() - drop)
        out = pygame.Surface((max(PW, art.get_width()), PH + lift), pygame.SRCALPHA)
        mid = out.get_width() // 2
        out.blit(body, body.get_rect(midtop=(mid, lift)))
        out.blit(art, art.get_rect(midbottom=(mid, lift + drop)))
        return out

    def draw_gallery(self, now):
        c, g = self.canvas, self.gallery
        hats = g["tab"] == "hats"
        items, have = self.gallery_items(), (self.unlocked if hats else self.skins)
        tiers, tier_names = (HAT_TIER_COLOR, HAT_TIER_NAME) if hats else (TIER_COLOR, COLOR_TIER_NAME)
        c.fill(NIGHT, (0, 0, W, H))  # its own screen: nothing of the game behind it
        self.text("GALLERY", W / 2, 60, 20, GOLD)
        for k, (tab, label) in enumerate((("hats", f"HATS {len(self.unlocked)}/{len(HATS)}"),
                                          ("colors", f"COLORS {len(self.skins)}/{len(SKINS)}"))):
            self.button(label, W / 2 + (k * 2 - 1) * 92, 92, 176, 28, lambda tab=tab: self.gallery_tab(tab), 10,
                        INK if g["tab"] == tab else DIM)
        # the grid, a page at a time
        per = GALLERY_COLS * GALLERY_ROWS
        page, pages = g["pick"] // per, -(-len(items) // per)
        x0 = (W - GALLERY_COLS * GALLERY_CELL) / 2
        worn = self.worn if hats else self.skin
        for slot in range(min(per, len(items) - page * per)):
            k = page * per + slot
            i = items[k]
            owned = i in have
            r = pygame.Rect(x0 + slot % GALLERY_COLS * GALLERY_CELL + 2, 114 + slot // GALLERY_COLS * GALLERY_CELL + 2,
                            GALLERY_CELL - 4, GALLERY_CELL - 4)
            c.fill(PANEL if owned else NIGHT, r)
            art = self.gallery_icon(i, hats, owned)
            c.blit(art, art.get_rect(center=r.center))
            picked = k == g["pick"]
            pygame.draw.rect(c, INK if picked else (tiers[i] if owned else EARTH), r, 3 if picked else 1)
            if i == worn:
                c.fill(GOLD, (r.right - 9, r.top + 3, 6, 6))  # wearing this one
            self.buttons.append((r, lambda k=k: self.gallery_tap(k)))
        if pages > 1:
            self.button("<", W / 2 - 70, 418, 36, 22, lambda: self.gallery_page(-1), 11, DIM)
            self.text(f"{page + 1}/{pages}", W / 2, 418, 10, DIM)
            self.button(">", W / 2 + 70, 418, 36, 22, lambda: self.gallery_page(1), 11, DIM)
        # the picked one: a big animated preview, its tier, and how to get it or wear it
        i = items[g["pick"]]
        preview = self.dressed(self.skin, i, now) if hats else self.dressed(i, self.worn, now)
        if i not in have:
            preview = preview.copy()
            preview.fill((110, 105, 120, 255), special_flags=pygame.BLEND_RGBA_MULT)
        c.blit(preview, preview.get_rect(midbottom=(58, 496)))
        self.text(HATS[i][0] if hats else SKINS[i][0], 112, 446, 12, tiers[i], "left")
        self.text(tier_names[i], 112, 463, 9, tiers[i], "left")
        if i in have:
            how = ("TAP AGAIN" if TOUCH else "ENTER") + (" TO TAKE IT OFF" if hats and i == worn else " TO WEAR")
            self.text("WEARING" if i == worn and not hats else how, 112, 480, 9, DIM, "left")
        else:
            parts = (self.hat_status(i) if hats else self.color_status(i)).split("  ")  # LOCKED, how, progress
            self.text(parts[1] if len(parts) > 1 else parts[0], 112, 480, 9, DIM, "left")
            if len(parts) > 2:
                self.text(parts[2], 112, 496, 9, INK, "left")
        if TOUCH:
            self.button("BACK", W / 2, 534, 140, 30, self.go("title"), 12, DIM)
        else:
            self.text("ARROWS PICK   ENTER WEAR   TAB HATS/COLORS   ESC BACK", W / 2, 534, 8, DIM)

    def pick_hat(self, d):
        """Title screen: cycle through no hat and every hat. Locked ones can be looked at but not worn."""
        order = [-1] + HAT_ORDER  # no hat, then easiest to hardest
        self.viewing = order[(order.index(self.viewing) + d) % len(order)]
        if self.viewing == -1 or self.viewing in self.unlocked:
            self.worn = self.viewing
            self.save_hats()

    def queue_pickup(self, kind):  # kind: "hearts", "bolts", "magnets" or "shields"
        """Power-ups drop one at a time; earned ones wait in line."""
        self.pickup_queue.append(kind)

    @property
    def multiplier(self):
        return min(MAX_MULT, 1 + self.streak // COMBO_STEP)

    def spawn(self):
        """Drop a block or a bomb. Returns False if there was no clear spot this time."""
        fall, _ = self.difficulty()
        d = min(1.0, self.t / 120)
        if self.t > BOMB_AFTER and random.random() < 0.1 + d * 0.08:
            size = 20
            x = self.clear_x(size, fall * 0.9)
            if x is None:
                return False
            self.blocks.append(dict(x=x, y=-size, s=size, vy=fall * 0.9,
                                    c=BOMB_RED, rot=0.0, spin=0.0, dead=False, bomb=True))
            return True
        size = 16 + random.randrange(3) * 4
        x = self.clear_x(size, fall)
        if x is None:
            return False
        self.blocks.append(dict(x=x, y=-size, s=size, vy=fall,
                                c=random.choice(BLOCK_COLORS), rot=0.0, spin=(random.random() - 0.5) * 70,
                                dead=False))
        return True

    def clear_x(self, size, vy):
        """A random x where something falling at vy won't run into anything already falling,
        or None if a few tries don't find one."""
        for _ in range(12):
            x = 12 + random.random() * (W - 24 - size)
            for b in self.blocks:
                if b["dead"] or not (b["x"] - FALL_GAP < x + size and x < b["x"] + b["s"] + FALL_GAP):
                    continue
                gap = b["y"] - FALL_GAP  # between the new one's bottom (just above the screen) and b's top
                if gap <= 0:
                    break
                if vy > b["vy"] and gap / (vy - b["vy"]) < (GROUND - b["y"] - b["s"]) / b["vy"]:
                    break  # would catch up with b before b lands
            else:
                return x
        return None

    def keep_off_bombs(self):
        """Slide any block that's touching a bomb (the magnet drags blocks around) out beside it."""
        bombs = [m for m in self.blocks if m.get("bomb") and not m["dead"]]
        for b in self.blocks:
            if b.get("bomb") or b["dead"]:
                continue
            for m in bombs:
                if not (b["x"] < m["x"] + m["s"] + FALL_GAP and m["x"] < b["x"] + b["s"] + FALL_GAP
                        and b["y"] < m["y"] + m["s"] + FALL_GAP and m["y"] < b["y"] + b["s"] + FALL_GAP):
                    continue
                right, left = m["x"] + m["s"] + FALL_GAP, m["x"] - b["s"] - FALL_GAP
                if b["x"] + b["s"] / 2 < m["x"] + m["s"] / 2:
                    right, left = left, right  # try the side it's already on first
                b["x"] = right if 0 <= right <= W - b["s"] else left

    def hit_block(self, b, air=False, value=1):
        """Score a destroyed block: combo multiplier, air chain bonus, and pickup drops."""
        b["dead"] = True
        self.streak += 1
        if self.p["dash"] > 0:
            self.count("dash_hits")
        if self.streak == COMBO_STEP * (MAX_MULT - 1):
            self.count("combo4")  # just reached the top combo
        self.count("blocks")
        self.hits += 1
        pts = value * self.multiplier
        bx, by = b["x"] + b["s"] / 2, b["y"] + b["s"] / 2
        if b["c"] == PURPLE:
            self.purples += 1
            if self.purples >= PURPLE_GOAL:
                self.unlock_color("purple")
        if air:
            self.p["chain"] += 1
            if self.p["chain"] >= AIR_STREAK:
                self.unlock_color("air")
            if self.p["chain"] >= 2:
                pts += self.p["chain"] - 1
                self.pops.append(dict(x=bx, y=by - 26, life=0.9, txt=f"AIR x{self.p['chain']}",
                                      c=(111, 183, 168), size=11))
        self.score += pts
        chain = air and self.p["chain"] >= 2
        self.play("gold" if value == GOLD_POINTS else "air" if chain else f"hit{self.multiplier}")
        if self.hits % BOLT_EVERY == 0 and self.charge < ZAP_MAX:  # no bolts while the zap is full
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
        if self.shielded:
            self.save_by_shield()
            return
        self.lives -= 1
        self.streak = 0
        self.game_counts["last_loss"] = self.t
        if self.lives <= 0:
            if self.t - self.game_counts["shield_pop_t"] <= JESTER_WINDOW:
                self.count("jester")
            self.game_over()

    def save_by_shield(self):
        """The shield takes the hit instead of a life: its outline swells out and bursts."""
        self.shielded = False
        self.play("heart")
        self.game_counts["shield_pop_t"] = self.t
        self.count("shield_saves")
        p = self.p
        cx, cy = p["x"] + PW / 2, p["y"] + PH / 2
        self.shield_pop = 0.0
        for x, y in self.shield_edge[::6]:  # the outline bursts into specks
            d = math.hypot(x - cx, y - cy) or 1
            self.parts.append(dict(x=x, y=y, vx=(x - cx) / d * 140, vy=(y - cy) / d * 140, life=0.4,
                                   c=random.choice((SHIELD_COLOR, (255, 250, 220))), s=3, g=0))
        self.pops.append(dict(x=cx, y=p["y"] - 30, life=0.9, txt="SAVED!", c=SHIELD_COLOR, size=14))

    def shield_layer(self, sprite, now):
        """The shield's outline around a Clawd sprite, 10px bigger on each side; and its edge points."""
        pts = pygame.mask.from_surface(sprite).outline()
        layer = pygame.Surface((sprite.get_width() + 20, sprite.get_height() + 20), pygame.SRCALPHA)
        k = 0.5 + 0.5 * math.sin(now / 200) if SHIELD_STYLE == "glow" else 1.0  # slow breathing
        if SHIELD_STYLE == "glow":
            for x, y in pts:
                layer.fill((*SHIELD_COLOR, int(30 + 50 * k)), (x + 7, y + 7, 7, 7))
        for x, y in pts:
            layer.fill((*SHIELD_COLOR, int(160 + 95 * k)), (x + 9, y + 9, 3, 3))
        return layer, pts

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
        p = self.p
        bounce = False
        if by < p["y"] + PH / 2:
            p["bomb_fx"] = "dizzy"  # bonked it with his head
        else:
            p["bomb_fx"] = "hotfoot"  # landed on it: legs kick, flames off his behind
            self.count("hotfoots")
            bounce = not p["on_ground"]
            if bounce:  # bouncing off it counts toward the air chain (no points, still costs a life)
                p["chain"] += 1
                if p["chain"] >= AIR_STREAK:
                    self.unlock_color("air")
                if p["chain"] >= 2:
                    self.pops.append(dict(x=bx, y=by - 40, life=0.9, txt=f"AIR x{p['chain']}",
                                          c=(111, 183, 168), size=11))
        p["bomb_t"] = 0.0
        if bounce:
            self.count("bomb_bounces")
            self.broke_in_air(bx, by, BOMB_RED)  # same as a block: jump off it, or a little bounce
        else:
            p["vy"] = min(p["vy"], -380)
        p["on_ground"] = False
        self.bombs_hit += 1
        self.count("bombs")
        if self.bombs_hit >= BOMB_GOAL:
            self.unlock_color("bombs")
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
        p["bj_t"], p["bj_flip"] = 0.0, abs(p["vx"]) > FLIP_SPEED
        self.count("jumps")
        if p["bj_flip"]:
            self.count("flips")
        self.burst(x, y, color, 10, 160)
        self.rings.append(dict(x=x, y=y, r=6.0, life=0.3, c=color))
        self.ghosts.append([p["x"], p["y"], 0.18])

    def broke_in_air(self, x, y, color):
        """After a midair hit: jump off the block if jump was just pressed, otherwise a little bounce
        (and a short moment where pressing jump still counts)."""
        p = self.p
        if color != BOMB_RED:
            self.count("block_bounces")
            self.count("block_bounces_total")
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

    def catch_bolt(self):
        """The first bolt charges a zap; each one after that, until it's used, makes it destroy one more block."""
        self.zaps += 1
        if self.zaps >= ZAP_GOAL:
            self.unlock_color("zaps")
        if self.charge >= ZAP_MAX:
            return  # already full (this one was falling when it filled up)
        self.charge = self.charge + 1 if self.charge else BOLT_KILLS
        self.play("speed")
        p = self.p
        txt = "+ZAP" if self.charge == BOLT_KILLS else ("ZAP MAX" if self.charge == ZAP_MAX else f"ZAP x{self.charge}")
        self.pops.append(dict(x=p["x"] + PW / 2, y=p["y"] - 14, life=0.9, txt=txt, c=BOLT_COLOR, size=12))

    def use_charge(self):
        """E or the ZAP button: use the stored zap, which then goes back to nothing. Kept if there's nothing to hit."""
        if self.mode != "play" or not self.charge or not any(not b.get("bomb") for b in self.blocks):
            return
        power, self.charge = self.charge, 0
        self.zap(power)

    def zap(self, power):
        """Lightning: destroy the power blocks closest to the ground."""
        self.play("zap")
        safe = [b for b in self.blocks if not b.get("bomb")]
        targets = sorted(safe, key=lambda b: -(b["y"] + b["s"]))[:power]
        if targets and power > BOLT_KILLS:
            self.pops.append(dict(x=W / 2, y=140, life=1.0, txt=f"ZAP x{power}", c=BOLT_COLOR, size=18))
        if targets:
            self.count("zapped", len(targets))
        for b in targets:
            b["dead"] = True
            if b["c"] == PURPLE:
                self.purples += 1
                if self.purples >= PURPLE_GOAL:
                    self.unlock_color("purple")
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
        self.swing_sprout(dt)
        for q in self.parts:
            q["life"] -= dt
            q["vy"] += q.get("g", 900) * dt  # flames have negative gravity and float up
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
                self.toast = self.toasts.pop(0) if self.toasts else None
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
        if self.mode == "paused" and self.leave_in is not None:
            before = math.ceil(self.leave_in)
            self.leave_in -= dt
            if self.leave_in <= 0:
                self.leave_to_menu()
                return
            if math.ceil(self.leave_in) < before:
                self.play("tick")
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
        self.hat_stats["playtime"] += dt
        p["air_t"] = 0.0 if p["on_ground"] else p["air_t"] + dt
        look = SKINS[self.skin][1]
        if look == "phoenix" and random.random() < 0.4:  # embers rising off him
            self.parts.append(dict(x=p["x"] + random.uniform(0, PW), y=p["y"] + random.uniform(0, 10),
                                   vx=random.uniform(-8, 8), vy=random.uniform(-45, -25), life=0.7,
                                   c=random.choice(PHOENIX_FIRE[2:]), s=2, g=0))
        elif look == "love" and random.random() < 0.05:  # little hearts floating up
            self.parts.append(dict(x=p["x"] + random.uniform(0, PW), y=p["y"], vx=random.uniform(-6, 6),
                                   vy=random.uniform(-30, -18), life=1.0, c=(255, 120, 160), s=1, g=0, heart=True))
        self.check_hats()  # the timed ones: an hour in one game, minutes without losing a life

        left, right, jump = controls

        accel, top = (2600 if p["on_ground"] else 1800), 230
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
        p["bj_t"] += dt
        wall = -1 if p["x"] <= 2 else (1 if p["x"] >= W - PW - 2 else 0)
        was_sliding, p["sliding"] = p["sliding"], 0
        if jump and p["on_ground"]:
            p["vy"], p["on_ground"], p["jump_buffer"] = -JUMP_SPEED, False, 0.0
            self.play("jump")
            self.count("jumps")
        elif pressed and p["block_grace"] > 0 and not p["on_ground"]:
            self.block_jump(*p["grace_at"])  # jump pressed just after breaking a block
        elif pressed and wall and not p["on_ground"]:
            # wall jump: kick off the screen edge, up and away
            p["vy"], p["vx"], p["jump_buffer"] = -WALL_JUMP, -wall * WALL_KICK, 0.0
            self.play("walljump")
            self.count("jumps")
            self.count("walljumps")
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
            if not was_sliding:
                p["slide_t"], p["slide_panic"] = 0.0, random.random() < SLIDE_PANIC
            p["sliding"] = wall
            p["slide_t"] += dt
            if random.random() < (0.9 if p["slide_panic"] else 0.5):
                self.parts.append(dict(x=0 if wall < 0 else W, y=p["y"] + PH - 6, vx=-wall * random.uniform(10, 40),
                                       vy=random.uniform(-40, 0), life=0.3, c=INK if p["slide_panic"] else DIM, s=2))
        p["bomb_t"] += dt
        if (p["bomb_fx"] == "dizzy" and p["bomb_t"] > DIZZY_TIME
                or p["bomb_fx"] == "hotfoot" and (p["bomb_t"] > HOTFOOT_TIME or p["on_ground"])):
            p["bomb_fx"] = None
        if p["bomb_fx"] == "hotfoot" and random.random() < 0.9:  # flames off his behind
            self.parts.append(dict(x=p["x"] + PW / 2 + random.uniform(-14, 14), y=p["y"] + PH - 4,
                                   vx=random.uniform(-25, 25), vy=random.uniform(-30, 60), life=0.3,
                                   c=random.choice(FIRE), s=random.choice((4, 5, 6)), g=-250))
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
            if not p.get("at_sky"):
                p["at_sky"] = True  # each separate touch of the top counts
                self.count("sky_total")
            p["y"], p["vy"] = 64, max(p["vy"], 0.0)
        elif p["y"] > 90:
            p["at_sky"] = False
        if p["y"] >= GROUND - PH:
            if not p["on_ground"]:
                self.landings += 1
                if self.landings >= LANDING_GOAL:
                    self.unlock_color("landings")
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
                self.count("golds")
                self.count("golds_total")
                if not p["on_ground"]:
                    self.broke_in_air(r["x"] + r["s"] / 2, r["y"] + r["s"] / 2, GOLD)
                self.burst(r["x"] + r["s"] / 2, r["y"] + r["s"] / 2, BOLT_COLOR, 20, 260)
                self.rings.append(dict(x=r["x"] + r["s"] / 2, y=r["y"] + r["s"] / 2, r=6.0, life=0.4, c=GOLD))
                self.pops.append(dict(x=max(90, min(W - 90, r["x"] + r["s"] / 2)), y=r["y"] - 30,
                                      life=JACKPOT_TIME, txt="JACKPOT!", c=GOLD, size=26, jackpot=True))
                self.shake = max(self.shake, 4)
            elif r["x"] < -30 or r["x"] > W + 10:
                r["dead"] = True  # got away, no penalty
        self.runners = [r for r in self.runners if not r.get("dead")]
        self.magnet = max(0.0, self.magnet - dt)
        if self.shield_pop is not None:
            self.shield_pop += dt
            if self.shield_pop > 0.3:
                self.shield_pop = None
        if self.shielded and SHIELD_STYLE == "sparkles" and self.shield_edge and random.random() < 0.35:
            x, y = random.choice(self.shield_edge)  # sparkles drift up off the outline
            self.parts.append(dict(x=x, y=y, vx=random.uniform(-8, 8), vy=random.uniform(-50, -25), life=0.6,
                                   c=random.choice((SHIELD_COLOR, (255, 250, 220))), s=2, g=0))

        self.spawn_in -= dt
        if self.spawn_in <= 0:
            # no clear spot: try again in a moment
            self.spawn_in = self.difficulty()[1] * (0.75 + random.random() * 0.5) if self.spawn() else 0.1

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
        self.keep_off_bombs()
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
                self.count("hearts")
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

        # lightning bolt pickups: catching one stores a zap for later
        for o in self.bolts:
            o["t"] += dt
            o["y"] += BOLT_FALL * dt
            bx = o["x"] + math.sin(o["t"] * 2.6) * 10
            if bx - 9 < p["x"] + PW - 4 and bx + 9 > p["x"] + 4 and o["y"] - 12 < p["y"] + PH - 6 and o["y"] + 12 > p["y"]:
                o["dead"] = True
                self.burst(bx, o["y"], BOLT_COLOR, 18, 200)
                self.catch_bolt()
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
                self.count("magnets_total")
                self.burst(mx, m["y"], MAGNET_COLOR, 18, 200)
                self.rings.append(dict(x=pcx, y=p["y"] + PH / 2, r=8.0, life=0.4, c=MAGNET_COLOR))
                self.pops.append(dict(x=mx, y=m["y"] - 14, life=1.0, txt="MAGNET", c=MAGNET_COLOR, size=14))
            elif m["y"] + 11 >= GROUND:
                m["dead"] = True
                self.burst(mx, GROUND - 4, MAGNET_COLOR, 8, 100)
        self.magnets = [m for m in self.magnets if not m["dead"]]

        # shield pickups drop at random times, at least SHIELD_COOLDOWN seconds apart
        if "shields" not in self.pickup_queue:
            self.shield_in -= dt
            if self.shield_in <= 0:
                self.queue_pickup("shields")
        self.pickup_wait -= dt
        if self.pickup_queue and self.pickup_wait <= 0:
            self.pickup_wait = PICKUP_GAP
            kind = self.pickup_queue.pop(0)
            if kind == "shields":  # the cooldown counts from when it actually drops
                self.shield_in = SHIELD_COOLDOWN + random.random() * SHIELD_RANDOM
            if kind != "bolts" or self.charge < ZAP_MAX:  # the zap may have filled up while this one waited
                getattr(self, kind).append(dict(x=40 + random.random() * (W - 80), y=-24.0, t=0.0, dead=False))

        # shield pickups: catching one saves Clawd's next lost life (they don't stack)
        for o in self.shields:
            o["t"] += dt
            o["y"] += SHIELD_FALL * dt
            ox = o["x"] + math.sin(o["t"] * 2.4) * 12
            if ox - 12 < p["x"] + PW - 4 and ox + 12 > p["x"] + 4 and o["y"] - 9 < p["y"] + PH - 6 and o["y"] + 9 > p["y"]:
                o["dead"] = True
                self.shielded = True
                self.play("speed")
                self.burst(ox, o["y"], SHIELD_COLOR, 18, 200)
                self.rings.append(dict(x=pcx, y=p["y"] + PH / 2, r=8.0, life=0.4, c=SHIELD_COLOR))
                self.pops.append(dict(x=ox, y=o["y"] - 14, life=1.0, txt="SHIELD", c=SHIELD_COLOR, size=14))
            elif o["y"] + 9 >= GROUND:
                o["dead"] = True
                self.burst(ox, GROUND - 4, SHIELD_COLOR, 8, 100)
        self.shields = [o for o in self.shields if not o["dead"]]

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

    def rainbow_button(self, label, x, y, w, h, action, size, now):
        """A button whose border and letters shimmer through the rainbow."""
        r = pygame.Rect(0, 0, w, h)
        r.center = (x, y)
        down = any(r.collidepoint(pos) for pos in self.pointers.values())
        self.canvas.fill(EARTH if down else NIGHT, r)
        shift = now / 1500
        pygame.draw.rect(self.canvas, rainbow(shift), r, 2)
        self.rainbow_text(label, x, y, size, shift)
        self.buttons.append((r, action))

    def rainbow_text(self, label, x, y, size, shift):
        f = self.font(size)
        lx = x - f.size(label)[0] / 2
        for i, ch in enumerate(label):
            w = f.size(ch)[0]
            self.text(ch, lx + w / 2, y, size, rainbow(shift - i / 18))
            lx += w

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
            if name == "zap" and live and self.charge and not on:
                col = BOLT_COLOR  # lit up while there's a stored bolt
            s.fill(EARTH if on else PANEL, r)
            pygame.draw.rect(s, col, r, 2)
            cx, cy = r.center
            if name in ("left", "right"):
                d = -1 if name == "left" else 1
                pygame.draw.polygon(s, col, [(cx - d * 14, cy - 22), (cx + d * 16, cy), (cx - d * 14, cy + 22)])
            elif name == "zap":  # a little bolt beside the label
                for row_i, row in enumerate(BOLT):
                    for k, ch in enumerate(row):
                        if ch == "X":
                            s.fill(col, (cx - 46 + k * 3, cy - 12 + row_i * 3, 3, 3))
                self.text(f"ZAP x{self.charge}" if live and self.charge else "ZAP", cx + 10, cy, 12, col, surf=s)
            else:
                pygame.draw.polygon(s, col, [(cx, cy - 32), (cx - 20, cy - 6), (cx + 20, cy - 6)])
                self.text("JUMP", cx, cy + 22, 12, col, surf=s)

    def pixel_sprite(self, rows, x, y, size, color):
        """color is one RGB, or a dict of RGB per character for art with more than one color."""
        for r, row in enumerate(rows):
            for k, ch in enumerate(row):
                if ch != ".":
                    self.canvas.fill(color[ch] if isinstance(color, dict) else color, (x + k * size, y + r * size, size, size))

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
            skin = s.get("skin")
            name_col = TIER_COLOR[skin] if skin is not None and skin in TIER_COLOR else col  # by the color they wore
            self.text(f"{i + 1}.", 92, y, 13, col if mine else DIM, "right")
            self.text(s["name"], 104, y, 13, name_col, "left")
            self.text(str(s["score"]), W - 80, y, 13, col, "right")
            if mine:
                self.text(">", 70, y, 13, CLAWD, "right")  # your new score

    def stat_rows(self):
        """Everything the stats page shows: (label, value)."""
        st = self.hat_stats
        hours, mins = divmod(int(st["playtime"] // 60), 60)
        n = lambda v: f"{int(v):,}"
        return [
            ("GAMES PLAYED", n(st["games"])), ("PLAY TIME", f"{hours}H {mins:02d}M"),
            ("DAYS PLAYED", n(len(st["days"]))), ("MY BEST SCORE", n(self.personal_best())),
            ("TOTAL SCORE", n(st["total_score"])),
            ("BLOCKS BROKEN", n(st["blocks"])), ("GOLD CAUGHT", n(st["golds_total"])),
            ("HEARTS CAUGHT", n(st["hearts"])), ("MAGNETS CAUGHT", n(st["magnets_total"])),
            ("BOLTS CAUGHT", n(self.zaps)),
            ("BLOCKS ZAPPED", n(st["zapped"])), ("SHIELD SAVES", n(st["shield_saves"])),
            ("BOMBS HIT", n(st["bombs"])), ("HOT FOOTS", n(st["hotfoots"])),
            ("BOMB BOUNCES", n(st["bomb_bounces"])), ("BLOCK BOUNCES", n(st["block_bounces_total"])),
            ("COMBO X4", n(st["combo4"])), ("JUMPS", n(st["jumps"])),
            ("WALL JUMPS", n(st["walljumps"])), ("DASHES", n(st["dashes"])),
            ("DASH HITS", n(st["dash_hits"])), ("LANDINGS", n(self.landings)),
            ("SKY TOUCHES", n(st["sky_total"])), ("DANCES", n(st["dances"])),
            ("HATS", f"{len(self.unlocked)}/{len(HATS)}"), ("COLORS", f"{len(self.skins)}/{len(SKINS)}"),
        ]

    def draw_stats(self):
        """Two columns of totals over every game played."""
        self.text("STATS", W / 2, 60, 20, GOLD)
        rows = self.stat_rows()
        half = (len(rows) + 1) // 2
        for i, (label, value) in enumerate(rows):
            col, row = divmod(i, half)
            x, y = 22 + col * 190, 100 + row * 28
            self.text(label, x, y, 9, DIM, "left")
            self.text(value, x + 176, y, 11, GOLD if label in ("MY BEST SCORE", "TOTAL SCORE", "HATS", "COLORS") else INK, "right")

    def draw_help(self):
        c = self.canvas
        self.text("HOW TO PLAY", W / 2, 60, 20, GOLD)
        sections = [
            ("CONTROLS", [("ARROWS", "move"), ("JUMP" if TOUCH else "UP", "jump"),
                          ("BLOCKS", "jump as you hit one"),
                          ("TAP TAP", "dash left or right"), ("WALL", "jump again off the edge"),
                          ("ZAP" if TOUCH else "E", "use a stored bolt")] + ([] if TOUCH else [("F11", "full screen")])),
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
                y += 15
            y += 4
        # pickups, drawn with their in-game sprites
        self.text("PICKUPS", 52, y, 11, CLAWD, "left")
        y += 20
        self.pixel_heart(64, y - 9, 3, CLAWD)
        self.text("extra life", 96, y, 10, DIM, "left")
        y += 20
        for r, row in enumerate(BOLT):
            for k, ch in enumerate(row):
                if ch == "X":
                    c.fill(BOLT_COLOR, (66 + k * 3, y - 12 + r * 3, 3, 3))
        self.text(f"zap  each bolt adds one (max {ZAP_MAX})", 96, y, 10, DIM, "left")
        y += 20
        for r, row in enumerate(MAGNET):
            for k, ch in enumerate(row):
                if ch != ".":
                    c.fill(MAGNET_TIP if ch == "T" else MAGNET_COLOR, (64 + k * 3, y - 10 + r * 3, 3, 3))
        self.text("pulls blocks to you", 96, y, 10, DIM, "left")
        y += 20
        self.pixel_sprite(SHIELD_ICON, 65, y - 10, 3, SHIELD_PIXELS)
        self.text("saves your next lost life", 96, y, 10, DIM, "left")

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
        sliding = p["sliding"]
        panic = sliding and p["slide_panic"]
        if panic or p["bomb_fx"] == "hotfoot":
            frame = 1 + int(now / 45) % 2  # legs flail
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
        skin = self.skin_viewing if self.mode == "title" else self.skin
        sprite = self.skin_sprite(skin, frame, p["blink"] > 0 or asleep or panic or p["bomb_fx"] == "dizzy", now)
        if skin not in self.skins:
            sprite = sprite.copy()
            sprite.fill((150, 145, 160, 255), special_flags=pygame.BLEND_RGBA_MULT)  # locked: dimmed
        plain, moves = sprite, []  # Clawd before he's squashed or spun, and each of those (the hat gets them too)
        squash = -0.05 if not p["on_ground"] and not sliding else 0
        if asleep:
            squash = 0.04 * math.sin(now / 700)  # slow breathing
        if squash:
            moves.append(("scale", 1 + squash, 1 - squash))
        if p["bj_flip"] and p["bj_t"] < 0.45 and not p["on_ground"]:
            spin = -1 if p["vx"] >= 0 else 1  # flip toward where Clawd is heading
            moves.append(("rotate", spin * 360 * p["bj_t"] / 0.45))
        elif not p["bj_flip"] and p["bj_t"] < 0.31:
            # spring off the block: squash flat on impact, then stretch tall and settle
            if p["bj_t"] < 0.06:
                sx, sy = 1.3, 0.7
            else:
                k = 1 - (p["bj_t"] - 0.06) / 0.25
                sx, sy = 1 - 0.2 * k, 1 + 0.3 * k
            moves.append(("scale", sx, sy))
        if p["dance"] > 0:
            moves.append(("rotate", 12 if beat % 2 else -12))  # wiggle with the beat
        if panic:
            sway, hop = random.choice((-1, 0, 1)), random.choice((-1, 0, 1))  # shaking
        elif sliding:
            # feet and arm braced on the wall, wobbling to keep balance
            lean = min(1.0, p["slide_t"] / 0.12) * (SLIDE_LEAN + 5 * math.sin(p["slide_t"] * 9))
            moves.append(("rotate", sliding * lean))
        sprite = apply_moves(plain, moves)
        for gx, gy, life in self.ghosts:
            ghost = self.skin_sprite(self.skin, 0, False, now).copy()
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
        if SKINS[skin][1] == "ghost":
            hop += math.sin(now / 400) * 3  # floats
        body = sprite.get_rect(midbottom=(round(p["x"] + PW / 2 + sway) + ox, round(p["y"] + PH + hop) + oy))
        if sliding and not panic:
            # press the tilted sprite's visible pixels flat against the wall
            vis = sprite.get_bounding_rect()
            body.x = (W - vis.right if sliding > 0 else -vis.left) + ox
            body.y = round(p["y"] + PH) - vis.bottom + oy
        if self.shielded and self.mode in ("play", "paused", "resume"):
            layer, edge = self.shield_layer(sprite, now)
            c.blit(layer, (body.x - 10, body.y - 10))
            self.shield_edge = [(x + body.x - ox, y + body.y - oy) for x, y in edge]
        elif self.shield_pop is not None and self.shield_edge:
            # the outline swells out and fades after a save
            layer, _ = self.shield_layer(sprite, now)
            scale = 1 + self.shield_pop * 2.5
            layer = pygame.transform.scale(layer, (int(layer.get_width() * scale), int(layer.get_height() * scale)))
            layer.set_alpha(int(255 * (1 - self.shield_pop / 0.3)))
            c.blit(layer, layer.get_rect(center=body.center))
        clawd = [(sprite, body)]
        hat = self.viewing if self.mode == "title" else self.worn
        if hat >= 0:
            # the hat goes on before he's squashed or spun, so it stays on his head through flips and wiggles.
            # Padded the same above and below, so spinning the whole thing turns it around his middle.
            art, name = self.hat_sprite(hat, now), HATS[hat][0]
            bob = round(HAT_BOB.get(name, 0) * (1 + math.sin(now / 400)) / 2)
            hat_bottom = HAT_DROP.get(name, 0) * PX - bob  # from the top of his head
            pad = max(0, art.get_height() - hat_bottom)
            whole = pygame.Surface((max(PW, art.get_width()), PH + 2 * pad), pygame.SRCALPHA)
            mid = whole.get_width() // 2
            whole.blit(plain, plain.get_rect(midtop=(mid, pad)))
            whole.blit(art, art.get_rect(midbottom=(mid, pad + hat_bottom)))
            whole = apply_moves(whole, moves)
            clawd = [(whole, whole.get_rect(center=body.center))]
        c.blits(clawd)
        if p["bomb_fx"] == "dizzy" and self.mode == "play":
            top = body.top - (10 if hat >= 0 else 0)
            for k in range(3):  # stars circling his head
                a = p["bomb_t"] * 7 + k * math.tau / 3
                sx, sy = int(body.centerx + math.cos(a) * 18), int(top - 8 + math.sin(a) * 5)
                c.fill(GOLD, (sx - 3, sy - 1, 7, 3))
                c.fill(GOLD, (sx - 1, sy - 3, 3, 7))

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
            if q.get("heart"):
                self.pixel_heart(q["x"] + ox, q["y"] + oy, 1, q["c"])
            else:
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
        for o in self.shields:
            bx = o["x"] + math.sin(o["t"] * 2.4) * 12
            pulse = 1 + 0.15 * math.sin(o["t"] * 9)
            glow = pygame.Surface((44, 44), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*SHIELD_COLOR, 55), (22, 22), int(17 * pulse))
            c.blit(glow, (bx - 22 + ox, o["y"] - 22 + oy))
            self.pixel_sprite(SHIELD_ICON, bx - 10 + ox, o["y"] - 10 + oy, 3, SHIELD_PIXELS)
        for h in self.hearts:
            hx = h["x"] + math.sin(h["t"] * 2) * 14
            pulse = 1 + 0.12 * math.sin(h["t"] * 8)
            glow = pygame.Surface((40, 40), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*CLAWD, 50), (20, 20), int(16 * pulse))
            c.blit(glow, (hx - 20 + ox, h["y"] - 20 + oy))
            self.pixel_heart(hx - 10 + ox, h["y"] - 9 + oy, 3, CLAWD)

        for q in self.pops:
            if q.get("jackpot"):
                # pops in big, wobbles and shimmers through the rainbow
                a = JACKPOT_TIME - q["life"]
                f = self.font(q["size"])
                rainbow = [int(v * 255) for v in colorsys.hsv_to_rgb(now / 650 % 1, 0.5, 1)]
                img = f.render(q["txt"], False, rainbow)
                art = pygame.Surface((img.get_width() + 2, img.get_height() + 2), pygame.SRCALPHA)
                art.blit(f.render(q["txt"], False, NIGHT), (2, 2))
                art.blit(img, (0, 0))
                scale = max(0.1, 1 + 0.8 * math.exp(-a * 10) * math.cos(a * 30))
                art = pygame.transform.rotozoom(art, 6 * math.sin(a * 14) * math.exp(-a * 3), scale)
                c.blit(art, art.get_rect(center=(q["x"] + ox, q["y"] + oy)))
                continue
            self.text(q["txt"], q["x"] + ox, q["y"] + oy, q.get("size", 14), q["c"])
        if self.wake > 0 and self.mode == "play":
            self.text("!", body.centerx, body.top - 18 - (8 if self.worn >= 0 else 0), 20, GOLD)

        if self.flash > 0:
            veil = pygame.Surface((W, H), pygame.SRCALPHA)
            veil.fill((255, 250, 220, int(90 * self.flash / 0.18)))
            c.blit(veil, (0, 0))

        for i in range(max(3, self.lives)):
            self.pixel_heart(14 + i * 26, 16, 3, CLAWD if i < self.lives else EARTH)
        x = 14 + max(3, self.lives) * 26
        if self.shielded and self.mode in ("play", "paused"):
            self.pixel_sprite(SHIELD_ICON, x, 15, 3, SHIELD_PIXELS)
            x += 26
        if self.mode in ("play", "paused"):
            if self.charge:  # the stored zap, and how many blocks it will destroy
                full = self.charge >= ZAP_MAX
                self.pixel_sprite(BOLT, x, 14, 2, INK if full and int(now / 250) % 2 else BOLT_COLOR)
                self.text(f"x{self.charge}", x + 16, 22, 10, BOLT_COLOR, "left")
        # streak meter: fills toward the next heart drop
        if self.mode in ("play", "paused"):
            fill = (self.streak % HEART_STREAK) / HEART_STREAK
            c.fill(EARTH, (14, 40, 124, 4))
            c.fill(GOLD, (14, 40, int(124 * fill), 4))
            if self.streak:
                label = f"STREAK {self.streak}" + (f"  x{self.multiplier}" if self.multiplier > 1 else "")
                self.text(label, 14, 54, 10, GOLD if self.streak >= 10 else DIM, "left")
            bar_y = 66
            if self.magnet:
                c.fill(EARTH, (14, bar_y, 124, 4))
                c.fill(MAGNET_COLOR, (14, bar_y, int(124 * self.magnet / MAGNET_TIME), 4))
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
                    for k, (label, action) in enumerate((("HELP", self.go("help")), ("SCORES", self.show_board),
                                                         ("STATS", self.go("stats")), ("GALLERY", self.open_gallery))):
                        self.button(label, W / 2 + (k - 1.5) * 92, 328, 86, 30, action, 9)
                    if not self.on_home_screen:
                        self.button("ADD TO HOME SCREEN", W / 2, 366, 354, 30, self.go("home"), 10, GOLD)
                else:
                    if blink_on:
                        self.text("PRESS SPACE", W / 2, 330, 16, INK)
                    self.text("I HELP   H SCORES   S STATS   G GALLERY   M SOUND", W / 2, 362, 10, DIM)
                if self.update_ready:
                    if TOUCH:
                        self.rainbow_button("NEW VERSION  TAP TO UPDATE", W / 2, 80, 300, 28, self.update_now, 10, now)
                    else:
                        self.rainbow_text("A NEW VERSION IS OUT", W / 2, 80, 11, now / 1500)
                self.text(build_label(self.build), W - 16, 64, 8, DIM, "right")
                # color picker, in the dirt under Clawd
                cname = SKINS[self.skin_viewing][0]
                ccol = TIER_COLOR[self.skin_viewing]  # the name's color shows how hard it is to get
                if TOUCH:
                    self.button("<", 30, 536, 44, 36, lambda: self.pick_color(-1), 14, DIM)
                    self.button(">", W - 30, 536, 44, 36, lambda: self.pick_color(1), 14, DIM)
                else:
                    cname = f"C  {cname}"
                self.text(cname, W / 2, 528, 11, ccol)
                self.text(self.color_status(self.skin_viewing), W / 2, 545, 9, DIM)
                if self.viewing == -1:
                    name, col = "NO HAT", DIM
                else:
                    name, col = HATS[self.viewing][0], HAT_TIER_COLOR[self.viewing]  # colored by how hard it is to get
                if TOUCH:
                    self.button("<", 30, 406, 44, 36, lambda: self.pick_hat(-1), 14, DIM)
                    self.button(">", W - 30, 406, 44, 36, lambda: self.pick_hat(1), 14, DIM)
                    self.text(name, W / 2, 400, 11, col)
                    self.text(self.hat_status(self.viewing), W / 2, 416, 9, DIM)
                else:
                    self.text(f"<  {name}  >", W / 2, 398, 11, col)
                    self.text(self.hat_status(self.viewing), W / 2, 414, 9, DIM)
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
            elif self.mode == "gallery":
                self.draw_gallery(now)
            elif self.mode == "stats":
                self.draw_stats()
                if TOUCH:
                    self.button("BACK", W / 2 - 76, 476, 140, 34, self.go("title"), 12, DIM)
                    self.button("PLAY", W / 2 + 76, 476, 140, 34, self.start, 12, CLAWD)
                elif blink_on:
                    self.text("SPACE TO PLAY   ESC TO GO BACK", W / 2, 476, 11, DIM)
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
                elif self.leave_in is not None:
                    n = math.ceil(self.leave_in)
                    grow = 1 + 0.4 * (self.leave_in - n + 1) ** 3
                    self.text("BACK TO MENU IN", W / 2, 170, 13, DIM)
                    self.text(str(n), W / 2, 225, int(56 * grow), CLAWD)
                    if TOUCH:
                        self.button("CANCEL", W / 2, 300, 170, 44, self.cancel_leave, 16, INK)
                    else:
                        self.text("SPACE OR ESC TO CANCEL", W / 2, 290, 13, INK)
                else:
                    self.text("PAUSED", W / 2, 220, 40, INK)
                    if TOUCH:
                        self.button("RESUME", W / 2, 290, 170, 44, self.resume, 16, CLAWD)
                        self.button("MAIN MENU", W / 2, 346, 170, 36, self.ask_leave, 12, DIM)
                    else:
                        if blink_on:
                            self.text("PRESS SPACE TO RESUME", W / 2, 280, 13, DIM)
                        self.text("Q  MAIN MENU", W / 2, 310, 11, DIM)
            elif self.mode == "entry":
                top_before = max([s["score"] for s in self.scores] + [0])
                self.text("GAME OVER", W / 2, 150, 40, CLAWD)
                self.text(f"{self.score} POINT{'' if self.score == 1 else 'S'}", W / 2, 200, 22, INK)
                self.text("NEW HIGH SCORE" if self.score > top_before else "YOU MADE THE TOP 10", W / 2, 246, 14, GOLD)
                self.text("TYPE YOUR NAME", W / 2, 290, 11, DIM)
                box = pygame.Rect(W / 2 - 120, 306, 240, 36)
                c.fill(NIGHT, box)
                pygame.draw.rect(c, CLAWD, box, 2)
                self.text(self.name + ("_" if blink_on and len(self.name) < NAME_LEN else " "), W / 2, 324, 18,
                          TIER_COLOR[self.skin])  # your name, in the tier color of what you're wearing
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
            if "hat" in t:
                icon, title, name = self.hat_icons[t["hat"]], "NEW HAT UNLOCKED", HATS[t["hat"]][0]
            else:
                icon, title, name = self.skin_icons[t["color"]], "NEW COLOR UNLOCKED", SKINS[t["color"]][0]
            c.blit(icon, icon.get_rect(center=(box.left + 34, box.centery)))
            self.text(title, box.left + 66, box.top + 18, 11, GOLD, "left")
            self.text(name, box.left + 66, box.top + 38, 13, INK, "left")

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
                    if self.mode in ("play", "resume", "paused"):
                        self.save_progress()
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
                    if e.key == pygame.K_F11:
                        self.toggle_fullscreen()
                        continue
                    if self.mode == "gallery":
                        self.gallery_key(e.key)
                        continue
                    if e.key == pygame.K_g and self.mode == "title":
                        self.open_gallery()
                        continue
                    if e.key == pygame.K_h and self.mode in ("title", "over"):
                        self.last_key = None
                        self.board.refresh()
                        self.mode = "board"
                        continue
                    if e.key == pygame.K_c and self.mode == "title":
                        self.pick_color(1)
                        continue
                    if e.key == pygame.K_i and self.mode == "title":
                        self.mode = "help"
                        continue
                    if e.key == pygame.K_s and self.mode == "title":
                        self.mode = "stats"
                        continue
                    if e.key == pygame.K_ESCAPE and self.mode == "over":
                        self.reset("title")
                        continue
                    if e.key == pygame.K_ESCAPE and self.mode in ("board", "help", "stats"):
                        self.mode = "title"
                        continue
                    if self.mode == "title" and e.key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
                        self.pick_hat(-1 if e.key in (pygame.K_LEFT, pygame.K_a) else 1)
                        continue
                    if e.key in (pygame.K_LEFT, pygame.K_a):
                        self.tap_direction(-1)
                    elif e.key in (pygame.K_RIGHT, pygame.K_d):
                        self.tap_direction(1)
                    elif e.key == pygame.K_e and self.mode == "play":
                        self.use_charge()
                    if self.mode == "paused" and self.leave_in is not None:
                        if e.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_p, pygame.K_q):
                            self.cancel_leave()
                        continue
                    if e.key == pygame.K_q and self.mode == "paused":
                        self.ask_leave()
                        continue
                    if e.key in (pygame.K_p, pygame.K_ESCAPE):
                        if self.mode in ("play", "resume"):
                            self.pause()
                        elif self.mode == "paused":
                            self.resume()
                    elif e.key in (pygame.K_SPACE, pygame.K_RETURN) and self.mode not in ("play", "resume"):
                        self.start()
            self.update(dt, self.controls())
            self.update_music(dt)
            self.draw(pygame.time.get_ticks())
            await asyncio.sleep(0)  # lets the browser run between frames


async def main():
    await Game().run()
    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
