# -*- coding: utf-8 -*-
"""讀題庫與考點標記的共用小工具（build.py 會用到）。"""
import json, glob, os, re, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANK_DIR = os.path.join(ROOT, 'data', 'bank')
CONCEPTS = os.path.join(ROOT, 'data', 'concepts.json')

# 學科資料夾 ←→ 題庫裡的科目名
SUBJECTS = {
    '行政學': {'pre': '【行】', 'bank': ['行政學']},
    '法學':   {'pre': '【法】', 'bank': ['法律常識', '法學緒論']},
    '管理學': {'pre': '【管】', 'bank': ['企業概論', '企業管理', '管理學']},
    '經濟學': {'pre': '【經】', 'bank': ['經濟學']},
    '國文':   {'pre': '【國】', 'bank': ['國文']},
    '英文':   {'pre': '【英】', 'bank': ['英文']},
}

def load_bank():
    """回傳 {qkey: question dict}，qkey 形如 A-110-2/0/1 或 B-110-3/0/一。"""
    qs = {}
    for f in sorted(glob.glob(os.path.join(BANK_DIR, '*.json'))):
        if f.endswith('index.json'):
            continue
        d = json.load(open(f, encoding='utf-8'))
        for pi, p in enumerate(d['parts']):
            for q in p.get('questions', []):
                n = q.get('n', q.get('label'))
                key = f"{d['id']}/{pi}/{n}"
                qs[key] = dict(q, _exam=d['exam'], _year=d['year'], _session=d['session'],
                               _part=pi, _kind=p['kind'], _subject=p['subject'], _n=n)
    return qs

def load_concepts():
    return json.load(open(CONCEPTS, encoding='utf-8'))

def ref(q):
    """題目代號：A110-Q01、A115-填19、A115-問1、B110-一"""
    ex, yr, n, kind = q['_exam'], q['_year'], q['_n'], q['_kind']
    if kind == 'mc':
        return f"{ex}{yr}-Q{int(n):02d}"
    if kind == 'fill':
        return f"{ex}{yr}-填{n}"
    if kind == 'written':
        return f"{ex}{yr}-問{n}" if str(n).isdigit() else f"{ex}{yr}-{n}"
    return f"{ex}{yr}-{n}"

def sort_key(q):
    n = q['_n']
    cn = '一二三四五六七八九十'
    nn = int(n) if str(n).isdigit() else (cn.index(n) + 1 if n in cn else 99)
    return (q['_year'], q['_exam'], q['_part'], nn)

def concept_index():
    """回傳 {考點名: {'qs': [ (q, tag) ... 依年份排序 ], 'n':次數, 'A':a, 'B':b, 'years':[...]}}"""
    qs, tags = load_bank(), load_concepts()
    out = collections.defaultdict(lambda: {'qs': [], 'A': 0, 'B': 0, 'years': set()})
    for key, t in tags.items():
        q = qs.get(key)
        if not q:
            continue
        for c in t['concepts']:
            e = out[c]
            e['qs'].append((q, t)); e[q['_exam']] += 1; e['years'].add(q['_year'])
    for c, e in out.items():
        e['qs'].sort(key=lambda x: sort_key(x[0]))
        e['n'] = len(e['qs']); e['years'] = sorted(e['years'])
    return out

def by_subject(index):
    out = {}
    for sub, meta in SUBJECTS.items():
        out[sub] = {c: e for c, e in index.items() if c.startswith(meta['pre'])}
    return out
