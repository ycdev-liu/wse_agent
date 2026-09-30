"""简单计算器:支持加减乘除、取余、乘方,以及交互式模式。"""


def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


def multiply(a, b):
    return a * b


def divide(a, b):
    if b == 0:
        raise ValueError("除数不能为零")
    return a / b


def modulo(a, b):
    if b == 0:
        raise ValueError("除数不能为零")
    return a % b


def power(a, b):
    return a ** b


OPERATIONS = {
    "+": add,
    "-": subtract,
    "*": multiply,
    "/": divide,
    "%": modulo,
    "**": power,
}


def calculate(a, op, b):
    if op not in OPERATIONS:
        raise ValueError(f"不支持的运算符: {op}")
    return OPERATIONS[op](float(a), float(b))


def parse_expression(expr):
    """解析形如 '1 + 2' 的表达式,支持 ** 运算符。"""
    expr = expr.strip()
    for op in sorted(OPERATIONS, key=len, reverse=True):
        parts = expr.split(op)
        if len(parts) == 2 and parts[0].strip() and parts[1].strip():
            return parts[0].strip(), op, parts[1].strip()
    raise ValueError(f"无法解析表达式: {expr}")


def main():
    print("简单计算器(输入 q 退出)")
    print("示例:3 + 5 、10 / 2 、2 ** 8")
    while True:
        line = input(">>> ").strip()
        if not line:
            continue
        if line.lower() in ("q", "quit", "exit"):
            print("再见!")
            break
        try:
            a, op, b = parse_expression(line)
            result = calculate(a, op, b)
            print(f"结果: {result}")
        except ValueError as e:
            print(f"错误: {e}")


if __name__ == "__main__":
    main()
