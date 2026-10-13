# CodeGuard Limitations & Supported Language Boundaries

CodeGuard is built as a compiler design demonstration platform featuring hand-written scanners, parsers, and transformers. To remain strictly hand-crafted, focused, and maintainable, specific language constructs are intentionally constrained.

---

## 1. C and C++ Limitations

- **Preprocessor**: `#define` macro expansion with arguments is not evaluated; macros are preserved or treated as single preprocessor tokens.
- **Complex C++ OOP**: Classes, virtual dispatch, operator overloading, and template metaprogramming are not lowered. The C parser includes resilience for basic C++ (namespace directives, references in parameters, range-based for, and `cin`/`cout`), but complex classes recover as `Unknown` nodes.
- **Bitfields & Unaligned Types**: Struct bitfields (`int a:4;`) and union layout tags are not analyzed.

---

## 2. Python Subset Limitations

- **Mandatory Static Type Hints**: Translating dynamically typed Python into static C requires explicit types on all function signatures (`def f(x: int) -> int:`). Code without type annotations triggers clear compiler diagnostics indicating the line and recommended annotation.
- **Dynamic Data Structures**: Dynamic arrays (`list.append()`), dictionaries (`dict`), and sets (`set`) are unsupported. Fixed-size lists (`[1, 2, 3]` or `list[int]`) are supported and lowered directly to static C arrays.
- **Object-Oriented & Meta-Programming**: Classes, inheritance, decorators, generators (`yield`), list comprehensions, `*args/**kwargs`, and `lambda` expressions produce actionable diagnostics.
- **Exceptions**: `try...except...finally` blocks are unsupported.
- **Imports**: Only the standard `math` module is supported for numeric functions.

---

## 3. Java Subset Limitations

- **Object-Oriented Architecture**: Only `public static` methods and the standard `public static void main(String[] args)` entrypoint are translated. Object instantiation (except `Scanner` and arrays) is unsupported.
- **Inheritance & Interfaces**: Class inheritance (`extends`) and interface implementation (`implements`) produce diagnostics.
- **Generics & Collections**: `List<T>`, `ArrayList`, `HashMap`, and stream pipelines (`.stream().map()`) are unsupported. Primitives, `String`, and 1D/2D arrays (`int[]`, `int[][]`) are supported.
- **Exceptions**: `try...catch...finally` and `throws` clauses produce diagnostics.

---

## 4. Execution Sandbox

- **Local Fallback Mode**: The local fallback runner applies `resource.setrlimit` (CPU time limit, file size limits) on Unix/macOS systems, but cannot fully isolate the root filesystem without root capabilities. Production deployments should always use the provided Docker container (`codeguard-sandbox`).
