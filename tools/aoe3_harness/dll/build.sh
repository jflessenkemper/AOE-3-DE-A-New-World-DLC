#!/usr/bin/env bash
# build.sh — Build anw harness DLLs via distrobox gs-build (MinGW64 cross-compiler)
#
# Usage:
#   ./build.sh [hello|hook|all|clean] [--verbose]
#
#   hello    — build hello_anw.dll (minimal load-verification DLL, no MinHook)
#   hook     — build anw_hook.dll  (full hook DLL: pipe server + SendInput + MinHook)
#   all      — build both
#   clean    — remove built .dll, .lib, .o files from the dll/ directory
#
# Options:
#   --verbose  Print full compiler command output instead of summary lines
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
# Parse --verbose flag (can appear anywhere in args)
# --------------------------------------------------------------------------
VERBOSE=0
ARGS=()
for arg in "$@"; do
    if [ "${arg}" = "--verbose" ]; then
        VERBOSE=1
    else
        ARGS+=("${arg}")
    fi
done
# Restore positional params without the --verbose flag
set -- "${ARGS[@]+"${ARGS[@]}"}"

vecho() {
    if [ "${VERBOSE}" -eq 1 ]; then
        echo "$@"
    fi
}

# --------------------------------------------------------------------------
# Pre-flight checks
# --------------------------------------------------------------------------

# Check distrobox is installed and gs-build container exists
check_distrobox() {
    if ! command -v distrobox &>/dev/null; then
        echo "[build] ERROR: distrobox is not installed or not on PATH."
        echo "[build] Install distrobox: https://distrobox.it/"
        exit 1
    fi
    if ! distrobox list 2>/dev/null | grep -q "gs-build"; then
        echo "[build] ERROR: distrobox container 'gs-build' does not exist."
        echo "[build] Create it with:"
        echo "[build]   distrobox create --name gs-build --image fedora:43"
        echo "[build]   distrobox enter gs-build -- sudo dnf install -y mingw64-gcc"
        exit 1
    fi
}

# Check that the AoE3 game EXE is NOT running before overwriting the DLL.
# A running game holds the DLL file open (locked); overwriting it will silently
# produce a corrupt copy or fail outright.
#
# We look specifically for the Wine wineserver process serving the game EXE,
# identified by the process name "AoE3DE_s.exe" in the Wine process list.
# Using --exact with pgrep avoids false positives from launcher wrapper processes
# that have the EXE path as a command-line argument.
check_game_not_running() {
    # Check Wine process by exact comm name (the wineserver-managed process)
    if pgrep --exact "AoE3DE_s.exe" &>/dev/null; then
        echo "[build] ERROR: AoE3DE_s.exe appears to be running (found via pgrep --exact)."
        echo "[build] Close the game before rebuilding and redeploying the DLL."
        echo "[build] (The running game holds anw_hook.dll locked; overwriting"
        echo "[build]  it while the game is open produces a corrupt DLL on disk.)"
        exit 1
    fi
}

# --------------------------------------------------------------------------
# Helper: run a command inside the gs-build distrobox container
# --------------------------------------------------------------------------
gs_run() {
    if [ "${VERBOSE}" -eq 1 ]; then
        distrobox enter gs-build -- bash -c "$*"
    else
        distrobox enter gs-build -- bash -c "$*" 2>&1
    fi
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
    if command -v x86_64-w64-mingw32-objdump &>/dev/null; then
        x86_64-w64-mingw32-objdump -p "${dll_path}" 2>/dev/null | grep "DLL Name" || true
    else
        gs_run "x86_64-w64-mingw32-objdump -p '${dll_path}'" | grep "DLL Name" || true
    fi

    echo "[verify] Exported/defined symbols:"
    if command -v x86_64-w64-mingw32-nm &>/dev/null; then
        x86_64-w64-mingw32-nm "${dll_path}" 2>/dev/null | grep -E "DllMain|inject_|Present_hook|worker_thread|dxgi_" || true
    else
        gs_run "x86_64-w64-mingw32-nm '${dll_path}'" | grep -E "DllMain|inject_|Present_hook|worker_thread|dxgi_" || true
    fi

    echo "[verify] ${dll_name} PASS"
}

# --------------------------------------------------------------------------
# Build: hello_anw.dll (minimal, no MinHook)
# --------------------------------------------------------------------------
build_hello() {
    check_distrobox
    check_game_not_running

    echo "[build] Building hello_anw.dll..."
    vecho "[build] Compiler: x86_64-w64-mingw32-gcc"

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
    else
        vecho "[drop] SYSTEM32_PATH not found, skipping: ${SYSTEM32_PATH}"
    fi
    if [ -d "${GAME_DATA_PATH}" ]; then
        cp "${DLL_DIR}/hello_anw.dll" "${GAME_DATA_PATH}/hello_anw.dll"
        echo "[drop] -> ${GAME_DATA_PATH}/hello_anw.dll"
    else
        vecho "[drop] GAME_DATA_PATH not found, skipping: ${GAME_DATA_PATH}"
    fi
}

# --------------------------------------------------------------------------
# Build: anw_hook.dll (full: MinHook + pipe server + SendInput + DXGI hook)
# --------------------------------------------------------------------------
build_anw_hook() {
    check_distrobox
    check_game_not_running

    echo "[build] Building anw_hook.dll..."

    # Verify MinGW is available inside the container
    if ! gs_run "command -v x86_64-w64-mingw32-gcc" &>/dev/null; then
        echo "[build] ERROR: x86_64-w64-mingw32-gcc not found inside gs-build."
        echo "[build] Install it: distrobox enter gs-build -- sudo dnf install -y mingw64-gcc"
        exit 1
    fi

    # Verify submodule is present
    if [ ! -f "${MINHOOK_SRC}/hook.c" ]; then
        echo "[build] ERROR: MinHook submodule not found at ${MINHOOK_SRC}"
        echo "[build] Run: git submodule update --init --recursive"
        exit 1
    fi

    vecho "[build] DXGI hook: always-on (vtable[8]=Present verified against MinGW dxgi.h)"
    vecho "[build] Sources: anw_hook.c anw_dxgi_hook.c anw_input.c + MinHook"

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
    else
        vecho "[drop] SYSTEM32_PATH not found, skipping: ${SYSTEM32_PATH}"
    fi
    if [ -d "${GAME_DATA_PATH}" ]; then
        cp "${DLL_DIR}/anw_hook.dll" "${GAME_DATA_PATH}/anw_hook.dll"
        echo "[drop] -> ${GAME_DATA_PATH}/anw_hook.dll"
    else
        vecho "[drop] GAME_DATA_PATH not found, skipping: ${GAME_DATA_PATH}"
    fi
}

# --------------------------------------------------------------------------
# Clean: remove build artifacts
# --------------------------------------------------------------------------
do_clean() {
    echo "[clean] Removing build artifacts from ${DLL_DIR}..."
    rm -fv \
        "${DLL_DIR}/hello_anw.dll" \
        "${DLL_DIR}/hello_anw.lib" \
        "${DLL_DIR}/anw_hook.dll" \
        "${DLL_DIR}/anw_hook.lib" \
        "${DLL_DIR}"/*.o
    echo "[clean] Done."
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
    clean)
        do_clean
        ;;
    *)
        echo "Usage: $0 [hello|hook|all|clean] [--verbose]"
        echo ""
        echo "  hello    Build hello_anw.dll (minimal load-verification DLL)"
        echo "  hook     Build anw_hook.dll  (full hook: pipe + SendInput + MinHook + DXGI)"
        echo "  all      Build both"
        echo "  clean    Remove built .dll/.lib/.o files"
        echo ""
        echo "  --verbose  Print full compiler output"
        exit 1
        ;;
esac

echo ""
echo "[build] Done."
