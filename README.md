# Smart Intro Skip (Kodi)

Skips TV intros using timestamps from **[TheIntroDB](https://theintrodb.org)**. Shows a skip button until the intro ends or you press it.

## Credits

Database and API: **[TheIntroDB](https://theintrodb.org)** — community-submitted timings.

**Creator / maintainer of the API:** [Pasithea0](https://github.com/Pasithea0) · org: [github.com/TheIntroDB](https://github.com/TheIntroDB)

This addon is just a Kodi client; it’s not run by them.

## Compatibility (Seren, Umbrella, etc.)

Nothing here is tied to one streaming addon. The service reads **whatever Kodi’s player has for the current file** — usually via `VideoInfoTag` and JSON-RPC (`uniqueid`, season, episode).

So it works with **Seren, Fen, Umbrella, or your local library** as long as the playing item actually has a **TMDB id** (and season + episode for TV). Some addons only set IMDB or leave IDs empty; then TheIntroDB can’t match. That’s a metadata problem.

## Features

- Pulls intro in/out from TheIntroDB
- Skip button stays up for the whole intro (or auto-skip if you turn that on)
- One HTTP request per episode when you have IDs

## Installation

**Download page:** [https://jzonethegit.github.io/Smart-Intro-Skip/](https://jzonethegit.github.io/Smart-Intro-Skip/)

**Kodi file source URL** (same zips as the page above):

`https://jzonethegit.github.io/Smart-Intro-Skip/zips/`

**Install from zip** → open that source → pick **`01-install-this-first-…`** first (recommended), or **`plugin.video.introskip-1.0.1.zip`** for addon-only.

You can also open the download page on a phone or PC, grab a zip, and copy it to your device (USB, share, etc.).

### Repo route (recommended — updates in Kodi)

1. **Settings → Add-ons → Install from zip file** → install **`01-install-this-first-repository.smartintro.jz-1.0.0.zip`** (from the **`zips`** link above, or copy the file over).
2. **Settings → Add-ons → Install from repository** → **Smart Intro Skip repo** → **Services** → **Smart Intro Skip** → **Install**.

### Direct zip (addon only, no repository)

1. **Settings → Add-ons → Install from zip file** → **`plugin.video.introskip-1.0.1.zip`** from the **`zips`** folder.

## Settings

| | |
|--|--|
| **General** | Auto-skip; extra seconds after intro end |
| **TheIntroDB** | On/off; optional API key from the site |
| **Coming soon** | Greyed placeholders for later stuff |
| **Debug** | Log spam; on-screen debug lines |

## Requirements

- Kodi 19+  
- TMDB id on the item (and S/E for episodes) or nothing lines up  

## License

GPL-2.0-or-later
