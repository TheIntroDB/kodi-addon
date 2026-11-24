# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 TheIntroDB
#
"""Unit tests for what a shipped language has to carry.

Nothing here starts the add-on: these tests stand in for Kodi's own string lookup and
the add-on manager's language list, both of which work off the files on disk.

- Kodi resolves a ``$ADDON[plugin.video.tidb <id>]`` label through the active
  language's ``strings.po``, keyed by the ``msgctxt`` id. Only the add-on's own
  ``resource.language.en_gb`` file is complete, so a language that is missing an id
  shows the English text (or the raw tag) in the middle of an otherwise translated
  dialog — which is how the Italian file came to be short of the string that shipped
  with the late-metadata retry.
- A new setting inherits the same problem twice: the id it labels has to exist in every
  language, and every language has to be one the add-on advertises at all.
- Advertising a language is an addon.xml job, not a strings.po job: the add-on manager
  describes the add-on in English until the metadata carries ``<summary lang="xx_YY">``
  and ``<description lang="xx_YY">`` for it (see the repo skill). The tag is ``xx_YY``
  casing — the addon-checker XSD rejects a lower-case region such as ``ar_sa``.
"""
import os
import re
import unittest
import xml.etree.ElementTree as ElementTree

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDON_DIR = os.path.join(REPO_DIR, 'plugin.video.tidb')
LANGUAGE_DIR = os.path.join(ADDON_DIR, 'resources', 'language')
SETTINGS_XML = os.path.join(ADDON_DIR, 'resources', 'settings.xml')
ADDON_XML = os.path.join(ADDON_DIR, 'addon.xml')
BASE_LANGUAGE = 'resource.language.en_gb'

#: One ``msgctxt``/``msgid``/``msgstr`` triple of a PO file. The escapes are allowed
#: through untouched: the tests compare the file's own text, not a decoded string.
ENTRY = re.compile(
    r'msgctxt "#(?P<id>\d+)"\s*\n'
    r'msgid "(?P<msgid>(?:[^"\\]|\\.)*)"\s*\n'
    r'msgstr "(?P<msgstr>(?:[^"\\]|\\.)*)"')

#: What a language tag in addon.xml has to look like: `fr_FR`, `zh_CN`, never `ar_sa`.
LANGUAGE_TAG = re.compile(r'^[a-z]{2}_[A-Z]{2}$')

#: Every `$ADDON[plugin.video.tidb <id>]` a setting is labelled with.
SETTING_LABEL = re.compile(r'\$ADDON\[plugin\.video\.tidb (\d+)\]')


def _language_folders():
    """Every shipped ``resource.language.*`` folder, sorted."""
    return sorted(name for name in os.listdir(LANGUAGE_DIR)
                  if name.startswith('resource.language.')
                  and os.path.isfile(os.path.join(LANGUAGE_DIR, name, 'strings.po')))


def _strings(folder):
    """One language file as ``{string id: (msgid, msgstr)}``."""
    with open(os.path.join(LANGUAGE_DIR, folder, 'strings.po'), encoding='utf-8') as handle:
        text = handle.read()
    return {int(match.group('id')): (match.group('msgid'), match.group('msgstr'))
            for match in ENTRY.finditer(text)}


def _metadata_languages():
    """The addon.xml language tags, as ``{tag: {'summary', 'description'}}``."""
    root = ElementTree.parse(ADDON_XML).getroot()
    languages = {}
    for element in root.iter():
        if element.tag in ('summary', 'description') and element.get('lang'):
            languages.setdefault(element.get('lang'), set()).add(element.tag)
    return languages


class StringCoverageTests(unittest.TestCase):
    """Every language carries every string, and every shipped language is advertised."""

    def test_the_english_file_is_the_reference(self):
        self.assertTrue(_strings(BASE_LANGUAGE),
                        '{} carries no strings to compare against'.format(BASE_LANGUAGE))

    def test_every_language_covers_the_english_ids(self):
        base = _strings(BASE_LANGUAGE)
        for folder in _language_folders():
            if folder == BASE_LANGUAGE:
                continue
            strings = _strings(folder)
            with self.subTest(language=folder):
                self.assertEqual(sorted(set(base) - set(strings)), [],
                                 '{}: ids en_gb has and this language does not'.format(folder))
                self.assertEqual(sorted(set(strings) - set(base)), [],
                                 '{}: ids that are not in en_gb'.format(folder))
                for string_id, (msgid, msgstr) in sorted(strings.items()):
                    self.assertEqual(base[string_id][0], msgid,
                                     '#{} in {}: msgid differs from en_gb'.format(string_id, folder))
                    self.assertTrue(msgstr.strip(),
                                    '#{} in {}: empty msgstr'.format(string_id, folder))

    def test_every_settings_label_is_a_string_in_every_language(self):
        with open(SETTINGS_XML, encoding='utf-8') as handle:
            wanted = {int(value) for value in SETTING_LABEL.findall(handle.read())}
        self.assertTrue(wanted, 'settings.xml labels no strings at all')
        for folder in _language_folders():
            with self.subTest(language=folder):
                self.assertEqual(sorted(wanted - set(_strings(folder))), [],
                                 '{}: settings.xml labels an id this language lacks'.format(folder))

    def test_every_shipped_language_is_advertised(self):
        advertised = {tag.lower() for tag in _metadata_languages()}
        shipped = {folder.rsplit('.', 1)[-1] for folder in _language_folders()}
        self.assertEqual(sorted(shipped - advertised), [],
                         'folders with no <summary>/<description> in addon.xml')
        self.assertEqual(sorted(advertised - shipped), [],
                         'metadata languages with no strings.po folder')

    def test_every_advertised_language_has_both_strings(self):
        for tag, elements in sorted(_metadata_languages().items()):
            with self.subTest(language=tag):
                self.assertEqual({'summary', 'description'}, elements,
                                 '{}: a summary and a description are both needed'.format(tag))

    def test_the_language_tags_use_the_xx_YY_casing(self):
        for tag in sorted(_metadata_languages()):
            with self.subTest(language=tag):
                self.assertRegex(tag, LANGUAGE_TAG)


if __name__ == '__main__':
    unittest.main()
