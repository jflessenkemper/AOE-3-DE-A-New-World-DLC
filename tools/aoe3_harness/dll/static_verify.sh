#!/usr/bin/env bash
# static_verify.sh — Static verification of anw harness DLL artifacts.
#
# Runs all checks that can be verified WITHOUT launching the game:
#   1-2.  PE32+ file type for hello_anw.dll and anw_hook.dll
#   3-4.  DLL imports for anw_hook.dll (KERNEL32, USER32 expected)
#   5-9.  Key symbols defined in anw_hook.dll
#   10.   Python syntax check: dll_client.py
#   11.   Python syntax check: cli.py
#   12-13. CLI --help shows 'input' and 'dll' subcommands
#   14.   CLI dll status exits 0
#   15.   build.sh passes bash -n
#   16.   static_verify.sh passes bash -n
#   17.   Present_hook has staging-texture pipeline (not a stub)
#   18.   hotreload.py syntax check
#   19.   diff.py syntax check
#   20.   bisect.py syntax check
#
# Usage:
#   cd tools/aoe3_harness/dll
#   ./static_verify.sh [--quiet]
#
#   --quiet   Print only the final PASS/FAIL summary (no per-check output)
#
# Exit code: 0 = all checks passed, 1 = one or more checks failed.
#
# IMPORTANT: This script does NOT launch the game.
# Live-game verification is documented in:
#   artifacts/harness_design/phase2_verification_checklist.md

set -uo pipefail

REPO_ROOT="/var/home/jflessenkemper/AOE-3-DE-A-New-World"
DLL_DIR="${REPO_ROOT}/tools/aoe3_harness/dll"

# Parse --quiet flag
QUIET=0
for arg in "$@"; do
    if [ "${arg}" = "--quiet" ]; then
        QUIET=1
    fi
done

PASS=0
FAIL=0

# Emit output only when not in quiet mode
qecho() {
    if [ "${QUIET}" -eq 0 ]; then
        echo "$@"
    fi
}

check() {
    local label="$1"
    local cmd="$2"
    local expected_pattern="$3"

    local tmpout
    tmpout=$(mktemp)
    eval "${cmd}" > "${tmpout}" 2>&1
    if grep -qE "${expected_pattern}" "${tmpout}"; then
        qecho "[PASS] ${label}"
        PASS=$((PASS + 1))
    else
        # Always print failures, even in quiet mode
        echo "[FAIL] ${label}"
        if [ "${QUIET}" -eq 0 ]; then
            echo "       Command: ${cmd}"
            echo "       Expected pattern: ${expected_pattern}"
            echo "       Output tail:"
            tail -5 "${tmpout}" | sed 's/^/         /'
        fi
        FAIL=$((FAIL + 1))
    fi
    rm -f "${tmpout}"
}

qecho "========================================"
qecho "  ANW Phase 2 Static Verification"
qecho "========================================"
qecho ""

# --------------------------------------------------------------------------
# Pre-flight: confirm build artifacts exist before running binary checks.
# --------------------------------------------------------------------------
ARTIFACTS_MISSING=0
for dll in hello_anw.dll anw_hook.dll; do
    if [ ! -f "${DLL_DIR}/${dll}" ]; then
        echo "[WARN] Build artifact missing: ${DLL_DIR}/${dll}"
        ARTIFACTS_MISSING=1
    fi
done
if [ "${ARTIFACTS_MISSING}" -eq 1 ]; then
    echo "[WARN] One or more DLL artifacts are missing."
    echo "[WARN] Run: bash ${DLL_DIR}/build.sh all"
    echo "[WARN] Continuing with remaining checks (binary checks will fail)."
fi
qecho ""

# --------------------------------------------------------------------------
# 1-2. PE32+ file type checks
# --------------------------------------------------------------------------
qecho "--- DLL file types ---"

check "hello_anw.dll is PE32+" \
    "file '${DLL_DIR}/hello_anw.dll'" \
    "PE32\+"

check "anw_hook.dll is PE32+" \
    "file '${DLL_DIR}/anw_hook.dll'" \
    "PE32\+"

# --------------------------------------------------------------------------
# 3-4. DLL import check
# --------------------------------------------------------------------------
qecho ""
qecho "--- DLL imports (anw_hook.dll) ---"

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

# dxgi.dll and d3d11.dll are loaded via GetProcAddress at runtime (not static imports).
# This is intentional — see install_present_hook() in anw_dxgi_hook.c.
qecho "       Note: dxgi.dll/d3d11.dll absent from imports (runtime-loaded via GetProcAddress — expected)."

# --------------------------------------------------------------------------
# 5-9. Key symbols in anw_hook.dll
# --------------------------------------------------------------------------
qecho ""
qecho "--- Key symbols (anw_hook.dll) ---"

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

# Verify Present_hook is compiled in (always-on since hardening pass 2026-05-29)
check "Present_hook compiled into anw_hook.dll" \
    "${NM} '${DLL_DIR}/anw_hook.dll'" \
    "Present_hook"

# --------------------------------------------------------------------------
# 10-11. Python syntax checks
# --------------------------------------------------------------------------
qecho ""
qecho "--- Python syntax ---"

check "dll_client.py compiles" \
    "python3 -m py_compile '${REPO_ROOT}/tools/aoe3_harness/dll_client.py' && echo OK" \
    "^OK$"

check "cli.py compiles" \
    "python3 -m py_compile '${REPO_ROOT}/tools/aoe3_harness/cli.py' && echo OK" \
    "^OK$"

# --------------------------------------------------------------------------
# 12-14. CLI subcommands
# --------------------------------------------------------------------------
qecho ""
qecho "--- CLI subcommands ---"

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
# 15-16. Shell script syntax checks
# --------------------------------------------------------------------------
qecho ""
qecho "--- Shell script syntax ---"

check "build.sh passes bash -n" \
    "bash -n '${DLL_DIR}/build.sh' && echo OK" \
    "^OK$"

check "static_verify.sh passes bash -n" \
    "bash -n '${DLL_DIR}/static_verify.sh' && echo OK" \
    "^OK$"

# --------------------------------------------------------------------------
# 17-20. New module syntax + pipeline completeness checks
# --------------------------------------------------------------------------
qecho ""
qecho "--- New module checks (Phase 3) ---"

check "Present_hook has staging-texture pipeline (not a stub)" \
    "grep -l 'CopyResource\|D3D11_USAGE_STAGING' '${DLL_DIR}/anw_dxgi_hook.c'" \
    "anw_dxgi_hook.c"

check "hotreload.py syntax check" \
    "python3 -m py_compile '${REPO_ROOT}/tools/aoe3_harness/hotreload.py' && echo OK" \
    "^OK$"

check "diff.py syntax check" \
    "python3 -m py_compile '${REPO_ROOT}/tools/aoe3_harness/diff.py' && echo OK" \
    "^OK$"

check "bisect.py syntax check" \
    "python3 -m py_compile '${REPO_ROOT}/tools/aoe3_harness/bisect.py' && echo OK" \
    "^OK$"

# --------------------------------------------------------------------------
# Summary
# --------------------------------------------------------------------------
qecho ""
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
