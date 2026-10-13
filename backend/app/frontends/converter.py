"""Unified multi-language to C source-to-source converter.

Routes C, C++, Python, and Java inputs through their respective hand-written frontends,
translating into shared Node IR and emitting compilable C text.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional

from app.engine.lexer import tokenize, LexerError
from app.engine.c_parser import parse_c, ParseResult
from app.codegen.c_codegen import generate_c
from app.frontends.py_lexer import tokenize_python, PyLexerError
from app.frontends.py_parser import parse_python, PySyntaxError
from app.frontends.py_to_ir import python_to_ir
from app.frontends.java_lexer import tokenize_java, JavaLexerError
from app.frontends.java_parser import parse_java, JavaSyntaxError
from app.frontends.java_to_ir import java_to_ir
from app.engine.ast_nodes import Node


@dataclass
class ConversionResult:
    c_source: str
    diagnostics: List[str] = field(default_factory=list)
    success: bool = True
    ir: Optional[Node] = None


def convert_to_c(language: str, source: str) -> ConversionResult:
    lang = language.lower().strip()

    if lang in ("c", "cpp", "c++"):
        try:
            parse_res: ParseResult = parse_c(source)
            if parse_res.errors:
                return ConversionResult(c_source=source, diagnostics=parse_res.errors, success=False)
            c_code = generate_c(parse_res.ast)
            return ConversionResult(c_source=c_code, ir=parse_res.ast, success=True)
        except Exception as e:
            return ConversionResult(c_source="", diagnostics=[str(e)], success=False)

    elif lang in ("python", "py"):
        try:
            py_ast = parse_python(source)
            ir = python_to_ir(py_ast)
            c_code = generate_c(ir)
            return ConversionResult(c_source=c_code, ir=ir, success=True)
        except (PyLexerError, PySyntaxError) as e:
            return ConversionResult(c_source="", diagnostics=[str(e)], success=False)
        except Exception as e:
            return ConversionResult(c_source="", diagnostics=[f"Python conversion error: {str(e)}"], success=False)

    elif lang in ("java",):
        try:
            j_ast = parse_java(source)
            ir = java_to_ir(j_ast)
            c_code = generate_c(ir)
            return ConversionResult(c_source=c_code, ir=ir, success=True)
        except (JavaLexerError, JavaSyntaxError) as e:
            return ConversionResult(c_source="", diagnostics=[str(e)], success=False)
        except Exception as e:
            return ConversionResult(c_source="", diagnostics=[f"Java conversion error: {str(e)}"], success=False)

    else:
        return ConversionResult(
            c_source="",
            diagnostics=[f"Unsupported language '{language}'. Supported: c, cpp, python, java"],
            success=False,
        )
