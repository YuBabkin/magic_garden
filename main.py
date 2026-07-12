import argparse
import json
import math
import random
import sys

import matplotlib.pyplot as plt
import numpy as np


class DNA:
    """ДНК дерева — контейнер всех настраиваемых параметров роста и внешнего вида.

    Загружается из JSON-конфига с русскоязычными ключами.
    Содержит три смысловые секции:
    - физические параметры роста дерева (коэффициенты длины и толщины)
    - внешний вид (начальный/конечный цвет, прозрачность, максимальный возраст)
    - параметры начала роста новой ветки (вероятности, азимут, число эпох)

    Все параметры имеют значения по умолчанию, соответствующие примеру из config.json.
    """

    def __init__(self, data: dict):
        """Инициализация ДНК из словаря, полученного из JSON-конфига.

        Разбирает три секции словаря и сохраняет параметры как атрибуты.
        Для отсутствующих ключей используются значения по умолчанию.

        Параметры:
            data: словарь с русскоязычными ключами из конфигурационного файла.
        """
        # --- Секция "физические параметры роста дерева" ---
        phys = data.get("физические параметры роста дерева", {})

        # Длина ветки: length = b * ln(age) + a
        length_params = phys.get("длина", {})
        self.length_a = length_params.get("a", 2.0)
        self.length_b = length_params.get("b", 1.5)

        # Толщина ветки: thickness = b * ln(age) + a
        thickness_params = phys.get("толщина", {})
        self.thickness_a = thickness_params.get("a", 0.3)
        self.thickness_b = thickness_params.get("b", 0.4)

        # --- Секция "внешний вид" ---
        look = data.get("внешний вид", {})

        # Цвет: линейная интерполяция RGB от начального (зелёный) к конечному (коричневый)
        self.color_start = tuple(look.get("цвет_начальный", [34, 139, 34]))
        self.color_end = tuple(look.get("цвет_конечный", [139, 69, 19]))
        self.color_max_age = look.get("макс_возраст_цвета", 50)

        # Прозрачность (alpha): линейная интерполяция от alpha_start к alpha_end
        self.alpha_start = look.get("alpha_start", 0.2)
        self.alpha_end = look.get("alpha_end", 1.0)
        self.alpha_max_age = look.get("макс_возраст_alpha", 20)

        # --- Секция "параметры начала роста новой ветки" ---
        growth = data.get("параметры начала роста новой ветки", {})

        # probabilities[n] — вероятность spawn, если у ветки уже n потомков
        self.probabilities = growth.get("вероятности", [0.5, 0.25, 0.15, 0.1, 0.05])
        # Параметры нормального распределения для отклонения направления новой ветки
        self.azimuth_loc = growth.get("азимут_loc", 0)
        self.azimuth_scale = growth.get("азимут_scale", 25)
        # Количество эпох (дискретных шагов) симуляции
        self.epochs = growth.get("эпох", 40)

    @staticmethod
    def from_json(path: str):
        """Загрузить и распарсить JSON-конфиг, вернуть экземпляр DNA.

        Последовательность действий:
        1. Открыть файл на чтение (кодировка UTF-8).
        2. Загрузить JSON через json.load().
        3. Передать полученный словарь в конструктор DNA.

        Параметры:
            path: путь к файлу конфигурации (например, "config.json").

        Возвращает:
            Экземпляр DNA с параметрами из файла.

        Исключения:
            FileNotFoundError — если файл не существует.
            json.JSONDecodeError — если файл содержит некорректный JSON.
        """
        with open(path, encoding="utf-8") as f:
            return DNA(json.load(f))


class Branch:
    """Ветка дерева — элемент иерархической структуры.

    Каждая ветка имеет:
    - первичные (заданные при создании) поля: возраст, этаж, азимут,
      координаты начала, угол родителя;
    - вторичные (вычисляемые от возраста по ДНК) параметры: длина, толщина,
      цвет, прозрачность, координаты конца.

    Потомки ветки хранятся в списке children, образуя древовидную структуру.
    """

    def __init__(self, age, floor, azimuth, start_pos, parent_angle):
        """Инициализация ветки с заданными первичными параметрами.

        Аргументы:
            age (int): возраст ветки в эпохах.
                0 — новая ветка (ещё не участвовала в росте).
            floor (int): этаж (уровень вложенности).
                0 — корневая ветка, +1 для каждого уровня потомков.
            azimuth (float): отклонение направления роста от родительской ветки
                (градусы). Вычисляется как random.gauss() и НЕ накапливается
                — наследование направления происходит через parent_angle.
            start_pos (tuple): координаты (x, y) начала ветки.
                Для корня — (0, 0). Для потомков — end_pos родителя.
            parent_angle (float): абсолютный угол направления родительской ветки
                (градусы). Для корня = 90° (вертикально вверх в координатах matplotlib).
        """
        self.age = age
        self.floor = floor
        self.azimuth = azimuth
        self.start_pos = start_pos
        self.parent_angle = parent_angle
        self.children = []

    @property
    def angle(self):
        """Абсолютный угол направления роста ветки в градусах.

        Вычисляется как parent_angle + azimuth.
        Для корня (parent_angle=90, azimuth=0) возвращает 90° — рост вверх.
        Используется при расчёте end_pos через cos/sin.

        Returns:
            float: угол в градусах от положительной оси X (стандарт math).
        """
        return self.parent_angle + self.azimuth

    def length(self, dna):
        """Вычислить длину ветки по формуле: b * ln(age) + a.

        Логарифм натуральный (np.log / math.log).
        Для age < 1 возвращает 0.0, так как логарифм от 0 не определён
        и ветка ещё не росла (первичное появление в текущей эпохе).

        Параметры:
            dna: экземпляр DNA с коэффициентами length_a, length_b.

        Возвращает:
            float: длина ветки в условных единицах.
        """
        if self.age < 1:
            return 0.0
        return dna.length_b * np.log(self.age) + dna.length_a

    def thickness(self, dna):
        """Вычислить толщину ветки по формуле: b * ln(age) + a.

        Аналогична length(), но с коэффициентами толщины.
        Для age < 1 возвращает 0.0.

        Параметры:
            dna: экземпляр DNA с коэффициентами thickness_a, thickness_b.

        Возвращает:
            float: толщина ветки в условных единицах.
        """
        if self.age < 1:
            return 0.0
        return dna.thickness_b * np.log(self.age) + dna.thickness_a

    def alpha(self, dna):
        """Вычислить прозрачность (alpha) ветки для отрисовки.

        Линейная интерполяция от alpha_start к alpha_end по возрасту:
        t = min(1, age / alpha_max_age)
        alpha = alpha_start + t * (alpha_end - alpha_start)

        При age >= alpha_max_age прозрачность достигает alpha_end и не меняется.

        Параметры:
            dna: экземпляр DNA с параметрами alpha_start, alpha_end, alpha_max_age.

        Возвращает:
            float: значение прозрачности в диапазоне [alpha_start, alpha_end].
        """
        t = min(1.0, self.age / dna.alpha_max_age)
        return dna.alpha_start + t * (dna.alpha_end - dna.alpha_start)

    def color(self, dna):
        """Вычислить цвет ветки в формате RGBA для matplotlib.

        Алгоритм:
        1. t = min(1, age / color_max_age) — коэффициент интерполяции.
        2. Каждый RGB-канал: channel = start + t * (end - start).
           Интерполяция поканальная, линейная.
        3. Деление каждого канала на 255 (matplotlib ожидает [0, 1]).
        4. Alpha из self.alpha(dna).

        При age >= color_max_age цвет достигает color_end и не меняется.

        Параметры:
            dna: экземпляр DNA с color_start, color_end, color_max_age.

        Возвращает:
            tuple: (r, g, b, a) — все компоненты в диапазоне [0, 1].
        """
        t = min(1.0, self.age / dna.color_max_age)
        r = dna.color_start[0] + t * (dna.color_end[0] - dna.color_start[0])
        g = dna.color_start[1] + t * (dna.color_end[1] - dna.color_start[1])
        b = dna.color_start[2] + t * (dna.color_end[2] - dna.color_start[2])
        return (r / 255, g / 255, b / 255, self.alpha(dna))

    def end_pos(self, dna):
        """Вычислить координаты конца ветки.

        Формула:
        - l = self.length(dna) — длина ветки.
        - α = math.radians(self.angle) — абсолютный угол в радианах.
        - x = start_x + l * cos(α)
        - y = start_y + l * sin(α)

        Для корня (angle=90°): x=0+0=0, y=0+l*1=l → строго вверх.

        Параметры:
            dna: экземпляр DNA (нужен для вычисления длины).

        Возвращает:
            tuple: (x, y) — координаты конца ветки.
        """
        rad = math.radians(self.angle)
        l = self.length(dna)
        x = self.start_pos[0] + l * math.cos(rad)
        y = self.start_pos[1] + l * math.sin(rad)
        return (x, y)

    def spawn_child(self, dna):
        """Создать новую ветку-потомок со случайным отклонением.

        Алгоритм:
        1. deviation = random.gauss(azimuth_loc, azimuth_scale) — случайное
           отклонение от направления родителя.
        2. Создаётся Branch с:
           - age=0 (новая, начнёт расти в следующую эпоху)
           - floor = parent.floor + 1 (уровень вложенности)
           - azimuth = deviation (НЕ накапливается!)
           - start_pos = self.end_pos(dna) (конец родительской ветки)
           - parent_angle = self.angle (абсолютный угол родителя)

        Важно: azimuth — это только собственное отклонение ветки, а не
        накопленная сумма. Наследование направления реализовано через
        parent_angle = self.angle (абсолютный угол родителя).

        Параметры:
            dna: экземпляр DNA с параметрами azimuth_loc, azimuth_scale.

        Возвращает:
            Branch: новая ветка-потомок.
        """
        deviation = random.gauss(dna.azimuth_loc, dna.azimuth_scale)
        return Branch(
            age=0,
            floor=self.floor + 1,
            azimuth=deviation,
            start_pos=self.end_pos(dna),
            parent_angle=self.angle,
        )


class Tree:
    """Дерево — контейнер иерархии веток и логики роста.

    Содержит:
    - корневую ветку (root), от которой отрастают все остальные;
    - плоский список всех веток (all_branches) для сквозной итерации;
    - счётчик эпох (epoch);
    - ссылку на ДНК (dna) с параметрами роста.

    Основные методы:
    - grow() — одна эпоха роста (старение + вероятностное ветвление).
    - draw(ax) — рекурсивная отрисовка дерева на matplotlib-осях.
    - animate() — полный цикл анимации: рост + отрисовка покадрово.
    """

    def __init__(self, dna):
        """Инициализировать дерево с корневой веткой.

        Корень создаётся в точке (0, 0) с нулевым азимутом,
        этажом 0 и parent_angle=90° (растёт строго вверх).

        Параметры:
            dna: экземпляр DNA с параметрами роста и внешнего вида.
        """
        self.dna = dna
        self.root = Branch(age=0, floor=0, azimuth=0, start_pos=(0, 0), parent_angle=90)
        self.all_branches = [self.root]
        self.epoch = 0

    def grow(self):
        """Выполнить одну эпоху роста дерева.

        Порядок операций:
        1. Увеличить счётчик эпох (self.epoch += 1).
        2. Увеличить возраст всех существующих веток на 1.
           Это нужно сделать ДО расчёта координат, чтобы длина/толщина
           обновились для корректного вычисления end_pos при spawn.
        3. Для каждой существующей ветки (из self.all_branches):
           - Определить число потомков n = len(branch.children).
           - Вычислить вероятность spawn = probabilities[n] (0 если n вне списка).
           - Если random.random() < prob: создать потомка через branch.spawn_child().
        4. Вновь созданные ветки собираются в отдельный список и добавляются
           в all_branches ТОЛЬКО после завершения цикла, чтобы они НЕ
           участвовали в розыгрыше той же эпохи.
        """
        self.epoch += 1

        for branch in self.all_branches:
            branch.age += 1

        new_branches = []

        for branch in self.all_branches:
            n = len(branch.children)
            prob = self.dna.probabilities[n] if n < len(self.dna.probabilities) else 0.0

            if random.random() < prob:
                child = branch.spawn_child(self.dna)
                branch.children.append(child)
                new_branches.append(child)

        self.all_branches.extend(new_branches)

    def draw(self, ax=None):
        """Нарисовать текущее состояние дерева на matplotlib-осях.

        Использует рекурсивный обход от корня. Каждая ветка рисуется
        как отрезок линии от start_pos до end_pos с параметрами:
        - толщина линии: max(0.5, thickness * 6) — масштабирование для наглядности
        - цвет: RGBA из метода color() (возрастной градиент)
        - solid_capstyle='round' — скруглённые концы отрезков

        После отрисовки настраивает оси: равный масштаб, без осей, заголовок.

        Параметры:
            ax: matplotlib Axes для отрисовки. Если None, создаются новые
                с размером фигуры 10x10 дюймов.
        """
        if ax is None:
            _, ax = plt.subplots(figsize=(10, 10))

        ax.set_xlim(-50, 50)
        ax.set_ylim(0, 100)

        def _draw(branch):
            end = branch.end_pos(self.dna)
            w = max(0.5, branch.thickness(self.dna) * 6)
            c = branch.color(self.dna)
            ax.plot(
                [branch.start_pos[0], end[0]],
                [branch.start_pos[1], end[1]],
                color=c, linewidth=w, solid_capstyle="round",
            )
            for child in branch.children:
                _draw(child)

        _draw(self.root)
        ax.set_aspect("equal")
        # ax.axis("off")
        ax.set_title(f"Волшебное дерево — Эпоха {self.epoch}")

    def animate(self):
        """Запустить полный цикл анимации роста дерева.

        Использует интерактивный режим matplotlib (plt.ion()) для
        покадрового вывода. Последовательность для каждой эпохи:
        1. self.grow() — одна эпоха роста (старение + ветвление).
        2. ax.clear() — очистка осей от предыдущего кадра.
        3. self.draw(ax) — отрисовка текущего состояния.
        4. plt.pause(0.2) — пауза 200 мс для визуального восприятия.

        После завершения всех эпох:
        - plt.ioff() — отключение интерактивного режима.
        - plt.show() — финальный кадр остаётся открытым до закрытия окна.

        Количество эпох задаётся в DNA (поле epochs).
        """
        plt.ion()
        fig, ax = plt.subplots(figsize=(10, 10))

        for _ in range(self.dna.epochs):
            self.grow()
            ax.clear()
            self.draw(ax)
            plt.pause(0.2)

        plt.ioff()
        plt.show()


def main():
    """Точка входа программы: парсинг аргументов, загрузка, запуск.

    Шаги:
    1. Парсинг аргументов командной строки через argparse:
       - -c/--config: путь к JSON-конфигу (по умолчанию 'config.json').
    2. Загрузка ДНК из JSON-файла через DNA.from_json().
       - Обработка FileNotFoundError: файл не найден → сообщение + exit(1).
       - Обработка JSONDecodeError: некорректный JSON → сообщение + exit(1).
    3. Создание дерева Tree(dna) и запуск анимации tree.animate().
    """
    parser = argparse.ArgumentParser(
        description="Моделирование роста волшебного дерева",
    )
    parser.add_argument(
        "-c", "--config", default="config.json",
        help="путь к файлу конфигурации (JSON)",
    )
    args = parser.parse_args()

    try:
        dna = DNA.from_json(args.config)
    except FileNotFoundError:
        print(f"Ошибка: файл {args.config} не найден")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Ошибка JSON: {e}")
        sys.exit(1)

    tree = Tree(dna)
    tree.animate()


if __name__ == "__main__":
    main()
