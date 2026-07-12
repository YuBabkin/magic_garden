# Промпт: Классы роста дерева (DNA, Branch)

## Что делать

Создать классы DNA и Branch для симуляции роста дерева по эпохам.

## Стек

Python, math, random. Без numpy. Без pygame (отдельный промпт).

## Класс DNA

Контейнер параметров из JSON. Загружается через `from_json(path)`.

```python
class DNA:
    def __init__(self, data: dict)
    @staticmethod
    def from_json(path: str) -> DNA
```

Параметры (с дефолтами):
- `length_a=2.0, length_b=1.5` — коэффициенты длины
- `thickness_a=0.3, thickness_b=0.4` — коэффициенты толщины
- `color_start=(34,139,34), color_end=(139,69,19)` — RGB
- `color_max_age=50` — возраст полного изменения цвета
- `alpha_start=0.2, alpha_end=1.0, alpha_max_age=20`
- `probabilities=[0.5,0.25,0.15,0.1,0.05]`
- `azimuth_loc=0, azimuth_scale=25`
- `epochs=40`

## Класс Branch

### Поля (все в __init__)
- `age: int` — возраст в эпохах (0 = новая)
- `floor: int` — уровень вложенности (0 = корень)
- `azimuth: float` — отклонение от родителя (градусы)
- `parent_angle: float` — абсолютный угол родителя (для корня 90°)
- `parent: Branch | None` — ссылка на родительскую ветку
- `children: list[Branch]`

### Методы

**`start_pos(dna) -> tuple`**
- Если parent is None: return (0.0, 0.0)
- Иначе: return parent.end_pos(dna)

**`angle` (property) -> float**
- parent_angle + azimuth

**`length(dna) -> float`**
- age < 1 → 0.0
- Иначе: dna.length_b * math.log(age) + dna.length_a

**`thickness(dna) -> float`**
- age < 1 → 0.0
- Иначе: dna.thickness_b * math.log(age) + dna.thickness_a

**`alpha(dna) -> float`**
- t = min(1.0, age / dna.alpha_max_age)
- dna.alpha_start + t * (dna.alpha_end - dna.alpha_start)

**`color(dna) -> tuple`**
- t = min(1.0, age / dna.color_max_age)
- Каждый канал: start + t * (end - start)
- Возврат: (int(r), int(g), int(b), int(alpha * 255))

**`end_pos(dna) -> tuple`**
- rad = math.radians(self.angle)
- l = self.length(dna)
- s = self.start_pos(dna)
- (s[0] + l * math.cos(rad), s[1] + l * math.sin(rad))

**`spawn_child(dna) -> Branch`**
- deviation = random.gauss(dna.azimuth_loc, dna.azimuth_scale)
- return Branch(age=0, floor=self.floor+1, azimuth=deviation, parent_angle=self.angle, parent=self)

## Подводные камни

- **azimuth НЕ накапливается.** Это только deviation. Наследование угла через `parent_angle`.
- **start_pos — метод, а не поле.** Вычисляется динамически от родителя.
- **log(age) при age < 1:** возвращать 0.0, иначе math.log(0) упадёт.
- **spawn_child:** age=0, начнёт расти в следующую эпоху.
