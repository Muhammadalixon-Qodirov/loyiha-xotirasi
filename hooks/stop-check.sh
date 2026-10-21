#!/usr/bin/env bash
# Claude javobni tugatmoqchi bo'lganda: kod o'zgargan, lekin docs/PROGRESS.md yangilanmagan bo'lsa —
# bir marta eslatadi (decision: block). Ikkinchi marta (stop_hook_active) to'xtatmaydi — cheksiz sikl bo'lmaydi.

input="$(cat)"
case "$input" in
  *'"stop_hook_active":true'*|*'"stop_hook_active": true'*) exit 0 ;;
esac

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0
[ -f docs/PROGRESS.md ] || exit 0

# commit qilinmagan o'zgarishlar: hujjat bo'lmagan fayllar
code_changed="$(git status --porcelain 2>/dev/null | cut -c4- | sed 's/.* -> //' \
  | grep -vE '^(docs/|\.claude/|\.agent/)|\.md$' | head -n 1)"
[ -n "$code_changed" ] || exit 0

# PROGRESS.md ham shu o'zgarishlar ichida bo'lsa — hammasi joyida
[ -n "$(git status --porcelain docs/PROGRESS.md 2>/dev/null)" ] && exit 0

cat <<'JSON'
{"decision": "block", "reason": "[loyiha-xotirasi] Kod o'zgardi (commit qilinmagan), lekin docs/PROGRESS.md yangilanmadi. Jurnalga sana bilan yozuv qo'sh (nima qilindi, qaysi fayllar, tekshiruv natijasi), funksiyalar holati va keyingi qadamlarni yangila; struktura yoki qaror o'zgargan bo'lsa docs/ARCHITECTURE.md ni ham. Agar bu o'zgarish jurnalga yozishga arzimasa (masalan vaqtinchalik sinov) — buni bir jumlada ayt va tugat."}
JSON
exit 0
