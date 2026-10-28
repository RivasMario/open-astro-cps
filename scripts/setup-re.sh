#!/usr/bin/env bash
# =============================================================================
# setup-re.sh — Reverse Engineering toolchain for open-astro-cps (Linux/Fedora)
# Installs OpenJDK 21, Ghidra, and rea-agents, and registers REA's MCP server
# at Claude Code LOCAL scope for open-astro-cps only.
# =============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS_DIR="$HOME/tools"

echo "==> Setting up Reverse Engineering toolchain for open-astro-cps ($REPO_ROOT)"

# 1. JDK 21
if command -v dnf &>/dev/null; then
    sudo dnf install -y java-21-openjdk-devel unzip curl jq
elif command -v apt-get &>/dev/null; then
    sudo apt-get update && sudo apt-get install -y openjdk-21-jdk unzip curl jq
fi

# 2. Ghidra
mkdir -p "$TOOLS_DIR"
GHIDRA_DIR="$(find "$TOOLS_DIR" -maxdepth 1 -type d -name 'ghidra_*' | sort -r | head -1 || true)"
if [[ -z "$GHIDRA_DIR" ]]; then
    echo "  [install] Downloading latest Ghidra release..."
    URL="$(curl -fsSL https://api.github.com/repos/NationalSecurityAgency/ghidra/releases/latest | jq -r '.assets[] | select(.name | endswith(".zip")) | .browser_download_url' | head -1)"
    ZIP="/tmp/ghidra.zip"
    curl -fSL "$URL" -o "$ZIP"
    unzip -q "$ZIP" -d "$TOOLS_DIR"
    rm -f "$ZIP"
    GHIDRA_DIR="$(find "$TOOLS_DIR" -maxdepth 1 -type d -name 'ghidra_*' | sort -r | head -1)"
fi
echo "  [ok] GHIDRA_INSTALL_DIR=$GHIDRA_DIR"

# 3. rea-agents
export PATH="$HOME/.npm-global/bin:$PATH"
if ! command -v rea &>/dev/null; then
    npm install -g rea-agents@latest
fi

# 4. Register REA MCP at local project scope for open-astro-cps only
cd "$REPO_ROOT"
unset CLAUDE_CONFIG_DIR
claude mcp remove --scope local rea 2>/dev/null || true
claude mcp add --scope local rea -e "GHIDRA_INSTALL_DIR=$GHIDRA_DIR" -- npx -y rea-agents@latest mcp
echo "  [ok] Registered REA MCP at local project scope ($REPO_ROOT)"
