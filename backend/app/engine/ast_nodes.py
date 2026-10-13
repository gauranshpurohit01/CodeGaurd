"""Shared Abstract Syntax Tree (AST) node representations for CodeGuard.

All language frontends (C, C++, Python, Java) produce or map into this shared Node IR.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, List, Optional, Union


@dataclass
class Node:
    kind: str
    value: Optional[Union[str, int, float, bool]] = None
    children: List["Node"] = field(default_factory=list)
    line: int = 1
    col: int = 1

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "kind": self.kind,
            "line": self.line,
            "col": self.col,
        }
        if self.value is not None:
            result["value"] = self.value
        if self.children:
            result["children"] = [child.to_dict() for child in self.children]
        return result

    def pretty(self, indent: int = 0) -> str:
        pad = "  " * indent
        val_str = f" [{self.value}]" if self.value is not None else ""
        lines = [f"{pad}{self.kind}{val_str} (L{self.line}:C{self.col})"]
        for child in self.children:
            lines.append(child.pretty(indent + 1))
        return "\n".join(lines)

    def count_nodes(self) -> int:
        return 1 + sum(child.count_nodes() for child in self.children)

    def clone(self) -> "Node":
        return Node(
            kind=self.kind,
            value=self.value,
            children=[child.clone() for child in self.children],
            line=self.line,
            col=self.col,
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Node):
            return False
        return (
            self.kind == other.kind
            and self.value == other.value
            and len(self.children) == len(other.children)
            and all(c1 == c2 for c1, c2 in zip(self.children, other.children))
        )
