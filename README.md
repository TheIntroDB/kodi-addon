<img align="right" width="88" src="https://raw.githubusercontent.com/TheIntroDB/.github/main/integrations/kodi.png" alt="Kodi">

[![Kodi 20%2B](https://img.shields.io/badge/Kodi-20%2B-17B2E7?style=flat-square&logo=kodi&logoColor=4ade80&labelColor=0d0d0d)](https://kodi.tv)
[![License](https://img.shields.io/github/license/TheIntroDB/kodi-addon?style=flat-square&logo=gnu&logoColor=4ade80&label=License&labelColor=0d0d0d&color=038939)](https://github.com/TheIntroDB/kodi-addon/blob/main/LICENSE)

[![Stars](https://img.shields.io/github/stars/TheIntroDB/kodi-addon?style=flat-square&logo=github&logoColor=4ade80&label=Stars&labelColor=0d0d0d&color=038939)](https://github.com/TheIntroDB/kodi-addon/stargazers)
[![Issues](https://img.shields.io/github/issues/TheIntroDB/kodi-addon?style=flat-square&logo=github&logoColor=4ade80&label=Issues&labelColor=0d0d0d&color=038939)](https://github.com/TheIntroDB/kodi-addon/issues)
[![Last commit](https://img.shields.io/github/last-commit/TheIntroDB/kodi-addon?style=flat-square&logo=git&logoColor=4ade80&label=Last%20commit&labelColor=0d0d0d&color=038939)](https://github.com/TheIntroDB/kodi-addon/commits)
[![Discord](https://img.shields.io/discord/1457550295742812307?style=flat-square&logo=discord&logoColor=4ade80&label=Discord&labelColor=0d0d0d&color=038939)](https://discord.com/channels/1457550295742812307/1457550298255200380)

### TheIntroDB – Kodi Addon

---

Kodi service add-on that gets intro, recap, credits, and preview segments from **[TheIntroDB](https://theintrodb.org)** for movies and TV shows and shows a skip button or auto skips for you!

**Requirements:** Kodi 20+. **TVDB metadata is recommended**: TVDB is the API's identity, so it is what the add-on asks with first (TMDB, then IMDb, are fallbacks).

**Important:** Lookups happen when playback starts. If the current item does not expose a usable **TVDB**, **TMDb** or **IMDb** ID, the add-on cannot match it with TheIntroDB.

**Troubleshooting (no skip button):** See the Metadata Requirements and Installation sections below.

---

## Installation

### Option A: Add repository (automatic updates)

1. Download [repository.tidb.repo-2.0.0.zip](https://theintrodb.github.io/kodi-addon/repository.tidb.repo-2.0.0.zip) or add `https://theintrodb.github.io/kodi-addon/` as a source in the Kodi File Manager.
3. Install `repository.tidb.repo.zip` by selecting **Settings → Add-ons → Install from zip file** within Kodi.
4. Go to **Settings → Add-ons → Install from Repository**.
5. Open **TheIntroDB Kodi Addon Repo** and install **TheIntroDB Kodi Addon**.
6. Allow third-party repository updates under **Settings → System → Add-ons** if you want automatic updates.

### Option B: Add-on zip only

1. Download the latest add-on zip [plugin.video.tidb-2.2.0.zip](https://theintrodb.github.io/kodi-addon/plugin.video.tidb-2.2.0.zip):
2. In Kodi, choose **Settings → Add-ons → Install from zip file**.
3. Select the zip to install the add-on directly.

### Option C: Copy into the Kodi add-ons folder

1. Unzip the add-on folder and rename it to `plugin.video.tidb`, move it into Kodi’s add-ons directory for your platform.
2. Restart Kodi or reload add-ons.

---

### Metadata Requirements

**TVDB is recommended.** TVDB is TheIntroDB's identity, so it is what the add-on asks with first; **TMDB** is next, then **IMDb** `tt...`. When the item exposes several, the add-on uses the best one and falls back to the others if the first finds nothing.

Alongside the id, an episode's own **TVDB episode id** is sent when Kodi has one. It is the add-on's way of saying which exact episode record it means; note that the API currently answers `/media` from the season/episode numbers rather than that id (measured 2026-10-17: a pinned id naming a different episode than the numbers returns the *numbers'* episode), so the numbering is still what decides the answer. The id is sent for when that precedence is honoured.

For TV episodes, the playing item also needs valid **season** and **episode** numbers. If your source add-on or library does not expose provider IDs, TheIntroDB cannot match the item.

Known limitation: for a series whose episode numbers follow a release order rather than TVDB's default (streaming rips, absolute-numbered anime, some specials), a lookup is answered from the numbers as TVDB's *default* order, which can be a different episode than the one you are watching. Kodi does not expose which order its numbers came from, so the add-on cannot pass an order to convert; if your library is scraped in a non-default order, prefer a source that carries a TVDB id and check the result against the episode you are watching.

## How It Works

On each new playback, the add-on reads what Kodi exposes for the current item through JSON-RPC `Player.GetItem` and `VideoInfoTag`: **TVDB ID** when available, otherwise **TMDb ID**, otherwise **IMDb** `tt...` ID, plus **season**, **episode** and (for episodes) the **TVDB episode ID**.

It then calls TheIntroDB, retrieves segment **start** and **end** times, waits until the segment window begins, and either shows the skip overlay or seeks automatically depending on your settings.

When an API key is set, the skip prompt also offers a **Report** pill under the skip pill. Pressing it reports the media (and, for an episode, the episode being watched) to TheIntroDB as having a wrong segment. Reporting does not skip, so the skip pill stays on offer, and each prompt reports a segment once.

With **Offer to submit intros on pause** enabled, pausing in the first five minutes of an episode offers to mark an intro start and end and submit it. The prompt is only offered for a title TheIntroDB has no intro for — if one exists, the add-on says so rather than staying silent, and the **Report** button is the way to contest it.

## Configuration

TheIntroDB Kodi Addon includes a few settings to adjust behavior:

- **Auto-skip**: Skip without showing the button
- **Extra seconds after segment end**: Adds a small offset to the skip target
- **Enable lookups**: Turns TheIntroDB requests on or off
- **API key**: Lets you use your TheIntroDB API key.
- **Report button**: Shows a **Report** button under the skip prompt whenever an API key is set, for telling TheIntroDB that a segment is wrong. The report is a vote on your account, so there is nothing to send without a key. Turn on **Hide the Report button** under Reporting if you would rather not see it.
- **Button style**: **Classic** (the flat pill the add-on has always drawn) or **Glass** (translucent, fully rounded, with a hairline edge, from the Stremio Enhanced glass theme). Both are drawn by the button itself, so the box fits its label in every language instead of scrolling: Kodi sizes a button to its text, with a design floor of 350px (1080i) or 230px (720p) and a cap of 390px/245px. Fitting every shipped label is why the pills are wider than they used to be. Glass is as close to glass as Kodi gets — its GUI has no backdrop blur, so it is translucency and a 1px edge rather than a frosted panel.
- **Debug options**: Enables verbose logging and on-screen notifications

---

## Credits

- **TheIntroDB** — database and API: [theintrodb.org](https://theintrodb.org) · [github.com/TheIntroDB](https://github.com/TheIntroDB)
- **JZOnTheGit** — original addon creator: [github.com/JZOnTheGit](https://github.com/JZOnTheGit)

## License

**GNU General Public License v3.0 or later** (`GPL-3.0-or-later`) — see [LICENSE](LICENSE) for the full text.

> This program is free software: you can redistribute it and/or modify it under the
> terms of the GNU General Public License as published by the Free Software
> Foundation, either version 3 of the License, or (at your option) any later version.
>
> This program is distributed in the hope that it will be useful, but WITHOUT ANY
> WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
> PARTICULAR PURPOSE. See the GNU General Public License for more details.

Every source file carries `SPDX-License-Identifier: GPL-3.0-or-later`. The "or later" grant is deliberate: it lets the project adopt a future GPL version without re-licensing from every contributor.

---

<p align="center">
  <a href="https://theintrodb.org"><img src="https://raw.githubusercontent.com/TheIntroDB/theintrodb-assets/main/badge.png" alt="TheIntroDB" width="44" height="44"></a>
  <br><br>
  <sub><b>TheIntroDB</b> · community-submitted intro, recap, credits and preview timestamps for your media server<br>
  <a href="https://theintrodb.org">theintrodb.org</a> · <a href="https://github.com/TheIntroDB">GitHub</a> · <a href="https://discord.com/channels/1457550295742812307/1457550298255200380">Discord</a></sub>
</p>
