# CodeGuard Architecture Specification

CodeGuard is an end-to-end compiler construction and plagiarism detection platform built without external parser generators (no ANTLR, Tree-Sitter, libclang, or Python `ast`). All lexers, parsers, canonicalization transforms, IR representations, and code generators are hand-crafted.

---

## 1. System Architecture

```mermaid
flowchart TD
    subgraph Frontends ["Hand-Written Language Frontends"]
        CSrc["C / C++ Source"] --> CLexer["C Lexer (lexer.py)"]
        CLexer --> CParser["C Recursive-Descent Parser (c_parser.py)"]
        
        PySrc["Typed Python Source"] --> PyLexer["Python Lexer with Indent Stack (py_lexer.py)"]
        PyLexer --> PyParser["Python Parser (py_parser.py)"]
        PyParser --> PyIR["Python to IR Lowering (py_to_ir.py)"]
        
        JavaSrc["Java Source"] --> JavaLexer["Java Lexer (java_lexer.py)"]
        JavaLexer --> JavaParser["Java Parser (java_parser.py)"]
        JavaParser --> JavaIR["Java to IR Lowering (java_to_ir.py)"]
    end

    subgraph IR ["Shared Representation & Canonicalization"]
        CParser --> SharedIR["Shared Node IR (ast_nodes.py)"]
        PyIR --> SharedIR
        JavaIR --> SharedIR
        SharedIR --> Normalizer["AST Canonicalization (ast_normalize.py)"]
    end

    subgraph Codegen ["Code Generation & Sandbox"]
        SharedIR --> CCodegen["C Code Generator (c_codegen.py)"]
        CCodegen --> Sandbox["Sandbox Execution (sandbox.py)"]
    end

    subgraph PlagiarismEngine ["Dual-Level Plagiarism Engine"]
        CLexer --> Winnowing["Token Winnowing Engine (winnowing.py)"]
        Normalizer --> TreeAlign["Tree Alignment DP (ast_similarity.py)"]
        Normalizer --> MerkleSubtrees["Merkle Subtree Hashing (ast_similarity.py)"]
        Winnowing --> Report["Plagiarism Report (report.py)"]
        TreeAlign --> Report
        MerkleSubtrees --> Report
    end
```

---

## 2. Core Modules

| Module | Location | Responsibility |
| :--- | :--- | :--- |
| **`ast_nodes.py`** | `backend/app/engine/` | Universal AST `Node(kind, value, children, line, col)` IR. |
| **`lexer.py`** | `backend/app/engine/` | Hand-written character scanner for C/C++ with token normalization. |
| **`winnowing.py`** | `backend/app/engine/` | Process-independent FNV-1a hashing & polynomial rolling hash ($K=5, W=4$). |
| **`c_parser.py`** | `backend/app/engine/` | Recursive-descent C parser with statement-boundary error recovery & C++ tolerance. |
| **`c_expr_parser.py`** | `backend/app/engine/` | Full C expression precedence climbing and postfix/primary parsing. |
| **`ast_normalize.py`** | `backend/app/engine/` | Semantic canonicalization pass (unifies loops, desugars operators, sorts commutative ops). |
| **`ast_similarity.py`** | `backend/app/engine/` | Weighted tree alignment DP (Dice) & Merkle subtree hashing with size guard. |
| **`report.py`** | `backend/app/engine/` | Consolidated dual-level plagiarism report and verdict calculator. |
| **`py_lexer.py`** | `backend/app/frontends/` | Indentation-aware scanner emitting INDENT, DEDENT, NEWLINE tokens. |
| **`py_parser.py`** | `backend/app/frontends/` | Enforces mandatory static type hints and parses typed Python subset. |
| **`py_to_ir.py`** | `backend/app/frontends/` | Lowers typed Python into shared Node IR with local type inference. |
| **`java_lexer.py`** | `backend/app/frontends/` | Hand-written Java scanner. |
| **`java_parser.py`** | `backend/app/frontends/` | Recursive-descent Java parser isolating static methods and control flow. |
| **`java_to_ir.py`** | `backend/app/frontends/` | Translates Java static methods, `System.out.println`, and `Math` calls to C IR. |
| **`c_codegen.py`** | `backend/app/codegen/` | Pretty-prints shared IR into valid, compilable C source code. |
| **`sandbox.py`** | `backend/app/execution/` | Resource-constrained runner (Docker sandbox + local `setrlimit` fallback). |
| **`signature_extractor.py`** | `backend/app/retrieval/` | Shannon-entropy & AST-guided signature token extractor. |
| **`web_retriever.py`** | `backend/app/retrieval/` | GitHub REST Code Search API client with in-memory decoding and SQLite caching. |
| **`web_plagiarism_runner.py`** | `backend/app/retrieval/` | Background multi-threaded pipeline comparing query against web candidates. |

---

## 3. Formal Grammars (EBNF Subsets)

### 3.1 C Grammar Subset
```ebnf
TranslationUnit ::= { ExternalDeclaration } ;
ExternalDeclaration ::= FunctionDef | FunctionDecl | VarDecl ;
FunctionDef ::= TypeSpecifier IDENTIFIER "(" [ ParameterList ] ")" Block ;
FunctionDecl ::= TypeSpecifier IDENTIFIER "(" [ ParameterList ] ")" ";" ;
ParameterList ::= Parameter { "," Parameter } ;
Parameter ::= TypeSpecifier [ IDENTIFIER [ "[" "]" ] ] ;
TypeSpecifier ::= { TypeQualifier } ( PrimitiveType | StructType | IDENTIFIER ) { "*" | "&" } ;
Block ::= "{" { Statement } "}" ;
Statement ::= Block
            | VarDecl
            | "if" "(" Expression ")" Statement [ "else" Statement ]
            | "while" "(" Expression ")" Statement
            | "for" "(" [ ForInit ] ";" [ Expression ] ";" [ Expression ] ")" Statement
            | "do" Statement "while" "(" Expression ")" ";"
            | "switch" "(" Expression ")" Statement
            | "case" Expression ":"
            | "default" ":"
            | "break" ";" | "continue" ";"
            | "return" [ Expression ] ";"
            | Expression ";" ;
Expression ::= AssignmentExpr ;
AssignmentExpr ::= TernaryExpr [ ( "=" | "+=" | "-=" | "*=" | "/=" | "%=" ) AssignmentExpr ] ;
TernaryExpr ::= LogicalOrExpr [ "?" Expression ":" TernaryExpr ] ;
LogicalOrExpr ::= LogicalAndExpr { "||" LogicalAndExpr } ;
LogicalAndExpr ::= BitwiseOrExpr { "&&" BitwiseOrExpr } ;
BitwiseOrExpr ::= BitwiseXorExpr { "|" BitwiseXorExpr } ;
BitwiseXorExpr ::= BitwiseAndExpr { "^" BitwiseAndExpr } ;
BitwiseAndExpr ::= EqualityExpr { "&" EqualityExpr } ;
EqualityExpr ::= RelationalExpr { ( "==" | "!=" ) RelationalExpr } ;
RelationalExpr ::= ShiftExpr { ( "<" | "<=" | ">" | ">=" ) ShiftExpr } ;
ShiftExpr ::= AdditiveExpr { ( "<<" | ">>" ) AdditiveExpr } ;
AdditiveExpr ::= MultiplicativeExpr { ( "+" | "-" ) MultiplicativeExpr } ;
MultiplicativeExpr ::= UnaryExpr { ( "*" | "/" | "%" ) UnaryExpr } ;
UnaryExpr ::= ( "++" | "--" | "+" | "-" | "!" | "~" | "*" | "&" ) UnaryExpr
            | "sizeof" ( "(" TypeSpecifier ")" | UnaryExpr )
            | "(" TypeSpecifier ")" UnaryExpr
            | PostfixExpr ;
PostfixExpr ::= PrimaryExpr { ( "++" | "--" | "(" [ ArgList ] ")" | "[" Expression "]" | "." IDENTIFIER | "->" IDENTIFIER | "::" IDENTIFIER ) } ;
PrimaryExpr ::= IDENTIFIER | NUMBER | STRING | CHAR | "(" Expression ")" ;
```

---

## 4. Canonicalization (Normalization) Rules

1. **Loop Unification**:
   - `for (init; cond; step) { body }` $\Longrightarrow$ `[init, Loop(cond, Block([body, step]))]`
   - `while (cond) { body }` $\Longrightarrow$ `Loop(cond, Block([body]))`
   - `do { body } while (cond);` $\Longrightarrow$ `Loop(cond, Block([body]))`
2. **Compound Assignments & Increments**:
   - `x += y` $\Longrightarrow$ `x = x + y` (and similar for `-=`, `*=`, `/=`, etc.)
   - `x++` / `++x` $\Longrightarrow$ `x = x + 1`
   - `x--` / `--x` $\Longrightarrow$ `x = x - 1`
3. **Control Flow Inlining**:
   - `if (c) return A; else return B;` $\Longrightarrow$ `return (c ? A : B);`
   - `if (c) v = A; else v = B;` $\Longrightarrow$ `v = (c ? A : B);`
4. **Commutative Operator Ordering**:
   - For binary operators $\odot \in \{+, *, ==, !=, \&\&, ||, \&, |, \^\}$, if `key(right) < key(left)`, swap operands to establish canonical lexicographical ordering.
5. **Boolean Negation & De Morgan**:
   - `!(a < b)` $\Longrightarrow$ `a >= b`
   - `!(a <= b)` $\Longrightarrow$ `a > b`
   - `!(a == b)` $\Longrightarrow$ `a != b`
   - `!(a && b)` $\Longrightarrow$ `!a || !b`
   - `!(a || b)` $\Longrightarrow$ `!a && !b`
   - `!!a` $\Longrightarrow$ `a`

---

## 5. Scoring Formulas

1. **Winnowing Token Similarity (Jaccard)**:
   $$\text{Sim}_{\text{token}}(A, B) = \frac{|H_A \cap H_B|}{|H_A \cup H_B|}$$
   Where $H_A, H_B$ are sets of selected minimum $K$-gram hashes ($K=5, W=4$).

2. **AST Tree Alignment (Weighted DP Dice Coefficient)**:
   $$\text{Align}(A, B) = \frac{2 \cdot \text{Matched}(A, B)}{|A| + |B|}$$
   Where node match gives $1.0$ if $\text{kind}_A = \text{kind}_B \land \text{val}_A = \text{val}_B$, and $0.5$ if $\text{kind}_A = \text{kind}_B \land \text{val}_A \ne \text{val}_B$.

3. **Merkle Maximal Subtree Coverage**:
   $$\text{Coverage}(A, B) = \frac{1}{2} \left( \frac{\sum_{M \in \mathcal{M}_A} |M|}{|A|} + \frac{\sum_{M \in \mathcal{M}_B} |M|}{|B|} \right)$$
   Where $\mathcal{M}$ is the set of maximal matching subtrees with $|M| \ge 3$.

4. **Overall Logic Similarity**:
   $$\text{Sim}_{\text{logic}}(A, B) = \max\left(\text{Align}(A, B),\, \text{Coverage}(A, B)\right)$$

5. **Consolidated Plagiarism Score**:
   $$\text{Score}_{\text{overall}} = 0.40 \cdot \text{Sim}_{\text{token}} + 0.60 \cdot \text{Sim}_{\text{logic}}$$
   - Verdict: $\ge 0.75 \implies \text{likely copied}$, $\ge 0.50 \implies \text{suspicious}$, $< 0.50 \implies \text{low}$.

---

## 6. Real-Time Web Candidate Retrieval Pipeline

```mermaid
flowchart LR
    Source["User Source Code"] --> Sig["Signature Extractor\n(Entropy & Identifiers)"]
    Sig -->|2-4 Unique Tokens| GH["GitHub Code Search API\nq={sig}+language:{lang}"]
    Sig -->|Generic Boilerplate| Skip["Local Database Only"]
    GH --> MemoryBuf["In-Memory Buffer\n(Base64 Decoded Source)"]
    MemoryBuf --> DB["SQLite Cache\n(hash(sig) -> JSON)"]
    MemoryBuf --> Engine["Two-Tier Plagiarism Check\n(Winnowing + AST Tree Align)"]
    Engine --> Threshold{"Composite Score\n>= 35% ?"}
    Threshold -->|Yes| Report["Flag Web Match\n& Surface Diff"]
    Threshold -->|No| Discard["Discard Candidate"]
```

### 6.1 Entropy-Based Signature Extraction
The signature extractor selects 2 to 4 distinctive identifiers:
- Filters out universal keywords and library headers (`main`, `solve`, `test`, `stdio`, `iostream`, `stdlib`, `print`, etc.).
- Computes Shannon entropy: $H(s) = -\sum_{c} p(c) \log_2 p(c)$ to prioritize rare and algorithmic identifiers (`find_shortest_cycle`, `MAX_VERTICES_LIMIT`, `fibonacci_memo`).
- Captures unique string literals and domain-specific constants.
- If no distinctive tokens exist (pure boilerplate), extraction returns an empty list to avoid redundant API queries.

### 6.2 GitHub REST Code Search Client
- **Endpoint**: `GET https://api.github.com/search/code?q={query}+language:{target_lang}`
- **Authentication**: Supports `GITHUB_TOKEN` from `.env` for elevated rate limits (30 req/min).
- **In-Memory Buffering**: Retrieves raw source via GitHub API `base64` decoding into memory strings; no intermediate files are written to disk.
- **Resilience**: 4-second hard request timeout with exponential retry and rate limit detection.
- **Two-Tier Cache**: In-memory hash table backed by persistent SQLite table `WebCandidateCache` keyed by `SHA-256(query + language)`.

### 6.3 Threshold Filtering & Diffing
- Evaluates each retrieved web candidate through the token-level Winnowing and logic-level AST normalizer.
- Flags matches with composite score $\ge 35\%$.
- Transmits repository URLs, token scores, logic scores, and source text to the UI for interactive side-by-side inspection.

