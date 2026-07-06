## Понимание задачи (после уточнений)

Программа-игра "Моделирование роста волшебного дерева" на Python с ООП и визуализацией.

### Уточнённые требования:
- **Анимация**: показывать рост дерева эпоха за эпохой с паузой
- **Scale factor** для толщины: 6
- **CLI**: argparse с флагом `-c`/`--config` для пути к конфигу

### Сущности

**Branch:**
- Поля: age, floor, children, azimuth, start_pos, parent_angle
- angle = parent_angle + azimuth
- length = b*log(age) + a (age<1 → 0)
- thickness = b*log(age) + a (age<1 → 0)
- color = линейная интерполяция RGB от start к end, t = min(1, age/max_age)
- alpha = линейная интерполяция alpha_start→alpha_end
- Каждую эпоху: розыгрыш новой ветки с вероятностью из списка по числу потомков
- azb = random.gauss(loc, scale) — добавляется к azimuth родителя

**Tree:**
- Корень: Branch(0, 0, 0, (0,0), 90)
- grow(): epoch++ → age всех++ → розыгрыш новых веток
- draw(): рекурсивно, отрезки от start_pos до end_pos, толщина*6, цвет RGBA

### План реализации

1. `argparse` для пути к конфигу (по умолчанию config.json)
2. Класс `DNA` — загрузка и хранение параметров из JSON
3. Класс `Branch` — все расчёты длины, толщины, цвета, углов
4. Класс `Tree` — grow(), draw() с рекурсией
5. Анимация через `plt.pause()` или `FuncAnimation` — обновление графика каждую эпоху
6. Обработка ошибок: FileNotFoundError, JSONDecodeError
