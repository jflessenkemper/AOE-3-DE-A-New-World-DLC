"""XS builtin functions — mock implementations.

Three flavors:
  • Pure stdlib (xsArrayCreate, xsVectorSet, sqrt, …): real implementations.
  • Game queries (kbGetAge, aiGetMilitaryUnitCount, …): read from GameState.
  • Game commands (aiTaskUnitWork, xsEnableRule, …): record into GameState
    and/or mutate scheduler state via the Interpreter handle passed in.

Unknown builtins return a typed zero rather than raising — XS code calls
several thousand functions across the codebase and we'd rather warn-once
than crash mid-rule.
"""
from __future__ import annotations
import math
from typing import Any, Callable

from .gamestate import GameState


# ---- Generic helpers ---------------------------------------------------

def _zero_for(name: str) -> Any:
    """Default return for an unknown builtin — pick by naming convention."""
    n = name.lower()
    if n.startswith(("kbget", "aiget", "xsget")):
        if "name" in n or "string" in n:
            return ""
        return 0
    if n.startswith(("kbis", "aiis", "kbcan", "aican", "xsis")):
        return False
    return 0


# ---- xs* stdlib --------------------------------------------------------

class XSArray:
    __slots__ = ("data",)
    def __init__(self, n: int, default):
        self.data = [default] * n


def _xsArrayCreateInt(args, gs, interp):
    n = int(args[0]); default = int(args[1]) if len(args) > 1 else 0
    return XSArray(n, default)

def _xsArrayCreateFloat(args, gs, interp):
    n = int(args[0]); default = float(args[1]) if len(args) > 1 else 0.0
    return XSArray(n, default)

def _xsArrayCreateBool(args, gs, interp):
    n = int(args[0]); default = bool(args[1]) if len(args) > 1 else False
    return XSArray(n, default)

def _xsArrayCreateString(args, gs, interp):
    n = int(args[0]); default = str(args[1]) if len(args) > 1 else ""
    return XSArray(n, default)

def _xsArraySet(args, gs, interp):
    arr, idx, val = args[0], int(args[1]), args[2]
    if isinstance(arr, XSArray) and 0 <= idx < len(arr.data):
        arr.data[idx] = val
    return 0

def _xsArrayGet(args, gs, interp):
    arr, idx = args[0], int(args[1])
    if isinstance(arr, XSArray) and 0 <= idx < len(arr.data):
        return arr.data[idx]
    return 0

def _xsArrayGetSize(args, gs, interp):
    arr = args[0]
    return len(arr.data) if isinstance(arr, XSArray) else 0


# ---- Rule control (interpreter-level) ----------------------------------

def _xsEnableRule(args, gs, interp):
    interp.set_rule_active(args[0], True)
    return 0

def _xsDisableRule(args, gs, interp):
    interp.set_rule_active(args[0], False)
    return 0

def _xsEnableSelf(args, gs, interp):
    if interp.current_rule:
        interp.set_rule_active(interp.current_rule, True)
    return 0

def _xsDisableSelf(args, gs, interp):
    if interp.current_rule:
        interp.set_rule_active(interp.current_rule, False)
    return 0

def _xsSetRuleMinIntervalSelf(args, gs, interp):
    if interp.current_rule:
        interp.set_rule_min_interval(interp.current_rule, float(args[0]))
    return 0

def _xsGetTime(args, gs, interp):
    return gs.sim_time_s * 1000.0     # ms

def _xsGetTimeSec(args, gs, interp):
    return gs.sim_time_s


# ---- Echo / chat -------------------------------------------------------

def _aiEcho(args, gs, interp):
    msg = " ".join(str(a) for a in args)
    gs.log_echo(msg)
    return 0

def _aiChat(args, gs, interp):
    # aiChat(targetID, msg)
    msg = args[1] if len(args) > 1 else (args[0] if args else "")
    gs.log_echo(f"[chat] {msg}")
    return 0


# ---- kb* queries -------------------------------------------------------

def _kbGetAge(args, gs, interp):       return gs.age
def _kbGetCiv(args, gs, interp):       return gs.civ_name
def _kbGetCivName(args, gs, interp):   return gs.civ_name
def _kbGetPlayerID(args, gs, interp):  return gs.player_id
def _kbGetPop(args, gs, interp):       return gs.pop
def _kbGetPopCap(args, gs, interp):    return gs.pop_cap

# Revolution civ check — key for the aggregator dispatch in
# leader_revolution_commanders.xs / leader_revolution_support.xs.
def _civIsRevolution(args, gs, interp): return gs.is_revolution

def _kbResourceGet(args, gs, interp):
    # kbResourceGet(cResourceFood) — args[0] is the resource enum int
    r = int(args[0])
    return [gs.food, gs.wood, gs.gold, gs.xp][r] if 0 <= r < 4 else 0


# ---- aiGet / aiIs ------------------------------------------------------

def _aiGetMilitaryUnitCount(args, gs, interp):
    return gs.counts.get("infantry", 0) + gs.counts.get("cavalry", 0) + gs.counts.get("artillery", 0)

def _aiGetEconomyUnitCount(args, gs, interp):
    return gs.counts.get("settler", 0)

def _aiGetWorldDifficulty(args, gs, interp):
    return gs.difficulty


# ---- aiTask / aiCommand (action recorders) -----------------------------

def _record(name: str):
    def fn(args, gs, interp):
        gs.log_action(name, tuple(args))
        return 0
    return fn


# ---- registry ----------------------------------------------------------

BUILTINS: dict[str, Callable] = {
    # array stdlib
    "xsArrayCreateInt":    _xsArrayCreateInt,
    "xsArrayCreateFloat":  _xsArrayCreateFloat,
    "xsArrayCreateBool":   _xsArrayCreateBool,
    "xsArrayCreateString": _xsArrayCreateString,
    "xsArraySetInt":    _xsArraySet, "xsArrayGetInt":    _xsArrayGet,
    "xsArraySetFloat":  _xsArraySet, "xsArrayGetFloat":  _xsArrayGet,
    "xsArraySetBool":   _xsArraySet, "xsArrayGetBool":   _xsArrayGet,
    "xsArraySetString": _xsArraySet, "xsArrayGetString": _xsArrayGet,
    "xsArrayGetSize":   _xsArrayGetSize,

    # rule control
    "xsEnableRule":  _xsEnableRule,
    "xsDisableRule": _xsDisableRule,
    "xsEnableSelf":  _xsEnableSelf,
    "xsDisableSelf": _xsDisableSelf,
    "xsSetRuleMinIntervalSelf": _xsSetRuleMinIntervalSelf,
    "xsGetTime":     _xsGetTime,
    "xsGetTimeSec":  _xsGetTimeSec,

    # math
    "sqrt":  lambda a, gs, i: math.sqrt(float(a[0])),
    "abs":   lambda a, gs, i: abs(a[0]),
    "min":   lambda a, gs, i: min(a),
    "max":   lambda a, gs, i: max(a),
    "floor": lambda a, gs, i: math.floor(float(a[0])),
    "ceil":  lambda a, gs, i: math.ceil(float(a[0])),
    "sin":   lambda a, gs, i: math.sin(float(a[0])),
    "cos":   lambda a, gs, i: math.cos(float(a[0])),

    # echo / chat
    "aiEcho":           _aiEcho,
    "aiChat":           _aiChat,
    "aiChatToAll":      _aiEcho,
    "aiChatToAllies":   _aiEcho,
    "aiChatToPlayer":   _aiChat,
    "xsChatData":       _aiEcho,

    # kb queries
    "kbGetAge":         _kbGetAge,
    "kbGetCiv":         _kbGetCiv,
    "kbGetCivName":     _kbGetCivName,
    "kbGetPlayerID":    _kbGetPlayerID,
    "kbGetPop":         _kbGetPop,
    "kbGetPopCap":      _kbGetPopCap,
    "kbResourceGet":    _kbResourceGet,

    # revolution check
    "civIsRevolution":  _civIsRevolution,

    # ai queries
    "aiGetMilitaryUnitCount": _aiGetMilitaryUnitCount,
    "aiGetEconomyUnitCount":  _aiGetEconomyUnitCount,
    "aiGetWorldDifficulty":   _aiGetWorldDifficulty,
}

# Wildcard recorders for action verbs.
for verb in (
    "aiTaskUnitWork", "aiTaskUnitMove", "aiTaskUnitBuild", "aiTaskUnitGather",
    "aiPlanCreate", "aiPlanDestroy", "aiPlanSetActive",
    "aiCommandUnit", "aiTrainUnit",
):
    BUILTINS.setdefault(verb, _record(verb))


def call_builtin(name: str, args: list, gs: GameState, interp) -> Any:
    fn = BUILTINS.get(name)
    if fn is not None:
        return fn(args, gs, interp)
    # Unknown — record and return zero. Track once so output isn't spammed.
    interp.unknown_calls.setdefault(name, 0)
    interp.unknown_calls[name] += 1
    return _zero_for(name)
