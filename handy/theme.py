import pygame

MODE = "night"

PALETTES = {
    "night": {
        "BG_TOP": (13, 17, 25),
        "BG_BOTTOM": (8, 10, 15),
        "BG": (10, 13, 19),
        "CARD": (21, 26, 36),
        "CARD_HI": (29, 36, 49),
        "CARD_PRESS": (36, 45, 61),
        "BORDER": (40, 49, 65),
        "TEXT": (238, 242, 249),
        "MUTED": (141, 152, 170),
        "FAINT": (94, 104, 122),
        "ACCENT": (112, 140, 255),
        "ACCENT_HI": (136, 160, 255),
        "ACCENT_SOFT": (44, 58, 100),
        "TEAL": (56, 224, 178),
        "AMBER": (255, 187, 108),
        "DANGER": (255, 107, 118),
        "WHITE": (255, 255, 255),
        "SOFT_PRESS": (58, 76, 130),
        "DANGER_PRESS": (48, 22, 27),
        "TEAL_PRESS": (100, 240, 205),
        "TEAL_TEXT": (10, 30, 25),
    },
    "day": {
        "BG_TOP": (238, 242, 248),
        "BG_BOTTOM": (222, 229, 238),
        "BG": (235, 239, 245),
        "CARD": (255, 255, 255),
        "CARD_HI": (244, 247, 251),
        "CARD_PRESS": (229, 235, 243),
        "BORDER": (203, 213, 225),
        "TEXT": (17, 24, 39),
        "MUTED": (71, 85, 105),
        "FAINT": (100, 116, 139),
        "ACCENT": (96, 120, 255),
        "ACCENT_HI": (67, 97, 238),
        "ACCENT_SOFT": (224, 231, 255),
        "TEAL": (13, 148, 136),
        "AMBER": (217, 119, 6),
        "DANGER": (220, 38, 38),
        "WHITE": (255, 255, 255),
        "SOFT_PRESS": (191, 206, 254),
        "DANGER_PRESS": (254, 226, 226),
        "TEAL_PRESS": (10, 110, 102),
        "TEAL_TEXT": (255, 255, 255),
    },
}


def apply_mode(mode):
    global MODE
    MODE = mode if mode in PALETTES else "night"
    globals().update(PALETTES[MODE])


BG_TOP = PALETTES[MODE]["BG_TOP"]
BG_BOTTOM = PALETTES[MODE]["BG_BOTTOM"]
BG = PALETTES[MODE]["BG"]
CARD = PALETTES[MODE]["CARD"]
CARD_HI = PALETTES[MODE]["CARD_HI"]
CARD_PRESS = PALETTES[MODE]["CARD_PRESS"]
BORDER = PALETTES[MODE]["BORDER"]
TEXT = PALETTES[MODE]["TEXT"]
MUTED = PALETTES[MODE]["MUTED"]
FAINT = PALETTES[MODE]["FAINT"]
ACCENT = PALETTES[MODE]["ACCENT"]
ACCENT_HI = PALETTES[MODE]["ACCENT_HI"]
ACCENT_SOFT = PALETTES[MODE]["ACCENT_SOFT"]
TEAL = PALETTES[MODE]["TEAL"]
AMBER = PALETTES[MODE]["AMBER"]
DANGER = PALETTES[MODE]["DANGER"]
WHITE = PALETTES[MODE]["WHITE"]
SOFT_PRESS = PALETTES[MODE]["SOFT_PRESS"]
DANGER_PRESS = PALETTES[MODE]["DANGER_PRESS"]
TEAL_PRESS = PALETTES[MODE]["TEAL_PRESS"]
TEAL_TEXT = PALETTES[MODE]["TEAL_TEXT"]

_FONT_ROOTS = [
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/truetype/liberation",
    "/usr/share/fonts/truetype/freefont",
    "/usr/share/fonts/truetype/noto",
    "/usr/local/share/fonts",
    "/usr/share/fonts",
]

_REGULAR_NAMES = [
    "DejaVuSans.ttf",
    "LiberationSans-Regular.ttf",
    "FreeSans.ttf",
    "NotoSans-Regular.ttf",
]

_BOLD_NAMES = [
    "DejaVuSans-Bold.ttf",
    "LiberationSans-Bold.ttf",
    "FreeSansBold.ttf",
    "NotoSans-Bold.ttf",
]

_font_paths = {}


def _find_font(bold):
    if bold in _font_paths:
        return _font_paths[bold]
    names = _BOLD_NAMES if bold else _REGULAR_NAMES
    found = None
    for root in _FONT_ROOTS:
        for name in names:
            candidate = f"{root}/{name}"
            try:
                with open(candidate, "rb"):
                    found = candidate
                    break
            except OSError:
                continue
        if found:
            break
    if found is None:
        match = pygame.font.match_font("dejavu sans" if not bold else "dejavu sans bold")
        found = match
    _font_paths[bold] = found
    return found


class Theme:
    def __init__(self, size):
        self.size = size
        self.mode = MODE
        self.w, self.h = size
        self.scale = max(0.78, min(2.4, min(size) / 480.0))
        self.radius = self.px(18)
        self._fonts = {}

    def px(self, value):
        return max(1, round(value * self.scale))

    def font(self, size, bold=False):
        key = (size, bold)
        if key not in self._fonts:
            path = _find_font(bold)
            pixels = self.px(size)
            if path:
                self._fonts[key] = pygame.font.Font(path, pixels)
            else:
                self._fonts[key] = pygame.font.Font(None, pixels)
        return self._fonts[key]


class Background:
    def __init__(self, size):
        w, h = size
        self.surface = pygame.Surface(size)
        for y in range(h):
            t = y / max(1, h - 1)
            color = (
                int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * t),
                int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * t),
                int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * t),
            )
            pygame.draw.line(self.surface, color, (0, y), (w, y))
        glow = pygame.Surface(size, pygame.SRCALPHA)
        radius = int(min(w, h) * 0.9)
        cx = int(w * 0.85)
        cy = int(-h * 0.15)
        steps = 26
        for i in range(steps, 0, -1):
            t = i / steps
            alpha = int(10 * (1 - t))
            pygame.draw.circle(glow, (*ACCENT, alpha), (cx, cy), int(radius * t))
        self.surface.blit(glow, (0, 0))

    def draw(self, surface):
        surface.blit(self.surface, (0, 0))
