# -*- coding: utf-8 -*-
"""
Daybook 知識庫更新腳本。在 repo 根目錄執行：

    python3 tools/build.py            # 重算六科的「考點」與「地圖」頁，並把 data/cards/ 裡的新卡併進「概念」頁
    python3 tools/build.py --check    # 只看報告，不改檔案
    python3 tools/build.py --fresh    # 地圖整頁重畫，不保留舊地圖裡手加的行（換版時用一次）

資料來源：
  data/bank/*.json      題庫（考場用）
  data/concepts.json    每題的考點標記（題目代號 → 考點名、出題角度、關鍵一句）
  data/map.json         每科的章節骨架：章 → 考點名清單＋延伸項目
  data/cards/*.md       待併入的概念卡（## 考點名 開頭的一張張卡）

會改的檔案：
  學科/<科>/考點.md     整頁重寫（這頁是索引，不要手改）
  學科/<科>/地圖.md     重寫，但會保留你自己加的「- [ ]」行（沒有 [[ ]] 連結的那些）
  學科/<科>/概念.md     只「加」還沒有的卡，已有的卡一個字都不動

新的一年考題進來的流程：
  1. 題庫 json 放進 data/bank/，把 index.json 補一筆
  2. 在 data/concepts.json 幫每一題標考點（名字照舊的，新考點再取新名）
  3. 跑這支腳本；報告會列出「還沒有章」和「還沒有卡」的考點
  4. 新考點到 data/map.json 指定章，再請 Claude 補卡到 data/cards/，再跑一次
"""
import json, os, re, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_bank import concept_index, by_subject, ref, SUBJECTS, ROOT

CHECK = '--check' in sys.argv
FRESH = '--fresh' in sys.argv   # 不保留舊地圖的手加行（第一次從舊版課本大綱換成考點地圖時用）
MAP_FILE = os.path.join(ROOT, 'data', 'map.json')
CARDS_DIR = os.path.join(ROOT, 'data', 'cards')

INTRO = {  # 考點頁的開頭說明
    '行政學': 'A 考 110–115 行政學概要依考點分類。同一個名字＝同一個理論，考過越多次越要先讀。',
    '法學':   'A 考法律常識（110–115）與 B 考法學緒論（110–114）合在一起依考點分類。',
    '管理學': 'B 考企業概論（110–114）、A 考 115 企管填充與問答、B 考管理學申論（110–114）合在一起依考點分類。',
    '經濟學': 'B 考經濟學申論（110–114）依考點分類。都是申論，重點是模型要會畫、會推。',
    '國文':   'A 考 110–114 的國文選擇題依考點分類（115 年起沒有選擇題，只剩作文）。',
    '英文':   '六年英文題（A 考 110–115、B 考 110–114）依考點分類。次數越多越常考；字彙類靠累積單字量，文法類每一格都是一個可以背的規則。',
}

def read(p):
    return open(p, encoding='utf-8').read() if os.path.exists(p) else ''

def write(p, s):
    if CHECK:
        return
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(s)

def exam_tag(e):
    return '〔AB〕' if e['A'] and e['B'] else ('〔A〕' if e['A'] else '〔B〕')

def exam_desc(e):
    if e['A'] and e['B']:
        return f"A 考 {e['A']}、B 考 {e['B']}"
    return 'A 考' if e['A'] else 'B 考'

# ---------------- 考點頁 ----------------
def build_index_page(sub, items, have_cards):
    order = sorted(items, key=lambda c: (-items[c]['n'], items[c]['qs'][0][0]['_year'], items[c]['qs'][0][0]['_exam']))
    total = sum(items[c]['n'] for c in order)
    out = [f'# {sub}考點', '', INTRO.get(sub, ''), '',
           f'共 {len(order)} 個考點、{total} 題次。每張卡下面的「開這張概念卡」會直接在概念頁開一張同名的卡，內容想怎麼寫就怎麼寫；寫過的會變成連結。', '']
    for c in order:
        e = items[c]
        out += [f'## {c}', '', f"**考過**：{e['n']} 次（{exam_desc(e)}） · {'、'.join(map(str, e['years']))}", '']
        for q, t in e['qs']:
            out.append(f"- {ref(q)} {t.get('angle', '')} → {t.get('key', '')}")
        out += ['', '**概念卡**：' + ('（已寫）' if c in have_cards else '（還沒寫）'), '']
    return '\n'.join(out).rstrip() + '\n'

# ---------------- 地圖頁 ----------------
AUTO_LINE = re.compile(r'^\s*[-*] \[( |x|X)\] \[\[')   # 自動產生的行以 [[ 開頭

def parse_manual(text):
    """把舊地圖裡「你自己加的行」依章收起來（非 [[ 開頭的 - [ ] 行）。"""
    manual = collections.OrderedDict(); cur = None
    for l in text.split('\n'):
        h = re.match(r'^## (.+)$', l)
        if h:
            cur = h.group(1).strip(); manual.setdefault(cur, []); continue
        m = re.match(r'^\s*[-*] \[( |x|X)\] (.+)$', l)
        if m and cur is not None and not AUTO_LINE.match(l):
            manual[cur].append(m.group(2).strip())
    return manual

def build_map_page(sub, data, items, old_text):
    manual = {} if FRESH else parse_manual(old_text)
    assigned = set()
    out = [f'# {sub}地圖', '',
           '這科的骨架：`##` 是母概念（章），底下每一格是一個子概念。前面有連結的格子是六年考古題真的考過的考點（×幾次＝考過幾題次，點名字直接看概念卡）；沒連結的是課本上有、但還沒考過的延伸項目。讀懂一格就打勾。', '',
           data.get('intro', ''), '',
           '用法：做題撞到不會的名詞，先回來這裡找它在哪一章，把同一章的兄弟姊妹一起看完再回去做題。〔A〕〔B〕是兩場考試的代號；〔AB〕表示兩場都考過。', '']
    # 總覽表
    rows = []
    for ch in data['chapters']:
        cs = [c for c in ch['concepts'] if c in items]
        rows.append((ch['title'], len(cs), sum(items[c]['n'] for c in cs)))
    out += ['| 章 | 考點數 | 題次 |', '|---|---:|---:|'] + [f'| {t} | {a} | {b} |' for t, a, b in rows] + ['']
    for ch in data['chapters']:
        title = ch['title']
        cs = sorted([c for c in ch['concepts'] if c in items], key=lambda c: -items[c]['n'])
        assigned.update(cs)
        out += [f'## {title}', '']
        for c in cs:
            e = items[c]
            out.append(f"- [ ] [[{c}]]{exam_tag(e)} ×{e['n']} · {'、'.join(map(str, e['years']))}")
        extras = list(ch.get('extra', []))
        for m in manual.get(title, []):
            if m not in extras:
                extras.append(m)
        if extras:
            if cs:
                out += ['', '**延伸（課本有、六年沒考過；有空再讀）**', '']
            out += [f'- [ ] {x}' for x in extras]
        out.append('')
    # 舊地圖裡有、但 map.json 沒有的章：整章保留在最後
    kept = [t for t in manual if t not in {ch['title'] for ch in data['chapters']} and manual[t]]
    for t in kept:
        out += [f'## {t}', ''] + [f'- [ ] {x}' for x in manual[t]] + ['']
    # 沒指定章的考點
    missing = sorted([c for c in items if c not in assigned], key=lambda c: -items[c]['n'])
    if missing:
        out += ['## 未歸類（新考點，請到 data/map.json 指定章）', '']
        out += [f"- [ ] [[{c}]]{exam_tag(items[c])} ×{items[c]['n']} · {'、'.join(map(str, items[c]['years']))}" for c in missing] + ['']
    return '\n'.join(out).rstrip() + '\n', missing

# ---------------- 概念頁：併入新卡 ----------------
CARD_RE = re.compile(r'^## (.+)$', re.M)

def split_cards(text):
    """回傳 (檔頭, OrderedDict{標題: 卡片全文})"""
    parts = CARD_RE.split(text)
    head = parts[0]
    cards = collections.OrderedDict()
    for i in range(1, len(parts), 2):
        title = parts[i].strip(); body = parts[i + 1]
        cards[title] = f'## {title}' + body.rstrip() + '\n'
    return head, cards

def load_inbox():
    """讀 data/cards/*.md，依考點前綴分科。回傳 {科: OrderedDict{標題: 卡片全文}}"""
    pre2sub = {m['pre']: s for s, m in SUBJECTS.items()}
    inbox = {s: collections.OrderedDict() for s in SUBJECTS}
    if not os.path.isdir(CARDS_DIR):
        return inbox
    for f in sorted(os.listdir(CARDS_DIR)):
        if not f.endswith('.md'):
            continue
        _, cards = split_cards(read(os.path.join(CARDS_DIR, f)))
        for t, body in cards.items():
            sub = pre2sub.get(t[:3])
            if sub:
                inbox[sub][t] = body
    return inbox

def merge_concepts(sub, data, inbox_cards, items):
    path = os.path.join(ROOT, '學科', sub, '概念.md')
    text = read(path)
    if not text.strip():
        text = f'# {sub}概念\n\n一個考點一張卡，標題照「考點」頁的名字。卡片內容隨時可以改、可以加自己的註記。\n'
    head, cards = split_cards(text)
    have = set(cards)
    # 依地圖順序排新卡，讀起來像一本書
    order = [c for ch in data['chapters'] for c in ch['concepts']] + [c for c in items if c not in {c for ch in data['chapters'] for c in ch['concepts']}]
    added = []
    for c in order:
        if c in inbox_cards and c not in have:
            cards[c] = inbox_cards[c]; added.append(c)
    for c, body in inbox_cards.items():   # 不在地圖上的也收
        if c not in cards:
            cards[c] = body; added.append(c)
    if added:
        write(path, head.rstrip() + '\n\n' + '\n'.join(cards.values()).rstrip() + '\n')
    return added, set(cards)

# ---------------- 主程式 ----------------
def main():
    maps = json.load(open(MAP_FILE, encoding='utf-8'))
    index = by_subject(concept_index())
    inbox = load_inbox()
    report = []
    for sub in SUBJECTS:
        items = index[sub]
        data = maps.get(sub, {'chapters': []})
        added, have_cards = merge_concepts(sub, data, inbox[sub], items)
        map_path = os.path.join(ROOT, '學科', sub, '地圖.md')
        map_text, unmapped = build_map_page(sub, data, items, read(map_path))
        write(map_path, map_text)
        write(os.path.join(ROOT, '學科', sub, '考點.md'), build_index_page(sub, items, have_cards))
        nocard = [c for c in items if c not in have_cards]
        report.append((sub, len(items), sum(e['n'] for e in items.values()), len(added), nocard, unmapped))
    print(('【只檢查，沒改檔】' if CHECK else '【已更新】') + ' 科目｜考點｜題次｜本次新增卡｜還沒有卡｜還沒有章')
    for sub, n, t, a, nocard, unmapped in report:
        print(f'  {sub}｜{n}｜{t}｜{a}｜{len(nocard)}｜{len(unmapped)}')
    for sub, n, t, a, nocard, unmapped in report:
        for c in nocard[:30]:
            print('  還沒有卡：', c)
        for c in unmapped:
            print('  還沒有章：', c)

if __name__ == '__main__':
    main()
