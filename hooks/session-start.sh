#!/usr/bin/env bash
# Sessiya boshida: loyihada docs/PROGRESS.md bo'lsa, uning boshini Claude context'iga beradi.
# stdout — Claude'ga qo'shimcha context sifatida qo'shiladi.

f="docs/PROGRESS.md"
[ -f "$f" ] || exit 0

echo "[loyiha-xotirasi] Bu loyihada $f bor — ishni boshlashdan oldin holat va keyingi qadamlarni hisobga ol."
echo "Har tugallangan o'zgarishdan keyin $f ni yangila (jurnal, status, keyingi qadam); struktura/qaror o'zgarsa docs/ARCHITECTURE.md ni ham."
echo
echo "----- $f (boshi) -----"
head -n 60 "$f"
exit 0
