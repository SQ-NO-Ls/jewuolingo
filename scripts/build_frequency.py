#!/usr/bin/env python3
"""
Assign a spoken-frequency rank and a level (1-6) to every word in index.html.

Base data: FDOSH (github.com/juandpinto/frequency-dictionary, MIT) — 5,000
lemmas from OpenSubtitles2018, ranked by dispersion-weighted usage, i.e. a
spoken-register list rather than a written one.

Resolution order per word:
  1. Verbs        -> hand-written VERB_LEMMA map, then a conservative heuristic.
  2. Single words -> direct FDOSH lookup.
  3. Phrases      -> curated chunk rank for common fixed expressions, otherwise
                     just after their hardest component word, so you are never
                     asked for a phrase containing a word you have not met.
  4. Unmatched    -> imputed from the word's existing hand-assigned difficulty,
                     with survival vocabulary (food, numbers, directions) given
                     a boost because subtitle corpora under-rank it.

Levels are assigned by POSITION in the final ordering, so level sizes are
predictable even though many ranks are imputed.

Run:  python3 -I scripts/build_frequency.py [--write]
"""
import re, io, csv, sys, os, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from verb_lemmas import VERB_LEMMA

FDOSH = os.path.join(HERE, 'fdosh.tsv')
INDEX = os.path.join(ROOT, 'index.html')

# Level bands by position in the frequency ordering.
BANDS = [(1,100),(2,250),(3,500),(4,800),(5,1200),(6,10**9)]

# Fixed expressions whose chunk frequency beats their component words: you learn
# "boker tov" as one unit long before you analyse boker and tov separately.
CHUNK_RANK = {
 "בוקר טוב":40, "ערב טוב":70, "לילה טוב":75, "יום טוב":80,
 "מה נשמע":45, "מה שלומך":50, "מה קורה":55, "מה המצב":85,
 "תודה רבה":60, "אין בעיה":65, "בבקשה רבה":150, "אין בעד מה":170,
 "כל טוב":120, "שבת שלום":130, "בתיאבון":140, "ברוך הבא":160,
 "מה זה":90, "מי זה":95, "מה יש":110, "מה קרה":100,
 "כמה זה":115, "כמה זה עולה":125, "איפה זה":105, "מה אתה עושה":135,
 "מה חדש":145, "איך הולך":155, "מה העניינים":200, "מה איתך":180,
 "סליחה רגע":260, "רגע אחד":240, "לא נורא":190, "בסדר גמור":210,
 "על הפנים":430, "על הכיפאק":440, "מה פתאום":300, "אין מצב":310,
 "יש מצב":330, "מה הקטע":420, "מה נסגר":450, "די באמת":460,
 "בוא נראה":350, "תכף ומיד":520, "אחר כך":175, "קודם כל":185,
 "בדרך כלל":270, "כל הזמן":230, "הרבה פעמים":340, "לפעמים כן":560,
 "מה דעתך":290, "איך אומרים":280, "אני מתגעגע אליך":600,
 "נעים מאוד":165, "להתראות בקרוב":480, "נתראה בקרוב":250,
}

# Subtitle corpora under-rank everyday survival vocabulary (food, numbers,
# directions, body). Unmatched words in these categories start higher.
SURVIVAL = {"Food","Numbers","Time","Time Talk","Greetings","Getting Around",
            "Shopping","Body","Family","Health","Colors","House","Questions",
            "Essentials","Pronouns","Conjunctions","Small Talk","Phrases",
            "Travel","Places","Weather","Work","School"}
BASE_SURVIVAL = {1:450, 2:800, 3:1400, 4:2200}
BASE_OTHER    = {1:700, 2:1300, 3:2000, 4:2800}

FIELDS = ['he','level','heV','pron','en','cat','sentence','sentenceEn']
OBJ_RE = re.compile(
  r'\{he:"(.*?)",level:(\d+),heV:"(.*?)",pron:"(.*?)",en:"(.*?)",'
  r'cat:"(.*?)",sentence:"(.*?)",sentenceEn:"(.*?)"\}')


def load_fdosh():
    fd = {}
    with io.open(FDOSH, encoding='utf-8') as fh:
        for row in list(csv.reader(fh, delimiter='\t'))[1:]:
            if len(row) > 1 and row[0] and row[0] not in fd:
                try: fd[row[0]] = int(row[1])
                except ValueError: pass
    return fd


def verb_candidates(v):
    """Conservative infinitive -> 3ms-past forms. Only for cat == Verbs."""
    out = []
    if v.startswith('ל') and len(v) > 2:
        b = v[1:]
        out.append(b.replace('ו', ''))                  # לכתוב -> כתב
        if b.endswith('ות'): out.append(b[:-2] + 'ה')   # לשתות -> שתה
        out.append(b)                                    # להגיע -> הגיע
    else:
        out.append(v)
    seen = []
    for x in out:
        if x and x not in seen: seen.append(x)
    return seen


def resolve(w, fd):
    """-> (rank, source)"""
    he, lvl, cat = w['he'], int(w['level']), w['cat']

    if ' ' not in he:
        if cat == 'Verbs':
            lem = VERB_LEMMA.get(he)
            if lem and lem in fd: return fd[lem], 'verb-map'
            for c in verb_candidates(he):
                if c in fd: return fd[c], 'verb-auto'
        if he in fd:
            r = fd[he]
            # Usefulness override. Subtitle corpora under-rank survival
            # vocabulary badly — FDOSH puts לחם ("bread") near rank 930 because
            # film dialogue rarely mentions it, which would bury it in Level 5.
            # The app's own hand-assigned difficulty encodes basicness, so for
            # basic survival words we cap how late they can land.
            if cat in SURVIVAL and lvl <= 2:
                cap = 350 if lvl == 1 else 750
                if r > cap: return cap, 'survival-boost'
            return r, 'fdosh'
        # strip a single attached prefix letter and retry
        if len(he) > 3 and he[0] in 'והבלכמש' and he[1:] in fd:
            return fd[he[1:]], 'deprefix'
        base = (BASE_SURVIVAL if cat in SURVIVAL else BASE_OTHER)[lvl]
        return base, 'imputed'

    # ── phrases ──
    if he in CHUNK_RANK: return CHUNK_RANK[he], 'chunk'
    base = (BASE_SURVIVAL if cat in SURVIVAL else BASE_OTHER)[lvl]
    parts, ranks, unresolved = he.split(), [], 0
    for p in parts:
        if p in fd: ranks.append(fd[p])
        elif len(p) > 2 and p[0] in 'והבלכמש' and p[1:] in fd: ranks.append(fd[p[1:]])
        elif p in VERB_LEMMA and VERB_LEMMA[p] in fd: ranks.append(fd[VERB_LEMMA[p]])
        else:
            # A component we cannot rank is almost always a RARE one (a
            # conjugated form, or a word outside the top 5,000). Ignoring it
            # lets "מה אתה ממליץ" inherit the rank of מה and land in Level 1.
            # Charge it the imputed rate so the rare part dominates the max.
            unresolved += 1
            ranks.append(base)
    if ranks:
        # Just AFTER the hardest component, never before it.
        return int(max(ranks) * 1.12) + 25, ('components' if not unresolved else 'components-part')
    return base + 120, 'imputed-phrase'


def main():
    write = '--write' in sys.argv
    fd = load_fdosh()
    src = io.open(INDEX, encoding='utf-8').read()
    words = [dict(zip(FIELDS, m)) for m in OBJ_RE.findall(src)]
    print("FDOSH lemmas: %d | app words: %d" % (len(fd), len(words)))

    srcs = collections.Counter()
    for w in words:
        w['rank'], w['src'] = resolve(w, fd)
        srcs[w['src']] += 1

    # Stable ordering: rank, then present-tense verbs before infinitives
    # (you speak in "ani rotse", not "lirtsot"), then shorter first.
    words.sort(key=lambda w: (w['rank'],
                              1 if (w['cat'] == 'Verbs' and w['he'].startswith('ל')) else 0,
                              len(w['he']), w['he']))
    for i, w in enumerate(words, 1):
        w['pos'] = i
        for lv, cap in BANDS:
            if i <= cap: w['newlevel'] = lv; break

    print("\nrank sources:")
    for k, v in srcs.most_common(): print("   %-16s %4d  (%2d%%)" % (k, v, round(100*v/len(words))))
    print("\nlevels:")
    lv = collections.Counter(w['newlevel'] for w in words)
    for k in sorted(lv): print("   L%d  %4d words" % (k, lv[k]))
    print("\nLEVEL 1 (first 40):")
    for w in words[:40]:
        print("   %3d  %-16s %-26s [%s]" % (w['pos'], w['he'], w['en'][:26], w['src']))

    if not write:
        print("\n(dry run — pass --write to apply)"); return

    out = src
    for w in words:
        old = ('{he:"%(he)s",level:%(level)s,heV:"%(heV)s",pron:"%(pron)s",'
               'en:"%(en)s",cat:"%(cat)s",sentence:"%(sentence)s",'
               'sentenceEn:"%(sentenceEn)s"}' % w)
        new = ('{he:"%s",level:%d,heV:"%s",pron:"%s",en:"%s",cat:"%s",'
               'sentence:"%s",sentenceEn:"%s",rank:%d}' % (
               w['he'], w['newlevel'], w['heV'], w['pron'], w['en'],
               w['cat'], w['sentence'], w['sentenceEn'], w['pos']))
        if out.count(old) != 1:
            print("!! could not uniquely place %s (%d matches)" % (w['he'], out.count(old)))
            continue
        out = out.replace(old, new)
    io.open(INDEX, 'w', encoding='utf-8').write(out)
    print("\nwritten to index.html")


def ranked():
    """Importable: the full word list, ranked and levelled, without writing."""
    fd = load_fdosh()
    src = io.open(INDEX, encoding='utf-8').read()
    words = [dict(zip(FIELDS, m)) for m in OBJ_RE.findall(src)]
    for w in words:
        w['rank'], w['src'] = resolve(w, fd)
    words.sort(key=lambda w: (w['rank'],
                              1 if (w['cat'] == 'Verbs' and w['he'].startswith('ל')) else 0,
                              len(w['he']), w['he']))
    for i, w in enumerate(words, 1):
        w['pos'] = i
        for lv, cap in BANDS:
            if i <= cap: w['L'] = lv; break
    return words


if __name__ == '__main__':
    main()
