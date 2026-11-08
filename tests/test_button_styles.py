# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 TheIntroDB
#
"""Unit tests for the pill styles.

A style is a folder under resources/skins/ that Kodi loads as the overlay window's own
skin (see button_styles.py), so the tests pin the three things that have to agree: the
folders on disk, the STYLES tuple, and the values= list of the button_style setting.

They also pin the geometry that keeps a pill on screen. Kodi works a control's position
out from its left edge before the label is measured, so an auto-width pill can only be
anchored by its left edge — which is why the pills are placed by where their *minimum*
width ends, and why the maximum width has to still fit inside the screen.

The widest label the pills can show is measured below, against the translations the
add-on actually ships, when PIL and a font are available. The real font belongs to the
user's Kodi skin, which is exactly why the pills use auto width instead of a fixed
number: the minimum is a design floor, and a label that outgrows it widens the pill up
to the maximum rather than scrolling.
"""
import os
import re
import sys
import unittest
import xml.etree.ElementTree as ElementTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'plugin.video.tidb'))

import kodi_stubs  # noqa: E402

import button_styles  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDON_DIR = os.path.join(REPO_DIR, 'plugin.video.tidb')
SKINS_DIR = os.path.join(ADDON_DIR, 'resources', 'skins')
SETTINGS_XML = os.path.join(ADDON_DIR, 'resources', 'settings.xml')
LANGUAGE_DIR = os.path.join(ADDON_DIR, 'resources', 'language')

RESOLUTIONS = ('1080i', '720p')
#: Kodi's GUI design resolutions, which the window coordinates live in.
SCREEN_WIDTH = {'1080i': 1920, '720p': 1280}
#: Where the old fixed-width pills ended, measured from the screen's right edge: the
#: design keeps the pills where they were and widens them, rather than moving them.
OLD_PILL_RIGHT_EDGE = {'1080i': 1870, '720p': 1260}
#: Font size the pill's label renders at, used to measure the shipped translations.
FONT_SIZE = {'1080i': 26, '720p': 17}
#: Every label a pill can show: the four segment types, next episode, and Report.
LABEL_STRING_IDS = ('32001', '32003', '32004', '32005', '32012', '32043')
FONT_CANDIDATES = (
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    '/usr/share/fonts/TTF/DejaVuSans.ttf',
    '/System/Library/Fonts/Helvetica.ttc',
)

#: The design floor each resolution documents in overlay.xml: the widest shipped label
#: measured with room inside the corners (295px at 1080i, 193px at 720p). Pinned here as
#: well as measured below, because the measurement needs PIL (so CI skips it) and a
#: coordinated change to the floor *and* the group position would otherwise stay green.
DOCUMENTED_FLOOR = {'1080i': 350, '720p': 230}

#: Kodi resolves a texture path only when it is "full" (a leading "/" or anything with
#: "://"); everything else is searched under the *active skin's* media folder. The
#: add-on's own textures are therefore addressed through this prefix.
ADDON_SPECIAL_PREFIX = 'special://home/addons/plugin.video.tidb/'

SKIP_BUTTON = 3001
REPORT_BUTTON = 3002


def _style_xml(style, res):
    """Path to one style's overlay.xml for one resolution."""
    return os.path.join(SKINS_DIR, style, res, 'overlay.xml')


def _control(style, res, control_id):
    """One pill's XML, as the assertions below need it."""
    root = ElementTree.parse(_style_xml(style, res)).getroot()
    group = root.find('controls/control')
    control = None
    for candidate in root.iter('control'):
        if candidate.get('id') == str(control_id):
            control = candidate
    if control is None:
        raise AssertionError('control {} missing from {}'.format(control_id, _style_xml(style, res)))
    width = control.find('width')
    focus = control.find('texturefocus')
    nofocus = control.find('texturenofocus')
    return {
        'type': control.get('type'),
        'auto': (width.text or '').strip() == 'auto',
        'min': int(width.get('min') or 0),
        'max': int(width.get('max') or 0),
        'height': int(control.findtext('height')),
        'posy': int(control.findtext('posy')),
        'visible': (control.findtext('visible') or '').strip(),
        'border': int(focus.get('border') or 0),
        'textures': (focus.text, nofocus.text),
        'group_posx': int(group.findtext('posx')),
        'group_width': int(group.findtext('width')),
        'group_height': int(group.findtext('height')),
    }


def _texture_file(texture):
    """The repository file a texture path in the XML names."""
    if texture.startswith(ADDON_SPECIAL_PREFIX):
        return os.path.join(ADDON_DIR, texture[len(ADDON_SPECIAL_PREFIX):])
    return os.path.join(SKINS_DIR, texture)


def _shipped_labels():
    """Every label a pill can show, in every shipped language."""
    labels = []
    for folder in sorted(os.listdir(LANGUAGE_DIR)):
        path = os.path.join(LANGUAGE_DIR, folder, 'strings.po')
        if not os.path.exists(path):
            continue
        with open(path, encoding='utf-8') as handle:
            text = handle.read()
        for string_id in LABEL_STRING_IDS:
            match = re.search(
                r'msgctxt "#{}"\s*\nmsgid "((?:[^"\\]|\\.)*)"\s*\nmsgstr "((?:[^"\\]|\\.)*)"'.format(
                    string_id), text)
            if match:
                labels.append(match.group(2) or match.group(1))
    return labels


def _measured_widest_label(res):
    """The widest shipped label in the pill's font, or None when it cannot be measured."""
    try:
        from PIL import ImageFont
    except ImportError:
        return None
    font_path = next((path for path in FONT_CANDIDATES if os.path.exists(path)), None)
    if font_path is None:
        return None
    font = ImageFont.truetype(font_path, FONT_SIZE[res])
    return max(int(font.getlength(label)) for label in _shipped_labels() if label)


class StyleCatalogueTests(unittest.TestCase):
    """The setting, the Python tuple and the folders have to agree."""

    def test_every_style_ships_both_resolutions(self):
        for style in button_styles.STYLES:
            for res in RESOLUTIONS:
                self.assertTrue(os.path.isfile(_style_xml(style, res)),
                                '{} is missing'.format(_style_xml(style, res)))

    def test_the_setting_lists_exactly_the_installed_styles(self):
        root = ElementTree.parse(SETTINGS_XML).getroot()
        settings = {element.get('id'): element for element in root.iter('setting')}
        self.assertIn(button_styles.SETTING_ID, settings)
        setting = settings[button_styles.SETTING_ID]
        # labelenum stores the value itself, not the index, so reordering the options
        # cannot silently point an existing install at a different style.
        self.assertEqual('labelenum', setting.get('type'))
        self.assertEqual(button_styles.DEFAULT_STYLE, setting.get('default'))
        self.assertEqual(list(button_styles.STYLES), setting.get('values').split('|'))
        self.assertEqual(len(button_styles.STYLES), len(setting.get('lvalues').split('|')))

    def test_the_setting_has_a_label_in_every_language(self):
        # The style names and the two labels around them, which the option list needs.
        with open(SETTINGS_XML, encoding='utf-8') as handle:
            settings_text = handle.read()
        wanted = set(re.findall(r'lvalues="([^"]+)"', settings_text)[0].split('|'))
        wanted.add('32047')
        wanted.add('32048')
        for folder in sorted(os.listdir(LANGUAGE_DIR)):
            path = os.path.join(LANGUAGE_DIR, folder, 'strings.po')
            if not os.path.exists(path):
                continue
            with open(path, encoding='utf-8') as handle:
                text = handle.read()
            for string_id in wanted:
                match = re.search(r'msgctxt "#{}"\s*\nmsgid "([^"]*)"\s*\nmsgstr "([^"]*)"'.format(
                    string_id), text)
                self.assertIsNotNone(match, '#{} missing from {}'.format(string_id, folder))
                if folder != 'resource.language.en_gb':
                    self.assertTrue(match.group(2), '#{} untranslated in {}'.format(string_id, folder))


class StyleResolutionTests(unittest.TestCase):
    """Which folder the window is told to load."""

    def setUp(self):
        kodi_stubs.remove_settings()
        kodi_stubs.SETTINGS.clear()

    def tearDown(self):
        kodi_stubs.remove_settings()
        kodi_stubs.SETTINGS.clear()

    def test_the_configured_style_is_used(self):
        for style in button_styles.STYLES:
            kodi_stubs.write_settings({button_styles.SETTING_ID: style})
            self.assertEqual(style, button_styles.resolve(ADDON_DIR, '1080i'))

    def test_a_style_chosen_in_the_dialog_applies_without_a_restart(self):
        # Same contract as every other setting: the value comes from the file the
        # settings dialog writes, not from what Kodi cached at add-on load.
        kodi_stubs.write_settings({button_styles.SETTING_ID: 'glass'})
        self.assertEqual('glass', button_styles.resolve(ADDON_DIR, '1080i'))
        kodi_stubs.write_settings({button_styles.SETTING_ID: 'default'})
        self.assertEqual('default', button_styles.resolve(ADDON_DIR, '1080i'))

    def test_an_unset_or_unknown_style_falls_back_to_the_default(self):
        # An unknown folder reaching WindowXMLDialog means WindowException("XML File for
        # Window is missing") and no prompt at all, which is worse than the wrong look.
        self.assertEqual(button_styles.DEFAULT_STYLE, button_styles.resolve(ADDON_DIR, '1080i'))
        for value in ('', '   ', 'nope', '../../etc', 'GLASSY'):
            kodi_stubs.write_settings({button_styles.SETTING_ID: value})
            self.assertEqual(button_styles.DEFAULT_STYLE,
                             button_styles.resolve(ADDON_DIR, '1080i'), repr(value))

    def test_a_style_whose_folder_is_missing_falls_back_to_the_default(self):
        kodi_stubs.write_settings({button_styles.SETTING_ID: 'glass'})
        self.assertEqual('glass', button_styles.resolve(ADDON_DIR, '1080i'))
        # A half-installed style, or one removed by an update, must not break the prompt.
        self.assertEqual(button_styles.DEFAULT_STYLE,
                         button_styles.resolve(os.path.join(ADDON_DIR, 'nowhere'), '1080i'))

    def test_the_default_style_is_the_one_that_shipped_before_styles(self):
        self.assertEqual('default', button_styles.DEFAULT_STYLE)
        self.assertIn(button_styles.DEFAULT_STYLE, button_styles.STYLES)

    def test_available_lists_the_installed_styles(self):
        self.assertEqual(button_styles.STYLES, button_styles.available(ADDON_DIR, '1080i'))
        self.assertEqual((), button_styles.available(os.path.join(ADDON_DIR, 'nowhere'), '1080i'))


class PillGeometryTests(unittest.TestCase):
    """The pills fit their labels, and fit on screen."""

    def test_the_pills_are_buttons_with_an_auto_width(self):
        # Auto width is what makes the box follow the label: Kodi sizes only buttons,
        # togglebuttons and grouplists to their text, and the <image> pills this
        # replaced could never follow it. This is the fix for the boxes that scrolled
        # in longer translations.
        for style in button_styles.STYLES:
            for res in RESOLUTIONS:
                for control_id in (SKIP_BUTTON, REPORT_BUTTON):
                    pill = _control(style, res, control_id)
                    self.assertEqual('button', pill['type'], (style, res, control_id))
                    self.assertTrue(pill['auto'], (style, res, control_id))
                    self.assertGreater(pill['max'], pill['min'], (style, res, control_id))

    def test_no_pill_is_drawn_by_a_background_image(self):
        for style in button_styles.STYLES:
            for res in RESOLUTIONS:
                root = ElementTree.parse(_style_xml(style, res)).getroot()
                types = [control.get('type') for control in root.iter('control')
                         if control.get('id') is not None]
                self.assertEqual(['button', 'button'], types, (style, res))

    def test_the_minimum_width_fits_the_widest_label(self):
        # The reported bug: French text scrolled inside a 260px box. The minimum is the
        # design width and has to clear the widest label the pills can show plus the
        # corner inset on both sides.
        for style in button_styles.STYLES:
            for res in RESOLUTIONS:
                pill = _control(style, res, SKIP_BUTTON)
                self.assertGreaterEqual(pill['min'], DOCUMENTED_FLOOR[res], (style, res))
                measured = _measured_widest_label(res)
                if measured is None:
                    continue
                self.assertGreaterEqual(
                    pill['min'], measured + 2 * pill['border'],
                    '{} {}: a {}px label does not fit a {}px pill'.format(
                        style, res, measured, pill['min']))

    def test_the_maximum_width_still_fits_on_screen(self):
        # Kodi anchors an auto-width control by its left edge, so the pill grows to the
        # right: the cap has to land inside the screen even for the longest label.
        for style in button_styles.STYLES:
            for res in RESOLUTIONS:
                pill = _control(style, res, SKIP_BUTTON)
                self.assertLessEqual(pill['group_posx'] + pill['max'], SCREEN_WIDTH[res],
                                     (style, res))
                self.assertGreaterEqual(pill['group_width'], pill['max'], (style, res))

    def test_the_pills_sit_where_the_fixed_width_pills_did(self):
        # The stack keeps its place: the minimum-width pill ends where the old pill
        # ended, so short labels are not left floating away from the screen edge.
        for style in button_styles.STYLES:
            for res in RESOLUTIONS:
                pill = _control(style, res, SKIP_BUTTON)
                self.assertEqual(OLD_PILL_RIGHT_EDGE[res],
                                 pill['group_posx'] + pill['min'], (style, res))

    def test_both_pills_share_a_left_edge_and_a_width(self):
        for style in button_styles.STYLES:
            for res in RESOLUTIONS:
                skip = _control(style, res, SKIP_BUTTON)
                report = _control(style, res, REPORT_BUTTON)
                self.assertEqual(skip['group_posx'], report['group_posx'], (style, res))
                self.assertEqual((skip['min'], skip['max']), (report['min'], report['max']),
                                 (style, res))
                self.assertGreaterEqual(report['posy'], skip['posy'] + skip['height'], (style, res))
                self.assertLessEqual(report['posy'] + report['height'],
                                     skip['group_height'], (style, res))

    def test_every_style_places_the_pills_identically(self):
        # Switching styles changes the look, not the layout.
        for res in RESOLUTIONS:
            layouts = []
            for style in button_styles.STYLES:
                skip = _control(style, res, SKIP_BUTTON)
                layouts.append((skip['group_posx'], skip['min'], skip['max'],
                                skip['height'], skip['posy']))
            self.assertEqual(1, len(set(layouts)), (res, layouts))

    def test_the_nine_slice_border_leaves_a_middle_strip_to_stretch(self):
        # Kodi needs something left in the middle of a 9-slice, so the border has to
        # stay below half the pill's height.
        for style in button_styles.STYLES:
            for res in RESOLUTIONS:
                pill = _control(style, res, SKIP_BUTTON)
                self.assertGreater(pill['border'], 0, (style, res))
                self.assertLess(pill['border'] * 2, pill['height'], (style, res))


class PillTextureTests(unittest.TestCase):
    """The textures the XML names are the ones the style ships."""

    def test_the_textures_are_full_paths_kodi_will_resolve(self):
        # A relative texture name is looked up under the *active skin's* media folder,
        # never the add-on's own skin folder, so a bare "pill.png" finds nothing: the
        # pill draws invisible with only its label showing. Full paths (CURL::IsFullPath:
        # a leading "/" or anything containing "://") are used as given. This shipped
        # broken once — both styles drew a label with no pill — so it is pinned here.
        for style in button_styles.STYLES:
            for res in RESOLUTIONS:
                for control_id in (SKIP_BUTTON, REPORT_BUTTON):
                    pill = _control(style, res, control_id)
                    for texture in pill['textures']:
                        where = (style, res, control_id)
                        self.assertTrue(texture, where)
                        self.assertTrue(texture.startswith(ADDON_SPECIAL_PREFIX),
                                        '{}: {!r} is not a full path Kodi resolves'.format(where, texture))
                        relative = texture[len(ADDON_SPECIAL_PREFIX):]
                        self.assertTrue(os.path.isfile(_texture_file(texture)), texture)
                        # and it names this style's own folder, not another style's
                        self.assertEqual(os.path.join('resources', 'skins', style, res),
                                         os.path.dirname(relative), texture)

    def test_a_texture_is_a_square_that_its_corners_fit_in(self):
        # A 9-slice draws its corners at their native size and stretches the middle, so
        # the texture has to be square and at least as wide as the two borders. The
        # classic texture is 64x64 for a 48px pill; the glass stadiums are exactly the
        # pill's height, so their corners are the pill's semicircles.
        try:
            from PIL import Image
        except ImportError:
            self.skipTest('PIL not installed')
        for style in button_styles.STYLES:
            for res in RESOLUTIONS:
                for control_id in (SKIP_BUTTON, REPORT_BUTTON):
                    pill = _control(style, res, control_id)
                    for texture in pill['textures']:
                        image = Image.open(_texture_file(texture)).convert('RGBA')
                        width, height = image.size
                        self.assertEqual(width, height, texture)
                        self.assertGreaterEqual(width, 2 * pill['border'], texture)
                        pixels = image.load()
                        self.assertEqual(0, pixels[0, 0][3], '{} corner is not transparent'.format(texture))
                        self.assertGreater(pixels[width // 2, height // 2][3], 0,
                                           '{} centre is transparent'.format(texture))
