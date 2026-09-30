import unittest
from calculator import calculate, parse_expression, divide


class TestCalculator(unittest.TestCase):
    def test_basic_ops(self):
        self.assertEqual(calculate(1, "+", 2), 3)
        self.assertEqual(calculate(5, "-", 3), 2)
        self.assertEqual(calculate(4, "*", 2.5), 10)
        self.assertEqual(calculate(10, "/", 4), 2.5)
        self.assertEqual(calculate(10, "%", 3), 1)
        self.assertEqual(calculate(2, "**", 8), 256)

    def test_divide_by_zero(self):
        with self.assertRaises(ValueError):
            divide(1, 0)

    def test_parse(self):
        self.assertEqual(parse_expression(" 3 + 5 "), ("3", "+", "5"))
        self.assertEqual(parse_expression("2 ** 8"), ("2", "**", "8"))

    def test_invalid_op(self):
        with self.assertRaises(ValueError):
            calculate(1, "^", 2)


if __name__ == "__main__":
    unittest.main()
