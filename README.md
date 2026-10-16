# Jewolingo

A Hebrew vocabulary trainer that installs to an iPhone home screen as a PWA. Single HTML file, no build step, works fully offline.

**Live:** https://sq-no-ls.github.io/jewuolingo/

> **Working on this? Read [HANDOVER.md](HANDOVER.md) first.** It is the source of truth:
> architecture, data model, the learning systems, the design system, the deploy
> procedure, and the traps that have actually caused bugs.

> **The URL says `jewuolingo` (two u's) on purpose.** The app is called Jewolingo,
> but that URL is the installed PWA's *origin* — renaming the repo wipes every
> installed copy's progress and kills the home-screen icon.

## Install on iPhone

1. Open the link above **in Safari** (not Chrome — only Safari can install).
2. Share → **Add to Home Screen** → Add.
3. **Open it from the home-screen icon from now on.**

That last step matters. iOS keeps *separate* storage for a Safari tab and the installed app, so progress made in the tab will not appear in the app. Installed home-screen apps are also exempt from WebKit's 7-day storage eviction, which a Safari tab is not.

## Current state

| | |
|---|---|
| Words | 1,441 across 42 categories, ranked by spoken frequency into 6 levels |
| Modes | 13 — Flashcards, Multiple Choice, Type It, Match, Fill-In, Convo, Roots, Word Families, Aleph-Bet, Grammar, Patterns, Test, Sicha |
| Systems | Spaced repetition across 4 dimensions (Recognize / Produce / Use / Connect), level checkpoints, can-dos, daily quests, streak freezes |
| Data | 1,149 annotated words (POS, gender, plural, root), 30 sentence patterns, 57 root families |
| Storage | `localStorage` key `jw_progress` (API key is separate, `jw_key`) |
| Offline | Full — app shell, annotations and Google Fonts are service-worker cached |

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
index.html                 the entire app (markup, CSS, JS, vocabulary)
manifest.webmanifest       PWA manifest
sw.js                      service worker (offline shell + font cache)
icons/                     180 / 192 / 512 / 512-maskable
data/annotations.json      part of speech, gender, plural, root (CC BY-SA — see data/DATA_LICENSE)
scripts/                   frequency ranking and annotation builders
HANDOVER.md                full project documentation — start here
DESIGN_BRIEF.md            the brief behind the current design
```

## Roadmap

Done: frequency levels, the four-dimension model, the progression layer, the
annotation layer, root families, the habit layer, and the portrait-first
redesign. Remaining, in rough order:

1. **Author feminine adjective forms** — agreement drills are blocked on data:
   144 adjectives are annotated but only one carries an explicit feminine form,
   so building them now would mean drilling unverified Hebrew.
2. **Review the 293 unmatched annotation words** and the low-confidence entries.
3. **Verify ~190 self-generated niqqud entries.**
4. **FSRS** behind `schedule()`, which is currently a hand-tuned interval ladder.
5. **Grammar tables → drills.**

Audio and timed/speed answering are **out of scope by explicit decision**.
