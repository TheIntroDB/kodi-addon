# TheIntroDB – Kodi Addon

<p align="center">
  <img src="https://raw.githubusercontent.com/TheIntroDB/theintrodb-assets/main/logo-banner.png">
</p>

Kodi service add-on that gets intro, recap, credits, and preview segments from **[TheIntroDB](https://theintrodb.org)** for movies and TV shows and shows a skip button or auto skips for you!

**Requirements:** Kodi 19+. **TVDB metadata is recommended**: TVDB is the API's identity, so it is what the add-on asks with first (TMDB, then IMDb, are fallbacks).

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

1. Download the latest add-on zip [plugin.video.tidb-1.8.1.zip](https://theintrodb.github.io/kodi-addon/plugin.video.tidb-1.8.1.zip):
2. In Kodi, choose **Settings → Add-ons → Install from zip file**.
3. Select the zip to install the add-on directly.

### Option C: Copy into the Kodi add-ons folder

1. Unzip the add-on folder and rename it to `plugin.video.tidb`, move it into Kodi’s add-ons directory for your platform.
2. Restart Kodi or reload add-ons.

---

### Metadata Requirements

**TVDB is recommended.** TVDB is TheIntroDB's identity, so it is what the add-on asks with first; **TMDB** is next, then **IMDb** `tt...`. When the item exposes several, the add-on uses the best one and falls back to the others if the first finds nothing.

Alongside the id, an episode's own **TVDB episode id** is sent when Kodi has one, which pins the exact episode instead of trusting the numbering.

For TV episodes, the playing item also needs valid **season** and **episode** numbers. If your source add-on or library does not expose provider IDs, TheIntroDB cannot match the item.

Known limitation: for a series whose episode numbers follow a release order rather than TVDB's default (streaming rips, absolute-numbered anime, some specials), a lookup addressed only by **TMDB** can miss content that is stored under another numbering. Kodi items carrying a TVDB id resolve exactly; for the others, passing season/episode as the release numbers them is all the add-on can do.

## How It Works

On each new playback, the add-on reads what Kodi exposes for the current item through JSON-RPC `Player.GetItem` and `VideoInfoTag`: **TVDB ID** when available, otherwise **TMDb ID**, otherwise **IMDb** `tt...` ID, plus **season**, **episode** and (for episodes) the **TVDB episode ID**.

It then calls TheIntroDB, retrieves segment **start** and **end** times, waits until the segment window begins, and either shows the skip overlay or seeks automatically depending on your settings.

## Configuration

TheIntroDB Kodi Addon includes a few settings to adjust behavior:

- **Auto-skip**: Skip without showing the button
- **Extra seconds after segment end**: Adds a small offset to the skip target
- **Enable lookups**: Turns TheIntroDB requests on or off
- **API key**: Lets you use your TheIntroDB API key.
- **Debug options**: Enables verbose logging and on-screen notifications

---

## Credits

- **TheIntroDB** — database and API: [theintrodb.org](https://theintrodb.org) · [github.com/TheIntroDB](https://github.com/TheIntroDB)
- **JZOnTheGit** — original addon creator: [github.com/JZOnTheGit](https://github.com/JZOnTheGit)

## License

See [LICENSE](LICENSE) for details.
