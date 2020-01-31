import pygame
import sys
import os

# Handle cli flags
windowed = "--windowed" in sys.argv
show_fps = "--showfps" in sys.argv
if "--debug" in sys.argv:
    windowed = True
    show_fps = True


# Resolution variables, Display is streched to match Screen which can be set by user
DISPLAY_WIDTH = 640
DISPLAY_HEIGHT = 360
SCREEN_WIDTH = 640
SCREEN_HEIGHT = 360

if os.path.isfile("data/settings.txt"):
    print("Settings file found!")
    video_settings = open("data/settings.txt").read().splitlines()
    for line in video_settings:
        if line.startswith("resolution="):
            SCREEN_WIDTH = int(line[line.index("=") + 1:line.index("x")])
            SCREEN_HEIGHT = int(line[line.index("x") + 1:])
            aspect_ratio = SCREEN_WIDTH / SCREEN_HEIGHT
            if aspect_ratio == 4 / 3:
                DISPLAY_HEIGHT = 480
            elif aspect_ratio == 16 / 10:
                DISPLAY_HEIGHT = 420
            elif aspect_ratio == 16 / 9:
                DISPLAY_HEIGHT = 360
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
input_states = {}
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
image_path = "res/"
image_cache = {}


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


# Fonts
font_small = pygame.font.SysFont("Serif", 11)


# game states
EXIT = -1
MAIN_LOOP = 0


def game():
    running = True
    while running:
        # Handle input
        handle_input()
        while len(input_queue) != 0:
            event = input_queue.pop()

        # Update

        # Render
        clear_display()

        display.blit(get_image("dirty-uncle", True), ((DISPLAY_WIDTH // 2) - 40, (DISPLAY_HEIGHT / 2) - 100))

        if show_fps:
            render_fps()
        flip_display()
        tick()


def handle_input():
    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            pygame.quit()
            sys.exit()
    """
    elif event.type == pygame.KEYDOWN:
    if event.key == pygame.K_w etc etc
    elif event.type == pygame.KEYUP:
    elif event.type == pygame.MOUSEMOTION:
    mouse_pos = pygame.mouse.get_pos()
    mouse_x = int(mouse_pos[0] / SCALE)
    mouse_y = int(mouse_pos[1] / SCALE)
    """


def clear_display():
    pygame.draw.rect(display, BLACK, (0, 0, DISPLAY_WIDTH, DISPLAY_HEIGHT), False)


def flip_display():
    global frames

    pygame.transform.scale(display, (SCREEN_WIDTH, SCREEN_HEIGHT), screen)
    pygame.display.flip()
    frames += 1


def render_fps():
    text = font_small.render("FPS: " + str(fps), False, YELLOW)
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
