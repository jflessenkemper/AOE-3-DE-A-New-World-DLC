#!/usr/bin/env bash
# static_verify.sh — Static verification of anw harness DLL artifacts.
#
# Runs all checks that can be verified WITHOUT launching the game:
#   1. PE32+ file type for hello_anw.dll and anw_hook.dll
#   2. DLL imports for anw_hook.dll (KERNEL32, USER32, msvcrt expected in stub build)
#   3. Key symbols defined/exported in anw_hook.dll
#   4. Python syntax check: dll_client.py
#   5. CLI --help shows input + dll subcommands
#   6. build.sh syntax check
#
# Usage:
#   cd tools/aoe3_harness/dll
#   ./static_verify.sh
#
# Exit code: 0 = all checks passed, 1 = one or more checks failed.
#
# IMPORTANT: This script does NOT launch the game.
# Live-game verification is documented in:
#   artifacts/harness_design/phase2_verification_checklist.md

set -uo pipefail

REPO_ROOT="/var/home/jflessenkemper/AOE-3-DE-A-New-World"
DLL_DIR="${REPO_ROOT}/tools/aoe3_harness/dll"

PASS=0
FAIL=0

check() {
    local label="$1"
    local cmd="$2"
    local expected_pattern="$3"

    # Use a temp file to avoid command substitution truncating large output
    local tmpout
    tmpout=$(mktemp)
    eval "${cmd}" > "${tmpout}" 2>&1
    if grep -qE "${expected_pattern}" "${tmpout}"; then
        echo "[PASS] ${label}"
        PASS=$((PASS + 1))
    else
        echo "[FAIL] ${label}"
        echo "       Command: ${cmd}"
        echo "       Expected pattern: ${expected_pattern}"
        echo "       Output tail:"
        tail -5 "${tmpout}" | sed 's/^/         /'
        FAIL=$((FAIL + 1))
    fi
    rm -f "${tmpout}"
}

echo "========================================"
echo "  ANW Phase 2 Static Verification"
echo "========================================"
echo ""

# --------------------------------------------------------------------------
# 1. PE32+ file type checks
# --------------------------------------------------------------------------
echo "--- DLL file types ---"

check "hello_anw.dll is PE32+" \
    "file '${DLL_DIR}/hello_anw.dll'" \
    "PE32\+"

check "anw_hook.dll is PE32+" \
    "file '${DLL_DIR}/anw_hook.dll'" \
    "PE32\+"

# --------------------------------------------------------------------------
# 2. DLL import check (requires mingw objdump — run inside gs-build if needed)
# --------------------------------------------------------------------------
echo ""
echo "--- DLL imports (anw_hook.dll) ---"

if command -v x86_64-w64-mingw32-objdump &>/dev/null; then
    OBJDUMP="x86_64-w64-mingw32-objdump"
else
    OBJDUMP="distrobox enter gs-build -- x86_64-w64-mingw32-objdump"
fi

check "anw_hook.dll imports KERNEL32.dll" \
    "${OBJDUMP} -p '${DLL_DIR}/anw_hook.dll'" \
    "KERNEL32"

check "anw_hook.dll imports USER32.dll" \
    "${OBJDUMP} -p '${DLL_DIR}/anw_hook.dll'" \
    "USER32"

# In stub build, dxgi.dll/d3d11.dll are NOT imported (they're inside #ifdef blocks)
# This is expected and correct.  Document it explicitly:
echo "       Note: dxgi.dll/d3d11.dll absent from imports in stub build — expected."

# --------------------------------------------------------------------------
# 3. Key symbols in anw_hook.dll
# --------------------------------------------------------------------------
echo ""
echo "--- Key symbols (anw_hook.dll) ---"

if command -v x86_64-w64-mingw32-nm &>/dev/null; then
    NM="x86_64-w64-mingw32-nm"
else
    NM="distrobox enter gs-build -- x86_64-w64-mingw32-nm"
fi

check "DllMain defined in anw_hook.dll" \
    "${NM} '${DLL_DIR}/anw_hook.dll'" \
    "DllMain"

check "inject_key defined in anw_hook.dll" \
    "${NM} '${DLL_DIR}/anw_hook.dll'" \
    "inject_key"

check "inject_click defined in anw_hook.dll" \
    "${NM} '${DLL_DIR}/anw_hook.dll'" \
    "inject_click"

check "dxgi_hook_init defined in anw_hook.dll" \
    "${NM} '${DLL_DIR}/anw_hook.dll'" \
    "dxgi_hook_init"

check "worker_thread defined in anw_hook.dll" \
    "${NM} '${DLL_DIR}/anw_hook.dll'" \
    "worker_thread"

# --------------------------------------------------------------------------
# 4. Python syntax check: dll_client.py
# --------------------------------------------------------------------------
echo ""
echo "--- Python syntax ---"

check "dll_client.py compiles" \
    "python3 -m py_compile '${REPO_ROOT}/tools/aoe3_harness/dll_client.py' && echo OK" \
    "^OK$"

check "cli.py compiles" \
    "python3 -m py_compile '${REPO_ROOT}/tools/aoe3_harness/cli.py' && echo OK" \
    "^OK$"

# --------------------------------------------------------------------------
# 5. CLI --help shows new subcommands
# --------------------------------------------------------------------------
echo ""
echo "--- CLI subcommands ---"

check "cli.py --help shows 'input' subcommand" \
    "cd '${REPO_ROOT}' && python3 -m tools.aoe3_harness.cli --help" \
    "input"

check "cli.py --help shows 'dll' subcommand" \
    "cd '${REPO_ROOT}' && python3 -m tools.aoe3_harness.cli --help" \
    "dll"

check "cli.py dll status exits 0" \
    "cd '${REPO_ROOT}' && python3 -m tools.aoe3_harness.cli dll status && echo OK" \
    "OK|All DLL files present"

# --------------------------------------------------------------------------
# 6. build.sh syntax check
# --------------------------------------------------------------------------
echo ""
echo "--- Shell script syntax ---"

check "build.sh passes bash -n" \
    "bash -n '${DLL_DIR}/build.sh' && echo OK" \
    "^OK$"

check "static_verify.sh passes bash -n" \
    "bash -n '${DLL_DIR}/static_verify.sh' && echo OK" \
    "^OK$"

# --------------------------------------------------------------------------
# Summary
# --------------------------------------------------------------------------
echo ""
echo "========================================"
echo "  Results: ${PASS} PASS, ${FAIL} FAIL"
echo "========================================"

if [ "${FAIL}" -gt 0 ]; then
    echo "  STATIC VERIFICATION FAILED"
    exit 1
else
    echo "  STATIC VERIFICATION PASSED"
    exit 0
fi
