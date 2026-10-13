import math

def slow_growth(x, a, b, p=1.0):
    """
    Логарифмическая функция с замедлением роста.
    
    Параметры:
        x : float  - аргумент (должен быть > 0)
        a : float  - значение при x=1
        b : float  - значение при x=100
        p : float  - степень логарифма (1 - стандартный, >1 - более резкое замедление)
    
    Возвращает:
        y : float
    """
    if x <= 1:
        return a
    # Отношение логарифмов (равно log_100(x))
    ratio = math.log(x) / math.log(100)
    # Возводим в степень p и масштабируем
    return a + (b - a) * (ratio ** p)


if __name__ == "__main__":
    # Генерация значений для x от 1 до 100 с шагом 1
    a, b = 10, 200
    xs = range(1, 101)
    ys = [slow_growth(x, a, b) for x in xs]

    # Вывод первых 10 и последних 10 значений
    for x in [1, 10, 20, 50, 80, 100]:
        print(f"x={x:3d} -> y={slow_growth(x, a, b):.2f}")

    import matplotlib.pyplot as plt

    plt.plot(xs, ys)
    plt.xlabel("x")
    plt.ylabel("y")
    plt.title("slow_growth")
    plt.grid(True)
    plt.show()

    
