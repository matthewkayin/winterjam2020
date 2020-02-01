import pygame
import sys
import os
import math
import random

# Handle cli flags
windowed = "--windowed" in sys.argv
show_fps = "--showfps" in sys.argv
if "--debug" in sys.argv:
    windowed = True
    show_fps = True


# Resolution variables, Display is streched to match Screen which can be set by user
DISPLAY_WIDTH = 1280
DISPLAY_HEIGHT = 720
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720

if os.path.isfile("data/settings.txt"):
    print("Settings file found!")
    video_settings = open("data/settings.txt").read().splitlines()
    for line in video_settings:
        if line.startswith("resolution="):
            SCREEN_WIDTH = int(line[line.index("=") + 1:line.index("x")])
            SCREEN_HEIGHT = int(line[line.index("x") + 1:])
            aspect_ratio = SCREEN_WIDTH / SCREEN_HEIGHT
            if aspect_ratio == 4 / 3:
                DISPLAY_HEIGHT = 960
            elif aspect_ratio == 16 / 10:
                DISPLAY_HEIGHT = 840
            elif aspect_ratio == 16 / 9:
                DISPLAY_HEIGHT = 720
else:
    print("No settings file found!")
print("Resolution set to " + str(SCREEN_WIDTH) + "x" + str(SCREEN_HEIGHT) + ".")

SCALE = SCREEN_WIDTH / DISPLAY_WIDTH

# Timing variables
TARGET_FPS = 60
SECOND = 1000
UPDATE_TIME = SECOND / 60.0
fps = 0
frames = 0
dt = 0
before_time = 0
before_sec = 0

# Init pygame
os.environ['SDL_VIDEO_CENTERED'] = '1'
pygame.init()
global screen
if windowed:
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), 0, 32)
else:
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.FULLSCREEN)
display = pygame.Surface((DISPLAY_WIDTH, DISPLAY_HEIGHT))
clock = pygame.time.Clock()


# Input variables
input_queue = []
input_states = {"player up": False, "player right": False, "player down": False, "player left": False, "left click": False}
mouse_x = 0
mouse_y = 0


# Color variables
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
PURPLE = (255, 0, 255)
YELLOW = (255, 255, 0)


# Images
image_path = "res/gfx/"
image_cache = {}


def get_sprite(path, index, size):
    base_sheet = get_image(path, True)
    coords = (0, 0)
    while index != 0:
        coords = (coords[0] + size[0], coords[1])
        if coords[0] >= base_sheet.get_width():
            coords = (0, coords[1] + size[1])
            if size[1] >= base_sheet.get_height():
                print("Spritesheet index out of range! " + path + ", " + str(index))
        index -= 1
    return base_sheet.subsurface(coords[0], coords[1], size[0], size[1])


def get_image(path, has_alpha, alpha=255, subrect=None):
    global image_cache

    if path not in image_cache.keys():
        if has_alpha:
            image_cache[path] = pygame.image.load(image_path + path + ".png").convert_alpha()
        else:
            image_cache[path] = pygame.image.load(image_path + path + ".png").convert()

    return_path = path
    if alpha != 255:
        return_path = path + "&alpha=" + str(alpha)
        if return_path not in image_cache.keys():
            new_image = image_cache[path].copy()
            new_image.fill((255, 255, 255, alpha), None, pygame.BLEND_RGBA_MULT)
            image_cache[return_path] = new_image

    if subrect is not None:
        return image_cache[return_path].subsurface(pygame.Rect(subrect))
    else:
        return image_cache[return_path]


def rotate_image(image, angle, origin_pos=None):
    if origin_pos is None:
        origin_pos = image.get_rect().center

    # calculate the axis aligned bounding box of the rotated image
    w, h = image.get_size()
    box = [pygame.math.Vector2(p) for p in [(0, 0), (w, 0), (w, -h), (0, -h)]]
    box_rotate = [p.rotate(angle) for p in box]
    min_box = (min(box_rotate, key=lambda p: p[0])[0], min(box_rotate, key=lambda p: p[1])[1])
    max_box = (max(box_rotate, key=lambda p: p[0])[0], max(box_rotate, key=lambda p: p[1])[1])

    # calculate the translation of the pivot
    pivot = pygame.math.Vector2(origin_pos[0], -origin_pos[1])
    pivot_rotate = pivot.rotate(angle)
    pivot_move = pivot_rotate - pivot

    rotated_image = pygame.transform.rotate(image, angle)
    offset = (int(min_box[0] - origin_pos[0] - pivot_move[0]), int(pivot_move[1] - max_box[1] - origin_pos[1]))

    return rotated_image, offset


class Animation():
    def __init__(self, spritesheet, size, frames, frame_duration):
        self.spritesheet = spritesheet
        self.size = size
        self.frames = frames
        self.frame_duration = frame_duration
        self.index = 0
        self.timer = 0

    def reset(self):
        self.index = 0
        self.timer = 0

    def update(self, dt):
        self.timer += dt
        if self.timer >= self.frame_duration:
            self.timer -= self.frame_duration
            self.index += 1
            if self.index >= self.frames:
                self.index = 0

    def get_image(self):
        return get_sprite(self.spritesheet, self.index, self.size)


# Fonts
font_small = pygame.font.SysFont("Serif", 11)
font_dialog = pygame.font.Font("res/ttf/oxygen.ttf", 32)


def split_dialog(dialog):
    result_dialog = []
    while len(dialog) > 52:
        split_point = 52
        if dialog[split_point - 1] != ' ' and dialog[split_point] != ' ':
            split_point = dialog[:split_point].rfind(' ') + 1
        result_dialog.append(dialog[:split_point])
        dialog = dialog[split_point:]
        if dialog[0] == ' ':
            dialog = dialog[1:]
    if dialog != "":
        result_dialog.append(dialog)

    return result_dialog

# game states
EXIT = -1
MAIN_LOOP = 0


def get_distance(point1, point2):
    return math.sqrt(((point2[0] - point1[0]) ** 2) + ((point2[1] - point1[1]) ** 2))


def sum_vectors(a, b):
    return (a[0] + b[0], a[1] + b[1])


def scale_vector(old_vector, new_magnitude):
    old_magnitude = math.sqrt((old_vector[0] ** 2) + (old_vector[1] ** 2))
    if old_magnitude == 0:
        return (0, 0)
    scale = new_magnitude / old_magnitude
    new_x = old_vector[0] * scale
    new_y = old_vector[1] * scale
    return (new_x, new_y)


def get_center(rect):
    return ((rect[0] + (rect[2] // 2)), (rect[1] + (rect[3] // 2)))


def rects_collide(rect1, rect2):
    r1_center_x, r1_center_y = get_center(rect1)
    r2_center_x, r2_center_y = get_center(rect2)
    return abs(r1_center_x - r2_center_x) * 2 < rect1[2] + rect2[2] and abs(r1_center_y - r2_center_y) * 2 < rect1[3] + rect2[3]


def point_in_rect(point, rect):
    return rects_collide((point[0], point[1], 1, 1), rect)


def get_point_angle(point1, point2):
    xdiff = point2[0] - point1[0]
    ydiff = point2[1] - point1[1]
    angle = math.degrees(math.atan2(ydiff, xdiff))
    if angle > 0:
        angle = 360 - angle
    elif angle < 0:
        angle *= -1

    return angle


class Entity():
    def __init__(self, size):

        self.rotation = None
        self.offset_x = 0
        self.offset_y = 0
        self.x = 0
        self.y = 0
        self.width, self.height = size
        self.vx = 0
        self.vy = 0

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt

    def get_x(self):
        return int(round(self.x)) + self.offset_x

    def get_y(self):
        return int(round(self.y)) + self.offset_y

    def get_rect(self):
        return (self.x, self.y, self.width, self.height)

    def get_center(self):
        return (self.x + self.width // 2, self.y + self.height // 2)

    def collides(self, other):
        return rects_collide(self.get_rect(), other)

    def check_collision(self, dt, collider):
        """
        This checks for a collision with a wall-like object and handles it if necessary
        """
        collides = False

        if self.collides(collider):
            collides = True

            x_step = self.vx * dt
            y_step = self.vy * dt

            # Since there was a collision, rollback our previous movement
            self.x -= x_step
            self.y -= y_step

            # Check to see if that collision happened due to x movement
            self.x += x_step
            x_caused_collision = self.collides(collider)
            self.x -= x_step

            # Check to see if that collision happened due to y movement
            self.y += y_step
            y_caused_collision = self.collides(collider)
            self.y -= y_step

            # If x/y didn't cause collision, we can move in x/y direction
            if not x_caused_collision:
                self.x += x_step
            if not y_caused_collision:
                self.y += y_step

        # This is for if we want to override the function and add extra behavior to the collision
        return collides


def game():
    running = True

    player = Entity((120, 160))
    player.x, player.y = (968, 3922)
    player_dx, player_dy = (0, 0)
    player_speed = 3
    player_animation = [Animation("mouse-walk", (120, 160), 6, 4), Animation("mouse-front", (120, 160), 3, 8), Animation("mouse-back", (120, 160), 3, 8)]
    player_animation_index = 0
    most_recent_dx = 0

    disp_dialog = False
    dialog_buffer = []
    display_dialog_one = ""
    display_dialog_two = ""
    dialog_one = ""
    dialog_two = ""
    dialog_timer = 0
    dialog_char_rate = 4

    dialog_index = -1
    dialog_questions = ["What is your name?", "Do you know who the heck has the corona virus?", "You wanna buy some deathsticks?"]
    kill_prompt = False

    npcs = []
    npc_behaviors = []
    npc_animations = []
    npc_dialogs = []

    npcs.append(Entity((100, 160)))
    npcs[0].x, npcs[0].y = (1354, 3243)
    npc_behaviors.append([True, False])
    npc_animations.append(Animation("bunny", (100, 160), 3, 16))
    npc_dialogs.append(["Hello frens I am a lil mouse what is your name? I need to add more characters so that we can test this. And this is the second sentence. I think we should add sentences like this seperately so as not to interrupt a sentance mid box. Actually just kidding.", "My name is bunny and I am a fren", "It's not heckin me lol pls no kill", "You don't want to sell me deathsticks."])

    npcs.append(Entity((100, 160)))
    npcs[1].x, npcs[1].y = (1480, 2340)
    npc_behaviors.append([True, 0.5, (npcs[1].x, npcs[1].y), (1913, 2340)])
    npc_animations.append(Animation("turtle", (100, 160), 4, 16))
    npc_dialogs.append(["Hello frens I am a lil mouse what is your name? I need to add more characters so that we can test this. And this is the second sentence. I think we should add sentences like this seperately so as not to interrupt a sentance mid box. Actually just kidding.", "My name is bunny and I am a fren", "It's not heckin me lol pls no kill", "You don't want to sell me deathsticks."])

    sick_npc = random.randint(0, len(npcs) - 1)
    chosen_npc = -1

    success_message = "Wow you heckin did it you found the right boi. The town is saved, but he is dead, which is sad."
    failed_message = "Wow you fucking monster you actually killed him you killed him and he wasn't even the right one you sick fuck I hope you're happy."
    end_message = ""
    end_message_buffer = []
    end_message_display = []
    end_screen_surface = None
    fade_alpha = 0
    fade_alpha_inc_rate = 0

    camera_x, camera_y = (0, 0)
    screen_center = (DISPLAY_WIDTH // 2, DISPLAY_HEIGHT // 2)
    camera_offset_x, camera_offset_y = (player.width // 2) - screen_center[0], (player.height // 2) - screen_center[1]
    mouse_sensitivity = 0.1

    map_colliders = []
    map_colliders.append((0, 0, 612, 4096))
    map_colliders.append((3478, 0, 618, 4096))
    map_colliders.append((1466, 0, 1154, 898))
    map_colliders.append((1470, 1478, 1150, 856))
    map_colliders.append((1476, 3196, 1144, 900))
    map_colliders.append((0, -1, 4096, 1))
    map_colliders.append((0, 4096, 4096, 1))

    print(sick_npc)

    while running:
        # Handle input
        handle_input()
        while len(input_queue) != 0:
            event = input_queue.pop()
            if event == ("player up", True):
                player_dy = -1
            elif event == ("player right", True):
                player_dx = 1
            elif event == ("player down", True):
                player_dy = 1
            elif event == ("player left", True):
                player_dx = -1
            elif event == ("player up", False):
                if input_states["player down"]:
                    player_dy = 1
                else:
                    player_dy = 0
            elif event == ("player right", False):
                if input_states["player left"]:
                    player_dx = -1
                else:
                    player_dx = 0
            elif event == ("player down", False):
                if input_states["player up"]:
                    player_dy = -1
                else:
                    player_dy = 0
            elif event == ("player left", False):
                if input_states["player right"]:
                    player_dx = 1
                else:
                    player_dx = 0
            elif event == ("kill", True):
                if not kill_prompt and disp_dialog and dialog_one == "" and dialog_two == "" and len(dialog_buffer) == 0:
                    kill_prompt = True
                    dialog_buffer = split_dialog("Are you sure you want to kill <Actually put NPC name here>?")
                    display_dialog_one = ""
                    display_dialog_two = ""
                    dialog_one = dialog_buffer[0]
                    if len(dialog_buffer) > 1:
                        dialog_two = dialog_buffer[1]
                        dialog_buffer = dialog_buffer[2:]
                    else:
                        dialog_two = ""
                        dialog_buffer = []
            elif event == ("left click", True):
                if chosen_npc != -1:
                    text = font_dialog.render("Exit", False, WHITE)
                    rect = (screen_center[0] - (text.get_width() // 2) - 10, int(DISPLAY_HEIGHT * 0.75) - 5, text.get_width() + 20, text.get_height() + 10)
                    if point_in_rect((mouse_x, mouse_y), rect):
                        sys.exit()
                    continue
                if disp_dialog:
                    if dialog_one == "" and dialog_two == "":
                        if len(dialog_buffer) == 0:
                            if kill_prompt:
                                for i in range(0, 2):
                                    if point_in_rect((mouse_x, mouse_y), (int(1280 * 0.1), DISPLAY_HEIGHT - 250 + (70 * i), int(1280 * 0.8), 60)):
                                        if i == 0:
                                            chosen_npc = dialog_index
                                            if chosen_npc == sick_npc:
                                                end_message_buffer = split_dialog(success_message)
                                            else:
                                                end_message_buffer = split_dialog(failed_message)
                                            end_screen_surface = display.copy()
                                            fade_alpha = 0
                                            npc_target_x = screen_center[0] - (npcs[chosen_npc].width // 2) + camera_x
                                            npc_target_y = screen_center[1] - (npcs[chosen_npc].height // 2) + camera_y
                                            npc_x = npcs[chosen_npc].x
                                            npc_y = npcs[chosen_npc].y
                                            fade_alpha_inc_rate = 255 / (get_distance((npc_x, npc_y), (npc_target_x, npc_target_y)) / 3)
                                        else:
                                            kill_prompt = False
                                            disp_dialog = False
                                            display_dialog_one = ""
                                            display_dialog_two = ""
                                            dialog_one = ""
                                            dialog_two = ""
                                            dialog_buffer = []
                                            dialog_index = -1
                            else:
                                clicked_dialog = False
                                for i in range(0, len(dialog_questions)):
                                    if point_in_rect((mouse_x, mouse_y), (int(1280 * 0.1), DISPLAY_HEIGHT - 250 + (70 * i), int(1280 * 0.8), 60)):
                                        dialog_buffer = split_dialog(npc_dialogs[dialog_index][i + 1])
                                        display_dialog_one = ""
                                        display_dialog_two = ""
                                        dialog_one = dialog_buffer[0]
                                        if len(dialog_buffer) > 1:
                                            dialog_two = dialog_buffer[1]
                                            dialog_buffer = dialog_buffer[2:]
                                        else:
                                            dialog_two = ""
                                            dialog_buffer = []
                                        clicked_dialog = True
                                        break
                                if not clicked_dialog:
                                    disp_dialog = False
                                    dialog_index = -1
                        else:
                            dialog_one = dialog_buffer[0]
                            if len(dialog_buffer) > 1:
                                dialog_two = dialog_buffer[1]
                                dialog_buffer = dialog_buffer[2:]
                            else:
                                dialog_two = ""
                                dialog_buffer = []
                            display_dialog_one = ""
                            display_dialog_two = ""
                    else:
                        display_dialog_one += dialog_one
                        display_dialog_two += dialog_two
                        dialog_one = ""
                        dialog_two = ""
                else:
                    for i in range(0, len(npcs)):
                        if point_in_rect((mouse_x + camera_x, mouse_y + camera_y), npcs[i].get_rect()) and get_distance(player.get_center(), npcs[i].get_center()) <= 200:
                            dialog_index = i
                            if len(npc_behaviors[i]) == 4:
                                npc_animations[dialog_index].reset()
                            dialog = npc_dialogs[dialog_index][0]
                            dialog_buffer = split_dialog(dialog)
                            display_dialog_one = ""
                            display_dialog_two = ""
                            dialog_one = dialog_buffer[0]
                            if len(dialog_buffer) > 1:
                                dialog_two = dialog_buffer[1]
                                dialog_buffer = dialog_buffer[2:]
                            else:
                                dialog_two = ""
                                dialog_buffer = []
                            disp_dialog = True
                            player_dx, player_dy = (0, 0)

        # Update
        if chosen_npc == -1:
            if disp_dialog:
                if (player_dx, player_dy) != (0, 0):
                    disp_dialog = False
                    dialog_one = ""
                    dialog_two = ""
                    display_dialog_one = ""
                    display_dialog_two = ""
                    dialog_buffer = []
                    dialog_index = -1
                else:
                    if dialog_one != "":
                        dialog_timer += dt
                        if dialog_timer >= dialog_char_rate:
                            dialog_timer -= dialog_char_rate
                            display_dialog_one += dialog_one[0]
                            dialog_one = dialog_one[1:]
                    elif dialog_two != "":
                        dialog_timer += dt
                        if dialog_timer >= dialog_char_rate:
                            dialog_timer -= dialog_char_rate
                            display_dialog_two += dialog_two[0]
                            dialog_two = dialog_two[1:]

            # update player
            if player_dx != 0:
                most_recent_dx = player_dx
            player.vx, player.vy = scale_vector((player_dx, player_dy), player_speed)
            player.update(dt)
            for collider in map_colliders:
                player.check_collision(dt, collider)
            for i in range(0, len(npcs)):
                player.check_collision(dt, npcs[i].get_rect())
            if (player.vx, player.vy) == (0, 0):
                for animation in player_animation:
                    animation.reset()
            else:
                if player_animation_index == 0 and player_dx == 0:
                    if player_dy == 1:
                        player_animation_index = 1
                    elif player_dy == -1:
                        player_animation_index = 2
                    player_animation[player_animation_index].reset()
                elif (player_animation_index == 1 or player_animation_index == 2) and player_dx != 0:
                    player_animation_index = 0
                    player_animation[player_animation_index].reset()
                elif player_animation_index == 1 and player_dx == 0:
                    if player_dy == -1:
                        player_animation_index = 2
                        player_animation[player_animation_index].reset()
                elif player_animation_index == 2 and player_dx == 0:
                    if player_dy == 1:
                        player_animation_index = 1
                        player_animation[player_animation_index].reset()
                player_animation[player_animation_index].update(dt)

            for i in range(0, len(npcs)):
                if i != dialog_index:
                    npcs[i].update(dt)
                    npcs[i].check_collision(dt, player.get_rect())
                if not (i == dialog_index and len(npc_behaviors[i]) == 4):
                    npc_animations[i].update(dt)
                if len(npc_behaviors[i]) != 2:
                    if npc_behaviors[i][0]:
                        if npcs[i].vx > 0:
                            if npcs[i].x >= npc_behaviors[i][3][0]:
                                npcs[i].x = npc_behaviors[i][3][0]
                                npcs[i].vx *= -1
                        elif npcs[i].vx < 0:
                            if npcs[i].x <= npc_behaviors[i][2][0]:
                                npcs[i].x = npc_behaviors[i][2][0]
                                npcs[i].vx *= -1
                        else:
                            npcs[i].vx = 1

            # update camera
            if not disp_dialog:
                camera_x, camera_y = player.get_x() + camera_offset_x + int((mouse_x - screen_center[0]) * mouse_sensitivity), player.get_y() + camera_offset_y + int((mouse_y - screen_center[1]) * mouse_sensitivity)
                camera_x, camera_y = max(min(camera_x, 4096 - DISPLAY_WIDTH), 0), max(min(camera_y, 4096 - DISPLAY_HEIGHT), 0)
        else:
            npc_target_x = screen_center[0] - (npcs[chosen_npc].width // 2) + camera_x
            npc_target_y = screen_center[1] - (npcs[chosen_npc].height // 2) + camera_y
            npc_x = npcs[chosen_npc].x
            npc_y = npcs[chosen_npc].y
            if get_distance((npc_x, npc_y), (npc_target_x, npc_target_y)) <= 10:
                npcs[chosen_npc].x = npc_target_x
                npcs[chosen_npc].y = npc_target_y
                npc_x = npcs[chosen_npc].x
                npc_y = npcs[chosen_npc].y
                fade_alpha = 255
            if npc_x != npc_target_x or npc_y != npc_target_y:
                distance_vector = (npc_target_x - npc_x, npc_target_y - npc_y)
                move_speed = 3
                npcs[chosen_npc].vx, npcs[chosen_npc].vy = scale_vector(distance_vector, move_speed)
                npcs[chosen_npc].update(dt)
                fade_alpha += fade_alpha_inc_rate
            else:
                if len(end_message_buffer) != 0 or end_message != "":
                    if end_message == "":
                        end_message = end_message_buffer[0]
                        end_message_buffer = end_message_buffer[1:]
                        end_message_display.append("")
                    dialog_timer += dt
                    if dialog_timer >= dialog_char_rate:
                        dialog_timer -= dialog_char_rate
                        end_message_display[len(end_message_display) - 1] += end_message[0]
                        end_message = end_message[1:]

        # Render
        clear_display()

        if chosen_npc == -1:
            display.blit(get_image("background_scaled", False), (0 - camera_x, 0 - camera_y))
            display.blit(pygame.transform.flip(player_animation[player_animation_index].get_image(), most_recent_dx < 0 and player_animation_index == 0, False), (player.get_x() - camera_x, player.get_y() - camera_y))
            for i in range(0, len(npcs)):
                flip_x = False
                flip_y = False
                if len(npc_behaviors[i]) != 2:
                    if npc_behaviors[i][0]:
                        flip_x = npcs[i].vx < 0
                    else:
                        flip_y = npcs[i].vy < 0
                else:
                    flip_x, flip_y = npc_behaviors[i]
                display.blit(pygame.transform.flip(npc_animations[i].get_image(), flip_x, flip_y), (npcs[i].get_x() - camera_x, npcs[i].get_y() - camera_y))

            if disp_dialog:
                pygame.draw.rect(display, BLUE, (int(1280 * 0.1), 0, int(1280 * 0.8), 120))
                text_one = font_dialog.render(display_dialog_one, False, WHITE)
                text_two = font_dialog.render(display_dialog_two, False, WHITE)
                display.blit(text_one, (int(1280 * 0.1) + 22, 17))
                display.blit(text_two, (int(1280 * 0.1) + 22, 57))

                if dialog_one == "" and dialog_two == ""and len(dialog_buffer) == 0:
                    if kill_prompt:
                        kill_prompt_questions = ["Yes", "No"]
                        for i in range(0, len(kill_prompt_questions)):
                            pygame.draw.rect(display, RED, (int(1280 * 0.1), DISPLAY_HEIGHT - 250 + (70 * i), int(1280 * 0.8), 60))
                            text = font_dialog.render(kill_prompt_questions[i], False, WHITE)
                            display.blit(text, (int(1280 * 0.1) + 22, DISPLAY_HEIGHT - 250 + (70 * i) + 10))
                    else:
                        pygame.draw.rect(display, RED, (int(1280 * 0.65), DISPLAY_HEIGHT - 250 - 70, int(1280 * 0.25), 60))
                        text = font_dialog.render("Press X to Kill", False, WHITE)
                        display.blit(text, (int(1280 * 0.65) + 17, DISPLAY_HEIGHT - 250 - 70 + 10))
                        for i in range(0, len(dialog_questions)):
                            pygame.draw.rect(display, BLUE, (int(1280 * 0.1), DISPLAY_HEIGHT - 250 + (70 * i), int(1280 * 0.8), 60))
                            text = font_dialog.render(dialog_questions[i], False, WHITE)
                            display.blit(text, (int(1280 * 0.1) + 22, DISPLAY_HEIGHT - 250 + (70 * i) + 10))
        else:
            if fade_alpha < 255:
                display.blit(end_screen_surface, (0, 0))
                fade_surface = pygame.Surface((DISPLAY_WIDTH, DISPLAY_HEIGHT), pygame.SRCALPHA)
                fade_surface.fill((0, 0, 0, fade_alpha))
                display.blit(fade_surface, (0, 0))
            display.blit(npc_animations[chosen_npc].get_image(), (npcs[chosen_npc].get_x() - camera_x, npcs[chosen_npc].get_y() - camera_y))
            for i in range(0, len(end_message_display)):
                text = font_dialog.render(end_message_display[i], False, WHITE)
                display.blit(text, (screen_center[0] - (text.get_width() // 2), 60 + (40 * i)))
            if len(end_message_buffer) == 0 and end_message == "":
                text = font_dialog.render("Exit", False, WHITE)
                rect = (screen_center[0] - (text.get_width() // 2) - 10, int(DISPLAY_HEIGHT * 0.75) - 5, text.get_width() + 20, text.get_height() + 10)
                display.blit(text, (screen_center[0] - (text.get_width() // 2), int(DISPLAY_HEIGHT * 0.75)))
                pygame.draw.rect(display, WHITE, rect, not point_in_rect((mouse_x, mouse_y), rect))

        if show_fps:
            render_fps()
        flip_display()
        tick()


def handle_input():
    global mouse_x, mouse_y

    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            pygame.quit()
            sys.exit()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_w:
                input_queue.append(("player up", True))
                input_states["player up"] = True
            elif event.key == pygame.K_d:
                input_queue.append(("player right", True))
                input_states["player right"] = True
            elif event.key == pygame.K_s:
                input_queue.append(("player down", True))
                input_states["player down"] = True
            elif event.key == pygame.K_a:
                input_queue.append(("player left", True))
                input_states["player left"] = True
            elif event.key == pygame.K_x:
                input_queue.append(("kill", True))
                input_states["kill"] = True
        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_w:
                input_queue.append(("player up", False))
                input_states["player up"] = False
            elif event.key == pygame.K_d:
                input_queue.append(("player right", False))
                input_states["player right"] = False
            elif event.key == pygame.K_s:
                input_queue.append(("player down", False))
                input_states["player down"] = False
            elif event.key == pygame.K_a:
                input_queue.append(("player left", False))
                input_states["player left"] = False
            elif event.key == pygame.K_x:
                input_queue.append(("kill", False))
                input_states["kill"] = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == pygame.BUTTON_LEFT:
                input_queue.append(("left click", True))
                input_states["left click"] = True
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == pygame.BUTTON_LEFT:
                input_queue.append(("left click", False))
                input_states["left click"] = False
        elif event.type == pygame.MOUSEMOTION:
            mouse_pos = pygame.mouse.get_pos()
            mouse_x = int(mouse_pos[0] / SCALE)
            mouse_y = int(mouse_pos[1] / SCALE)


def clear_display():
    pygame.draw.rect(display, BLACK, (0, 0, DISPLAY_WIDTH, DISPLAY_HEIGHT), False)


def flip_display():
    global frames

    pygame.transform.scale(display, (SCREEN_WIDTH, SCREEN_HEIGHT), screen)
    pygame.display.flip()
    frames += 1


def render_fps():
    text = font_small.render("FPS: " + str(fps), False, BLACK)
    display.blit(text, (0, 0))


def tick():
    global before_time, before_sec, fps, frames, dt

    # Update delta based on the time elapsed
    after_time = pygame.time.get_ticks()
    dt = (after_time - before_time) / UPDATE_TIME

    # Update fps if a second has passed
    if after_time - before_sec >= SECOND:
        fps = frames
        frames = 0
        before_sec += SECOND
    before_time = pygame.time.get_ticks()

    # Update pygame clock
    clock.tick(TARGET_FPS)


if __name__ == "__main__":
    before_time = pygame.time.get_ticks()
    before_sec = before_time
    game()
    pygame.quit()
