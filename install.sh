#!/usr/bin/env sh
# Install park-the-car-v2 into agent skill directories.
set -e
SRC="$(cd "$(dirname "$0")/park-the-car-v2" && pwd)"
copy() { rm -rf "$1/park-the-car-v2"; mkdir -p "$1"; cp -R "$SRC" "$1/park-the-car-v2"; echo "installed -> $1/park-the-car-v2"; }
case "${1:---help}" in
  --claude)  copy "$HOME/.claude/skills" ;;
  --cursor)  copy "$HOME/.cursor/skills" ;;
  --project) copy ".cursor/skills"; copy ".agents/skills" ;;
  --all)     copy "$HOME/.claude/skills"; copy "$HOME/.cursor/skills" ;;
  *) echo "usage: ./install.sh [--claude | --cursor | --project | --all]"; exit 1 ;;
esac
