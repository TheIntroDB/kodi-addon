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

**Download page:** [https://jzonethegit.github.io/Smart-Intro-Skip/zips](https://jzonethegit.github.io/Smart-Intro-Skip/zips/)

**Kodi file source URL** (same zips as the page above):

`https://jzonethegit.github.io/Smart-Intro-Skip/zips/`

**Install from zip** → open that source → pick **`01-install-this-first-…1.0.1.zip`** first (recommended), or **`plugin.video.introskip-1.0.1.zip`** for addon-only.

If **github.io** still 404s in a browser, download the zips from GitHub instead (same files):  
[repository installer](https://github.com/JZOnTheGit/Smart-Intro-Skip/raw/main/docs/zips/01-install-this-first-repository.smartintro.jz-1.0.1.zip) · [addon only](https://github.com/JZOnTheGit/Smart-Intro-Skip/raw/main/docs/zips/plugin.video.introskip-1.0.1.zip)

The repository addon loads **`addons.xml`** from **`raw.githubusercontent.com`** (not github.io), so **Install from repository** works even when Pages is not deployed.

### Repo route (recommended — updates in Kodi)

1. **Settings → Add-ons → Install from zip file** → install **`01-install-this-first-repository.smartintro.jz-1.0.1.zip`** (from the **`zips`** link above, or the raw link). If you already installed **`1.0.0`**, install **`1.0.1`** over it (or remove the old repo add-on, then install the new zip).
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
