import argparse
import json
import math
import random
import sys

import pygame

from aspiration import step_relative


class DNA:
    def __init__(self, data: dict):
        phys = data.get("физические параметры роста дерева", {})

        length_params = phys.get("длина", {})
        self.length_a = length_params.get("a", 2.0)
        self.length_b = length_params.get("b", 1.5)

        thickness_params = phys.get("толщина", {})
        self.thickness_a = thickness_params.get("a", 0.3)
        self.thickness_b = thickness_params.get("b", 0.4)

        look = data.get("внешний вид дерева", {})

        self.color_start = tuple(look.get("цвет_начальный", [34, 139, 34]))
        self.color_end = tuple(look.get("цвет_конечный", [139, 69, 19]))
        self.color_max_age = look.get("макс_возраст_цвета", 50)

        self.alpha_start = look.get("прозрачность_начальная", 0.2)
        self.alpha_end = look.get("прозрачность_конечная", 1.0)
        self.alpha_max_age = look.get("макс_возраст_прозрачности", 20)

        dna_params = data.get("ДНК", {})

        self.probabilities = dna_params.get("вероятность", [0.5, 0.25, 0.15, 0.1, 0.05])
        self.azimuth_loc = dna_params.get("азимут_среднее", [0, 0, 0, 0, 0])
        self.azimuth_scale = dna_params.get("азимут_отклонение", [25, 25, 25, 25, 25])
        self.twist_loc = dna_params.get("скручивание_среднее", [0, 0, 0, 0, 0])
        self.twist_scale = dna_params.get("скручивание_отклонение", [0, 0, 0, 0, 0])
        self.aspiration = dna_params.get("стремление", [0, 0, 0, 0, 0])
        self.aspiration_strength = dna_params.get("сила стремления", [0.0, 0.0, 0.0, 0.0, 0.0])
        self.epochs = dna_params.get("эпох", 40)

        viz = data.get("визуализация", {})

        self.window_width = viz.get("ширина_окна", 1000)
        self.window_height = viz.get("высота_окна", 800)
        self.sky_background = tuple(viz.get("цвет_неба", [230, 245, 255]))
        self.ground_background = tuple(viz.get("цвет_земли", [100, 180, 80]))
        self.ground_height = viz.get("высота_земли", 0.25)

    @staticmethod
    def from_json(path: str):
        with open(path, encoding="utf-8") as f:
            return DNA(json.load(f))


class Branch:
    def __init__(self, age, floor, azimuth, parent_azimuth, parent=None, twist=0.0,
                 aspiration=0.0, aspiration_strength=0.0):
        self.age = age
        self.floor = floor
        self.azimuth = azimuth
        self.parent_azimuth = parent_azimuth
        self.parent = parent
        self.twist = twist
        self.aspiration = aspiration
        self.aspiration_strength = aspiration_strength
        self.children = []

    def start_pos(self, dna):
        if self.parent is None:
            return (0.0, 0.0)
        return self.parent.end_pos(dna)

    @property
    def angle(self):
        return self.parent_azimuth + self.azimuth + self.twist

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
        x = s[0] + l * math.sin(rad)
        y = s[1] + l * math.cos(rad)
        return (x, y)

    def spawn_child(self, dna, n):
        loc = dna.azimuth_loc[n] if n < len(dna.azimuth_loc) else dna.azimuth_loc[-1]
        scale = dna.azimuth_scale[n] if n < len(dna.azimuth_scale) else dna.azimuth_scale[-1]
        deviation = random.choice([-1, 1]) * abs(random.gauss(loc, scale))
        twist_loc = dna.twist_loc[n] if n < len(dna.twist_loc) else dna.twist_loc[-1]
        twist_scale = dna.twist_scale[n] if n < len(dna.twist_scale) else dna.twist_scale[-1]

        twist = self.twist + random.gauss(twist_loc, twist_scale)

        if n == 0:
            aspiration = self.aspiration
            aspiration_strength = self.aspiration_strength
        else:
            aspiration = dna.aspiration[n] if n < len(dna.aspiration) else dna.aspiration[-1]
            aspiration = random.choice([-1, 1]) * abs(aspiration)
            aspiration_strength = dna.aspiration_strength[n] if n < len(dna.aspiration_strength) else dna.aspiration_strength[-1]
            aspiration_strength = min(1.0, max(0.0, aspiration_strength))

        angle = self.angle + deviation + twist
        angle = step_relative(angle, aspiration, aspiration_strength)

        return Branch(
            age=n,
            floor=self.floor + 1,
            azimuth=angle - self.angle - twist,
            parent_azimuth=self.angle,
            parent=self,
            twist=twist,
            aspiration=aspiration,
            aspiration_strength=aspiration_strength
        )


class Tree:
    def __init__(self, dna):
        self.dna = dna
        root_aspiration = dna.aspiration[0] if dna.aspiration else 0.0
        root_aspiration = random.choice([-1, 1]) * abs(root_aspiration)
        root_strength = dna.aspiration_strength[0] if dna.aspiration_strength else 0.0
        root_strength = min(1.0, max(0.0, root_strength))
        self.root = Branch(
            age=0,
            floor=0,
            azimuth=0,
            parent_azimuth=0,
            aspiration=root_aspiration,
            aspiration_strength=root_strength
        )
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
                child = branch.spawn_child(self.dna, n)
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

    def animate(self):
        width, height = self.dna.window_width, self.dna.window_height

        pygame.init()
        pygame.display.set_mode((width, height), pygame.RESIZABLE)
        pygame.display.set_caption("Волшебное дерево")
        font = pygame.font.SysFont("Arial", 24)
        small_font = pygame.font.SysFont("Arial", 18)

        try:
            from pygame._sdl2 import video as sdl2_video

            window = sdl2_video.Window.from_display_module()
        except Exception:
            window = None

        fullscreen = False
        maximized = False
        tree_surface = None

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
                    elif event.key == pygame.K_F11:
                        fullscreen = not fullscreen
                        if window is not None:
                            if fullscreen:
                                window.set_fullscreen(True)
                            else:
                                window.set_windowed()
                        else:
                            if fullscreen:
                                desktop = pygame.display.Info()
                                pygame.display.set_mode(
                                    (desktop.current_w, desktop.current_h), pygame.FULLSCREEN
                                )
                            else:
                                pygame.display.set_mode((width, height), pygame.RESIZABLE)
                    elif event.key == pygame.K_F10 and window is not None:
                        maximized = not maximized
                        if maximized:
                            window.maximize()
                        else:
                            window.restore()

            if not finished and not paused:
                self.grow()

            screen = pygame.display.get_surface()
            new_width, new_height = screen.get_size()
            if (new_width, new_height) != (width, height):
                width, height = new_width, new_height
                tree_surface = None
            if tree_surface is None:
                tree_surface = pygame.Surface((width, height), pygame.SRCALPHA)

            tree_surface.fill((0, 0, 0, 0))
            self.draw(tree_surface, width, height)

            ground_sy = int(height * (1 - self.dna.ground_height))

            screen.fill(self.dna.sky_background)
            pygame.draw.rect(screen, self.dna.ground_background, (0, ground_sy, width, height - ground_sy))
            pygame.draw.line(screen, (80, 140, 60), (0, ground_sy), (width, ground_sy), 3)

            screen.blit(tree_surface, (0, 0))

            info = f"Эпоха {self.epoch}/{self.dna.epochs}"
            text_surface = font.render(info, True, (30, 30, 30))
            screen.blit(text_surface, (15, 15))

            hint = "Пробел — пауза, F10 — развернуть окно, F11 — полный экран, ESC — выход"
            hint_surface = small_font.render(hint, True, (120, 120, 120))
            screen.blit(hint_surface, (15, 48))

            if finished:
                done_surface = small_font.render("Симуляция завершена. ESC — выход.", True, (100, 100, 100))
                screen.blit(done_surface, (15, 72))
            elif paused:
                pause_surface = small_font.render("ПАУЗА. Пробел — продолжить.", True, (100, 100, 100))
                screen.blit(pause_surface, (15, 72))

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
