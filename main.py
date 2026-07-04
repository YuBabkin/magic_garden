import json
import math
import random
import sys

import matplotlib.pyplot as plt
import numpy as np


class DNA:
    def __init__(self, data: dict):
        phys = data.get("физические параметры роста дерева", {})
        look = data.get("внешний вид", {})
        growth = data.get("параметры начала роста новой ветки", {})

        self.length_a = phys.get("длина", {}).get("a", 2.0)
        self.length_b = phys.get("длина", {}).get("b", 1.0)
        self.thickness_a = phys.get("толщина", {}).get("a", 0.3)
        self.thickness_b = phys.get("толщина", {}).get("b", 0.2)

        self.color_start = tuple(look.get("цвет_начальный", [34, 139, 34]))
        self.color_end = tuple(look.get("цвет_конечный", [139, 69, 19]))
        self.color_max_age = look.get("макс_возраст_цвета", 50)

        self.alpha_start = look.get("alpha_start", 0.2)
        self.alpha_end = look.get("alpha_end", 1.0)
        self.alpha_max_age = look.get("макс_возраст_alpha", 20)

        self.probabilities = growth.get("вероятности", [0.5, 0.25, 0.15, 0.1, 0.05])
        self.azimuth_loc = growth.get("азимут_loc", 0)
        self.azimuth_scale = growth.get("азимут_scale", 25)
        self.epochs = growth.get("эпох", 40)


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

    def length(self, dna):
        if self.age < 1:
            return 0.0
        return dna.length_b * np.log(self.age) + dna.length_a

    def end_pos(self, dna):
        rad = math.radians(self.angle)
        l = self.length(dna)
        x = self.start_pos[0] + l * math.cos(rad)
        y = self.start_pos[1] + l * math.sin(rad)
        return (x, y)

    def thickness(self, dna):
        if self.age < 1:
            return 0.0
        return dna.thickness_b * np.log(self.age) + dna.thickness_a

    def alpha(self, dna):
        t = min(1.0, self.age / dna.alpha_max_age)
        return dna.alpha_start + t * (dna.alpha_end - dna.alpha_start)

    def color(self, dna):
        t = min(1.0, self.age / dna.color_max_age)
        r = dna.color_start[0] + t * (dna.color_end[0] - dna.color_start[0])
        g = dna.color_start[1] + t * (dna.color_end[1] - dna.color_start[1])
        b = dna.color_start[2] + t * (dna.color_end[2] - dna.color_start[2])
        return (r / 255, g / 255, b / 255, self.alpha(dna))


class Tree:
    def __init__(self, dna):
        self.dna = dna
        self.root = Branch(0, 0, 0, (0, 0), 90)
        self.all_branches = [self.root]
        self.epoch = 0

    def grow(self):
        self.epoch += 1

        for branch in self.all_branches:
            branch.age += 1

        new_branches = []

        for branch in self.all_branches:
            n = len(branch.children)
            prob = self.dna.probabilities[n] if n < len(self.dna.probabilities) else 0.0

            if random.random() < prob:
                alpha = random.gauss(self.dna.azimuth_loc, self.dna.azimuth_scale)
                child = Branch(
                    age=0,
                    floor=branch.floor + 1,
                    azimuth=branch.azimuth + alpha,
                    start_pos=branch.end_pos(self.dna),
                    parent_angle=branch.angle,
                )
                branch.children.append(child)
                new_branches.append(child)

        self.all_branches.extend(new_branches)

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
