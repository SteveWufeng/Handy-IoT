import pygame

BG_TOP = (13, 17, 25)
BG_BOTTOM = (8, 10, 15)
BG = (10, 13, 19)
CARD = (21, 26, 36)
CARD_HI = (29, 36, 49)
CARD_PRESS = (36, 45, 61)
BORDER = (40, 49, 65)
TEXT = (238, 242, 249)
MUTED = (141, 152, 170)
FAINT = (94, 104, 122)
ACCENT = (112, 140, 255)
ACCENT_HI = (136, 160, 255)
ACCENT_SOFT = (44, 58, 100)
TEAL = (56, 224, 178)
AMBER = (255, 187, 108)
DANGER = (255, 107, 118)
WHITE = (255, 255, 255)

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
