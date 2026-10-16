#!/usr/bin/env python3
"""
Build a lexical annotation layer for the app's vocabulary.

Source: English Wiktionary via kaikki.org/wiktextract (CC BY-SA; the extractor
itself is MIT). It is the only free bulk source that stores niqqud on BOTH
lemmas and inflected forms, which is what lets us join on the vocalized form
instead of the bare consonants.

Why that matters: unvocalized Hebrew is heavily homographic. ספר alone is
sefer "book", sapar "barber", safar "counted" and siper "told". Joining on
consonants returns four candidates; joining on niqqud returns one. The app
stores heV for every entry, so we can use the good key.

Keys, tried in order (match quality is recorded, never hidden):
  K1  exact vocalized, normalized
  K2  loose vocalized — dagesh-insensitive, matres-insensitive, which
      reconciles our ktiv-male-with-niqqud against Wiktionary's ktiv-haser
  K3  consonant skeleton — ALWAYS ambiguous, so it only ever proposes

Output: data/annotations.json  {he: {pos, gender, plural, root, binyan,
infinitive, key, confidence}}. Register is deliberately absent: no free
resource carries it at usable coverage, so it stays a manual field.

Usage:  python3 -I scripts/build_annotations.py <hebrew.jsonl>
"""
import json, re, sys, io, os, unicodedata, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
INDEX = os.path.join(ROOT, 'index.html')
OUT   = os.path.join(ROOT, 'data', 'annotations.json')

OBJ_RE = re.compile(
  r'\{he:"(.*?)",level:(\d+),heV:"(.*?)",pron:"(.*?)",en:"(.*?)",'
  r'cat:"(.*?)",sentence:"(.*?)",sentenceEn:"(.*?)"(?:,rank:(\d+))?\}')
FIELDS = ['he','level','heV','pron','en','cat','sentence','sentenceEn','rank']

FINALS = {'ך':'כ','ם':'מ','ן':'נ','ף':'פ','ץ':'צ'}
# Marks that carry no lexical weight and must go before comparing.
DROP = set(range(0x0591,0x05B0)) | {0x05BD,0x05BF,0x05C0,0x05C3,0x05C4,0x05C5,0x05C6}
VOWELS = set(range(0x05B0,0x05BC))          # sheva .. qubuts
DAGESH, SHIN, SIN, QAMATZ_QATAN, QAMATZ = 0x05BC, 0x05C1, 0x05C2, 0x05C7, 0x05B8
BEGEDKEFET = set('בגדכפת')


def norm(s, loose=False):
    if not s: return ''
    s = s.replace('־', ' ').replace('־', ' ')       # maqaf
    s = unicodedata.normalize('NFD', s)
    out = []
    for ch in s:
        o = ord(ch)
        if o in DROP: continue
        if o == QAMATZ_QATAN: out.append(chr(QAMATZ)); continue
        out.append(ch)
    s = ''.join(out)
    s = ''.join(FINALS.get(c, c) for c in s)
    s = re.sub(r'\s+', ' ', s).strip()
    if not loose: return s
    # Loose: drop the dagesh (LLM niqqud gets it wrong constantly) and the
    # plene vav/yod, so ktiv male and ktiv haser meet in the middle.
    s = ''.join(c for c in s if ord(c) != DAGESH)
    s = re.sub(r'(?<=[ְ-ֻ])[וי]', '', s)
    return s


def skel(s):
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(c for c in s if not (0x0591 <= ord(c) <= 0x05C7))
    s = ''.join(FINALS.get(c, c) for c in s)
    return re.sub(r'\s+', ' ', s).replace('־', ' ').strip()


ROOT_RE = re.compile(r'root ([֐-׿־־\-]+)')
BINYAN = {'pa':"pa'al",'pi':"pi'el",'hif':"hif'il",'nif':"nif'al",
          'hit':"hitpa'el",'pu':"pu'al",'huf':"huf'al","hitpu'al":"hitpu'al"}


def entry_root(e):
    buckets = [e.get('categories') or []]
    for s in e.get('senses', []): buckets.append(s.get('categories') or [])
    for b in buckets:
        for c in b:
            nm = c.get('name', '') if isinstance(c, dict) else str(c)
            m = ROOT_RE.search(nm)
            if m: return m.group(1).strip()
    return None


def load_wiktionary(path):
    """vocalized/skeleton key -> list of annotation dicts"""
    k1, k2, k3 = collections.defaultdict(list), collections.defaultdict(list), collections.defaultdict(list)
    n = 0
    for line in io.open(path, encoding='utf-8'):
        line = line.strip()
        if not line: continue
        try: e = json.loads(line)
        except ValueError: continue          # truncated tail while downloading
        if e.get('lang_code') != 'he': continue
        pos = e.get('pos')
        if pos in ('character','root','name'): continue
        head = (e.get('head_templates') or [{}])[0].get('args', {}) or {}
        glosses = []
        biblical = False
        for s in e.get('senses', []):
            glosses += s.get('glosses') or []
            if any('iblical' in str(t) for t in (s.get('tags') or [])): biblical = True
        if biblical and len(glosses) <= 1: continue

        inf = None
        for f in e.get('forms', []):
            # The infinitive is emitted under an ERROR tag. Filtering on known
            # tags silently loses every single one.
            if 'error-unrecognized-form' in (f.get('tags') or []):
                v = f.get('form', '')
                if v and v[0] == 'ל': inf = v; break

        b = head.get('1')
        ann = {
            'pos': pos,
            'gender': head.get('g'),
            'plural': head.get('pl'),
            'root': entry_root(e),
            'binyan': BINYAN.get(b) if b else None,
            'infinitive': inf,
            'pattern': head.get('pat'),
            'glosses': glosses[:6],
            'word': e.get('word'),
        }
        n += 1
        # Index the headword AND every inflected form, so a present-tense
        # entry in the app still reaches its lemma's root and binyan.
        cands = []
        wv = head.get('wv') or ''
        if wv: cands.append(wv)
        for f in e.get('forms', []):
            tags = f.get('tags') or []
            if 'romanization' in tags or 'table-tags' in tags or 'inflection-template' in tags: continue
            if f.get('form'): cands.append(f['form'])
        cands.append(e.get('word') or '')
        for c in cands:
            a = norm(c)
            if a: k1[a].append(ann)
            bl = norm(c, loose=True)
            if bl: k2[bl].append(ann)
            sk = skel(c)
            if sk: k3[sk].append(ann)
    return k1, k2, k3, n


def gloss_overlap(app_en, glosses):
    def toks(t):
        return set(w for w in re.split(r'[^a-z]+', (t or '').lower()) if len(w) > 2)
    a = toks(app_en)
    if not a: return False
    for g in glosses:
        if a & toks(g): return True
    return False


def main():
    src_path = sys.argv[1] if len(sys.argv) > 1 else None
    if not src_path or not os.path.exists(src_path):
        print('usage: build_annotations.py <hebrew.jsonl>'); return
    k1, k2, k3, n = load_wiktionary(src_path)
    print('wiktionary entries indexed: %d  (k1 %d / k2 %d / k3 %d keys)'
          % (n, len(k1), len(k2), len(k3)))

    src = io.open(INDEX, encoding='utf-8').read()
    words = [dict(zip(FIELDS, m)) for m in OBJ_RE.findall(src)]
    print('app words: %d' % len(words))

    out, stats, fields = {}, collections.Counter(), collections.Counter()
    for w in words:
        hits, key = None, None
        for name, idx, probe in (('K1', k1, norm(w['heV'])),
                                 ('K2', k2, norm(w['heV'], loose=True)),
                                 ('K3', k3, skel(w['he']))):
            if probe and idx.get(probe):
                hits, key = idx[probe], name
                break
        if not hits:
            stats['nomatch'] += 1; continue

        confirmed = [h for h in hits if gloss_overlap(w['en'], h['glosses'])]
        pick = confirmed[0] if confirmed else hits[0]
        # The KEY tells you the join is sound; the GLOSS tells you it is the
        # right sense. Without gloss agreement we genuinely do not know which
        # homograph we landed on — מדבר matched "desert" for an entry meaning
        # "speak" — so that is 'low' however exact the vocalized match was.
        conf = ('high' if (key in ('K1','K2') and confirmed)
                else 'medium' if confirmed
                else 'low')
        if key == 'K3' and not confirmed and len(hits) > 1:
            stats['ambiguous-skeleton'] += 1

        rec = {k: pick[k] for k in ('pos','gender','plural','root','binyan','infinitive','pattern')
               if pick.get(k)}
        if not rec: stats['empty'] += 1; continue
        rec['key'] = key; rec['confidence'] = conf
        out[w['he']] = rec
        stats[key + '-' + conf] += 1
        for f in ('pos','gender','plural','root','binyan','infinitive'):
            if rec.get(f): fields[f] += 1

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, 'w', encoding='utf-8').write(
        json.dumps(out, ensure_ascii=False, sort_keys=True, indent=0))

    tot = len(words)
    print('\nmatch quality:')
    for k, v in sorted(stats.items()): print('   %-22s %5d' % (k, v))
    print('\nfield coverage (of %d app words):' % tot)
    for f in ('pos','gender','plural','root','binyan','infinitive'):
        print('   %-11s %5d  (%d%%)' % (f, fields[f], round(100*fields[f]/tot)))
    print('\nwrote %s  (%d entries)' % (OUT, len(out)))


main()
