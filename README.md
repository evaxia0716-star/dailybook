# Daybook

白天的筆記本：學科、學習、隨寫、考場。網站在 https://evaxia0716-star.github.io/dailybook/

- `index.html`：整個網站（單一檔案，不用建置）
- `_sidebar.md`：目錄。沒連結的一行是分區，縮排的連結是頁面
- `學科/<科目>/`：每科三頁——地圖（章節骨架，可打勾）、錯題、概念；`## ` 開頭是一張卡
- `學習/`：白紙，一個主題一頁
- `隨寫/`：日記，一個月一檔，網站的「今天寫一筆」會自動寫進來
- `assets/年/月/`：貼進編輯器的圖片，自動壓縮後存這裡
- `data/bank/`：考古題題庫，一份考卷一個 JSON，`index.json` 是清單；網站的「考場」從這裡出題
- `data/reviews.json`、`data/progress.json`、`data/exams.json`：複習、地圖進度、考試成績，由網站自動寫入
- 用法與格式見網站上的「使用說明」
