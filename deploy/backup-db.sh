#!/bin/bash
# Copy the assistant's database (records, waiting changes, chat memory, audit) to a dated file and keep the
# newest 14. Uses sqlite3's .backup, which takes a consistent copy while the backend is running.
#
#   deploy/backup-db.sh                 run by hand, or nightly by com.crm-assistant.backup
#
# Settings (environment): CRM_DB (default backend/data/crm.db), BACKUP_DIR (default ~/Backups/crm-assistant),
# KEEP (default 14).

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DB="${CRM_DB:-$ROOT/backend/data/crm.db}"
DEST="${BACKUP_DIR:-$HOME/Backups/crm-assistant}"
KEEP="${KEEP:-14}"
SQLITE=/usr/bin/sqlite3

umask 077  # student records: only this user can read the copies
mkdir -p "$DEST"

if [[ ! -f "$DB" ]]; then
  echo "$(date '+%F %T') No database at $DB. Nothing backed up." >&2
  exit 1
fi

name="crm-$(date +%Y-%m-%d-%H%M%S).db"
tmp="$DEST/.$name.partial"
trap 'rm -f "$tmp"' EXIT

"$SQLITE" "$DB" ".timeout 10000" ".backup '$tmp'"
check="$("$SQLITE" "$tmp" "pragma integrity_check")"
if [[ "$check" != "ok" ]]; then
  echo "$(date '+%F %T') The copy failed its integrity check: $check" >&2
  exit 1
fi
mv "$tmp" "$DEST/$name"

# Keep the newest $KEEP copies (names sort by date)
ls -1 "$DEST"/crm-*.db | sort -r | tail -n +"$((KEEP + 1))" | while read -r old; do rm -f "$old"; done

echo "$(date '+%F %T') Backed up to $DEST/$name ($(du -h "$DEST/$name" | cut -f1 | xargs)); $(ls -1 "$DEST"/crm-*.db | wc -l | tr -d ' ') kept."
