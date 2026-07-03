import json
import math
import random
import sys

import matplotlib.pyplot as plt


class DNA:
    def __init__(self, data: dict):
        phys = data.get("физические параметры роста дерева", {})
        look = data.get("внешний вид", {})
        growth = data.get("параметры начала роста новой ветки", {})

        self.length_a = phys.get("длина", {}).get("a", 2.0)
        self.length_b = phys.get("длина", {}).get("b", 0.05)
        self.thickness_a = phys.get("толщина", {}).get("a", 0.3)
        self.thickness_b = phys.get("толщина", {}).get("b", 0.08)

        self.color_start = tuple(look.get("цвет_начальный", [34, 139, 34]))
        self.color_end = tuple(look.get("цвет_конечный", [139, 69, 19]))

        self.base_prob = growth.get("вероятность_базовая", 0.4)
        self.decay = growth.get("вероятность_затухание", 0.2)
        self.max_children = growth.get("максимум_потомков", 4)
        self.azimuth_min = growth.get("азимут_мин", -40)
        self.azimuth_max = growth.get("азимут_макс", 40)
        self.epochs = growth.get("эпох", 30)


class Branch:
    def __init__(self, age, floor, azimuth, start_pos, parent_angle):
        self.age = age
        self.floor = floor
        self.azimuth = azimuth
        self.start_pos = start_pos
        self.parent_angle = parent_angle
        self.children = []

    @property
    def angle(self):
        return self.parent_angle + self.azimuth

    def end_pos(self, dna):
        rad = math.radians(self.angle)
        length = dna.length_a * (1 - math.exp(-dna.length_b * self.age))
        x = self.start_pos[0] + length * math.cos(rad)
        y = self.start_pos[1] + length * math.sin(rad)
        return (x, y)

    def thickness(self, dna):
        return dna.thickness_a * (1 - math.exp(-dna.thickness_b * self.age))

    def color(self, dna):
        t = min(1.0, self.age / 50.0)
        r = dna.color_start[0] + t * (dna.color_end[0] - dna.color_start[0])
        g = dna.color_start[1] + t * (dna.color_end[1] - dna.color_start[1])
        b = dna.color_start[2] + t * (dna.color_end[2] - dna.color_start[2])
        return (r / 255, g / 255, b / 255)


class Tree:
    def __init__(self, dna):
        self.dna = dna
        self.root = Branch(0, 0, 0, (0, 0), 90)
        self.all_branches = [self.root]
        self.epoch = 0

    def grow(self):
        self.epoch += 1
        new = []

        for branch in self.all_branches:
            branch.age += 1

            n = len(branch.children)
            prob = self.dna.base_prob * (self.dna.decay ** n)

            if random.random() < prob and n < self.dna.max_children:
                offset = random.uniform(self.dna.azimuth_min, self.dna.azimuth_max)
                child = Branch(
                    age=0,
                    floor=branch.floor + 1,
                    azimuth=offset,
                    start_pos=branch.end_pos(self.dna),
                    parent_angle=branch.angle,
                )
                branch.children.append(child)
                new.append(child)

        self.all_branches.extend(new)

    def draw(self, ax=None):
        if ax is None:
            _, ax = plt.subplots(figsize=(10, 10))

        def draw_branch(branch):
            end = branch.end_pos(self.dna)
            w = max(0.5, branch.thickness(self.dna) * 6)
            c = branch.color(self.dna)
            ax.plot(
                [branch.start_pos[0], end[0]],
                [branch.start_pos[1], end[1]],
                color=c, linewidth=w, solid_capstyle="round",
            )
            for child in branch.children:
                draw_branch(child)

        draw_branch(self.root)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(f"Волшебное дерево — Эпоха {self.epoch}")


def load_config(path):
    with open(path, encoding="utf-8") as f:
        return DNA(json.load(f))


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "config.json"

    try:
        dna = load_config(path)
    except FileNotFoundError:
        print(f"Ошибка: файл {path} не найден")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Ошибка JSON: {e}")
        sys.exit(1)

    tree = Tree(dna)

    for _ in range(dna.epochs):
        tree.grow()

    tree.draw()
    plt.show()


if __name__ == "__main__":
    main()
