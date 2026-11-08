#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 TheIntroDB
#
"""Write the pill textures for the add-on's button styles.

Each style is a folder under resources/skins/ that Kodi loads as its own skin for the
overlay window (see the third argument to WindowXMLDialog in overlay.py), and each pill
is a <control type="button"> whose texturefocus/texturenofocus are 9-slice PNGs in that
folder. This script writes those PNGs.

The classic style keeps the texture that shipped before the styles existed
(rounded_rect.png: a white 64x64 9-slice, hard-edged, 11px radius) so its pills look
exactly as they did — it is tinted per pill with colordiffuse in overlay.xml.

Geometry the XML depends on:

* a texture is square with side == the pill height, so a full-round style is a stadium;
* <border> in the XML must stay below half the pill height, because Kodi has to have a
  middle strip left to stretch; the usual value is radius == height / 2 with
  border == height / 2 - 1;
* a 9-slice whose corner radius equals the pill height and whose middle strip is very
  thin renders a stadium with one or two pixels of straight edge, which is what the
  glass style wants (Stremio Enhanced's glass theme uses a 50px radius on a smaller
  button, i.e. fully round);
* the colours are baked in rather than applied with colordiffuse, because colordiffuse
  can only darken a texture — it cannot make the hairline border lighter than the fill,
  and it cannot make the focused state brighter.

Measured before choosing the min widths in overlay.xml (tests/test_button_styles.py
re-asserts the floor): the widest label the pills can show across the six shipped
languages is Polish "Pomiń napisy końcowe" at 295px in the 1080i font and 193px in the
720p font, against a 260px/200px box in the old fixed-width design.
"""
import os
import sys

from PIL import Image, ImageDraw

SUPERSAMPLE = 4

# Stremio Enhanced's glass theme, as rgba over the video.
GLASS_FILL = (70, 70, 70, 56)  # background: rgba(70, 70, 70, 0.22)
GLASS_EDGE = (255, 255, 255, 10)  # 1px border: rgba(255, 255, 255, 0.04)
# The focused pill is a white veil, as Stremio's hover is — but its label is dark, not
# white: a 22%-white veil over video is a light grey, and white text on that is barely
# legible. The overlay's XML pairs this with focusedcolor FF111111, the same
# light-pill-dark-text pairing the classic style uses.
GLASS_FOCUS_FILL = (255, 255, 255, 77)  # ~0.30 white, enough for dark text to read
GLASS_FOCUS_EDGE = (255, 255, 255, 26)
# The report pill is the secondary one, so it sits darker than the skip pill.
GLASS_SECONDARY_FILL = (12, 12, 12, 97)
GLASS_SECONDARY_EDGE = (255, 255, 255, 10)
GLASS_SECONDARY_FOCUS_FILL = GLASS_FOCUS_FILL
GLASS_SECONDARY_FOCUS_EDGE = GLASS_FOCUS_EDGE

STYLES = {
    'glass': {
        '1080i': {'pill_height': 48},
        '720p': {'pill_height': 38},
    },
}

TEXTURES = {
    'pill.png': (GLASS_FILL, GLASS_EDGE),
    'pill_focus.png': (GLASS_FOCUS_FILL, GLASS_FOCUS_EDGE),
    'pill_secondary.png': (GLASS_SECONDARY_FILL, GLASS_SECONDARY_EDGE),
    'pill_secondary_focus.png': (GLASS_SECONDARY_FOCUS_FILL, GLASS_SECONDARY_FOCUS_EDGE),
}


def stadium(side: int, fill, edge, edge_width: int = 1) -> Image.Image:
    """A fully rounded pill: a rounded rect whose radius is half its height."""
    big = side * SUPERSAMPLE
    image = Image.new('RGBA', (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    radius = big // 2
    draw.rounded_rectangle((0, 0, big - 1, big - 1), radius=radius, fill=edge)
    inset = edge_width * SUPERSAMPLE
    draw.rounded_rectangle((inset, inset, big - 1 - inset, big - 1 - inset),
                           radius=radius - inset, fill=fill)
    return image.resize((side, side), Image.LANCZOS)


def write_style(style: str, resources_root: str) -> int:
    """Write every texture for one style, one set per resolution."""
    written = 0
    for res, geometry in STYLES[style].items():
        folder = os.path.join(resources_root, 'skins', style, res)
        os.makedirs(folder, exist_ok=True)
        for name, (fill, edge) in TEXTURES.items():
            path = os.path.join(folder, name)
            stadium(geometry['pill_height'], fill, edge).save(path, optimize=True)
            written += 1
            print('wrote {}'.format(os.path.relpath(path)))
    return written


def main() -> int:
    """Write every style's textures, resolving the add-on's resources folder."""
    resources_root = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', 'plugin.video.tidb', 'resources')
    resources_root = os.path.normpath(resources_root)
    if not os.path.isdir(resources_root):
        print('resources folder not found: {}'.format(resources_root), file=sys.stderr)
        return 1
    total = 0
    for style in sorted(STYLES):
        total += write_style(style, resources_root)
    print('{} textures written'.format(total))
    return 0


if __name__ == '__main__':
    sys.exit(main())
