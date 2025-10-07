#!/usr/bin/env bash
# ============================================
# 🧪 Testskript für CRM Inbox (macOS-kompatibel)
# Funktionen:
# 1️⃣ Login als admin
# 2️⃣ Nachricht erstellen
# 3️⃣ Nachricht archivieren
# 4️⃣ Nachricht löschen
# ============================================

# Konfiguration
BASE_URL="http://127.0.0.1:8000"
USERNAME="admin@example.com"
PASSWORD="123456"
COOKIE_FILE="cookies.txt"

# --------------------------------------------
echo "🚀 [1/4] Login als $USERNAME ..."
curl -s -X POST "$BASE_URL/auth/login" \
  -F "username=$USERNAME" \
  -F "password=$PASSWORD" \
  -c "$COOKIE_FILE" \
  -o /dev/null -w "HTTP:%{http_code}\n"

# --------------------------------------------
echo "📩 [2/4] Testnachricht wird erstellt ..."
curl -s -X POST "$BASE_URL/dashboard/inbox/create" \
  -F "sender_name=Max Mustermann" \
  -F "sender_email=max@test.de" \
  -F "subject=Test per Script $(date +%H:%M:%S)" \
  -F "content=Hallo, dies ist ein automatischer Test $(date)" \
  -b "$COOKIE_FILE" \
  -o /dev/null -w "HTTP:%{http_code}\n"

# --------------------------------------------
# ⬇️ Nachrichten-ID extrahieren (macOS-kompatibel)
LAST_ID=$(curl -s -b "$COOKIE_FILE" "$BASE_URL/dashboard/inbox/" \
  | grep -Eo '/dashboard/inbox/[0-9]+/toggle-read' \
  | sed -E 's|.*/inbox/([0-9]+)/toggle-read|\1|' \
  | head -n 1)

if [ -z "$LAST_ID" ]; then
  echo "❌ Fehler: Konnte keine Nachricht finden."
  exit 1
else
  echo "✅ Neue Nachricht hat die ID: $LAST_ID"
fi

# --------------------------------------------
echo "🗄️ [3/4] Nachricht #$LAST_ID wird archiviert ..."
curl -s -X POST "$BASE_URL/dashboard/inbox/$LAST_ID/toggle-archive" \
  -b "$COOKIE_FILE" \
  -o /dev/null -w "HTTP:%{http_code}\n"

# --------------------------------------------
echo "🗑️ [4/4] Nachricht #$LAST_ID wird gelöscht ..."
curl -s -X POST "$BASE_URL/dashboard/inbox/$LAST_ID/delete" \
  -b "$COOKIE_FILE" \
  -o /dev/null -w "HTTP:%{http_code}\n"

# --------------------------------------------
echo "✅ Testlauf abgeschlossen! Bitte prüfe die Inbox im Browser:"
echo "👉 $BASE_URL/dashboard/inbox/"