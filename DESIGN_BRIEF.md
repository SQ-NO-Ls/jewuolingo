# Jewolingo — Design Brief

A brief for redesigning the interface of an existing, working Hebrew-learning
PWA. **The logic, data and learning systems described here already work and
are not up for redesign** — what is wanted is a new visual and layout
treatment for them. Think of this as a re-skin plus information-architecture
rework, not a rebuild.

---

## 1. What the thing is

An installable iPhone web app (PWA) for learning **spoken** Hebrew from
scratch, built for one user, free to run, works offline. Installed to the home
screen, it opens full-screen with no browser chrome. Everything is in a single
`index.html` (~5,000 lines, no build step, no framework) plus a service worker
and one JSON data file.

**Hard constraints the design must respect:**

- **One self-contained HTML file.** No React, no build step, no npm. Plain
  HTML/CSS/JS. Fonts come from Google Fonts; nothing else is loaded remotely.
- **Offline-first.** Every screen must work with no network. Only one feature
  (the AI conversation mode) needs the internet, and it must degrade cleanly.
- **Right-to-left Hebrew next to left-to-right English, constantly, often in
  the same sentence.** This is the single hardest layout problem in the app
  and the main reason a redesign is wanted.
- **Phone-first: 375×812 is the design target.** Must handle the notch and
  home indicator (`env(safe-area-inset-*)`). Desktop is secondary.
- **No audio and no timers.** Deliberate product decisions — do not design for
  a play button, a waveform, a countdown, or a speed score.
- **Tap targets ≥44px.** The app is tapped continuously during a session.

---

## 2. Content scale (what has to fit on screen)

| Thing | Count |
|---|---|
| Vocabulary entries | 1,441 |
| Categories | 42 |
| Frequency levels | 6 |
| Game modes | 13 |
| Sentence patterns | 30 |
| Root (word-family) groups | 57 |
| Annotated words (part of speech, gender, plural, root) | 1,149 |

Every vocabulary entry carries: Hebrew, vocalized Hebrew (with niqqud vowel
points), transliteration, English, category, an example sentence with one
blank, the sentence's English, and a frequency rank.

---

## 3. The learning systems (these drive the UI — do not redesign the logic)

### Frequency levels
Words are ordered by how often they actually occur in **spoken** Hebrew
(subtitle corpus, dispersion-weighted), then cut into 6 bands: L1 = the 100
most frequent, up to L6. You learn the most useful words first. Every word
shows its rank ("#4 most frequent").

### Four knowledge dimensions
Each item is tracked separately along four axes, and the UI shows progress per
dimension:
- **R — Recognize**: see Hebrew, know the meaning
- **P — Produce**: see English, write the Hebrew
- **U — Use**: put the word into a sentence pattern
- **C — Connect**: link a word to others from the same Semitic root

A word only counts as "secure" once *Production* is stable — recognition alone
does not count.

### Spaced repetition
An interval ladder with three-way grading (again / hard / good). Items come due
on a schedule; the app shows how many are due.

### The round
The core loop. One tap on "Start round" assembles ~12 steps mixing: new-word
introductions (**max 3 per round**), recognition questions, typing, sentence
patterns, and one word-family item. Each new word is introduced and then
re-tested later in the same round. A load governor pauses new words when the
review backlog is too big.

### Levels, checkpoints, can-dos, quests
- Levels unlock in order; a **checkpoint** test (type words from memory, no
  hints) gates the next one.
- **Can-dos**: plain-language goals ("order a coffee", "ask where something
  is") rather than abstract percentages.
- **Daily quests**: 3 small goals, e.g. "secure 3 words", "clear every due
  review".

### Streak
Daily streak with **banked freezes** — one earned per 5 consecutive days,
capped at 3, spent automatically to cover a missed day.

---

## 4. The 13 modes

| Mode | Hebrew | What happens |
|---|---|---|
| Flashcard | — | Tap to flip, self-grade |
| Multiple Choice | — | Hebrew shown, pick the English from 4 |
| Type It | כתוב בעברית | English shown, type Hebrew on a custom keyboard |
| Match | התאם | Pair Hebrew tiles to English tiles |
| Fill the Blank | מלא את החסר | Sentence with a gap |
| Conversation | שיחה | Scripted exchanges, translate a turn |
| Shoresh | שורש | Root browsing and quiz |
| Word Families | משפחות | Given a root and a word you know, pick the relative |
| Alphabet | אלפבית | Letter names and sounds |
| Grammar | דקדוק | Reference tables plus a quiz |
| Patterns | תבנית | Fill a sentence frame with the right word |
| Test | מבחן | Multi-format exam, several styles at once |
| Sicha (AI) | שיחה חיה | Live back-and-forth chat in Hebrew with an AI, then a debrief |

---

## 5. Current structure

A four-tab bottom bar:

- **Today** — the home screen. A big number (items in next round), a
  "Start round" button, today's 3 quests, and a one-line summary.
- **Levels** — the 6 frequency levels, their lock state, per-dimension
  progress (R/P/U/C), and the checkpoint test.
- **Practice** — free practice. Mode picker, category picker, level picker,
  then the question card.
- **Me** — stats, settings (vowels on/off, print vs cursive script), analytics,
  reset.

### Known weaknesses to solve in the redesign

1. **Practice is buried under chrome.** On a phone you scroll past 6 stat
   pills, 2 buttons and 3 dropdowns before reaching the actual question. The
   question should lead.
2. **Today is sparse.** A big empty gap between the quests and the tab bar.
3. **The custom Hebrew keyboard eats half the screen.** It must stay (the
   device keyboard is suppressed on purpose, because it would come up in
   English and cover the app's own), but the question, the answer field, the
   submit button and the keyboard all have to coexist on a 375×812 screen
   without scrolling. This is the tightest layout problem in the app.
4. **13 modes is a lot to present.** Currently a dropdown. There is probably a
   better organising principle — by skill, by dimension, by session length.
5. **The four dimensions (R/P/U/C) are shown as bare percentages** and mean
   nothing to a learner at a glance. They need a visual language.
6. **No visible sense of the 1,441-word journey.** Nothing conveys where you
   are in the whole map.

---

## 6. Visual language today

Dark, high-contrast, close to black.

```
background  #000000
surface     slightly lifted dark grey panels, 12–16px radius
accent      #2563EB  (blue — used for every primary action and all Hebrew
                      pronunciation hints)
success     #48BB78  green
error       #E05C7A  rose
muted grey  secondary text
```

- **Latin type:** DM Sans. **Hebrew type:** a dedicated Hebrew face, with an
  optional **cursive** mode (handwritten Hebrew differs sharply from print, and
  the learner can switch the whole app over).
- **Niqqud (vowel points) can be toggled on or off globally** — the same word
  renders as `שָׁלוֹם` or `שלום`. The design must hold both without the line
  height jumping.
- Pill-shaped buttons and tabs, generous radii, a soft blue glow on the primary
  action.
- Emoji used as iconography throughout (🔥 streak, 📚 learned, 🌿 word
  families). Open to replacing these with a real icon set.

---

## 7. What to produce

A design for the same app with the same systems, aimed at:

- Getting to the first question in as few taps and as little scroll as
  possible
- A credible answer to the keyboard-plus-question layout squeeze
- Making progress legible: the four dimensions, the 6 levels, the 1,441-word
  journey
- A coherent treatment of bilingual RTL/LTR text, including mixed lines
- Light mode as well as dark, if that is worth doing

Deliver as a spec plus static HTML/CSS mockups of the key screens (Today,
a round in progress, the typing step with the keyboard, Levels, Practice).
Plain HTML and CSS, no framework — the result has to drop into a single-file
app.

### Things that will break the app if changed
- Hebrew must always render through the app's own helper, never raw
- Hebrew comparison always strips vowel points before matching
- Everything stays in one HTML file
- No audio, no timers
