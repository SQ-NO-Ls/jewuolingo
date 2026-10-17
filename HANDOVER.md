# Jewolingo — Handover

**Read this file first. It is the source of truth for the project.**

Last updated: 2026-10-16, after the Ledger redesign and polish pass.

---

## 1. What this is

A Hebrew-learning app for one user (Joey), installed to an iPhone home screen
as a PWA. Free to run, works fully offline, no accounts, no backend.

- **Live:** https://sq-no-ls.github.io/jewuolingo/
- **Repo:** `~/projects/jewuolingo` → `github.com/SQ-NO-Ls/jewuolingo` (branch `main`)
- **Deployed version:** service-worker `jw-v49`
- **Vocabulary:** 1,441 words · 42 categories · 6 frequency levels · 13 modes
  · 30 sentence patterns · 57 root families · 1,149 annotated words

### ⚠️ The URL is load-bearing — do not rename the repo

The display name is **Jewolingo** (one `u`). The repo and URL path are still
`jewuolingo` (two `u`s) **on purpose**. That URL is the installed PWA's
*origin*. Renaming the repo mints a new origin, which iOS treats as a
different app: all stored progress, SRS schedule and streak are wiped and the
home-screen icon goes dead. Same trap as the earlier Netlify Drop problem.

For the same reason, **never change the `jw_progress` localStorage key**.

If the clean URL is ever wanted, it needs: export progress → rename → re-install
→ import. Do not do it casually.

---

## 2. Files

```
index.html              6,202 lines — THE APP. Everything: markup, CSS, JS, vocab.
sw.js                   Service worker. Offline shell + font cache.
fonts/                  Self-hosted woff2 (Google Fonts subsets, unmodified) + OFL.txt.
                        frl-* Frank Ruhl Libre, ss4-* Source Serif 4 (roman+italic,
                        latin+latin-ext), gveret-* Gveret Levin. ~546KB total.
splash/                 iOS launch screens (apple-touch-startup-image), 7 iPhone
                        sizes, ~63KB total. make_splash.py regenerates them.
manifest.webmanifest    PWA manifest (name: "Jewolingo — Hebrew Mastery").
icons/                  180 / 192 / 512 / 512-maskable PNGs. Full-bleed (no baked-in
                        corners: iOS masks it), dark א on accent #9AA3E8.
data/annotations.json   132KB — POS, gender, plural, root, binyan per word.
data/DATA_LICENSE       CC BY-SA. Scoped to the DATA FILE ONLY, not the app code.
scripts/build_frequency.py    Assigns rank + level from FDOSH.
scripts/build_annotations.py  Builds annotations.json from kaikki Wiktionary dump.
scripts/verb_lemmas.py        93 hand-written verb→lemma mappings. KEEP HAND-WRITTEN.
scripts/audit_niqqud.py       Read-only audit of heV/pron against Wiktionary.
DESIGN_BRIEF.md         The brief that produced the current design.
README.md               Short public readme + install instructions.
.claude/launch.json     Dev server on port 8771.
```

There is **no build step**. No npm, no bundler, no framework. Open the file,
edit it, reload.

---

## 3. Non-negotiable code rules

These are carried over from the original build spec and from bugs that have
actually bitten. Breaking them causes silent breakage, not loud errors.

1. **Everything stays in `index.html`.** One file. No modules, no imports.
2. **No template literals in render functions.** String concatenation only.
   (The codebase is consistent on this; mixing styles has caused escaping bugs.)
3. **Render functions set `innerHTML`.** They do not append or mutate nodes.
4. **`dHe(w)` wherever Hebrew is displayed** — it handles the niqqud and
   cursive toggles. Never print `w.he` raw.
5. **`stripV()` before any Hebrew comparison.** Vowel points must not affect
   matching.
6. **`esc()` every interpolated string** that could contain user or data text.
7. **`renderModes()` / `renderCats()` / `renderLevels()` are called together.**
8. **Bump `CACHE_VERSION` in `sw.js` on EVERY deploy.** See §8 — this has
   silently wasted hours more than once.
9. **API key: localStorage only.** Never hardcode, never log, never put in a
   URL, never write to disk. Shown masked in the UI.
10. **No audio and no timed/speed answering.** Both were explicitly ruled out
    by the user. Do not reintroduce them in any form.

---

## 4. Data model

### Vocab object — the format is strict

```js
{he:"...",level:N,heV:"...",pron:"...",en:"...",cat:"...",sentence:"...",sentenceEn:"...",rank:N}
```

- `he` — unvocalized Hebrew. **No niqqud in this field.**
- `heV` — vocalized (with niqqud).
- `pron` — transliteration, stressed syllable in CAPS (`sha-LOM`).
- `en` — English gloss. **Must be unique across the whole vocabulary** —
  duplicates make multiple choice unanswerable (two correct answers).
- `cat` — one of the 42 categories.
- `sentence` / `sentenceEn` — example with **exactly one** `___` in each.
  `sentence` is Hebrew-only, `sentenceEn` is English-only (a few body-part
  entries deliberately include Hebrew dual forms in the English — that is
  intentional, not a bug).
- `rank` — frequency rank. **Assigned once and kept.** `9999` = unassigned.
- `level` — 1–6, **derived from `rank`** by position, not hand-set.

`scripts/build_frequency.py` writes `rank` and `level`. It is idempotent:
words with a real rank keep it (`src:'kept'`); only `9999`/absent get resolved.
Feeding derived levels back into the imputation would be circular.

### Items and cards

```
itemWord(he)      → "w:<he>"
itemPattern(id)   → "p:<id>"
itemRoot(root)    → "r:<root>"
ST.cards["<itemId>|<dim>"] = {n, reps, lapses, due, ...}
```

Only **R** and **P** schedule cards on words. **U** belongs to the pattern,
**C** to the root — as items in their own right. This is deliberate: duplicating
U and C onto every word is what would make the review load unsurvivable.

---

## 5. The learning systems

### Frequency levels
Words ordered by spoken-Hebrew frequency (FDOSH, MIT, 5,000 lemmas from
OpenSubtitles2018, dispersion-weighted), cut into 6 bands by **position**:
L1 = top 100, L2 = 101–250, L3 = 251–500, L4 = 501–800, L5 = 801–1200, L6 = 1201+.

### Four dimensions (`DIMS`)
- **R** Recognize — see Hebrew, retrieve meaning
- **P** Produce — type Hebrew from the English (**this is the real gate**)
- **U** Use — deploy inside a sentence pattern
- **C** Connect — link to root and relatives

A word is **secure** on *production stability only*. Recognition does not count.
`wordState(he)` implements this.

### `CFG` — all tunable thresholds in one place
```js
newPerDay: 7, secureDays: 7, masteredDays: 21,
gate: {breadth:0.85, patterns:0.80, checkpoint:0.85, softUnlock:0.70},
minDimension: null   // the "no dimension below 70%" hard gate is NOT enforced:
                     // four ways to be blocked risks deadlock. Shown as a
                     // shape chart first. Revisit with real data.
```

### The round — one funnel
`buildRound()` returns an array of steps; **it does not set `ROUND.steps`**
(a test once got this wrong). `startRound()` assigns it. Every mode goes
through `advance(ok)` → `roundNext()` → `roundStep()`, not through `newQ()`.

Round composition, in order of priority:
1. Due **P** cards (max 5) → `type` steps
2. Due **R** cards (max 5) → `mc` steps
3. **Production unlock**: words with `R.n>=2 && P.reps===0` (max 3). Without
   this the P dimension can never start — chicken-and-egg: a word only gets a
   P card by being typed, and was only typed if it had a due P card.
4. Patterns at `level <= activeLevel()+1` (max 3) → `U`
5. **One** root-family step → `C`
6. Top up from words already met, never by adding new ones
7. **Max 3 genuine new words** (`intro`), each echoed later in the same round
   so it is retrieved, not just re-read. Intros are placed first so every echo
   lands after its own introduction.

`ROUND_LEN = 12`.

### Load governor
`LOAD = {pauseNewAt:60, catchUpCap:40}` — new words pause when the backlog
exceeds 60. `newPaused()` reports it and Today says so in words.

### Levels, checkpoints, can-dos, quests
- `levelLocked(n)` genuinely restricts *new-word arrival* (it was once
  decorative — only drawing an icon — which was worse than no gate at all).
- Checkpoint: `CHK_LEN = 20` words, typed, no hints. Unlocks at 85% secure.
- `CANDOS` — 11 plain-language goals, L1–L2.
- `QUEST_DEFS` — daily and weekly. Daily quests key on `dayKey()` (local
  date; they used `toISOString()` until 2026-10-16 and rolled over
  mid-evening). "Clear every due review" is **earned**: it completes only
  when at least one due review was answered today (`questReviewed()`,
  called from `reviewItem`) and none remain. With nothing due and nothing
  answered it shows "none due" rather than a free tick.

### Streak with banked freezes
`dayKey()` uses **local** date parts. **Never use `toISOString()`** for this:
it is UTC, so an evening session west of Greenwich was filed under tomorrow,
advancing the streak a day early and then breaking it the next morning.

One freeze earned per 5 consecutive days, capped at 3, spent automatically to
cover a missed day, and surfaced with a toast so it does not look like a bug.

### Root families
`ROOT_OK` is a **curated allow-list of 57 roots** (out of 93 the annotation
layer yields). The excluded ones are etymologically correct but pedagogically
harmful — `ב־ט־ח` ties watermelon to insurance, `כ־ו־ן` ties "yes" to "car".
Drilling those teaches that Hebrew roots are arbitrary, which is the opposite
of the point. Pure gender pairs (`צריך`/`צריכה`) are inflection, not family,
and are free guesses, so they are out too.

**If you regenerate annotations, re-audit `ROOT_OK` by hand.** Do not auto-expand it.

---

## 6. The Ledger design system

Implemented from `DESIGN_BRIEF.md` + the user's research. The intent is *a
quiet reading room at night*: Hebrew set like a well-printed book, everything
else subordinate.

### Tokens (in `:root`)
```
bg #0E0F14   surface #16181F   surface2 #1E2029   surface3 #272A35
border #2E3140
text #E6E4DE   text2 #A6A8B3   text3 #8A8D9A
accent #9AA3E8   accent-hi #B3BAF0   accent-muted #262A47
green #7FBF9A   rose #E58F8F   warning #D9B46A
level ramp --lv1..--lv6 (fills only, never text)
radii: --r-sm 4px, --r-md 8px     ease: cubic-bezier(.2,.8,.2,1)
```

### Rules that must hold
- **Not `#000`** — leaves no room for elevation, smears on OLED during scroll.
- **Not white text** — halates. Off-white only.
- **Dark text on the accent fill.** Inverting the default white-on-blue is the
  single most distinctive move in the design. Never white-on-accent.
- **One accent per screen**, reserved for the primary action and focus. Hints
  (pronunciation etc.) use `--text3`, never the accent.
- **No glows, no gradients, no hover lifts, no decorative background layers.**
  These are the stock "AI-generated UI" tells.
- **Two radii only.** No pills.
- **No per-category colour.** 42 hues cannot be told apart, and colour with no
  task-relevant meaning is a seductive detail, which the coherence literature
  consistently finds harms learning. Colour is used *only* as the ordered
  lightness ramp for levels, and for correctness.
- **R/P/U/C by POSITION**, never hue — a fixed four-slot glyph (`dimGlyph()`),
  always in R-P-U-C order. Never a radar chart: with four axes the area
  exaggerates differences and the shape depends on axis order.

### Type
- Hebrew: **Frank Ruhl Libre** (`--he-font`). Serif keeps the cues that
  distinguish ב/כ, ד/ר, ה/ח/ת, ו/ז/ן, ם/ס.
- Latin/UI: **Source Serif 4** (`--ui-font`).
- Cursive: **Gveret Levin** (`--he-cursive`), a real Israeli *ktav yad* hand.
- **All three are self-hosted** in `fonts/` (2026-10-17): no request goes to
  Google. The `@font-face` block is a small `<style>` in `<head>`, before the
  main sheet, with Google's subsets and unicode-ranges. Only
  `ss4-latin` and `frl-hebrew` are preloaded (the faces on screen at
  launch); italic, latin-ext and Gveret load on first use. If a face is ever
  added, add its file to `FONT_FILES` in `sw.js` too.
- **Launch screen** is the header wordmark ("Jewolingo", Frank Ruhl Libre 900,
  `--text2` on `--bg`), so launch hands over to the app with no flash. iOS
  only picks a startup image whose `media` matches the device exactly; a new
  iPhone size needs a new PNG and `<link>`.
- Transliteration is *italic*, `--text3`, 0.8× — so shape alone tells you
  "how it sounds" vs "what it means".
- **Niqqud is VERIFIED.** Frank Ruhl Libre positions every problem case
  correctly: holam vav (שָׁלוֹם) vs shuruk (שׁוּק) are clearly distinct, and
  double-yod, dagesh-with-a-below-mark and both שׁ/שׂ dots sit right. Gveret
  Levin also carries niqqud. Both work with vowels on.
- Hebrew line-height is **fixed at 1.9** whether or not niqqud is shown, so
  toggling vowels never shifts the layout.

### Focus mode — the central interaction
When a round is running, `document.body` gets `.focus`, which hides the tab
bar, header, stat pills and all pickers. The question screen is a CSS grid
(`.focus-wrap` → `#stepBody`) whose **last row is the keyboard** — not fixed
positioning, so nothing can ever overlap the submit control.

Order within a step: prompt (flex) → answer field → **reserved** feedback slot
(so nothing jumps) → actions → keyboard.

Rank, root family and the example sentence appear **after** the answer, where
they help encoding instead of competing with retrieval.

**Practice uses the same layer.** Tapping a mode calls `openPractice(id)`:
`body.focus.pfocus` turns `#viewPractice .quiz-card` into a fixed
full-screen layer (close strip + `#quizContent`). Modes built from the shared
step bodies are listed in `FSQ_MODES` and get the round's no-scroll grid;
the rest (grammar, aleph-bet, scripted conversation…) scroll inside the
layer. `setMode()` calls `prFrame()` so switches made from inside the layer
(Sicha → "practice these now") update its title and grid. `closePractice()`
restores the list's scroll position. Showing the Practice tab renders the
list only; nothing renders a question until a mode is opened.

Wrong answers show the correct form **beside** the attempt with differing
letters underlined (`diffMark()`). No shake, no red flood. "Again" is
information, not punishment.

### Keyboard
**Standard Israeli SI-1452** — the layout iOS uses, so the hunting cost buys a
transferable skill. **Finals are their own keys** (ן ם ך ף ץ): long-press is
undiscoverable and finals are distinct letters a learner must choose
deliberately.

All five Hebrew inputs carry **`inputmode="none"`**, which stops iOS raising
its own (English) keyboard on top of the app's Hebrew one. **If you add a new
Hebrew input, it needs `inputmode="none"` and `buildKbd()`, and the submit
control must come BEFORE the keyboard in source order.**

Proportioned like the system keyboard (2026-10-16): a **full-bleed tray**
(`margin-inline:-16px`, 4px outer inset, `--surface`, top hairline). Letter
keys are equal-width, sized off the widest row (10 keys → ~31px at 375), so
the 8- and 9-key rows sit centred. 46px tall, 6px gaps, 10px row gap, keys
`--surface3` with a 1px base shadow. Hit areas tile the gaps via
`.kbd-key::after`. Pressing a letter shows a callout above the thumb
(`data-ch` + `:active::before`); iOS only applies `:active` because of the
passive `touchstart` listener at the bottom of the script — keep it.

### Paper — the light theme (2026-10-17)
`:root[data-theme="paper"]` overrides the tokens; Me → Display →
**Appearance: Dark · Paper · Auto** (Auto follows the iPhone). The choice
lives in its own key `jw_theme` (display only; `jw_progress` is untouched)
and is applied by a tiny inline script at the top of `<body>` so Paper never
flashes dark. Rules carried over: warm paper not white, near-black ink not
black, **dark ink on the accent fill** (`--on-accent`), the accent as TEXT
uses `--accent-ink` (#3D479E on paper), levels still by lightness (the ramp
darkens with level on paper). All paper text pairs pass WCAG AA (lowest:
warning 4.8:1). The map canvas reads colours from tokens via `cssv()`, so
**never hard-code a colour in canvas or inline styles again**. iOS fixes
the status-bar style at install (white icons), so Paper paints a dark band
behind the status bar (`--status-band`). Dark was verified unchanged by a
computed-style diff and a pixel-identical map.

### Motion (2026-10-17)
Entrance-only, transform + opacity, house curve `--ease`, all under 300ms:
a new step settles in (`step-in`, 200ms; the keyboard never animates),
feedback fades up beside the answer (`fb-in`), the Practice layer lifts in
(`layer-in`, 240ms; closing is instant), buttons press to `scale(.98)`
instantly and release in 80ms. Tab changes use View Transitions through
`goTab()`, with the tab bar and header named so they stay still.

**Nothing may wait for an animation.** No `animationend`/`transitionend`
anywhere — that is what makes Reduce Motion (`animation:none`) safe: content
simply appears. Verified by playing full rounds, typing included, with all
animation forced off. `goTab()` also has a 150ms fallback, because a view
transition only runs its update on a rendered frame (see trap 14).
Chat-style Practice modes (Sicha, Dialogue) are excluded from the entrance
via `#quizContent[data-mode]`, since they redraw the whole thread per turn.

### Information architecture
Four tabs: **Today · Map · Practice · Me** (the `Levels` view id is still
`viewLevels` internally; the tab is labelled Map).

- **Header** — one labelled line, `renderHead()`: "12 due · 4-day streak ·
  1 freeze". Zero parts are omitted (first run shows nothing).
- **Today** — date, due/new count, the current level as a labelled bar
  (secure over met, `scaleX`, read right-to-left), 3 quests, then **"New in
  your next round"** (`upNextHTML`) sitting directly above **Start round**,
  pinned in the thumb zone. New words are previewed by name; due reviews are
  shown only as counts — previewing a word right before testing it would
  turn retrieval into re-reading.
- **New-word step** (`introHTML`) — 60px hero (44/34px for long phrases),
  gloss, then the example with the word filled in on the Hebrew side. The
  English keeps a drawn gap: filling it from the gloss produced broken
  English in 35+ entries ("I to love you").
- **Map** — the 1,441-word journey canvas (all words as dots by frequency,
  read right-to-left, state by **lightness only** so it survives any
  colour-vision deficiency), weekly quests, then per-level rows with four
  labelled R/P/U/C bars, can-dos and the checkpoint.
- **Practice** — grouped by dimension (`MODE_DIM`), weakest first, with two
  quiet filter buttons. Each mode has a line icon (`#i-m-<id>` in the
  sprite, drawn in-house — no third-party set) instead of a Hebrew letter. The stat pills and three dropdowns were removed.
- **Me** — iOS inset grouped lists (`.group` / `.group-b` / `.row`): an
  identity block (secure count + `dimGlyph`), Progress, Display (real
  `.switch` controls — the one exception to the two-radii rule, because a
  square toggle reads as a checkbox), What the slots mean, More, and Reset
  progress alone in rose. First run leads with the R/P/U/C explanation.
  "Words met" now counts map states (`dotState`), not the legacy
  `ST.learned` set, so Me and the Map agree.
- **Map canvas** (`drawMap`) — 8px filled cells with 2px gaps, labelled level
  bands, drawn at up to 3× density. **All five states are kept** (unseen,
  met, recognised, secure, due) and encoded by lightness: the research
  proposal to colour learned cells by level was rejected because it
  collapses those states and swaps lightness for hue.
- **First run** — Today says "Your first words" with a **Begin** button; the
  Map carries a one-line caption; the header is silent.

---

## 7. Traps that have actually bitten (read before debugging)

1. **Stale service worker.** By far the most common. You edit `index.html`,
   reload, and see the OLD build — it looks like your write failed. It did not.
   Either bump `CACHE_VERSION`, or in DevTools console:
   ```js
   for(const r of await navigator.serviceWorker.getRegistrations()) await r.unregister();
   for(const k of await caches.keys()) await caches.delete(k);
   location.reload();
   ```
   This cost real time at least four separate times.

2. **Sparse array holes.** An insertion script once appended a comma where one
   already existed, creating `},,` → an `undefined` in `vocab`. **`node --check`
   PASSED** (it is valid JS) and regex counts looked right. It only surfaced at
   runtime. Always verify in the browser:
   ```js
   vocab.filter(w => w === undefined).length === 0
   ```

3. **`buildRound()` returns; it does not assign.** Reading `ROUND.steps` after
   calling it gives stale data and looks like "empty round" bug.

4. **CSS specificity vs the legacy sheet.** Cleaned 2026-10-16: 66 dead rules
   deleted, 69 duplicate selectors merged, old blue/gradients/glows/`#fff`
   removed (948 → 736 CSS lines), verified by a computed-style diff of 21
   screen states. Pre-redesign rules for older modes (flashcard, match…) are
   still present. New rules appended at the end of `<style>` win on equal
   specificity, but older rules that set `background`/`border`/`border-radius`
   will persist unless you explicitly reset them. Check with
   `getComputedStyle()` rather than assuming.

5. **Hebrew verb lemmas must stay hand-written.** Auto-mapping produced
   5-level errors: `לדעת`→`דעת` ("knowledge", #1557) instead of `ידע` (#15);
   `ללכת`→`כת` (#4807) instead of `הלך` (#32); `לספר`→`ספר` ("book").

6. **"Starts with ל" is not an infinitive test.** It matched `לומד`, `לוקחת`
   and generated "אפשר לומד?" ("Can I studies?"). `isInfinitive()` requires the
   gloss to start with "to ".

7. **Gloss overlap can confirm the WRONG part of speech.** `עבודה` "work / job"
   matched a verb sense "to work". `build_annotations.py` has a POS tiebreaker
   keyed on the app's own gloss shape.

8. **Duplicate English glosses break multiple choice** (two correct answers).
   Check after any vocab addition.

9. **Typo tolerance needs a 4-letter floor, not 5.** Hebrew drops vowels, so
   `שלום` (4 letters) never qualified under an English-instinct 5-letter rule.
   Also rejects any typed string that is itself a real word, so חלון/חלום
   cannot be confused.

10. **`toISOString()` is UTC.** See §5 streak.

11. **Font cache was keyed to `CACHE_VERSION`** — every deploy deleted it and
    re-downloaded ~200KB, leaving the app briefly unstyled offline right after
    an update. Fonts now live in their own **unversioned** cache, `jw-fonts-v2`
    (the self-hosted `fonts/` files; `v1` held Google's responses and is
    deleted on activate). They are precached at **install**, so even the first
    offline launch has the real faces, and install skips files the cache
    already holds, so a deploy re-downloads only the shell (verified: zero
    font requests on a version bump). Do not move them into `SHELL`, and do
    not bump the `jw-fonts-vN` name unless the font files themselves change.

12. **iOS keeps `:hover` applied after a tap.** A tapped key stayed lit in the
    accent until you tapped elsewhere. Every `:hover` rule is now wrapped in
    `@media (hover:hover) and (pointer:fine)`. New hover rules must be too.

13. **A full-bleed child is clipped by an `overflow` ancestor.** The keyboard's
    `-16px` margins vanished inside `#quizContent{overflow:hidden}` while
    `getBoundingClientRect()` still reported 0–375. Overflow clips at the
    padding edge, so the 16px side padding lives on the scroll container, not
    on the card around it. Check with a screenshot, not rects.

14. **View Transitions wait for a frame.** In a page that renders no frames
    (hidden preview pane, backgrounded tab) `startViewTransition`'s update
    never runs, so a tab tap did nothing. `goTab()` switches directly after
    150ms if the transition has not started. Never make a state change
    depend on an animation or a frame. The hidden Claude preview pane also
    leaves CSS animations at frame 0 until a screenshot forces a paint.

---

## 8. Workflow

### Run locally
Dev server is registered in `.claude/launch.json` (port 8771). In Claude Code,
use the preview tool with name `jewuolingo`. Never run a dev server via Bash.

### Verify a change
Always test at **375×812** (iPhone). The useful checks, run in the console:
- All modes render: loop `MODES`, `setMode(m.id)`, check `#quizContent` non-empty
  (`test` is expected to be empty — it draws into `#testOverlay`)
- No horizontal overflow: compare every element's `getBoundingClientRect().right`
  against `window.innerWidth`, skipping `position:fixed` and `.gram-wrap`
- Tap targets ≥ ~40px
- Soak the generators (`rootHTML`, `patternHTML`, `buildRound`) a few hundred
  iterations and catch throws
- A full round: `startRound()` then step through, confirming max 3 intros and
  that echoes never precede their intro
- **Offline**: stop the server and reload — the app must boot fully

### Deploy
```bash
# 1. bump the cache version FIRST
#    sw.js: const CACHE_VERSION = 'jw-vNN'
# 2.
git add -A && git commit -m "..." && git push origin main
# 3. wait for GitHub Pages, then verify
until curl -s https://sq-no-ls.github.io/jewuolingo/sw.js | grep -q "jw-vNN"; do sleep 5; done
```
GitHub Pages takes ~1–3 minutes. **Verify the deployed build actually runs**,
not just that the bytes are present — load it and check `vocab.length`,
`Object.keys(ANN).length` and that a round builds.

**The user has asked to be consulted before deploying.** Once they said "don't
deploy till we redesign" after an unprompted deploy. Ask, unless they have
clearly asked for it to go live.

A worktree's preview needs its own entry in `.claude/launch.json` (another
port, `--directory` set to the worktree). Do not commit that entry.

### Regenerate launch screens (rarely needed)
```bash
python3 -I splash/make_splash.py <FrankRuhlLibre[wght].ttf>
```
The TTF is a build input only (github.com/google/fonts, `ofl/frankruhllibre`);
PIL cannot read the woff2 in `fonts/`.

### Regenerate data (rarely needed)
```bash
python3 -I scripts/build_frequency.py            # dry run
python3 -I scripts/build_frequency.py --write
python3 -I scripts/build_annotations.py <hebrew.jsonl>   # kaikki.org dump
```
After either, re-audit `ROOT_OK` and re-check for duplicate English glosses.

---

## 9. State of play

### Done
- 1,441 words, frequency-ranked into 6 levels, no duplicates, no array holes
- 13 modes incl. Sicha (live AI conversation) and Word Families
- Four-dimension model with production-gated mastery
- Progression: level gating, checkpoints, 11 can-dos, daily/weekly quests,
  load governor, typo tolerance
- 57 curated root families driving the Connect dimension
- Streak with banked freezes, on local dates
- Annotation layer: 1,149 words, ~80% POS coverage
- Ledger redesign: focus mode, journey map, SI-1452 keyboard, dimension glyph,
  Practice by dimension, Me rebuilt, overlays restyled
- Offline verified with fonts intact; fonts self-hosted, iOS launch screens
- Niqqud verified in both print and cursive

### Open / deliberately deferred
- **Agreement drills — NOT viable as data stands.** 144 adjectives are
  annotated but **only 1 has an explicit feminine form in vocab**. Building
  them means generating forms by rule and drilling unverified Hebrew. Needs the
  feminine forms authored first.
- **293 unmatched annotation words** and the low-confidence entries need human
  review.
- **Niqqud/pron audit — L1–L2 done (2026-10-16), L3–L6 open.**
  `scripts/audit_niqqud.py <index.html> <kaikki-hebrew.jsonl> <out.json>`
  compares every `heV` with Wiktionary's vowelled forms. It also checks `pron`
  stress against Wiktionary's `tr`, and flags `heV` whose *letters* differ
  from `he`. It is read-only, and its statuses are leads, not verdicts.
  `EXACT-NOGLOSS` hid the worst error (`את` "you (f.)" carried the vowels of
  the object marker אֶת), so read those by eye too.
  - L1–L2: 21 fixes (heV + pron only, never `he`).
  - **Convention: `heV` uses the same letters as `he`**, i.e. ktiv male with
    niqqud (`לַחְשׁוֹב`, not `לַחְשֹׁב`). Otherwise turning vowels on changes
    the spelling the learner is then asked to type. Four doubled-letter
    words are left as they are (`עדיין חייב עניין להתכוון`): the vowelled
    ktiv-male form there is not settled.
  - Still open: **~212 letter mismatches in L3–L6** (mostly holam-haser
    infinitives). **39 stress mismatches** (some are false alarms where vowels
    are adjacent, e.g. `batúakh`). **~330 `NOSRC`**: mostly phrases, which
    need review by eye.
  - Expect false `HOMOGRAPH`/`DIFF` hits when the only entry that agrees on
    meaning has no vowels (verb infinitives often do).
- **Register is a manual field** — no free resource carries it at usable coverage.
- FSRS behind `schedule()` (currently a hand-tuned interval ladder).
- Grammar tables → drills.
- Haptics: iOS Safari has never implemented the Vibration API. Since iOS 18 a
  native `<input type="checkbox" switch>` produces a Taptic tick, but it is an
  undocumented side-effect. Optional enhancement only, if ever.

---

## 10. Working with this user

- Wants **real learning value**, not gamification theatre. Pushes back on
  anything decorative.
- **No audio. No speed/timed answering.** Both explicitly ruled out.
- Prefers things fixed and polished before being shown — "make it best it can
  then ill see the product when its in a positoon to see".
- Does research externally and pastes it in; follow it closely but say so
  plainly when the evidence or the data does not support a part of it (e.g.
  the agreement drills, the per-category colour).
- Wants to be asked before deploying.
- Phrasing like "get it as close as possible odesnt need to be perfectl" means
  judgement calls are welcome — do not over-ask.
