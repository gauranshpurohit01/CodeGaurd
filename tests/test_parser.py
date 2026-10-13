"""Unit tests for recursive-descent C parser with C++ tolerance."""

from app.engine.c_parser import parse_c


def test_function_definition_and_prototype():
    code = """
    int add(int a, int b);
    int add(int a, int b) {
        return a + b;
    }
    """
    res = parse_c(code)
    assert len(res.errors) == 0
    kinds = [child.kind for child in res.ast.children]
    assert "FunctionDecl" in kinds
    assert "FunctionDef" in kinds


def test_declarations_and_pointers():
    code = """
    void test() {
        int a, *b, c = 10;
        double arr[10];
    }
    """
    res = parse_c(code)
    assert len(res.errors) == 0
    func = res.ast.children[0]
    block = func.children[2]
    decls = [s for s in block.children if s.kind == "VarDecl"]
    assert len(decls) == 4
    names = [d.value for d in decls]
    assert "a" in names
    assert "*b" in names
    assert "c" in names
    assert "arr" in names


def test_control_flow_constructs():
    code = """
    void control(int n) {
        if (n > 0) { n--; } else { n++; }
        while (n < 5) { n++; }
        for (int i = 0; i < n; i++) { break; }
        do { n--; } while (n > 0);
        switch (n) {
            case 1: n = 2; break;
            default: n = 0;
        }
    }
    """
    res = parse_c(code)
    assert len(res.errors) == 0
    block = res.ast.children[0].children[2]
    kinds = [s.kind for s in block.children]
    assert "If" in kinds
    assert "While" in kinds
    assert "For" in kinds
    assert "DoWhile" in kinds
    assert "Switch" in kinds


def test_expression_precedence():
    code = """
    int calc() {
        return a + b * c == d && e || !f;
    }
    """
    res = parse_c(code)
    assert len(res.errors) == 0
    ret_expr = res.ast.children[0].children[2].children[0].children[0]
    # Root of expression should be '||' (lowest precedence)
    assert ret_expr.kind == "BinaryOp"
    assert ret_expr.value == "||"


def test_calls_indexing_and_members():
    code = """
    void ops() {
        foo(1, 2);
        arr[idx] = 3;
        ptr->val = 4;
        obj.member = 5;
    }
    """
    res = parse_c(code)
    assert len(res.errors) == 0
    stmts = res.ast.children[0].children[2].children
    assert stmts[0].children[0].kind == "Call"
    assert stmts[1].children[0].children[0].kind == "Index"
    assert stmts[2].children[0].children[0].kind == "Member"
    assert stmts[3].children[0].children[0].kind == "Member"


def test_ternary_sizeof_and_cast():
    code = """
    int advanced(int x) {
        int a = (x > 0) ? 1 : 0;
        int sz = sizeof(int);
        float y = (float) x;
        return a;
    }
    """
    res = parse_c(code)
    assert len(res.errors) == 0


def test_error_recovery_at_statement_boundary():
    # Unsupported syntax in middle statement
    code = """
    int test() {
        int a = 1;
        $$$ unsupported garbage statement $$$;
        int b = 2;
        return a + b;
    }
    """
    res = parse_c(code)
    assert len(res.recovery_events) > 0
    # Following statement 'int b = 2;' should still be parsed!
    block = res.ast.children[0].children[2]
    var_names = [s.value for s in block.children if s.kind == "VarDecl"]
    assert "a" in var_names
    assert "b" in var_names


def test_cpp_tolerance():
    code = """
    using namespace std;
    int test_cpp(int& ref) {
        bool flag = true;
        std::cout << ref << std::endl;
        for (auto x : vec) {
            ref += x;
        }
        return ref;
    }
    """
    res = parse_c(code)
    assert len(res.errors) == 0
    func = res.ast.children[0]
    assert func.kind == "FunctionDef"
