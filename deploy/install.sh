#!/bin/bash
# Install, check or remove the launchd agents that run the CRM Assistant on this Mac.
#
#   deploy/install.sh              fill in this Mac's paths, copy to ~/Library/LaunchAgents and start them
#   deploy/install.sh status       are they loaded, and their last exit codes
#   deploy/install.sh uninstall    stop them and remove them from ~/Library/LaunchAgents
#   deploy/install.sh render DIR   only write the filled-in plists to DIR, to read them first
#
# Logs go to ~/Library/Logs/crm-assistant/ (also visible in Console.app).

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AGENTS="$HOME/Library/LaunchAgents"
LOGS="$HOME/Library/Logs/crm-assistant"
NAMES=(backend frontend backup)
DOMAIN="gui/$(id -u)"

# launchd starts jobs with a bare PATH; add Node.js (for UI rebuilds) as found now
node_dir="$(dirname "$(command -v npm 2>/dev/null || echo /usr/local/bin/npm)")"
PATH_FOR_JOBS="$node_dir:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

render() {  # render <name> <out file>
  sed -e "s|__ROOT__|$ROOT|g" -e "s|__LOGS__|$LOGS|g" -e "s|__PATH__|$PATH_FOR_JOBS|g" \
    "$ROOT/deploy/com.crm-assistant.$1.plist" > "$2"
  plutil -lint -s "$2"
}

case "${1:-install}" in
  install)
    mkdir -p "$AGENTS" "$LOGS"
    for n in "${NAMES[@]}"; do
      label="com.crm-assistant.$n"
      launchctl bootout "$DOMAIN/$label" 2>/dev/null || true  # reinstall: stop the old copy first
      render "$n" "$AGENTS/$label.plist"
      launchctl bootstrap "$DOMAIN" "$AGENTS/$label.plist"
      echo "Loaded $label"
    done
    echo "Staff app: http://localhost:8080 · logs: $LOGS"
    ;;
  status)
    for n in "${NAMES[@]}"; do
      label="com.crm-assistant.$n"
      if info="$(launchctl print "$DOMAIN/$label" 2>/dev/null)"; then
        echo "$label: $(grep -m1 -E '^\s*state =' <<<"$info" | xargs), $(grep -m1 'last exit code' <<<"$info" | xargs)"
      else
        echo "$label: not loaded"
      fi
    done
    ;;
  uninstall)
    for n in "${NAMES[@]}"; do
      label="com.crm-assistant.$n"
      launchctl bootout "$DOMAIN/$label" 2>/dev/null && echo "Stopped $label" || true
      rm -f "$AGENTS/$label.plist"
    done
    echo "Removed. Logs and backups are left where they are."
    ;;
  render)
    out="${2:?render needs a folder}"
    mkdir -p "$out"
    for n in "${NAMES[@]}"; do render "$n" "$out/com.crm-assistant.$n.plist"; done
    echo "Wrote ${#NAMES[@]} plists to $out"
    ;;
  *)
    sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'
    exit 1
    ;;
esac
