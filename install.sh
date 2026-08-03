#!/usr/bin/env bash
#
# install.sh — install the il2cpp-to-csharp skill and let the USER choose
# which backend(s) to install:
#
#   1) IDA backend only      (original skill, byte-identical to upstream)
#   2) Ghidra backend only   (custom skill, byte-identical to the modified version)
#   3) Both                  (dual-backend dispatcher; the agent picks at runtime)
#
# Usage:
#   ./install.sh [target-dir] [--ida|--ghidra|--both]
#
# Without a backend flag you are prompted interactively. When stdin is not a
# terminal (e.g. an agent installing), a backend flag is required.
#
# target-dir defaults to ~/.claude/skills/il2cpp-to-csharp-skill.
# Examples:
#   ./install.sh                                              # prompt, default target
#   ./install.sh --ida                                        # IDA only, default target
#   ./install.sh --ghidra ~/.codex/skills/il2cpp-to-csharp-skill
#   ./install.sh --both ~/.dsh/skills/il2cpp-to-csharp-skill

set -euo pipefail

SKILL_NAME="il2cpp-to-csharp-skill"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BACKEND=""
TARGET=""

usage() {
  cat <<'USAGE_EOF'
Usage: ./install.sh [target-dir] [--ida|--ghidra|--both]

Install the il2cpp-to-csharp skill and choose which backend to install:

  --ida      install the original IDA Pro MCP backend only
  --ghidra   install the custom Ghidra backend only
  --both     install both backends (root dispatcher SKILL.md)

Without a backend flag you are prompted to choose interactively (requires a
terminal). target-dir defaults to ~/.claude/skills/il2cpp-to-csharp-skill.
USAGE_EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --ida)     BACKEND="ida" ;;
    --ghidra)  BACKEND="ghidra" ;;
    --both)    BACKEND="both" ;;
    -h|--help) usage; exit 0 ;;
    *)         TARGET="$1" ;;
  esac
  shift
done

if [ -z "$BACKEND" ]; then
  if [ ! -t 0 ]; then
    echo "No backend chosen and stdin is not a terminal; pass --ida, --ghidra, or --both." >&2
    usage >&2
    exit 1
  fi
  echo "Which backend do you want to install?"
  echo "  1) IDA backend    — original skill, needs IDA Pro + IDA Pro MCP"
  echo "  2) Ghidra backend — custom skill, needs Ghidra GUI or analyzeHeadless"
  echo "  3) Both           — dual-backend dispatcher (agent picks at runtime)"
  printf "Choose 1-3: "
  read -r choice
  case "$choice" in
    1) BACKEND="ida" ;;
    2) BACKEND="ghidra" ;;
    3) BACKEND="both" ;;
    *)
      echo "Invalid choice: $choice" >&2
      exit 1
      ;;
  esac
fi

if [ -z "$TARGET" ]; then
  TARGET="$HOME/.claude/skills/$SKILL_NAME"
fi
TARGET="${TARGET/#\~/$HOME}"

case "$TARGET" in
  ""|/|"$HOME")
    echo "Refusing to install into unsafe target: $TARGET" >&2
    exit 1
    ;;
esac

if [ ! -f "$SRC_DIR/SKILL.md" ] || [ ! -d "$SRC_DIR/ida" ] || [ ! -d "$SRC_DIR/ghidra" ]; then
  echo "This script must be run from the skill repository root." >&2
  exit 1
fi

echo "Installing '$BACKEND' backend to: $TARGET"
rm -rf "$TARGET"
mkdir -p "$TARGET"

install_ida() {
  cp "$SRC_DIR/LICENSE" "$TARGET/"
  cp "$SRC_DIR/ida/SKILL.md" "$TARGET/SKILL.md"
  for f in ida-usage.md ida-quirks.md strings.md helpers.md compiler-patterns.md; do
    cp "$SRC_DIR/ida/$f" "$TARGET/$f"
  done
  cp -R "$SRC_DIR/ida/scripts" "$TARGET/scripts"
}

install_ghidra() {
  cp "$SRC_DIR/LICENSE" "$TARGET/"
  cp "$SRC_DIR/ghidra/SKILL.md" "$TARGET/SKILL.md"
  for f in ghidra-setup.md ghidra-query.md ghidra-quirks.md strings.md helpers.md \
           string-formatting.md lambdas-closures.md linq-generics.md coroutines.md \
           async.md runtime-exceptions.md runtime-memory.md; do
    cp "$SRC_DIR/ghidra/$f" "$TARGET/$f"
  done
  cp -R "$SRC_DIR/ghidra/scripts" "$TARGET/scripts"
  cp -R "$SRC_DIR/ghidra/agents" "$TARGET/agents"
}

install_both() {
  cp "$SRC_DIR/LICENSE" "$SRC_DIR/SKILL.md" "$SRC_DIR/README.md" "$SRC_DIR/README.zh-CN.md" "$TARGET/"
  cp -R "$SRC_DIR/ida" "$TARGET/ida"
  cp -R "$SRC_DIR/ghidra" "$TARGET/ghidra"
}

case "$BACKEND" in
  ida)    install_ida ;;
  ghidra) install_ghidra ;;
  both)   install_both ;;
  *)
    echo "Unknown backend: $BACKEND" >&2
    exit 1
    ;;
esac

echo "Done: $BACKEND backend installed to $TARGET"
