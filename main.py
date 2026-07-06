import argparse
import json
import math
import random
import sys

import matplotlib.pyplot as plt
import numpy as np


class DNA:
    """ДНК дерева — все настраиваемые параметры роста и внешнего вида.

    Загружается из JSON-конфига, содержит секции:
    - физические параметры роста дерева (длина, толщина)
    - внешний вид (цвет, прозрачность)
    - параметры начала роста новой ветки (вероятности, азимут, эпохи)
    """

    def __init__(self, data: dict):
        """Инициализация ДНК из словаря, полученного из JSON.

        Параметры:
            data: словарь с русскоязычными ключами из конфигурационного файла.
        """
        # --- Секция "физические параметры роста дерева" ---
        phys = data.get("физические параметры роста дерева", {})

        # Длина ветки: length = b * log(age) + a
        self.length_a = phys.get("длина", {}).get("a", 2.0)
        self.length_b = phys.get("длина", {}).get("b", 1.5)

        # Толщина ветки: thickness = b * log(age) + a
        self.thickness_a = phys.get("толщина", {}).get("a", 0.3)
        self.thickness_b = phys.get("толщина", {}).get("b", 0.4)

        # --- Секция "внешний вид" ---
        look = data.get("внешний вид", {})

        # Цвет ветки: линейная интерполяция от начального (зелёный) к конечному (коричневый)
        self.color_start = tuple(look.get("цвет_начальный", [34, 139, 34]))
        self.color_end = tuple(look.get("цвет_конечный", [139, 69, 19]))
        self.color_max_age = look.get("макс_возраст_цвета", 50)

        # Прозрачность ветки: линейная интерполяция
        self.alpha_start = look.get("alpha_start", 0.2)
        self.alpha_end = look.get("alpha_end", 1.0)
        self.alpha_max_age = look.get("макс_возраст_alpha", 20)

        # --- Секция "параметры начала роста новой ветки" ---
        growth = data.get("параметры начала роста новой ветки", {})

        # Вероятности появления новой ветки в зависимости от числа существующих потомков
        self.probabilities = growth.get("вероятности", [0.5, 0.25, 0.15, 0.1, 0.05])
        # Параметры нормального распределения для отклонения азимута новой ветки
        self.azimuth_loc = growth.get("азимут_loc", 0)
        self.azimuth_scale = growth.get("азимут_scale", 25)
        # Количество эпох симуляции
        self.epochs = growth.get("эпох", 40)

    @staticmethod
    def from_json(path: str):
        """Загрузить ДНК из JSON-файла.

        Параметры:
            path: путь к файлу конфигурации.

        Возвращает:
            Экземпляр DNA с параметрами из файла.
        """
        with open(path, encoding="utf-8") as f:
            return DNA(json.load(f))


class Branch:
    """Ветка дерева.

    Каждая ветка имеет возраст, этаж (уровень в иерархии), азимут отклонения
    от родительской ветки, координаты начала и список потомков.

    Вторичные параметры (длина, толщина, цвет, прозрачность) вычисляются
    от возраста по формулам, заданным в ДНК.
    """

    def __init__(self, age, floor, azimuth, start_pos, parent_angle):
        """Инициализация ветки.

        Параметры:
            age: возраст ветки в эпохах (0 — новая, ещё не росла).
            floor: номер этажа (0 — корень, +1 на каждый уровень вложенности).
            azimuth: угол отклонения от направления родительской ветки (градусы).
            start_pos: координаты (x, y) начала ветки.
            parent_angle: абсолютный угол направления родительской ветки (градусы).
        """
        self.age = age
        self.floor = floor
        self.azimuth = azimuth
        self.start_pos = start_pos
        self.parent_angle = parent_angle
        self.children = []  # Список веток-потомков

    @property
    def angle(self):
        """Абсолютный угол направления роста ветки (градусы).

        Вычисляется как сумма угла родительской ветки и собственного азимута.
        """
        return self.parent_angle + self.azimuth

    def length(self, dna):
        """Длина ветки.

        Вычисляется по формуле: length = b * ln(age) + a.
        Для age < 1 (новая ветка) возвращает 0, так как ln(0) не определён.

        Параметры:
            dna: экземпляр DNA с коэффициентами a, b для длины.

        Возвращает:
            Длину ветки в условных единицах.
        """
        if self.age < 1:
            return 0.0
        return dna.length_b * np.log(self.age) + dna.length_a

    def thickness(self, dna):
        """Толщина ветки.

        Вычисляется по формуле: thickness = b * ln(age) + a.
        Для age < 1 возвращает 0.

        Параметры:
            dna: экземпляр DNA с коэффициентами a, b для толщины.

        Возвращает:
            Толщину ветки в условных единицах.
        """
        if self.age < 1:
            return 0.0
        return dna.thickness_b * np.log(self.age) + dna.thickness_a

    def alpha(self, dna):
        """Прозрачность ветки (для отрисовки).

        Линейная интерполяция от alpha_start к alpha_end в зависимости от возраста.

        Параметры:
            dna: экземпляр DNA с параметрами прозрачности.

        Возвращает:
            Значение прозрачности от alpha_start до alpha_end.
        """
        t = min(1.0, self.age / dna.alpha_max_age)
        return dna.alpha_start + t * (dna.alpha_end - dna.alpha_start)

    def color(self, dna):
        """Цвет ветки в формате RGBA (нормализованный под matplotlib, 0–1).

        Цвет линейно интерполируется от начального (зелёный) к конечному (коричневый).
        Компоненты RGB делятся на 255 для совместимости с matplotlib.

        Параметры:
            dna: экземпляр DNA с цветовыми параметрами.

        Возвращает:
            Кортеж (r, g, b, alpha) с компонентами в диапазоне [0, 1].
        """
        t = min(1.0, self.age / dna.color_max_age)
        r = dna.color_start[0] + t * (dna.color_end[0] - dna.color_start[0])
        g = dna.color_start[1] + t * (dna.color_end[1] - dna.color_start[1])
        b = dna.color_start[2] + t * (dna.color_end[2] - dna.color_start[2])
        return (r / 255, g / 255, b / 255, self.alpha(dna))

    def end_pos(self, dna):
        """Координаты конца ветки.

        Вычисляются по направлению (angle) и длине ветки из точки начала.

        Параметры:
            dna: экземпляр DNA (нужен для вычисления длины).

        Возвращает:
            Кортеж (x, y) — координаты конца ветки.
        """
        rad = math.radians(self.angle)
        l = self.length(dna)
        x = self.start_pos[0] + l * math.cos(rad)
        y = self.start_pos[1] + l * math.sin(rad)
        return (x, y)

    def spawn_child(self, dna):
        """Создать новую ветку-потомок.

        Новая ветка имеет возраст 0, этаж на 1 больше родительского.
        Азимут отклоняется на случайную величину из нормального распределения.

        Параметры:
            dna: экземпляр DNA с параметрами азимута.

        Возвращает:
            Новый экземпляр Branch — потомок текущей ветки.
        """
        azb = random.gauss(dna.azimuth_loc, dna.azimuth_scale)
        return Branch(
            age=0,
            floor=self.floor + 1,
            azimuth=self.azimuth + azb,
            start_pos=self.end_pos(dna),
            parent_angle=self.angle,
        )


class Tree:
    """Дерево — контейнер для всех веток и логики роста.

    Содержит корневую ветку, список всех веток для итерации,
    а также методы grow() (одна эпоха роста) и draw() (отрисовка).
    """

    def __init__(self, dna):
        """Инициализация дерева.

        Создаёт корневую ветку в точке (0, 0) с нулевым азимутом,
        этажом 0 и родительским углом 90° (растёт вертикально вверх).

        Параметры:
            dna: экземпляр DNA с параметрами роста.
        """
        self.dna = dna
        self.root = Branch(0, 0, 0, (0, 0), 90)
        self.all_branches = [self.root]
        self.epoch = 0

    def grow(self):
        """Одна эпоха роста дерева.

        Последовательность действий:
        1. Увеличить счётчик эпох.
        2. Увеличить возраст всех существующих веток на 1.
        3. Для каждой ветки — розыгрыш появления новой ветки-потомка
           с вероятностью, зависящей от текущего числа потомков.
        4. Добавить созданные ветки в общий список.
        """
        self.epoch += 1

        # Увеличиваем возраст всех существующих веток
        for branch in self.all_branches:
            branch.age += 1

        # Собираем новые ветки в отдельный список,
        # чтобы не итерироваться по ним в той же эпохе
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
        """Нарисовать дерево на matplotlib-осях.

        Выполняет рекурсивный обход от корня:
        каждая ветка рисуется как отрезок от start_pos до end_pos.
        Толщина линии пропорциональна толщине ветки (scale_factor = 6),
        цвет — RGBA с учётом возраста.

        Параметры:
            ax: matplotlib Axes для отрисовки. Если None, создаются новые.
        """
        if ax is None:
            _, ax = plt.subplots(figsize=(10, 10))

        def _draw(branch):
            """Рекурсивная отрисовка ветки и её потомков."""
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
        ax.axis("off")
        ax.set_title(f"Волшебное дерево — Эпоха {self.epoch}")

    def animate(self):
        """Анимировать рост дерева.

        В интерактивном режиме matplotlib последовательно:
        1. Выполняется grow() (одна эпоха).
        2. Очищаются оси и дерево перерисовывается.
        3. Пауза 0.2 секунды для визуализации.

        После завершения всех эпох финальный кадр остаётся на экране.
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
    """Точка входа: парсинг аргументов, загрузка ДНК, запуск симуляции.

    Поддерживает аргумент -c/--config для указания пути к JSON-конфигу
    (по умолчанию config.json). При ошибках чтения или парсинга файла
    выводит сообщение и завершает работу с кодом 1.
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
