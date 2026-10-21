---
name: loyiha-xotirasi
description: Loyiha xotirasi — har loyihada docs/ARCHITECTURE.md (kod arxitekturasi, qarorlar), docs/PROGRESS.md (nima qilindi / nima qoldi / o'zgarishlar jurnali) va interaktiv kod xaritasini (docs/ARCHITECTURE.html + docs/architecture.json — modullar, funksiyalar, endpointlar, jadvallar, bog'lanishlar va ehtimoliy zaif joylar) yuritadi va har o'zgarishdan keyin yangilaydi. Yangi loyiha boshlanganda, mavjud loyihaga qaytilganda, "nima qilgan edik", "qayerda to'xtadik", "arxitekturani yoz", "kod xaritasi", "zaif joylar", "bog'lanishlarni ko'rsat", "jurnalni yangila" deyilganda va har qanday kod o'zgarishi tugagach ishlatiladi.
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
   Kod allaqachon bor bo'lsa — avval skanerni ishga tushir (4-bo'lim): `architecture.json` modullar, endpointlar va jadvallarni beradi, ARCHITECTURE.md ni shundan to'ldirish tezroq va aniqroq.
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

## 4. Kod xaritasi (grafik + zaif joylar)

Odam ham, boshqa AI ham loyihani **bir qarashda** tushunishi uchun:

| Fayl | Kim uchun | Kim yozadi |
|---|---|---|
| `docs/ARCHITECTURE.html` | odam — brauzerda interaktiv graf: modullar, bog'lanishlar, funksiyalar, endpointlar, jadvallar, xavflar | skaner (avtomatik) |
| `docs/architecture.json` | AI — xuddi shu ma'lumot bitta JSON'da (`about` maydoni uni qanday o'qishni tushuntiradi) | skaner (avtomatik, qo'lda tahrirlanmaydi) |
| `docs/architecture.notes.json` | Claude'ning qatlami: izohlar, komponentlar, xavflarni ko'rib chiqish | **Claude** (qo'lda) |

### Skanerni ishga tushirish

Bu skill papkasidagi skript (faqat Python standart kutubxonasi):

```bash
python "<skill papkasi>/scripts/scan.py" <repo ildizi>        # docs/ ga yozadi
python "<skill papkasi>/scripts/scan.py" <repo> --render-only # faqat notes o'zgarganda HTML'ni yangilash
```

Qachon: hujjatlar birinchi yaratilganda; yangi modul/endpoint/jadval qo'shilganda; katta o'zgarishdan keyin; foydalanuvchi xarita yoki zaif joylarni so'raganda. Mayda o'zgarishlarda shart emas.

### Claude qatlami — `docs/architecture.notes.json`

Skaner faqat strukturani va **taxminiy** xavf signallarini topadi. Ma'noni Claude qo'shadi:

```json
{
  "project": "Loyiha nomi",
  "components": [
    {"id": "auth", "name": "Autentifikatsiya", "description": "Ro'yxatdan o'tish, login, sessiyalar", "paths": ["internal/auth", "internal/auth/*"]}
  ],
  "modules":   {"internal/auth": "Login, sessiya, parol tiklash; JWT emas — server sessiyasi"},
  "functions": {"internal/auth/service.go:Service.Login": "Parolni tekshiradi, 5 xatodan keyin bloklaydi"},
  "risks": [
    {"severity": "high", "title": "Admin endpointlarida rol tekshiruvi yo'q", "file": "internal/httpapi/server.go", "line": 140,
     "function": "NewServer", "detail": "/v1/admin/* faqat RequireAuth bilan, RequireRole yo'q"}
  ],
  "reviews": {
    "<risk id>": {"status": "ok", "note": "clause faqat oq ro'yxatdagi ustun nomlaridan tuziladi — injection emas"},
    "<risk id>": {"status": "confirmed", "note": "q parametri to'g'ridan-to'g'ri SQL'ga qo'shiladi"}
  }
}
```

Ish tartibi (skanerdan keyin):
1. `docs/architecture.json` dagi `summary` va `unreviewed_high` ni o'qi.
2. Har bir **yuqori** (keyin vaqt bo'lsa **o'rta**) avtomatik xavf uchun kodni o'qib, `reviews` ga hukm yoz: `confirmed` (haqiqiy), `ok` (yolg'on signal — sababi bilan), `fixed` (tuzatildi). Hukmsiz "ok" qo'yma.
3. Kodni o'qiyotganda skaner ko'ra olmaydigan zaif joylarni o'zing `risks` ga qo'sh: avtorizatsiya yo'qligi, kiruvchi ma'lumot validatsiyasi yo'qligi, IDOR, maxfiy ma'lumot logga yozilishi, race condition, tranzaksiyasiz bir nechta yozuv va h.k.
4. Asosiy modullarga bir qatorli izoh (`modules`) va katta loyihada `components` yoz — grafda guruhlanadi.
5. `--render-only` bilan HTML'ni yangila. `docs/ARCHITECTURE.md` ga "Kod xaritasi" havolasi va **tasdiqlangan** xavflarning qisqa ro'yxatini qo'sh; `PROGRESS.md` ning "Ma'lum muammolar" bo'limiga ham.

Xavfni tuzatgan bo'lsang — `reviews` da `fixed` qil va jurnalga yoz. Risk `id` lari barqaror (qator raqami o'zgarsa ham saqlanadi).

## 5. Yozish qoidalari

- Qisqa va aniq: "nima" + "qayerda" + "nega". Kodni hujjatga ko'chirma — fayl yo'li va funksiya nomini yoz (`internal/auth/service.go: Login`).
- Arxitektura chizmalari — mermaid (`flowchart`, `erDiagram`, `sequenceDiagram`); murakkab oqim uchun bitta chizma 3 abzas matndan yaxshi.
- Raqamlar va natijalar (benchmark, test soni, vaqt) bo'lsa — yoz; ular keyin solishtirish uchun kerak.
- Maxfiy ma'lumot (parol, token, server kaliti) hujjatga **hech qachon** yozilmaydi — faqat qayerda saqlanishi ("`.env` da, `DB_URL`").
- Hujjat hajmi oshib ketsa (PROGRESS > ~400 qator): eski jurnal yozuvlarini `docs/progress-archive/YYYY-MM.md` ga ko'chir, PROGRESS da faqat oxirgi 1–2 oy qolsin.

## 6. Foydalanuvchi so'rasa

- "Qayerda to'xtadik?" / "nima qilgan edik?" → PROGRESS dagi "Hozirgi holat", oxirgi 3–5 jurnal yozuvi va "Keyingi qadamlar" asosida qisqa javob.
- "Arxitekturani tushuntir" → ARCHITECTURE asosida, kerak bo'lsa kodni tekshirib.
- "Hujjatlarni yangila / tekshir" → hujjatni joriy kod bilan solishtir, farqlarni tuzat, jurnalga yoz.
- "Xaritani ko'rsat" / "zaif joylar qayerda?" → skanerni ishga tushir, yuqori xavflarni ko'rib chiq (4-bo'lim), `docs/ARCHITECTURE.html` yo'lini ber va eng muhim 3–5 tasdiqlangan xavfni ayt.
