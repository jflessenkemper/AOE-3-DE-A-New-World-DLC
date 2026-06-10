"""AST node dataclasses for the XS interpreter.

Tree-walked by interpreter.py. Kept minimal — only the concrete shapes the
evaluator needs to dispatch on. Source location is carried on every node
so runtime errors can point back at the .xs file.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Union


@dataclass
class Node:
    line: int = 0
    col: int = 0


# ---- expressions ----------------------------------------------------------

@dataclass
class IntLit(Node):
    value: int = 0

@dataclass
class FloatLit(Node):
    value: float = 0.0

@dataclass
class BoolLit(Node):
    value: bool = False

@dataclass
class StrLit(Node):
    value: str = ""

@dataclass
class VectorLit(Node):
    """vector(x, y, z) constructor."""
    x: "Expr" = None  # type: ignore
    y: "Expr" = None  # type: ignore
    z: "Expr" = None  # type: ignore

@dataclass
class Var(Node):
    name: str = ""

@dataclass
class Index(Node):
    target: "Expr" = None  # type: ignore
    index: "Expr" = None  # type: ignore

@dataclass
class Call(Node):
    name: str = ""
    args: list = field(default_factory=list)

@dataclass
class Unary(Node):
    op: str = ""
    operand: "Expr" = None  # type: ignore

@dataclass
class Binary(Node):
    op: str = ""
    left: "Expr" = None  # type: ignore
    right: "Expr" = None  # type: ignore

@dataclass
class Ternary(Node):
    cond: "Expr" = None  # type: ignore
    then: "Expr" = None  # type: ignore
    els: "Expr" = None   # type: ignore

@dataclass
class Assign(Node):
    op: str = "="
    target: "Expr" = None  # type: ignore
    value: "Expr" = None  # type: ignore


@dataclass
class LambdaExpr(Node):
    """Lambda / function-pointer literal:  []( params ) [-> return_type] { body }"""
    params: list = field(default_factory=list)   # list[Param]
    return_type: Optional[str] = None
    body: "Block" = None  # type: ignore


@dataclass
class MemberAccess(Node):
    """Member access: obj.field"""
    target: "Expr" = None  # type: ignore
    field: str = ""


Expr = Union[IntLit, FloatLit, BoolLit, StrLit, VectorLit, Var, Index, Call,
             Unary, Binary, Assign, "LambdaExpr", "MemberAccess"]


# ---- statements -----------------------------------------------------------

@dataclass
class VarDecl(Node):
    typ: str = ""
    name: str = ""
    init: Optional[Expr] = None
    is_const: bool = False

@dataclass
class ExprStmt(Node):
    expr: Expr = None  # type: ignore

@dataclass
class Block(Node):
    stmts: list = field(default_factory=list)

@dataclass
class If(Node):
    cond: Expr = None  # type: ignore
    then: Block = None  # type: ignore
    els: Optional[Block] = None

@dataclass
class While(Node):
    cond: Expr = None  # type: ignore
    body: Block = None  # type: ignore

@dataclass
class For(Node):
    var: str = ""
    start: Expr = None  # type: ignore
    end: Expr = None  # type: ignore
    body: Block = None  # type: ignore

@dataclass
class CForLoop(Node):
    init: Optional["Stmt"] = None    # VarDecl or ExprStmt
    cond: Optional["Expr"] = None
    step: Optional["Expr"] = None
    body: "Block" = None  # type: ignore

@dataclass
class SwitchCase(Node):
    value: Optional["Expr"] = None    # None = default
    body: "Block" = None  # type: ignore

@dataclass
class Switch(Node):
    expr: "Expr" = None  # type: ignore
    cases: list = field(default_factory=list)

@dataclass
class Return(Node):
    value: Optional[Expr] = None

@dataclass
class Break(Node):
    pass

@dataclass
class Continue(Node):
    pass


# ---- top level -----------------------------------------------------------

@dataclass
class Param:
    typ: str
    name: str
    default: Optional[Expr] = None

@dataclass
class FuncDef(Node):
    return_type: str = "void"
    name: str = ""
    params: list = field(default_factory=list)  # list[Param]
    body: Block = None  # type: ignore

@dataclass
class RuleDef(Node):
    name: str = ""
    active: bool = True              # `active` / `inactive`
    min_interval: float = 1.0        # seconds
    max_interval: Optional[float] = None
    high_frequency: bool = False
    run_immediately: bool = False
    priority: int = 0
    group: Optional[str] = None
    body: Block = None  # type: ignore

@dataclass
class Include(Node):
    path: str = ""

@dataclass
class ClassField(Node):
    """A field declaration inside a class body."""
    typ: str = ""
    name: str = ""
    init: Optional[Expr] = None

@dataclass
class ClassDef(Node):
    """class Name { fields* };"""
    name: str = ""
    fields: list = field(default_factory=list)  # list[ClassField]

@dataclass
class Program(Node):
    items: list = field(default_factory=list)  # mix of VarDecl/FuncDef/RuleDef/Include/ClassDef
