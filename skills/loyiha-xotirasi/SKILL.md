---
name: loyiha-xotirasi
description: Loyiha xotirasi — har loyihada docs/ARCHITECTURE.md (kod arxitekturasi, qarorlar) va docs/PROGRESS.md (nima qilindi / nima qoldi / o'zgarishlar jurnali) hujjatlarini yuritadi va har o'zgarishdan keyin yangilaydi. Yangi loyiha boshlanganda, mavjud loyihaga qaytilganda, "nima qilgan edik", "qayerda to'xtadik", "arxitekturani yoz", "jurnalni yangila" deyilganda va har qanday kod o'zgarishi tugagach ishlatiladi.
---

# Loyiha xotirasi

Maqsad: bir necha kun yoki boshqa vazifalardan keyin loyihaga qaytilganda — foydalanuvchi ham, Claude ham — **5 daqiqada** qayerda turganini, nima uchun shunday qilinganini va keyingi qadamni tushunsin. Xotira suhbatda emas, **repo ichida** saqlanadi.

Ikki hujjat yuritiladi:

| Fayl | Nima uchun | Qachon yangilanadi |
|---|---|---|
| `docs/ARCHITECTURE.md` | Tizim qanday tuzilgan va **nega** shunday | Struktura, modul, ma'lumot modeli, tashqi bog'liqlik yoki muhim qaror o'zgarganda |
| `docs/PROGRESS.md` | Nima qilindi, nima qoldi, nima bloklangan | **Har** tugallangan o'zgarishdan keyin (har commit bilan) |

Hujjatlar foydalanuvchi gaplashadigan tilda yoziladi (odatda o'zbekcha).

## 1. Ish boshida (har sessiyada)

1. `docs/PROGRESS.md` mavjud bo'lsa — **birinchi** uni o'qi ("Hozirgi holat", "Keyingi qadamlar", "Bloklar"). Keyin vazifaga tegishli bo'lsa `docs/ARCHITECTURE.md` ni o'qi.
2. Hujjatda yozilgan holat koddan farq qilsa (fayl yo'q, funksiya boshqa nomda) — kodga ishon, hujjatni tuzat va buni jurnalga yoz.
3. Hujjatlar yo'q va loyiha yangi yoki kod yozish boshlanmoqda → **2-bo'lim**.

## 2. Hujjatlarni yaratish (bir marta)

1. Repo'ni ko'rib chiq: ildizdagi fayllar (`package.json`, `go.mod`, `pyproject.toml`, `pubspec.yaml`, `manage.py`, `Dockerfile`, `compose.yaml` …), asosiy papkalar, kirish nuqtalari, testlar, mavjud README/TT hujjatlari.
2. Shu skill yonidagi shablonlardan nusxa ol: `templates/ARCHITECTURE.md`, `templates/PROGRESS.md` → `docs/` ga. Shablon bo'limlarini **haqiqiy** ma'lumot bilan to'ldir; bilmagan narsangni o'ylab topma — `❓ aniqlanmagan` deb qoldir.
3. `CLAUDE.md` (yo'q bo'lsa yarat) ga quyidagi qoidani qo'sh:

   ```markdown
   ## Loyiha xotirasi
   - Ishni boshlashdan oldin `docs/PROGRESS.md` ni o'qi; arxitekturaga tegsang — `docs/ARCHITECTURE.md` ni ham.
   - Har tugallangan o'zgarishdan keyin `docs/PROGRESS.md` ni yangila (status, jurnal, keyingi qadam);
     struktura yoki qaror o'zgarsa — `docs/ARCHITECTURE.md` ni ham.
   ```

4. Foydalanuvchiga bitta qatorda ayt: hujjatlar yaratildi, qayerda.

## 3. Har o'zgarishdan keyin (asosiy qoida)

Kod o'zgarishi tugagach (testlar o'tgach, commitdan oldin) `docs/PROGRESS.md` ni yangila:

- **Jurnal** — eng yuqoriga yangi yozuv: sana (`YYYY-MM-DD`, nisbiy emas), nima qilindi (1–3 qator), qaysi fayllar/modullar, tekshiruv natijasi (testlar ✓/✗, raqamlar bo'lsa raqamlar).
- **Funksiyalar holati** — tegishli qatorlarning statusini o'zgartir: `✅ tayyor`, `🟡 qisman`, `⬜ boshlanmagan`, `⛔ bloklangan`.
- **Hozirgi holat / Keyingi qadamlar** — eskirganini o'chir, yangisini yoz. Keyingi qadam aniq bo'lsin ("X faylida Y ni qilish"), umumiy emas.
- **Bloklar** — foydalanuvchidan kutilayotgan narsa paydo bo'lsa (kalit, qaror, ruxsat) — shu yerga.
- **Ma'lum muammolar** — topilgan, lekin hozir tuzatilmagan xatolar.

`docs/ARCHITECTURE.md` ni faqat quyidagilarda yangila: yangi modul/paket/servis, ma'lumot modeli (jadval, maydon) o'zgarishi, yangi tashqi bog'liqlik, API kontrakti o'zgarishi, **qaror** qabul qilinganda (nima tanlandi, nima rad etildi, nega). Qarorlar bo'limiga yozuv **o'chirilmaydi** — eskirsa, "bekor qilindi: sabab" deb belgilanadi.

Mayda o'zgarishlarda (matn, formatlash, bitta qatorli tuzatish) jurnalga bitta qator yetarli; bir sessiyadagi bir nechta mayda o'zgarishni bitta yozuvga birlashtir.

## 4. Yozish qoidalari

- Qisqa va aniq: "nima" + "qayerda" + "nega". Kodni hujjatga ko'chirma — fayl yo'li va funksiya nomini yoz (`internal/auth/service.go: Login`).
- Arxitektura chizmalari — mermaid (`flowchart`, `erDiagram`, `sequenceDiagram`); murakkab oqim uchun bitta chizma 3 abzas matndan yaxshi.
- Raqamlar va natijalar (benchmark, test soni, vaqt) bo'lsa — yoz; ular keyin solishtirish uchun kerak.
- Maxfiy ma'lumot (parol, token, server kaliti) hujjatga **hech qachon** yozilmaydi — faqat qayerda saqlanishi ("`.env` da, `DB_URL`").
- Hujjat hajmi oshib ketsa (PROGRESS > ~400 qator): eski jurnal yozuvlarini `docs/progress-archive/YYYY-MM.md` ga ko'chir, PROGRESS da faqat oxirgi 1–2 oy qolsin.

## 5. Foydalanuvchi so'rasa

- "Qayerda to'xtadik?" / "nima qilgan edik?" → PROGRESS dagi "Hozirgi holat", oxirgi 3–5 jurnal yozuvi va "Keyingi qadamlar" asosida qisqa javob.
- "Arxitekturani tushuntir" → ARCHITECTURE asosida, kerak bo'lsa kodni tekshirib.
- "Hujjatlarni yangila / tekshir" → hujjatni joriy kod bilan solishtir, farqlarni tuzat, jurnalga yoz.
