#!/usr/bin/env bash
# build.sh — Build anw harness DLLs via distrobox gs-build (MinGW64 cross-compiler)
#
# Usage:
#   ./build.sh [hello|hook|all]
#
#   hello  — build hello_anw.dll (minimal load-verification DLL, no MinHook)
#   hook   — build anw_hook.dll  (full hook DLL: pipe server + SendInput + MinHook)
#   all    — build both
#
# Requirements:
#   - distrobox container 'gs-build' (Fedora 43) with mingw64-gcc installed
#   - git submodule tools/aoe3_harness/dll/minhook initialised
#
# After a successful build, DLLs are copied to Wine system32 and game data dir.
# Static verification (file, objdump, nm) is run automatically.
#
# IMPORTANT: This script does NOT launch the game.  Live verification is
# documented in artifacts/harness_design/phase2_verification_checklist.md.

set -euo pipefail

REPO_ROOT="/var/home/jflessenkemper/AOE-3-DE-A-New-World"
DLL_DIR="${REPO_ROOT}/tools/aoe3_harness/dll"
MINHOOK_SRC="${DLL_DIR}/minhook/src"

# Wine/Proton paths for DLL drop
SYSTEM32_PATH="${HOME}/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/windows/system32"
GAME_DATA_PATH="${HOME}/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE"

# --------------------------------------------------------------------------
# Helper: run a command inside the gs-build distrobox container
# --------------------------------------------------------------------------
gs_run() {
    distrobox enter gs-build -- bash -c "$*"
}

# --------------------------------------------------------------------------
# Helper: static verification after build
# --------------------------------------------------------------------------
static_verify_dll() {
    local dll_name="$1"
    local dll_path="${DLL_DIR}/${dll_name}"

    echo ""
    echo "[verify] === ${dll_name} ==="
    if [ ! -f "${dll_path}" ]; then
        echo "[verify] ERROR: ${dll_path} not found"
        return 1
    fi

    echo "[verify] file output:"
    file "${dll_path}"

    echo "[verify] Import DLL names:"
    x86_64-w64-mingw32-objdump -p "${dll_path}" 2>/dev/null | grep "DLL Name" || \
        gs_run "x86_64-w64-mingw32-objdump -p '${dll_path}'" | grep "DLL Name"

    echo "[verify] Exported/defined symbols:"
    x86_64-w64-mingw32-nm "${dll_path}" 2>/dev/null | grep -E "DllMain|inject_|Present_hook|worker_thread|dxgi_" || \
        gs_run "x86_64-w64-mingw32-nm '${dll_path}'" | grep -E "DllMain|inject_|Present_hook|worker_thread|dxgi_"

    echo "[verify] ${dll_name} PASS"
}

# --------------------------------------------------------------------------
# Build: hello_anw.dll (minimal, no MinHook)
# --------------------------------------------------------------------------
build_hello() {
    echo "[build] Building hello_anw.dll..."
    gs_run "
        cd '${DLL_DIR}' &&
        x86_64-w64-mingw32-gcc -shared \
            -o hello_anw.dll hello_anw.c \
            -Wl,--out-implib,hello_anw.lib \
            -O2 -Wall
    "
    echo "[build] hello_anw.dll built."
    static_verify_dll "hello_anw.dll"

    # Drop to Wine paths
    if [ -d "${SYSTEM32_PATH}" ]; then
        cp "${DLL_DIR}/hello_anw.dll" "${SYSTEM32_PATH}/hello_anw.dll"
        echo "[drop] -> ${SYSTEM32_PATH}/hello_anw.dll"
    fi
    if [ -d "${GAME_DATA_PATH}" ]; then
        cp "${DLL_DIR}/hello_anw.dll" "${GAME_DATA_PATH}/hello_anw.dll"
        echo "[drop] -> ${GAME_DATA_PATH}/hello_anw.dll"
    fi
}

# --------------------------------------------------------------------------
# Build: anw_hook.dll (full: MinHook + pipe server + SendInput)
# --------------------------------------------------------------------------
build_anw_hook() {
    echo "[build] Building anw_hook.dll..."

    # Verify submodule is present
    if [ ! -f "${MINHOOK_SRC}/hook.c" ]; then
        echo "[build] ERROR: MinHook submodule not found at ${MINHOOK_SRC}"
        echo "[build] Run: git submodule update --init --recursive"
        return 1
    fi

    gs_run "
        cd '${DLL_DIR}' &&
        x86_64-w64-mingw32-gcc -shared \
            -DUNICODE -D_UNICODE \
            -o anw_hook.dll \
            anw_hook.c \
            anw_dxgi_hook.c \
            anw_input.c \
            '${MINHOOK_SRC}/buffer.c' \
            '${MINHOOK_SRC}/hook.c' \
            '${MINHOOK_SRC}/trampoline.c' \
            '${MINHOOK_SRC}/hde/hde64.c' \
            -I'${DLL_DIR}/minhook/include' \
            -ldxgi -ld3d11 -luser32 \
            -Wl,--out-implib,anw_hook.lib \
            -O2 -Wall
    "
    echo "[build] anw_hook.dll built."
    static_verify_dll "anw_hook.dll"

    # Drop to Wine paths
    if [ -d "${SYSTEM32_PATH}" ]; then
        cp "${DLL_DIR}/anw_hook.dll" "${SYSTEM32_PATH}/anw_hook.dll"
        echo "[drop] -> ${SYSTEM32_PATH}/anw_hook.dll"
    fi
    if [ -d "${GAME_DATA_PATH}" ]; then
        cp "${DLL_DIR}/anw_hook.dll" "${GAME_DATA_PATH}/anw_hook.dll"
        echo "[drop] -> ${GAME_DATA_PATH}/anw_hook.dll"
    fi
}

# --------------------------------------------------------------------------
# Main dispatch
# --------------------------------------------------------------------------
TARGET="${1:-hello}"

case "${TARGET}" in
    hello)
        build_hello
        ;;
    hook)
        build_anw_hook
        ;;
    all)
        build_hello
        build_anw_hook
        ;;
    *)
        echo "Usage: $0 [hello|hook|all]"
        echo ""
        echo "  hello  Build hello_anw.dll (minimal load-verification DLL)"
        echo "  hook   Build anw_hook.dll  (full hook: pipe + SendInput + MinHook)"
        echo "  all    Build both"
        exit 1
        ;;
esac

echo ""
echo "[build] Done."
