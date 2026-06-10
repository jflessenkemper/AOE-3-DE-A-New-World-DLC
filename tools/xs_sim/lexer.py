"""XS tokenizer.

XS is a C-like language: keywords, identifiers, numbers, strings, operators,
and #include directives. Comments are // line and /* block */.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterator

KEYWORDS = {
    "void", "int", "float", "bool", "string", "vector",
    "if", "else", "while", "for", "return", "break", "continue",
    "switch", "case", "default",
    "true", "false",
    "rule", "active", "inactive", "minInterval", "maxInterval",
    "highFrequency", "runImmediately", "priority", "group",
    "const", "static", "extern", "mutable",
    "class",
}

# Multi-char operators must come first (longest match).
OPS = [
    "==", "!=", "<=", ">=", "&&", "||", "<<=", ">>=", "<<", ">>",
    "->",  # lambda arrow: []() -> bool { ... }
    "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=",
    "++", "--",
    "&", "|", "^", "~",
    "<", ">", "+", "-", "*", "/", "%", "=", "!",
    "?", ":",
    "(", ")", "{", "}", "[", "]", ",", ";", ".",
]


@dataclass
class Token:
    kind: str            # "kw", "id", "int", "float", "str", "op", "include", "eof"
    value: str
    line: int
    col: int

    def __repr__(self) -> str:
        return f"Token({self.kind}, {self.value!r}, {self.line}:{self.col})"


class LexError(Exception):
    pass


def tokenize(src: str, filename: str = "<src>") -> list[Token]:
    toks: list[Token] = []
    i, n = 0, len(src)
    line, col = 1, 1

    def advance(k: int = 1) -> None:
        nonlocal i, line, col
        for _ in range(k):
            if i < n and src[i] == "\n":
                line += 1
                col = 1
            else:
                col += 1
            i += 1

    while i < n:
        c = src[i]

        # Whitespace
        if c in " \t\r\n":
            advance()
            continue

        # Line comment
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            while i < n and src[i] != "\n":
                advance()
            continue

        # Block comment
        if c == "/" and i + 1 < n and src[i + 1] == "*":
            advance(2)
            while i < n and not (src[i] == "*" and i + 1 < n and src[i + 1] == "/"):
                advance()
            if i < n:
                advance(2)
            continue

        # #include "file.xs"
        if c == "#":
            start_line, start_col = line, col
            advance()
            # read directive name
            j = i
            while j < n and src[j].isalpha():
                j += 1
            directive = src[i:j]
            advance(j - i)
            if directive != "include":
                raise LexError(f"{filename}:{line}:{col} unknown directive #{directive}")
            # skip ws
            while i < n and src[i] in " \t":
                advance()
            if i >= n or src[i] != '"':
                raise LexError(f"{filename}:{line}:{col} expected \"…\" after #include")
            advance()  # opening quote
            start = i
            while i < n and src[i] != '"' and src[i] != "\n":
                advance()
            path = src[start:i]
            if i >= n or src[i] != '"':
                raise LexError(f"{filename}:{start_line}:{start_col} unterminated #include path")
            advance()  # closing quote
            toks.append(Token("include", path, start_line, start_col))
            continue

        # Identifier / keyword
        if c.isalpha() or c == "_":
            start_line, start_col = line, col
            j = i
            while j < n and (src[j].isalnum() or src[j] == "_"):
                j += 1
            word = src[i:j]
            advance(j - i)
            if word in KEYWORDS:
                toks.append(Token("kw", word, start_line, start_col))
            else:
                toks.append(Token("id", word, start_line, start_col))
            continue

        # Number
        if c.isdigit() or (c == "." and i + 1 < n and src[i + 1].isdigit()):
            start_line, start_col = line, col
            j = i
            saw_dot = False
            while j < n and (src[j].isdigit() or (src[j] == "." and not saw_dot)):
                if src[j] == ".":
                    saw_dot = True
                j += 1
            num = src[i:j]
            advance(j - i)
            toks.append(Token("float" if saw_dot else "int", num, start_line, start_col))
            continue

        # String
        if c == '"':
            start_line, start_col = line, col
            advance()
            buf = []
            while i < n and src[i] != '"':
                if src[i] == "\\" and i + 1 < n:
                    nxt = src[i + 1]
                    buf.append({"n": "\n", "t": "\t", "r": "\r",
                                "\\": "\\", '"': '"'}.get(nxt, nxt))
                    advance(2)
                else:
                    buf.append(src[i])
                    advance()
            if i >= n:
                raise LexError(f"{filename}:{start_line}:{start_col} unterminated string")
            advance()  # closing quote
            toks.append(Token("str", "".join(buf), start_line, start_col))
            continue

        # Operator (longest-match)
        matched = False
        for op in OPS:
            if src.startswith(op, i):
                toks.append(Token("op", op, line, col))
                advance(len(op))
                matched = True
                break
        if matched:
            continue

        raise LexError(f"{filename}:{line}:{col} unexpected character {c!r}")

    toks.append(Token("eof", "", line, col))
    return toks
