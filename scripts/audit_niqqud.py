#!/usr/bin/env python3
"""Audit app heV/pron against Wiktionary (kaikki). Read-only on the repo.
usage: audit_niqqud.py <index.html> <hebrew.jsonl> <out.json>"""
import json, re, sys, io, unicodedata, collections

OBJ_RE = re.compile(
  r'\{he:"(.*?)",level:(\d+),heV:"(.*?)",pron:"(.*?)",en:"(.*?)",'
  r'cat:"(.*?)",sentence:"(.*?)",sentenceEn:"(.*?)"(?:,rank:(\d+))?\}')
FIELDS = ['he','level','heV','pron','en','cat','sentence','sentenceEn','rank']
FINALS = {'ך':'כ','ם':'מ','ן':'נ','ף':'פ','ץ':'צ'}
DROP = set(range(0x0591,0x05B0)) | {0x05BD,0x05BF,0x05C0,0x05C3,0x05C4,0x05C5,0x05C6}
DAGESH, QAMATZ_QATAN, QAMATZ = 0x05BC, 0x05C7, 0x05B8
STOP = set('the and for with not but are was you your one any who its his her this that from have has'.split())

def norm(s, loose=False):
    s = (s or '').replace('־', ' ').rstrip('־')
    s = unicodedata.normalize('NFD', s)
    s = ''.join(chr(QAMATZ) if ord(c) == QAMATZ_QATAN else c for c in s if ord(c) not in DROP)
    s = ''.join(FINALS.get(c, c) for c in s)
    s = re.sub(r'\s+', ' ', s).strip()
    if loose:
        s = ''.join(c for c in s if ord(c) != DAGESH)
        s = re.sub(r'(?<=[ְ-ֻ])[וי]', '', s)
    return s

def skel(s):
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(c for c in s if not (0x0591 <= ord(c) <= 0x05C7))
    s = ''.join(FINALS.get(c, c) for c in s)
    return re.sub(r'\s+', ' ', s.replace('־', ' ')).strip()

def toks(t):
    return set(w for w in re.split(r'[^a-z]+', (t or '').lower()) if len(w) > 2 and w not in STOP)

def load(path):
    by_skel = collections.defaultdict(list)   # skel -> [(form, is_head, entry)]
    for line in io.open(path, encoding='utf-8'):
        try: e = json.loads(line)
        except ValueError: continue
        if e.get('lang_code') != 'he' or e.get('pos') in ('character','root','name'): continue
        head = (e.get('head_templates') or [{}])[0].get('args', {}) or {}
        gl = []
        for s in e.get('senses', []): gl += s.get('glosses') or []
        ent = {'word': e.get('word'), 'pos': e.get('pos'), 'wv': head.get('wv'),
               'tr': head.get('tr'), 'glosses': gl[:5]}
        seen = set()
        def add(f, is_head):
            if not f or f in seen: return
            seen.add(f); by_skel[skel(f)].append((f, is_head, ent))
        for f in e.get('forms', []):
            if 'canonical' in (f.get('tags') or []): add(f.get('form'), True)
        add(head.get('wv'), True)
        for f in e.get('forms', []):
            t = f.get('tags') or []
            if 'romanization' in t or 'table-tags' in t or 'inflection-template' in t or 'class' in t: continue
            add(f.get('form'), False)
    return by_skel

VOW = 'aeiouáéíóú'
def stress_from_end_tr(tr):
    tr = unicodedata.normalize('NFC', tr or '')
    groups = re.findall(r'[aeiouáéíóú]+', tr.lower())
    if not groups: return None
    for i, g in enumerate(groups):
        if any(c in 'áéíóú' for c in g): return len(groups) - 1 - i
    return 0   # no accent mark = final stress by Wiktionary convention

def stress_from_end_pron(p):
    syl = [s for s in re.split(r'[-\s]+', p or '') if s]
    if not syl: return None
    for i, s in enumerate(reversed(syl)):
        letters = re.sub(r'[^A-Za-z]', '', s)
        if letters and letters.isupper() and len(letters) > 0: return i
    return None

def main():
    src = io.open(sys.argv[1], encoding='utf-8').read()
    words = [dict(zip(FIELDS, m)) for m in OBJ_RE.findall(src)]
    by_skel = load(sys.argv[2])
    out = []
    for w in words:
        cands = by_skel.get(skel(w['he']), [])
        a = toks(w['en'])
        def gok(ent): return bool(a & toks(' '.join(ent['glosses'])))
        hv, hvl = norm(w['heV']), norm(w['heV'], True)
        exact = [c for c in cands if norm(c[0]) == hv]
        loose = [c for c in cands if norm(c[0], True) == hvl]
        good = [c for c in cands if gok(c[2])]
        if any(gok(c[2]) for c in exact): status = 'OK'
        elif any(gok(c[2]) for c in loose): status = 'LOOSE'
        elif exact and good: status = 'HOMOGRAPH'
        elif good: status = 'DIFF'
        elif exact: status = 'EXACT-NOGLOSS'
        elif cands: status = 'SKEL-NOGLOSS'
        else: status = 'NOSRC'
        # stress: from the matched headword's tr, else gloss-agreeing headword
        trsrc = [c for c in exact + loose if c[1] and c[2]['tr'] and gok(c[2])] or \
                [c for c in good if c[1] and c[2]['tr']]
        tr = trsrc[0][2]['tr'] if trsrc else None
        st = None
        if tr and ' ' not in w['he'].strip() and ' ' not in tr:
            a1, b1 = stress_from_end_tr(tr), stress_from_end_pron(w['pron'])
            if a1 is not None and b1 is not None and a1 != b1: st = 'tr=%s pron=%s' % (a1, b1)
        props = []
        for f, ih, ent in (good or cands)[:8]:
            props.append({'form': f, 'head': ih, 'word': ent['wv'] or ent['word'], 'pos': ent['pos'],
                          'tr': ent['tr'], 'gl': '; '.join(ent['glosses'])[:120], 'gloss_ok': gok(ent)})
        out.append({'he': w['he'], 'heV': w['heV'], 'pron': w['pron'], 'en': w['en'],
                    'level': int(w['level']), 'rank': int(w['rank'] or 9999), 'status': status,
                    'tr': tr, 'stress': st, 'cands': props})
    json.dump(out, io.open(sys.argv[3], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    c = collections.Counter((r['level'], r['status']) for r in out)
    sts = ['OK','LOOSE','HOMOGRAPH','DIFF','EXACT-NOGLOSS','SKEL-NOGLOSS','NOSRC']
    print('lvl ' + ' '.join('%13s' % s for s in sts) + '  stress-mismatch')
    for lv in range(1, 7):
        print('L%d  ' % lv + ' '.join('%13d' % c[(lv, s)] for s in sts) +
              '  %d' % sum(1 for r in out if r['level'] == lv and r['stress']))

main()
