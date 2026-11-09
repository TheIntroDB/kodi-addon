#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 TheIntroDB
#
"""Render a preview of each pill style, using Kodi's own auto-width rule.

Writes button-style-<style>.png into $TIDB_PREVIEW_DIR — the temp directory by default,
and deliberately not into the repository: this repo's docs/ folder is the published Kodi
repository. One sheet per style, a row per shipped language, plus a row whose label is
long enough to widen the pill past its floor.

These are mockups, not Kodi screenshots: the only thing simulated is Kodi's sizing rule
(width = CLAMP(label width, min, max), from CGUIButtonControl::GetWidth) and the
compositing of a translucent texture over video. The colours below are the ones
tools/make_pill_textures.py bakes for the glass style and the ones overlay.xml tints the
classic style with — keep the three in step.

Width = CLAMP(text_width, min, max) is what CGUIButtonControl::GetWidth computes, so
what is drawn here is what Kodi would draw for each label: all shipped labels land on
the 350px floor, and the last row shows a label long enough to push the pill towards
its 390px cap instead of scrolling.
"""
import os
import re
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANG_DIR = os.path.join(REPO, 'plugin.video.tidb/resources/language')
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
OUT = os.path.join(os.environ.get('TIDB_PREVIEW_DIR', tempfile.gettempdir()),
                   'button-style-{}.png')
#: Candidates for the row that demonstrates growth, in the order to try them: the first
#: one that measures between the floor and the cap wins, so the row shows the pill
#: widening rather than the label being clipped (measured, not guessed).
LONG_CANDIDATES = (
    'Pomiń napisy końcowe teraz',
    'Pomiń napisy końcowe filmu',
    'Pomiń napisy końcowe serialu',
)

MIN_W, MAX_W, PILL_H, GAP = 350, 390, 48, 8
GROUP_RIGHT = 1870          # where the 350px pill ends, as the XML places it
FONT_SIZE = 26

STYLES = {
    'default': {
        'title': 'Classic',
        'radius': 11,
        # The focused pill (the skip pill, which holds focus when the prompt opens).
        'skip_fill': (255, 255, 255, 255),
        'skip_text': (17, 17, 17, 255),
        # The resting secondary pill (Report).
        'report_fill': (0, 0, 0, 176),
        'report_text': (240, 240, 240, 255),
        'edge': None,
    },
    'glass': {
        'title': 'Glass',
        'radius': PILL_H // 2,
        'skip_fill': (255, 255, 255, 77),
        'skip_text': (17, 17, 17, 255),
        'report_fill': (12, 12, 12, 97),
        'report_text': (255, 255, 255, 255),
        'edge': (255, 255, 255, 26),
    },
}

LABELS = (('32001', 'skip intro'), ('32003', 'skip recap'), ('32004', 'skip credits'),
          ('32005', 'skip preview'), ('32012', 'next episode'), ('32043', 'report'))


def labels_for(folder):
    """The six labels a pill can show, for one language folder."""
    path = os.path.join(LANG_DIR, folder, 'strings.po')
    text = open(path, encoding='utf-8').read()
    found = {}
    for string_id, name in LABELS:
        match = re.search(r'msgctxt "#{}"\s*\nmsgid "((?:[^"\\]|\\.)*)"\s*\nmsgstr "((?:[^"\\]|\\.)*)"'.format(string_id), text)
        found[name] = match.group(2) or match.group(1)
    return found


def pill(draw, image, font, style, label, top, focused):
    """Draw one pill the way Kodi would: width = CLAMP(label, min, max), then the label.

    `focused` picks the state, because the skip pill holds focus when the prompt opens
    while the report pill does not — which is also why the two use different text
    colours in the glass style.
    """
    cfg = STYLES[style]
    width = min(max(int(font.getlength(label)), MIN_W), MAX_W)
    left = GROUP_RIGHT - width
    fill = cfg['skip_fill'] if focused else cfg['report_fill']
    text_colour = cfg['skip_text'] if focused else cfg['report_text']
    box = (left, top, left + width - 1, top + PILL_H - 1)
    draw.rounded_rectangle(box, radius=cfg['radius'], fill=fill,
                           outline=cfg['edge'], width=1 if cfg['edge'] else 0)
    text_w = font.getlength(label)
    draw.text((left + (width - text_w) / 2, top + PILL_H / 2), label,
              font=font, fill=text_colour, anchor='lm')
    return width


def main():
    """Write one sheet per style, and report the growth-row label it settled on."""
    font = ImageFont.truetype(FONT, FONT_SIZE)
    small = ImageFont.truetype(FONT, 20)
    title = ImageFont.truetype(FONT, 34)

    # A label wide enough to leave the floor, but still inside the cap, so the row shows
    # the pill growing rather than the label being clipped.
    measured = [(candidate, int(font.getlength(candidate))) for candidate in LONG_CANDIDATES]
    in_band = [item for item in measured if MIN_W < item[1] <= MAX_W - 4]
    long_label = (in_band or measured)[0][0]
    print('growth row: {!r} measures {}px'.format(long_label, dict(measured)[long_label]))
    if not in_band:
        print('warning: none of {} lands between {} and {}px'.format(
            LONG_CANDIDATES, MIN_W, MAX_W))

    os.makedirs(os.path.dirname(OUT.format('x')), exist_ok=True)
    folders = sorted(os.listdir(LANG_DIR))
    for style in ('default', 'glass'):
        cfg = STYLES[style]
        width, height = 1920, 1080
        image = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(image)
        for y in range(height):
            shade = 26 - int(18 * y / height)
            draw.line([(0, y), (width, y)], fill=(shade, shade + 4, shade + 10))
        # Pills go on their own layer so their alpha composites over the background the
        # way Kodi composites a translucent texture over the video.
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        draw.text((60, 40), 'TheIntroDB Kodi add-on — {} pills'.format(cfg['title']),
                  font=title, fill=(255, 255, 255))
        draw.text((60, 92), 'Pill width = CLAMP(label width, 350, 390), the rule Kodi applies to an '
                            'auto-width button. Every shipped label sits on the 350px floor, so the '
                            'stack stays aligned; only a longer one widens it.', font=small,
                  fill=(170, 180, 195))
        draw.text((60, 122), 'radius {}px  ·  border {}px  ·  pill height 48px  ·  right edge 50px from the screen edge'.format(
            cfg['radius'], 14 if style == 'default' else 23), font=small, fill=(120, 130, 145))

        y = 170
        for folder in folders:
            labels = labels_for(folder)
            code = folder.split('resource.language.')[1].split('/')[0]
            draw.text((60, y + 12), code, font=small, fill=(150, 160, 175))
            w1 = pill(draw, image, font, style, labels['skip intro'], y, focused=True)
            pill(draw, image, font, style, labels['report'], y + PILL_H + GAP, focused=False)
            draw.text((1440, y + 12), '{}px'.format(w1), font=small, fill=(120, 130, 145), anchor='ra')
            y += 2 * PILL_H + GAP + 14

        draw.text((60, y + 12), 'long', font=small, fill=(150, 160, 175))
        w = pill(draw, image, font, style, long_label, y, focused=True)
        pill(draw, image, font, style, 'Report', y + PILL_H + GAP, focused=False)
        draw.text((1440, y + 12), '{}px — grew past the floor'.format(w), font=small,
                  fill=(120, 130, 145), anchor='ra')

        image = Image.alpha_composite(image.convert('RGBA'), overlay).convert('RGB')
        path = OUT.format(style)
        image.save(path)
        print(path)


if __name__ == '__main__':
    sys.exit(main())
