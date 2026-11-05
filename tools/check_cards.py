# -*- coding: utf-8 -*-
"""檢查一份卡片檔：每張卡標題是否剛好對應輸入清單的考點名。用法：python3 tools/check_cards.py 卡片檔.md 考點清單檔.md"""
import re, sys
cards = open(sys.argv[1], encoding='utf-8').read()
want = re.findall(r'^### (【.】.+)$', open(sys.argv[2], encoding='utf-8').read(), re.M)
have = re.findall(r'^## (【.】.+)$', cards, re.M)
have_s = [h.strip() for h in have]
miss = [w for w in want if w.strip() not in have_s]
extra = [h for h in have_s if h not in [w.strip() for w in want]]
dup = {h for h in have_s if have_s.count(h) > 1}
bad = [l for l in cards.split('\n') if re.search(r'旨在|總的來說|不是.{1,12}而是', l)]
print(f'應有 {len(want)} 張，實際 {len(have)} 張；缺 {len(miss)}，多 {len(extra)}，重複 {len(dup)}，用語 {len(bad)}')
for x in miss: print('缺：', x)
for x in extra: print('多：', x)
for x in dup: print('重複：', x)
for x in bad[:10]: print('用語：', x[:80])
sys.exit(0 if not (miss or extra or dup or bad) else 1)
