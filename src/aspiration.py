import math


def step_relative(current, target, strength):
    """
    Пропорциональное стремление: за шаг преодолевается доля от остатка до цели.

    Параметры:
        current  : float - текущее значение A
        target   : float - целевое значение B
        strength : float - сила стремления, 0..1 (0 - стоим на месте, 1 - прыжок в B)

    Возвращает:
        float - новое значение A

    Замечание:
        При strength < 1 цель достигается асимптотически, шаг уменьшается с каждым
        приближением. Это экспоненциальное сглаживание: A(t) = B + (A0 - B)*(1 - k)^t.
    """
    strength = min(1.0, max(0.0, strength))
    return current + strength * (target - current)


def step_absolute(current, target, speed, dt=1.0):
    """
    Абсолютное стремление: за шаг значение сдвигается к цели на фиксированную величину.

    Параметры:
        current : float - текущее значение A
        target  : float - целевое значение B
        speed   : float - скорость, единиц за единицу времени (>= 0)
        dt      : float - длительность шага (эпоха, кадр, секунда)

    Возвращает:
        float - новое значение A, никогда не перескакивает через B
    """
    distance = target - current
    limit = abs(speed) * dt
    if abs(distance) <= limit:
        return target
    return current + math.copysign(limit, distance)


def closed_form(start, target, strength, steps):
    """
    Значение пропорционального стремления после steps шагов, без итераций.

    Параметры:
        start    : float - начальное значение A
        target   : float - целевое значение B
        strength : float - сила стремления, 0..1
        steps    : int   - количество шагов (>= 0)

    Возвращает:
        float - значение A после steps шагов
    """
    strength = min(1.0, max(0.0, strength))
    steps = max(0, steps)
    return target + (start - target) * (1.0 - strength) ** steps


class Aspiration:
    """
    Состояние стремления величины A к величине B.

    Хранит текущее значение и параметры скорости, метод step() продвигает значение
    на один шаг. Режим "relative" - доля от остатка, режим "absolute" - фиксированная
    величина за шаг.
    """

    def __init__(self, value, target, speed=0.1, mode="relative"):
        """
        Параметры:
            value  : float - начальное значение A
            target : float - целевое значение B
            speed  : float - скорость (для relative - сила 0..1, для absolute - единиц/шаг)
            mode   : str   - "relative" или "absolute"
        """
        if mode not in ("relative", "absolute"):
            raise ValueError(f"Неизвестный режим стремления: {mode}")
        self.value = float(value)
        self.target = float(target)
        self.speed = float(speed)
        self.mode = mode
        self.steps_done = 0

    def step(self, dt=1.0):
        """
        Продвинуть значение на один шаг.

        Параметры:
            dt : float - длительность шага (используется только в режиме absolute)

        Возвращает:
            float - новое значение A
        """
        if self.mode == "relative":
            self.value = step_relative(self.value, self.target, self.speed)
        else:
            self.value = step_absolute(self.value, self.target, self.speed, dt)
        self.steps_done += 1
        return self.value

    def reached(self, tolerance=1e-6):
        """
        Проверить, достигнуто ли целевое значение в пределах допуска.

        Параметры:
            tolerance : float - допуск сравнения

        Возвращает:
            bool
        """
        return abs(self.target - self.value) <= tolerance

    def reset(self, value):
        """
        Сбросить состояние к новому начальному значению.

        Параметры:
            value : float - новое значение A
        """
        self.value = float(value)
        self.steps_done = 0


if __name__ == "__main__":
    a, b = 0.0, 90.0

    print("Пропорциональное стремление (сила = 0.2):")
    for i in range(1, 11):
        print(f"  шаг {i:2d} -> {closed_form(a, b, 0.2, i):7.3f}")

    print()
    print("Абсолютное стремление (скорость = 15.0 за шаг):")
    asp = Aspiration(a, b, speed=15.0, mode="absolute")
    while not asp.reached():
        asp.step()
        print(f"  шаг {asp.steps_done:2d} -> {asp.value:7.3f}")
