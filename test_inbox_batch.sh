#!/usr/bin/env bash
# ======================================================
# 🧪 Vollständiger CRM Inbox Batch-Test
# - Login mit Admin-Credentials
# - Erstellt N Testnachrichten
# - Archiviert und löscht sie automatisch
# - Erstellt einen HTML-Report
# - Optionaler Cleanup-Job für alte Testnachrichten
# ======================================================

# ⚙️ Konfiguration
BASE_URL="http://127.0.0.1:8000"
USERNAME="admin@example.com"
PASSWORD="123456"
COOKIE_FILE="cookies.txt"
REPORT_FILE="inbox_test_report.html"
NUM_MESSAGES=10

# 🕒 Zeitmessung Start
START_TIME=$(date +%s)

# 🧹 Ergebnis-Zähler
SUCCESS_CREATE=0
SUCCESS_ARCHIVE=0
SUCCESS_DELETE=0

# ======================================================
# 📝 HTML-Report: Kopfbereich
# ======================================================
echo "<!DOCTYPE html>
<html lang='de'>
<head>
  <meta charset='UTF-8'>
  <title>📊 CRM Inbox Testreport</title>
  <style>
    body { font-family: Arial, sans-serif; background:#f4f6f8; padding:20px; }
    h1 { color:#4f46e5; }
    table { border-collapse: collapse; width: 100%; margin-top: 20px; background:#fff; }
    th, td { border:1px solid #ddd; padding:8px; text-align:center; }
    th { background:#eef2ff; }
    .ok { color:green; font-weight:bold; }
    .fail { color:red; font-weight:bold; }
    .meta { background:#fff; padding:10px; border:1px solid #ddd; border-radius:8px; }
  </style>
</head>
<body>
<h1>📨 CRM Inbox Testreport</h1>
<div class='meta'>
<p><strong>Datum:</strong> $(date)</p>
<p><strong>Anzahl Testnachrichten:</strong> $NUM_MESSAGES</p>
</div>

<table>
<tr>
<th>#</th>
<th>Erstellt</th>
<th>Archiviert</th>
<th>Gelöscht</th>
<th>Dauer (s)</th>
</tr>
" > "$REPORT_FILE"

# ======================================================
# 1️⃣ LOGIN
# ======================================================
echo "🔐 Login als $USERNAME ..."
LOGIN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST "$BASE_URL/auth/login" \
  -F "username=$USERNAME" \
  -F "password=$PASSWORD" \
  -c "$COOKIE_FILE")

if [ "$LOGIN_STATUS" != "303" ]; then
  echo "❌ Login fehlgeschlagen (HTTP $LOGIN_STATUS)"
  exit 1
fi
echo "✅ Login erfolgreich (HTTP $LOGIN_STATUS)"

# ======================================================
# 2️⃣ NACHRICHTEN ERSTELLEN / ARCHIVIEREN / LÖSCHEN
# ======================================================
for i in $(seq 1 $NUM_MESSAGES); do
  echo "📩 [$i/$NUM_MESSAGES] Erstelle Nachricht ..."
  SUBJECT="BatchTest $i - $(date +%H:%M:%S)"
  CONTENT="Automatischer Testlauf #$i am $(date)"

  CREATED="❌"
  ARCHIVED="❌"
  DELETED="❌"

  # Nachricht erstellen
  CREATE_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/dashboard/inbox/create" \
    -F "sender_name=Batch Tester" \
    -F "sender_email=batch$i@test.de" \
    -F "subject=$SUBJECT" \
    -F "content=$CONTENT" \
    -b "$COOKIE_FILE")

  if [ "$CREATE_STATUS" == "303" ]; then
    SUCCESS_CREATE=$((SUCCESS_CREATE+1))
    CREATED="✅"
  fi

  # Letzte ID ermitteln
  LAST_ID=$(curl -s -b "$COOKIE_FILE" "$BASE_URL/dashboard/inbox/" \
    | grep -Eo '/dashboard/inbox/[0-9]+/toggle-read' \
    | sed -E 's|.*/inbox/([0-9]+)/toggle-read|\1|' \
    | head -n 1)

  if [ -n "$LAST_ID" ]; then
    # Archivieren
    ARCHIVE_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/dashboard/inbox/$LAST_ID/toggle-archive" -b "$COOKIE_FILE")
    if [ "$ARCHIVE_STATUS" == "303" ]; then
      SUCCESS_ARCHIVE=$((SUCCESS_ARCHIVE+1))
      ARCHIVED="✅"
    fi

    # Löschen
    DELETE_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/dashboard/inbox/$LAST_ID/delete" -b "$COOKIE_FILE")
    if [ "$DELETE_STATUS" == "303" ]; then
      SUCCESS_DELETE=$((SUCCESS_DELETE+1))
      DELETED="✅"
    fi
  fi

  STEP_END=$(date +%s)
  STEP_TIME=$((STEP_END - START_TIME))

  # Zeile in HTML schreiben
  echo "<tr>
  <td>$i</td>
  <td class='$( [ "$CREATED" == "✅" ] && echo ok || echo fail )'>$CREATED</td>
  <td class='$( [ "$ARCHIVED" == "✅" ] && echo ok || echo fail )'>$ARCHIVED</td>
  <td class='$( [ "$DELETED" == "✅" ] && echo ok || echo fail )'>$DELETED</td>
  <td>$STEP_TIME</td>
  </tr>" >> "$REPORT_FILE"
done

# ======================================================
# 3️⃣ HTML-REPORT ABSCHLUSS
# ======================================================
END_TIME=$(date +%s)
TOTAL_TIME=$((END_TIME - START_TIME))

echo "</table>
<h2>📊 Zusammenfassung</h2>
<ul>
<li>Erstellt: $SUCCESS_CREATE / $NUM_MESSAGES</li>
<li>Archiviert: $SUCCESS_ARCHIVE / $NUM_MESSAGES</li>
<li>Gelöscht: $SUCCESS_DELETE / $NUM_MESSAGES</li>
<li>⏱️ Gesamtdauer: ${TOTAL_TIME}s</li>
</ul>
</body>
</html>" >> "$REPORT_FILE"

echo "✅ Batch-Test abgeschlossen!"
echo "👉 HTML-Report: $REPORT_FILE"

# ======================================================
# 4️⃣ OPTIONAL: Cleanup-Job für alte Testnachrichten 🧼
# ======================================================
# ❗ Nutze diesen Teil nur, wenn du MySQL-Zugang hast!
# Beispiel:
# mysql -u root -p CRM_DB -e "DELETE FROM messages WHERE sender_email LIKE 'batch%@test.de';"

# ======================================================
# 5️⃣ Report automatisch öffnen (macOS)
# ======================================================
if [[ "$OSTYPE" == "darwin"* ]]; then
  open "$REPORT_FILE"
fi