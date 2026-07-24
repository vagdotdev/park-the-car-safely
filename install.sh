#!/usr/bin/env sh
# Install the park skills into agent skill directories.
#
#   main  -> park-the-car-safely-v2  (current, evidence engine)
#   v1    -> park-the-car-safely     (legacy prose edition, on the v1 branch)
#
# The two use different skill names on purpose, so both can sit side by side
# in one skill directory and be selected independently.
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
SRC="$ROOT/park-the-car-safely-v2"
WITH_V1=0

copy() { # copy <dest-dir> <src> <name>
  rm -rf "$1/$3"
  mkdir -p "$1"
  cp -R "$2" "$1/$3"
  echo "installed -> $1/$3"
}

# v1 lives on another branch; materialize it without disturbing this checkout.
v1_src() {
  tmp="$(mktemp -d)"
  for ref in origin/v1 v1; do
    if git -C "$ROOT" rev-parse --verify --quiet "$ref" >/dev/null 2>&1; then
      git -C "$ROOT" archive "$ref" park-the-car-safely | tar -x -C "$tmp"
      echo "$tmp/park-the-car-safely"
      return 0
    fi
  done
  echo "" # not available (e.g. shallow clone or tarball download)
}

install_to() {
  copy "$1" "$SRC" "park-the-car-safely-v2"
  [ "$WITH_V1" -eq 1 ] || return 0
  v1dir="$(v1_src)"
  if [ -n "$v1dir" ] && [ -d "$v1dir" ]; then
    copy "$1" "$v1dir" "park-the-car-safely"
  else
    echo "skipped v1 -> branch 'v1' not present locally; run: git fetch origin v1" >&2
  fi
}

for arg in "$@"; do
  [ "$arg" = "--with-v1" ] && WITH_V1=1
done

case "${1:---help}" in
  --claude)  install_to "$HOME/.claude/skills" ;;
  --cursor)  install_to "$HOME/.cursor/skills" ;;
  --project) install_to ".cursor/skills"; install_to ".agents/skills" ;;
  --all)     install_to "$HOME/.claude/skills"; install_to "$HOME/.cursor/skills" ;;
  *)
    echo "usage: ./install.sh [--claude | --cursor | --project | --all] [--with-v1]"
    echo "  --with-v1   also install the legacy v1 skill from the v1 branch"
    exit 1 ;;
esac
