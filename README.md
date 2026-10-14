# Jewuolingo

A Hebrew vocabulary trainer that installs to an iPhone home screen as a PWA. Single HTML file, no build step, works fully offline.

**Live:** https://sq-no-ls.github.io/jewuolingo/

## Install on iPhone

1. Open the link above **in Safari** (not Chrome — only Safari can install).
2. Share → **Add to Home Screen** → Add.
3. **Open it from the home-screen icon from now on.**

That last step matters. iOS keeps *separate* storage for a Safari tab and the installed app, so progress made in the tab will not appear in the app. Installed home-screen apps are also exempt from WebKit's 7-day storage eviction, which a Safari tab is not.

## Current state

| | |
|---|---|
| Words | 1,391 across 42 categories |
| Modes | 11 — Flashcards, Multiple Choice, Type It, Match, Fill-In, Convo, Roots, Aleph-Bet, Grammar, Test, Sicha |
| Storage | `localStorage` key `jw_progress` (API key is separate, `jw_key`) |
| Offline | Full — app shell and Google Fonts are service-worker cached |

**Sicha** (live AI conversation) needs your own Anthropic API key, entered in ⚙ Settings. It is stored in this browser only and never leaves the device except in calls to `api.anthropic.com`.

## Backup

⚙ Settings → **Export progress** writes a JSON file (via the iOS share sheet, so you can save it to iCloud Drive). **Restore** reads it back. Do this before clearing website data or reinstalling — there is no cloud sync. The export deliberately excludes the API key.

## Deploying

```bash
git add -A && git commit -m "..." && git push
```

GitHub Pages redeploys automatically. **Bump `CACHE_VERSION` in `sw.js` on every deploy**, or installed clients keep serving the old cached build.

## Layout

```
index.html                 the entire app
manifest.webmanifest       PWA manifest
sw.js                      service worker (offline shell + font cache)
icons/                     180 / 192 / 512 / 512-maskable
```

## Roadmap

1. **Frequency levels** — re-rank vocabulary against [FDOSH](https://github.com/juandpinto/frequency-dictionary) (MIT, 5,000 spoken-Hebrew lemmas) so Level 1 is the genuinely most frequent words. Phrases fold in beside the words they contain.
2. **FSRS** scheduling with separate recognition and production memory states; a word counts as known only on *production* evidence that survives spaced intervals.
3. **Portrait-first UI** — the current layout is a desktop design on a phone; answers need to sit in the thumb zone.
4. **Audio** — pre-generated with macOS `say -v Carmit`.
5. **Habit layer** — forgiving streak, one daily reminder.
