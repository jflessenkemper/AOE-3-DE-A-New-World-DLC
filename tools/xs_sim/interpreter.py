"""Tree-walking interpreter for XS, with a tick-based rule scheduler.

Execution model
---------------
1. Load Program(s). Each Include is resolved relative to a search root.
2. Top-level VarDecls evaluate to globals; FuncDefs register; RuleDefs
   register in the scheduler with their `active`/`minInterval` attrs.
3. If an `initLeader<X>()` function is defined, the harness calls it once.
   That call typically activates rules via xsEnableRule(...).
4. Scheduler.tick(dt) advances sim_time and fires every rule whose
   (now - last_fire) >= minInterval and whose active flag is True.

Vectors are 3-tuples; vector arithmetic is supported via Binary on tuples.
Type coercion follows XS-ish rules: int↔float promote, bool ⇄ int, string
concat works with `+` if either operand is a string.
"""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from . import ast_nodes as A
from .gamestate import GameState
from . import builtins as B
from .parser import parse


# ---- runtime control flow ---------------------------------------------

class _ReturnEx(Exception):
    def __init__(self, value): self.value = value
class _BreakEx(Exception): pass
class _ContinueEx(Exception): pass


class XSRuntimeError(Exception):
    pass


# Constants the engine pre-defines but the simulator can't otherwise see
# (declared in aiHeader.xs / engine, not always loaded by the harness).
_DEFAULT_CONSTS: dict[str, Any] = {
    "cAge0": 0, "cAge1": 1, "cAge2": 2, "cAge3": 3, "cAge4": 4, "cAge5": 5,
    "cResourceFood": 0, "cResourceWood": 1, "cResourceGold": 2, "cResourceXP": 3,
    "cMyID": 1, "cPlayerRelationAny": 0, "cPlayerRelationEnemy": 2,
    "cPlayerRelationAlly": 1, "cPlayerRelationSelf": 0,
    # Area type constants (P1 — explicit values override the c-prefix fallback
    # which would return 0 for all, colliding with cAreaTypeLand).
    "cAreaTypeLand": 0,
    "cAreaTypeWater": 1,
    "cAreaTypeImpassableLand": 2,
    "cAreaTypeCliff": 3,
    # Invalid vector sentinel used throughout wall-strategy code.
    "cInvalidVector": (-1.0, -1.0, -1.0),
}


# ---- scheduler --------------------------------------------------------

@dataclass
class _Rule:
    decl: A.RuleDef
    active: bool
    min_interval: float            # seconds
    last_fire: float = -1.0e18     # so runImmediately rules fire immediately
    priority: int = 0


# ---- interpreter ------------------------------------------------------

class Interpreter:
    def __init__(self, gs: Optional[GameState] = None,
                 search_paths: Optional[list[Path]] = None,
                 strict: bool = False):
        self.gs = gs or GameState()
        self.search_paths = list(search_paths or [])
        self.strict = strict

        # Globals, functions, rules
        self.globals: dict[str, Any] = dict(_DEFAULT_CONSTS)
        self.functions: dict[str, A.FuncDef] = {}
        self.rules: dict[str, _Rule] = {}

        # Loaded files (avoid #include cycles)
        self._loaded: set[Path] = set()

        # Per-rule context (set during fire())
        self.current_rule: Optional[str] = None

        # Diagnostics
        self.unknown_calls: dict[str, int] = {}
        self.fired_log: list[tuple[float, str]] = []   # (time, rule_name)

    # ---- loading ----

    def load_file(self, path: Path) -> None:
        path = path.resolve()
        if path in self._loaded:
            return
        self._loaded.add(path)
        src = path.read_text(encoding="utf-8", errors="ignore")
        prog = parse(src, str(path))
        self._install_program(prog, path.parent)

    def load_source(self, src: str, name: str = "<src>") -> None:
        prog = parse(src, name)
        self._install_program(prog, Path(".").resolve())

    def _install_program(self, prog: A.Program, base: Path) -> None:
        for item in prog.items:
            if isinstance(item, A.Include):
                self._resolve_include(item.path, base)
            elif isinstance(item, A.VarDecl):
                self.globals[item.name] = self._eval_init(item)
            elif isinstance(item, A.FuncDef):
                self.functions[item.name] = item
            elif isinstance(item, A.RuleDef):
                self.rules[item.name] = _Rule(
                    decl=item,
                    active=item.active,
                    min_interval=item.min_interval,
                    last_fire=(0.0 if item.run_immediately else -1.0e18),
                    priority=item.priority,
                )

    def _resolve_include(self, raw: str, base: Path) -> None:
        candidates = [base / raw] + [p / raw for p in self.search_paths]
        for c in candidates:
            if c.exists():
                self.load_file(c)
                return
        # Missing include — non-fatal; many leaders include shared headers
        # that the simulator doesn't need (full game's aiHeader.xs etc.).
        self.gs.log_echo(f"[include miss] {raw}")

    # ---- eval helpers ----

    def _default_for(self, typ: str) -> Any:
        return {
            "int": 0, "float": 0.0, "bool": False, "string": "",
            "vector": (0.0, 0.0, 0.0), "void": None,
        }.get(typ, 0)

    def _eval_init(self, decl: A.VarDecl) -> Any:
        if decl.init is None:
            return self._default_for(decl.typ)
        return self._eval(decl.init, self.globals)

    # ---- scheduler ----

    def call_init(self, name: str) -> None:
        """Call e.g. initLeaderNapoleon() once before ticking."""
        if name in self.functions:
            self._call_user(self.functions[name], [])

    def tick(self, dt: float) -> list[str]:
        """Advance sim time by dt seconds and fire eligible rules."""
        self.gs.sim_time_s += dt
        fired: list[str] = []
        # Fire highest-priority first; tie-break by registration order.
        order = sorted(
            self.rules.items(),
            key=lambda kv: (-kv[1].priority, kv[0]),
        )
        for rname, r in order:
            if not r.active:
                continue
            if (self.gs.sim_time_s - r.last_fire) < r.min_interval:
                continue
            r.last_fire = self.gs.sim_time_s
            self.current_rule = rname
            try:
                # Rules see globals directly (Var lookup falls through to
                # self.globals); only declarations inside the rule create
                # locals. Mirrors how the engine schedules rules.
                self._exec_block(r.decl.body, {})
            except _ReturnEx:
                pass
            except XSRuntimeError as e:
                self.gs.log_echo(f"[rule error: {rname}] {e}")
                if self.strict:
                    raise
            finally:
                self.current_rule = None
            fired.append(rname)
            self.fired_log.append((self.gs.sim_time_s, rname))
        return fired

    def run(self, total_seconds: float, dt: float = 1.0) -> None:
        steps = int(total_seconds / dt)
        for _ in range(steps):
            self.tick(dt)

    # Used by builtins.
    def set_rule_active(self, name: str, active: bool) -> None:
        if name in self.rules:
            self.rules[name].active = active

    def set_rule_min_interval(self, name: str, mi: float) -> None:
        if name in self.rules:
            self.rules[name].min_interval = mi

    # ---- statement execution ----

    def _exec_block(self, block: A.Block, env: dict) -> None:
        # Locals shadow globals: stmts may declare new names; we treat env
        # as a flat scope chain (block-scoped XS isn't strict about this).
        for s in block.stmts:
            self._exec(s, env)

    def _exec(self, s, env: dict) -> None:
        if isinstance(s, A.VarDecl):
            env[s.name] = self._eval(s.init, env) if s.init is not None else self._default_for(s.typ)
            return
        if isinstance(s, A.ExprStmt):
            self._eval(s.expr, env)
            return
        if isinstance(s, A.Block):
            self._exec_block(s, env)
            return
        if isinstance(s, A.If):
            if self._truthy(self._eval(s.cond, env)):
                self._exec_block(s.then, env)
            elif s.els is not None:
                self._exec_block(s.els, env)
            return
        if isinstance(s, A.While):
            while self._truthy(self._eval(s.cond, env)):
                try:
                    self._exec_block(s.body, env)
                except _BreakEx:
                    break
                except _ContinueEx:
                    continue
            return
        if isinstance(s, A.For):
            start = int(self._eval(s.start, env))
            end = int(self._eval(s.end, env))
            for i in range(start, end):
                env[s.var] = i
                try:
                    self._exec_block(s.body, env)
                except _BreakEx:
                    break
                except _ContinueEx:
                    continue
            return
        if isinstance(s, A.CForLoop):
            if s.init is not None:
                self._exec(s.init, env)
            while True:
                if s.cond is not None and not self._truthy(self._eval(s.cond, env)):
                    break
                try:
                    self._exec_block(s.body, env)
                except _BreakEx:
                    break
                except _ContinueEx:
                    pass
                if s.step is not None:
                    self._eval(s.step, env)
            return
        if isinstance(s, A.Switch):
            v = self._eval(s.expr, env)
            matched = False
            for c in s.cases:
                if matched or c.value is None or self._eval(c.value, env) == v:
                    matched = True
                    try:
                        self._exec_block(c.body, env)
                    except _BreakEx:
                        return
            return
        if isinstance(s, A.Return):
            raise _ReturnEx(self._eval(s.value, env) if s.value is not None else None)
        if isinstance(s, A.Break):
            raise _BreakEx()
        if isinstance(s, A.Continue):
            raise _ContinueEx()
        raise XSRuntimeError(f"unknown stmt {type(s).__name__}")

    # ---- expression evaluation ----

    def _eval(self, e, env: dict) -> Any:
        if isinstance(e, A.IntLit):   return e.value
        if isinstance(e, A.FloatLit): return e.value
        if isinstance(e, A.BoolLit):  return e.value
        if isinstance(e, A.StrLit):   return e.value
        if isinstance(e, A.VectorLit):
            return (float(self._eval(e.x, env)),
                    float(self._eval(e.y, env)),
                    float(self._eval(e.z, env)))

        if isinstance(e, A.Var):
            if e.name in env: return env[e.name]
            if e.name in self.globals: return self.globals[e.name]
            # Common pattern: leader files reference c-prefixed enum constants
            # (cAge1, cResourceFood, …) declared in headers we didn't load.
            # Treat undefined identifiers starting with "c" + UpperCase as 0
            # to keep the rule body executable.
            if e.name.startswith("c") and len(e.name) > 1 and e.name[1].isupper():
                return 0
            if self.strict:
                raise XSRuntimeError(f"undefined variable {e.name!r} at {e.line}:{e.col}")
            return 0

        if isinstance(e, A.Index):
            arr = self._eval(e.target, env); idx = int(self._eval(e.index, env))
            if hasattr(arr, "data"):  # XSArray
                return arr.data[idx] if 0 <= idx < len(arr.data) else 0
            if isinstance(arr, (list, tuple)) and 0 <= idx < len(arr):
                return arr[idx]
            return 0

        if isinstance(e, A.Call):
            args = [self._eval(a, env) for a in e.args]
            if e.name in self.functions:
                return self._call_user(self.functions[e.name], args)
            return B.call_builtin(e.name, args, self.gs, self)

        if isinstance(e, A.Ternary):
            return (self._eval(e.then, env) if self._truthy(self._eval(e.cond, env))
                    else self._eval(e.els, env))

        if isinstance(e, A.Unary):
            v = self._eval(e.operand, env)
            if e.op == "-": return -v
            if e.op == "+": return +v
            if e.op == "!": return not self._truthy(v)
            if e.op == "~": return ~int(v)
            raise XSRuntimeError(f"bad unary {e.op}")

        if isinstance(e, A.Binary):
            # Short-circuit logicals
            if e.op == "&&":
                lv = self._eval(e.left, env)
                return self._truthy(lv) and self._truthy(self._eval(e.right, env))
            if e.op == "||":
                lv = self._eval(e.left, env)
                return self._truthy(lv) or self._truthy(self._eval(e.right, env))
            lv = self._eval(e.left, env); rv = self._eval(e.right, env)
            return self._binop(e.op, lv, rv)

        if isinstance(e, A.Assign):
            val = self._eval(e.value, env)
            tgt = e.target
            if isinstance(tgt, A.Var):
                cur = env.get(tgt.name, self.globals.get(tgt.name))
                if e.op != "=":
                    val = self._binop(e.op[:-1], cur if cur is not None else 0, val)
                if tgt.name in env:
                    env[tgt.name] = val
                else:
                    # Unknown name: promote to global. Real XS requires
                    # declarations, but headers like aiHeader.xs aren't
                    # always loaded by the harness — promoting here lets
                    # tests observe the effective doctrine state.
                    self.globals[tgt.name] = val
                return val
            if isinstance(tgt, A.Index):
                arr = self._eval(tgt.target, env)
                idx = int(self._eval(tgt.index, env))
                if hasattr(arr, "data") and 0 <= idx < len(arr.data):
                    if e.op != "=":
                        val = self._binop(e.op[:-1], arr.data[idx], val)
                    arr.data[idx] = val
                return val
            raise XSRuntimeError("invalid assignment target")

        raise XSRuntimeError(f"unknown expr {type(e).__name__}")

    # ---- helpers ----

    @staticmethod
    def _truthy(v: Any) -> bool:
        if isinstance(v, bool): return v
        if isinstance(v, (int, float)): return v != 0
        if isinstance(v, str): return len(v) > 0
        return v is not None

    @staticmethod
    def _binop(op: str, a: Any, b: Any) -> Any:
        # Vector arithmetic: XS supports vec+vec, vec-vec, vec*scalar, scalar*vec,
        # vec/scalar, and vec==vec comparisons. Tuples represent vectors.
        a_is_vec = isinstance(a, tuple)
        b_is_vec = isinstance(b, tuple)
        if a_is_vec or b_is_vec:
            if op == "+":
                if a_is_vec and b_is_vec:
                    return (a[0]+b[0], a[1]+b[1], a[2]+b[2])
                if a_is_vec:
                    s = float(b)
                    return (a[0]+s, a[1]+s, a[2]+s)
                s = float(a)
                return (s+b[0], s+b[1], s+b[2])
            if op == "-":
                if a_is_vec and b_is_vec:
                    return (a[0]-b[0], a[1]-b[1], a[2]-b[2])
                if a_is_vec:
                    s = float(b)
                    return (a[0]-s, a[1]-s, a[2]-s)
                s = float(a)
                return (s-b[0], s-b[1], s-b[2])
            if op == "*":
                if a_is_vec and not b_is_vec:
                    s = float(b)
                    return (a[0]*s, a[1]*s, a[2]*s)
                if b_is_vec and not a_is_vec:
                    s = float(a)
                    return (s*b[0], s*b[1], s*b[2])
                # vec*vec (dot product in some contexts) — return scalar
                if a_is_vec and b_is_vec:
                    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]
            if op == "/":
                if a_is_vec and not b_is_vec:
                    s = float(b)
                    return (a[0]/s, a[1]/s, a[2]/s) if s != 0 else (0.0, 0.0, 0.0)
            if op == "==": return a == b
            if op == "!=": return a != b
            # Fallthrough for unknown vector ops — return 0 rather than crash
            return 0
        if op == "+":
            if isinstance(a, str) or isinstance(b, str):
                return str(a) + str(b)
            return a + b
        if op == "-": return a - b
        if op == "*": return a * b
        if op == "/":
            if isinstance(a, int) and isinstance(b, int) and b != 0:
                return a // b if (a % b == 0) else a / b
            return a / b if b != 0 else 0
        if op == "%": return a % b if b != 0 else 0
        if op == "&": return int(a) & int(b)
        if op == "|": return int(a) | int(b)
        if op == "^": return int(a) ^ int(b)
        if op == "==": return a == b
        if op == "!=": return a != b
        if op == "<":  return a < b
        if op == "<=": return a <= b
        if op == ">":  return a > b
        if op == ">=": return a >= b
        raise XSRuntimeError(f"bad binop {op}")

    def _call_user(self, fn: A.FuncDef, args: list) -> Any:
        env: dict[str, Any] = {}
        for i, p in enumerate(fn.params):
            if p.typ == "void":
                continue
            if i < len(args):
                env[p.name] = args[i]
            elif p.default is not None:
                env[p.name] = self._eval(p.default, self.globals)
            else:
                env[p.name] = self._default_for(p.typ)
        try:
            self._exec_block(fn.body, env)
        except _ReturnEx as r:
            return r.value
        return None
