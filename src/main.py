import argparse
import json
import math
import random
import sys

import pygame


class DNA:
    def __init__(self, data: dict):
        phys = data.get("физические параметры роста дерева", {})

        length_params = phys.get("длина", {})
        self.length_a = length_params.get("a", 2.0)
        self.length_b = length_params.get("b", 1.5)

        thickness_params = phys.get("толщина", {})
        self.thickness_a = thickness_params.get("a", 0.3)
        self.thickness_b = thickness_params.get("b", 0.4)

        look = data.get("внешний вид", {})

        self.color_start = tuple(look.get("цвет_начальный", [34, 139, 34]))
        self.color_end = tuple(look.get("цвет_конечный", [139, 69, 19]))
        self.color_max_age = look.get("макс_возраст_цвета", 50)

        self.alpha_start = look.get("alpha_start", 0.2)
        self.alpha_end = look.get("alpha_end", 1.0)
        self.alpha_max_age = look.get("макс_возраст_alpha", 20)

        growth = data.get("параметры начала роста новой ветки", {})

        self.probabilities = growth.get("вероятности", [0.5, 0.25, 0.15, 0.1, 0.05])
        self.azimuth_loc = growth.get("азимут_loc", 0)
        self.azimuth_scale = growth.get("азимут_scale", 25)
        self.epochs = growth.get("эпох", 40)

    @staticmethod
    def from_json(path: str):
        with open(path, encoding="utf-8") as f:
            return DNA(json.load(f))


class Branch:
    def __init__(self, age, floor, azimuth, parent_angle, parent=None):
        self.age = age
        self.floor = floor
        self.azimuth = azimuth
        self.parent_angle = parent_angle
        self.parent = parent
        self.children = []

    def start_pos(self, dna):
        if self.parent is None:
            return (0.0, 0.0)
        return self.parent.end_pos(dna)

    @property
    def angle(self):
        return self.parent_angle + self.azimuth

    def length(self, dna):
        if self.age < 1:
            return 0.0
        return dna.length_b * math.log(self.age) + dna.length_a

    def thickness(self, dna):
        if self.age < 1:
            return 0.0
        return dna.thickness_b * math.log(self.age) + dna.thickness_a

    def alpha(self, dna):
        t = min(1.0, self.age / dna.alpha_max_age)
        return dna.alpha_start + t * (dna.alpha_end - dna.alpha_start)

    def color(self, dna):
        t = min(1.0, self.age / dna.color_max_age)
        r = dna.color_start[0] + t * (dna.color_end[0] - dna.color_start[0])
        g = dna.color_start[1] + t * (dna.color_end[1] - dna.color_start[1])
        b = dna.color_start[2] + t * (dna.color_end[2] - dna.color_start[2])
        a = self.alpha(dna)
        return (int(r), int(g), int(b), int(a * 255))

    def end_pos(self, dna):
        rad = math.radians(self.angle)
        l = self.length(dna)
        s = self.start_pos(dna)
        x = s[0] + l * math.cos(rad)
        y = s[1] + l * math.sin(rad)
        return (x, y)

    def spawn_child(self, dna):
        deviation = random.gauss(dna.azimuth_loc, dna.azimuth_scale)
        return Branch(
            age=0,
            floor=self.floor + 1,
            azimuth=deviation,
            parent_angle=self.angle,
            parent=self,
        )


class Tree:
    def __init__(self, dna):
        self.dna = dna
        self.root = Branch(age=0, floor=0, azimuth=0, parent_angle=90)
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
                child = branch.spawn_child(self.dna)
                branch.children.append(child)
                new_branches.append(child)

        self.all_branches.extend(new_branches)

    def bounds(self):
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        for branch in self.all_branches:
            s = branch.start_pos(self.dna)
            e = branch.end_pos(self.dna)
            min_x = min(min_x, s[0], e[0])
            max_x = max(max_x, s[0], e[0])
            min_y = min(min_y, s[1], e[1])
            max_y = max(max_y, s[1], e[1])
        return min_x, min_y, max_x, max_y

    def draw(self, surface, width, height):
        min_x, min_y, max_x, max_y = self.bounds()

        range_x = max_x - min_x
        range_y = max_y - min_y
        if range_x < 0.1:
            range_x = 80
            min_x = -40
            max_x = 40
        if range_y < 0.1:
            range_y = 90
            min_y = -10
            max_y = 80

        margin = 0.15
        range_x *= 1 + 2 * margin
        range_y *= 1 + 2 * margin
        min_x -= range_x * margin
        max_x += range_x * margin
        min_y -= range_y * margin
        max_y += range_y * margin

        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        scale = min(width / (max_x - min_x), height / (max_y - min_y))

        def to_screen(pos):
            sx = width / 2 + (pos[0] - center_x) * scale
            sy = height / 2 - (pos[1] - center_y) * scale
            return sx, sy

        def _draw(branch):
            end = branch.end_pos(self.dna)
            w = max(1, int(branch.thickness(self.dna) * 6))
            c = branch.color(self.dna)
            s = branch.start_pos(self.dna)
            s_screen = to_screen(s)
            e_screen = to_screen(end)
            pygame.draw.line(surface, c, s_screen, e_screen, w)

            for child in branch.children:
                _draw(child)

        _draw(self.root)

        ground_sy = to_screen((0, 0))[1]
        return ground_sy

    def animate(self):
        WIDTH, HEIGHT = 1000, 800

        pygame.init()
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Волшебное дерево")
        font = pygame.font.SysFont("Arial", 24)
        small_font = pygame.font.SysFont("Arial", 18)

        tree_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

        finished = False
        paused = False
        running = True

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE and not finished:
                        paused = not paused
                    elif event.key == pygame.K_ESCAPE:
                        running = False

            if not finished and not paused:
                self.grow()

            tree_surface.fill((0, 0, 0, 0))
            ground_sy = self.draw(tree_surface, WIDTH, HEIGHT)

            screen.fill((230, 245, 255))
            pygame.draw.rect(screen, (100, 180, 80), (0, int(ground_sy), WIDTH, HEIGHT - int(ground_sy)))
            pygame.draw.line(screen, (80, 140, 60), (0, int(ground_sy)), (WIDTH, int(ground_sy)), 3)

            screen.blit(tree_surface, (0, 0))

            info = f"Эпоха {self.epoch}/{self.dna.epochs}"
            text_surface = font.render(info, True, (30, 30, 30))
            screen.blit(text_surface, (15, 15))

            if finished:
                done_surface = small_font.render("Симуляция завершена. ESC — выход.", True, (100, 100, 100))
                screen.blit(done_surface, (15, 50))
            elif paused:
                pause_surface = small_font.render("ПАУЗА. Пробел — продолжить.", True, (100, 100, 100))
                screen.blit(pause_surface, (15, 50))

            pygame.display.flip()

            if not finished and not paused:
                if self.epoch >= self.dna.epochs:
                    finished = True
                else:
                    pygame.time.wait(200)

        pygame.quit()


def main():
    parser = argparse.ArgumentParser(
        description="Моделирование роста волшебного дерева",
    )
    parser.add_argument(
        "epochs", nargs="?", type=int, default=None,
        help="количество эпох (переопределяет значение из config.json)",
    )
    parser.add_argument(
        "-c", "--config", default="src/config.json",
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

    if args.epochs is not None:
        dna.epochs = args.epochs

    tree = Tree(dna)
    tree.animate()


if __name__ == "__main__":
    main()
