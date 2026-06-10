#!/usr/bin/env python3
"""
Validator to ensure AI diagnostic probes do not leak into in-game chat.

Checks:
 (a) Three control flags in aiGlobals.xs are declared "= false":
     cANWProbeToHostChat, cANWProbeToSelfChat, cANWDebugVisible
 (b) The anwProbe() function in aiUtilities.xs contains no unconditional
     aiChat() calls — every aiChat( must be preceded by an if guard.
     aiEcho() may be unconditional.

Exits 0 (PASS) if both hold; exits 1 (FAIL) with diagnostic message otherwise.
"""

import sys
import re
from pathlib import Path

def check_globals_flags():
    """Verify three flags in aiGlobals.xs are declared false."""
    globals_file = Path("game/ai/core/aiGlobals.xs")
    if not globals_file.exists():
        print(f"FAIL: {globals_file} not found")
        return False

    content = globals_file.read_text()
    required_flags = {
        "cANWProbeToHostChat": False,
        "cANWProbeToSelfChat": False,
        "cANWDebugVisible": False,
    }

    failures = []
    for flag_name in required_flags:
        # Match: extern const bool <flag_name> = <value>;
        pattern = rf"extern\s+const\s+bool\s+{re.escape(flag_name)}\s*=\s*(true|false);"
        match = re.search(pattern, content)
        if not match:
            failures.append(f"{flag_name} not declared or malformed")
        elif match.group(1) != "false":
            failures.append(f"{flag_name} = {match.group(1)} (expected false)")

    if failures:
        print(f"FAIL: aiGlobals.xs flag check:")
        for msg in failures:
            print(f"  {msg}")
        return False

    return True


def check_anwprobe_no_unconditional_aichat():
    """Verify anwProbe() has no unconditional aiChat calls."""
    utilities_file = Path("game/ai/core/aiUtilities.xs")
    if not utilities_file.exists():
        print(f"FAIL: {utilities_file} not found")
        return False

    content = utilities_file.read_text()

    # Extract the anwProbe() function body.
    # Pattern: find "void anwProbe(" and extract until the matching closing brace.
    match = re.search(r"void\s+anwProbe\s*\([^)]*\)\s*\{", content)
    if not match:
        print("FAIL: anwProbe() function not found")
        return False

    start = match.end()
    brace_count = 1
    pos = start
    while pos < len(content) and brace_count > 0:
        if content[pos] == '{':
            brace_count += 1
        elif content[pos] == '}':
            brace_count -= 1
        pos += 1

    if brace_count != 0:
        print("FAIL: anwProbe() function body could not be parsed (unmatched braces)")
        return False

    func_body = content[start:pos-1]

    # Now check: every aiChat( in func_body must be preceded by an if guard.
    # Strategy: find all aiChat( calls and check if there's an if (...) guard before each.

    lines = func_body.split('\n')
    failures = []

    for i, line in enumerate(lines):
        if 'aiChat(' in line:
            # Check if this line has an if guard before it.
            # Look at the context: is there an if statement guarding this aiChat?
            # Simple heuristic: check if the line is inside an if block.
            # More robust: look backwards for the nearest if ( ... ) {

            # For now, check: does the current line or very near context have if?
            # Extract the part of the line before aiChat(
            before_aichat = line[:line.index('aiChat(')]

            # Check: is there an if with "==" in the immediate context?
            # Look back a few lines for an unclosed if statement.
            if_found = False
            for j in range(max(0, i-3), i):
                if 'if (' in lines[j] and '== true' in lines[j]:
                    if_found = True
                    break

            # Also check the current line or next line for if.
            if 'if (' in before_aichat:
                if_found = True

            if not if_found:
                # More thorough check: look back for an if and forward for its closing brace
                brace_depth = 0
                found_guard = False
                for j in range(i-1, max(0, i-10), -1):
                    if '}' in lines[j]:
                        brace_depth += lines[j].count('}')
                    if '{' in lines[j]:
                        brace_depth -= lines[j].count('{')
                    if brace_depth < 0 and 'if (' in lines[j]:
                        found_guard = True
                        break

                if not found_guard:
                    failures.append(
                        f"Line {i+1}: unconditional aiChat( found: {line.strip()}"
                    )

    if failures:
        print("FAIL: anwProbe() contains unconditional aiChat() calls:")
        for msg in failures:
            print(f"  {msg}")
        return False

    return True


def main():
    if not check_globals_flags():
        sys.exit(1)

    if not check_anwprobe_no_unconditional_aichat():
        sys.exit(1)

    print("PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
