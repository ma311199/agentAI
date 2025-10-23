import math
from typing import Union

Number = Union[int, float]


def power(a: Number, b: Number) -> float:
    """计算 a 的 b 次方
    
    参数:
    - a: 底数
    - b: 指数
    [{"name":"a","type":"int","description":"被执行次方的数","required":true},{"name":"b","type":"int","description":"次方数","required":true}]
    返回:
    - a ** b 的结果（float）
    """
    return float(a) ** float(b)


def root(a: Number, b: Number) -> float:
    """计算 a 的 1/b 次方（即 b 次方根）
    
    参数:
    - a: 被开方数
    - b: 根指数（不可为 0）
    规则与说明:
    - 若 b = 0，抛出异常（无法计算 1/0）。
    - 若 a < 0：
      - 若 b 为整数且为偶数：无实数根，抛出异常。
      - 若 b 为整数且为奇数：返回负的奇次根。
      - 若 b 非整数：结果为复数，本函数不计算，抛出异常。
    - 其他情况使用实数域下的幂函数计算。
    """
    a_val = float(a)
    b_val = float(b)

    if b_val == 0.0:
        raise ValueError("b 不能为 0（无法计算 1/b）")

    # 判断 b 是否为整数
    b_is_int = b_val.is_integer()

    if a_val < 0:
        if b_is_int:
            # 偶数次根无实数解
            if int(abs(b_val)) % 2 == 0:
                raise ValueError("a 为负数且 b 为偶数次根时无实数结果")
            # 奇数次根：对正数取根后加负号（支持 b 为负的情况）
            return -math.pow(-a_val, 1.0 / b_val)
        else:
            # 负数的非整数次幂为复数，不在此函数的计算范围
            raise ValueError("a 为负数且 b 非整数时结果为复数，不在此函数计算范围")

    # a >= 0 的情况直接计算
    return math.pow(a_val, 1.0 / b_val)


if __name__ == "__main__":
    # 简单示例
    print("power(2, 3) =", power(2, 3))           # 8.0
    print("root(9, 2) =", root(9, 2))             # 3.0（平方根）
    print("root(27, 3) =", root(27, 3))           # 3.0（立方根）
    print("root(16, -2) =", root(16, -2))         # 0.25（1/平方根的平方）
    try:
        print("root(-8, 3) =", root(-8, 3))        # -2.0（负数的奇次根）
    except ValueError as e:
        print("error:", e)
    try:
        print("root(-16, 2) =", root(-16, 2))      # 抛异常：偶次根无实数解
    except ValueError as e:
        print("error:", e)