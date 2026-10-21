# loyiha-xotirasi

[Claude Code](https://claude.com/claude-code) uchun plugin: har bir loyihada **kod arxitekturasi** va **ish jurnalini** repo ichida yuritadi, shunda bir necha kundan keyin qaytsangiz ham — siz ham, Claude ham — qayerda to'xtaganingizni darhol tushunasiz.

| Fayl | Nima |
|---|---|
| `docs/ARCHITECTURE.md` | Tizim tuzilishi (mermaid chizmalar), modullar, ma'lumot modeli, tashqi bog'liqliklar, **qarorlar va sabablari**, yangi modul qo'shish retsepti |
| `docs/PROGRESS.md` | Hozirgi holat, keyingi qadamlar, bloklar, funksiyalar holati (✅ 🟡 ⬜ ⛔), ma'lum muammolar, sanali **o'zgarishlar jurnali** |

## Nima qiladi

- **Skill `loyiha-xotirasi`** — yangi loyihada ikki hujjatni shablondan yaratadi va repo asosida to'ldiradi, `CLAUDE.md` ga qoida qo'shadi; har tugallangan o'zgarishdan keyin jurnalni, statuslarni va keyingi qadamni yangilaydi; arxitektura yoki qaror o'zgarsa `ARCHITECTURE.md` ni ham.
- **SessionStart hook** — loyihada `docs/PROGRESS.md` bo'lsa, sessiya boshida uning boshini Claude'ga ko'rsatadi.
- **Stop hook** — Claude ishni tugatmoqchi bo'lganda kod o'zgargan, lekin `PROGRESS.md` yangilanmagan bo'lsa, **bir marta** eslatadi (cheksiz sikl yo'q).

## O'rnatish

Claude Code ichida:

```
/plugin marketplace add Muhammadalixon-Qodirov/loyiha-xotirasi
/plugin install loyiha-xotirasi@loyiha-xotirasi
```

Hook'lar `bash` va `git` ni ishlatadi (Windows'da Git Bash bilan ishlaydi).

## Ishlatish

- Yangi loyihada: *"loyiha xotirasini boshla"* yoki `/loyiha-xotirasi` — hujjatlar yaratiladi.
- Keyin odatdagidek ishlang: har o'zgarishdan keyin jurnal yangilanadi.
- Qaytganda: *"qayerda to'xtadik?"* — `PROGRESS.md` asosida javob.

Hujjatlar siz gaplashgan tilda yoziladi.
