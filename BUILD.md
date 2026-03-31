# Maintainer notes (releases & GitHub Pages)

## Turn on github.io (one-time — required for Kodi “Install from repository”)

Kodi loads **`addons.xml`** from **`https://jzonthegit.github.io/Smart-Intro-Skip/addons.xml`**. If that URL 404s in a browser, the repo add-on cannot connect.

Use **one** deployment method (branch is simplest):

1. GitHub repo → **Settings** → **Pages**
2. **Build and deployment → Source**: **Deploy from a branch** (not “GitHub Actions” unless you add a workflow back).
3. **Branch**: `main`, **Folder**: **`/docs`**, **Save**
4. Wait ~1 minute, then open **`https://jzonthegit.github.io/Smart-Intro-Skip/addons.xml`** — you should see XML, not a 404 page.

The site is the **`docs/`** folder on **`main`** served as static files. No Jekyll build is needed (`docs/.nojekyll` is present).

**Layout:** `addons.xml` and checksums stay in **`docs/`** root (what Kodi’s repo uses). **Zips** are in **`docs/zips/`**. **`docs/zips/index.html`** is required so **`/zips/`** does not 404 on GitHub Pages (folders need an `index.html`). The site root **`docs/index.html`** is the minimal download page.

The repository addon uses **`.../zips/`** for `datadir`. Kodi’s default package URL is **`datadir/id/id-version.zip`** ([`AddonInfoBuilder.cpp`](https://github.com/xbmc/xbmc/blob/master/xbmc/addons/addoninfo/AddonInfoBuilder.cpp)); for a **flat** zip (`zips/plugin.video.introskip-X.Y.Z.zip`), set **`<path>plugin.video.introskip-X.Y.Z.zip</path>`** (matching **`version`**) under **`xbmc.addon.metadata`** in **`addons.xml`** (and the add-on’s `addon.xml`). **`info` / `checksum` / `datadir` must be inside `<dir>`** — Kodi 20+ ([`Repository.cpp`](https://github.com/xbmc/xbmc/blob/master/xbmc/addons/Repository.cpp)).

## Release checklist

1. Bump **`version`** in **`plugin.video.introskip/addon.xml`**
2. Copy the `<addon>...</addon>` block into **`docs/addons.xml`**
3. From project root:
   ```bash
   rm -f docs/zips/plugin.video.introskip-*.zip
   zip -r docs/zips/plugin.video.introskip-X.Y.Z.zip plugin.video.introskip
   md5 -q docs/addons.xml > docs/addons.xml.md5
   ```
4. If **`repository.smartintro.jz/addon.xml`** changed, rebuild the **named** repository installer:
   ```bash
   rm -f docs/zips/01-install-this-first-repository.smartintro.jz-*.zip
   zip -r docs/zips/01-install-this-first-repository.smartintro.jz-1.0.5.zip repository.smartintro.jz
   ```
5. Update **`docs/index.html`** and **`docs/zips/index.html`** if zip names or versions changed
6. Commit and push **`main`**

Repo must stay **public** for Pages and for Kodi to fetch files.

**Updates:** Users must set Kodi to **Update official add-ons from → Any repositories** (not “official only”), or third-party add-ons never auto-update. Bumping **`repository.smartintro.jz`**’s **`version`** and shipping a new **`01-install-this-first-…zip`** clears cached repo checksums for clients who get stuck.
