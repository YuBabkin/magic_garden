# Моделирование роста волшебного дерева

Создай программу на Python 3, которая моделирует рост дерева с визуализацией через matplotlib.

## Требования

### Структура
- Единый файл `main.py`.
- Классы: `DNA`, `Branch`, `Tree`.
- Все методы и классы с русскоязычными docstring.
- CLI через `argparse`: `-c/--config <путь>` (по умолчанию `config.json`).

### Входные данные (config.json)
JSON-файл с русскоязычными ключами:

```json
{
    "физические параметры роста дерева": {
        "длина": {"a": 2.0, "b": 1.5},
        "толщина": {"a": 0.3, "b": 0.4}
    },
    "внешний вид": {
        "цвет_начальный": [34, 139, 34],
        "цвет_конечный": [139, 69, 19],
        "макс_возраст_цвета": 50,
        "alpha_start": 0.2,
        "alpha_end": 1.0,
        "макс_возраст_alpha": 20
    },
    "параметры начала роста новой ветки": {
        "вероятности": [0.5, 0.25, 0.15, 0.1, 0.05],
        "азимут_loc": 0,
        "азимут_scale": 25,
        "эпох": 40
    }
}
```

### Класс DNA
- Хранит все параметры из JSON в атрибутах.
- Статический метод `from_json(path)` → загружает и парсит JSON.
- Секции:
  - **Физические параметры:** коэффициенты a, b для длины и толщины.
  - **Внешний вид:** начальный/конечный RGB-цвет, макс. возраст цвета, alpha_start, alpha_end, макс. возраст alpha.
  - **Параметры роста:** список вероятностей, параметры нормального распределения азимута (loc, scale), количество эпох.

### Класс Branch
**Поля (задаются при создании):**
- `age` (int) — возраст в эпохах, 0 = новая.
- `floor` (int) — этаж (0 = корень).
- `children` (list) — список дочерних веток.
- `azimuth` (float) — отклонение от направления родителя в градусах.
- `parent_angle` (float) — абсолютный угол родителя в градусах (для корня 90°).
- `start_pos` (tuple) — координаты (x, y) начала.

**Вычисляемые методы (принимают DNA):**
- `angle` (property) → `parent_angle + azimuth`
- `length(dna)` → `b·ln(age) + a` (натуральный логарифм), при age < 1 → 0
- `thickness(dna)` → `b·ln(age) + a`, при age < 1 → 0
- `color(dna)` → RGBA (R,G,B,A) с компонентами 0..1:
  - RGB: линейная интерполяция color_start → color_end по `age / color_max_age`, делёная на 255
  - Alpha: линейная интерполяция alpha_start → alpha_end по `age / alpha_max_age`
- `end_pos(dna)` → `(x + length·cos(α), y + length·sin(α))`, α в радианах
- `spawn_child(dna)` → новая Branch:
  - `age=0, floor=parent.floor+1, start_pos=parent.end_pos, parent_angle=parent.angle`
  - `azimuth = parent.azimuth + random.gauss(loc, scale)`

### Класс Tree
**Поля:**
- Корень: `Branch(0, 0, 0, (0,0), 90)`
- `all_branches` — список всех веток
- `epoch` — счётчик эпох

**Методы:**
- `grow()`:
  1. `epoch += 1`
  2. `age += 1` для всех веток
  3. Для каждой ветки: вероятность spawn = `probabilities[n]` (n = число потомков); если n >= len(probabilities) → 0
  4. При успешном розыгрыше: `branch.spawn_child(dna)` → добавляется в `children` и `all_branches`.
  5. Новые ветки НЕ участвуют в spawn той же эпохи.
- `draw(ax)` — рекурсивная отрисовка:
  - Каждая ветка: отрезок от start_pos до end_pos
  - Толщина: `max(0.5, thickness * 6)`
  - Цвет: RGBA из `color()`
  - `ax.set_aspect("equal")`, `ax.axis("off")`, заголовок
- `animate()`:
  - `plt.ion()`, создать Figure/Axes
  - Цикл по эпохам: `grow()` → `ax.clear()` → `draw(ax)` → `plt.pause(0.2)`
  - После цикла: `plt.ioff()`, `plt.show()`

### Обработка ошибок
- Файл конфига не найден → `print("Ошибка: файл ... не найден")` + `sys.exit(1)`
- Некорректный JSON → `print(f"Ошибка JSON: {e}")` + `sys.exit(1)`

### Точка входа
```python
if __name__ == "__main__":
    main()
```

### Пример запуска
```
$ python3 main.py -c config.json
```
