"""Testing utilities and mocks for SentinelAI."""

class MockAgent:
    """Mock agent for demos and testing."""

    def search(self, query: str) -> dict:
        return {"results": [f"Result 1 for {query}", f"Result 2 for {query}"], "count": 2}

    def calculate(self, expression: str) -> dict:
        try:
            result = _safe_math_eval(expression)
            return {"expression": expression, "result": result}
        except Exception:
            return {"expression": expression, "error": "Could not evaluate"}

    def fetch_data(self, resource_id: str) -> dict:
        return {"id": resource_id, "data": {"name": "Sample", "value": 42}}


def _safe_math_eval(expression: str) -> float:
    """Safely evaluate basic arithmetic expressions without eval().

    Supports: +, -, *, /, parentheses, integers, and floats.
    Raises ValueError for unsupported expressions.
    """
    import ast
    import operator

    allowed_operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def _eval_node(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return _eval_node(node.body)
        elif isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        elif isinstance(node, ast.BinOp):
            op_func = allowed_operators.get(type(node.op))
            if op_func is None:
                raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
            return op_func(_eval_node(node.left), _eval_node(node.right))
        elif isinstance(node, ast.UnaryOp):
            op_func = allowed_operators.get(type(node.op))
            if op_func is None:
                raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
            return op_func(_eval_node(node.operand))
        else:
            raise ValueError(f"Unsupported expression node: {type(node).__name__}")

    tree = ast.parse(expression.strip(), mode="eval")
    return _eval_node(tree)
