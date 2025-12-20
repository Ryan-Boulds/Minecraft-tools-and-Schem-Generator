import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import asyncio
import platform
import math
import numpy as np
import re  # Added missing import for regular expressions

class Block3DViewer:
    def __init__(self, commands):
        pygame.init()
        self.WIDTH, self.HEIGHT = 800, 600
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT), DOUBLEBUF | OPENGL)
        pygame.display.set_caption("Minecraft Block Renderer")
        self.clock = pygame.time.Clock()
        self.FPS = 60

        # Colors
        self.WHITE = (1.0, 1.0, 1.0, 1.0)
        self.GRAY = (0.5, 0.5, 0.5, 1.0)
        self.RED = (1.0, 0.0, 0.0, 1.0)
        self.BLUE = (0.0, 0.0, 1.0, 1.0)
        self.GREEN = (0.0, 1.0, 0.0, 1.0)
        self.ORANGE = (1.0, 0.65, 0.0, 1.0)
        self.LIGHT_GRAY = (0.7, 0.7, 0.7, 0.4)
        self.DARK_GRAY = (0.4, 0.4, 0.4, 0.4)

        # Render region
        self.RENDER_WIDTH = 600
        self.RENDER_HEIGHT = 400
        self.RENDER_X = (self.WIDTH - self.RENDER_WIDTH) // 2
        self.RENDER_Y = (self.HEIGHT - self.RENDER_HEIGHT) // 2

        # Camera settings
        self.camera_distance = 15.0
        self.camera_yaw = 45.0
        self.camera_pitch = 20.0
        self.fov = 60.0
        self.near = 2.0
        self.far = 1000.0
        self.camera_x, self.camera_y, self.camera_z = 0.0, 0.0, 0.0

        # Lighting settings
        self.light_dir = np.array([0.0, 0.0, -1.0], dtype=np.float32)
        self.ambient = 0.3

        # Block data
        self.blocks = self.parse_commands(commands)
        self.current_color = self.GRAY
        self.color_options = {"g": self.GRAY, "r": self.RED, "b": self.BLUE, "n": self.GREEN}
        self.color_names = {"g": "Gray", "r": "Red", "b": "Blue", "n": "Green"}
        self.selected_block = None

        # Text input
        self.input_text = ""
        self.font = pygame.font.SysFont("arial", 24)
        self.input_active = False

        # Mouse interaction
        self.dragging_left = False
        self.dragging_middle = False
        self.last_mouse_pos = (0, 0)

        self.init_opengl()

    def init_opengl(self):
        """Initialize OpenGL settings."""
        if not glGetString(GL_VERSION):
            print("OpenGL context not initialized. Check your GPU drivers or OpenGL support.")
            pygame.quit()
            exit()
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glViewport(self.RENDER_X, self.RENDER_Y, self.RENDER_WIDTH, self.RENDER_HEIGHT)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(self.fov, self.RENDER_WIDTH / self.RENDER_HEIGHT, self.near, self.far)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

    def parse_commands(self, commands):
        blocks = []
        for cmd in commands.split('\n'):
            match = re.match(r'setblock\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(.+)', cmd.strip())
            if match:
                x, y, z, block = match.groups()
                # Convert block type to color (simplified mapping for demo)
                color = self.GRAY  # Default to gray; extend this logic if needed
                if "red" in block.lower():
                    color = self.RED
                elif "blue" in block.lower():
                    color = self.BLUE
                elif "green" in block.lower():
                    color = self.GREEN
                blocks.append((int(x), int(y), int(z), color))
        return blocks

    def update_camera(self):
        """Update camera position and orientation."""
        cos_pitch = math.cos(math.radians(self.camera_pitch))
        sin_pitch = math.sin(math.radians(self.camera_pitch))
        cos_yaw = math.cos(math.radians(self.camera_yaw))
        sin_yaw = math.sin(math.radians(self.camera_yaw))
        camera_pos = np.array([
            self.camera_x + self.camera_distance * cos_pitch * sin_yaw,
            self.camera_y + self.camera_distance * sin_pitch,
            self.camera_z - self.camera_distance * cos_pitch * cos_yaw
        ], dtype=np.float32)
        glLoadIdentity()
        gluLookAt(
            camera_pos[0], camera_pos[1], camera_pos[2],
            self.camera_x, self.camera_y, self.camera_z,
            0.0, 1.0, 0.0
        )
        return camera_pos

    def get_camera_vectors(self):
        """Return camera right, up, and forward vectors based on yaw and pitch."""
        cos_pitch = math.cos(math.radians(self.camera_pitch))
        sin_pitch = math.sin(math.radians(self.camera_pitch))
        cos_yaw = math.cos(math.radians(self.camera_yaw))
        sin_yaw = math.sin(math.radians(self.camera_yaw))
        forward = np.array([
            -cos_pitch * sin_yaw,
            sin_pitch,
            -cos_pitch * cos_yaw
        ], dtype=np.float32)
        forward = forward / np.linalg.norm(forward)
        right = np.array([
            cos_yaw,
            0.0,
            -sin_yaw
        ], dtype=np.float32)
        right = right / np.linalg.norm(right)
        up = np.cross(right, forward)
        up = up / np.linalg.norm(up)
        return right, up, forward

    def draw_block(self, x, y, z, color, is_selected=False):
        """Draw a block using OpenGL."""
        vertices = np.array([
            [x-0.5, y-0.5, z-0.5], [x+0.5, y-0.5, z-0.5],
            [x+0.5, y+0.5, z-0.5], [x-0.5, y+0.5, z-0.5],
            [x-0.5, y-0.5, z+0.5], [x+0.5, y-0.5, z+0.5],
            [x+0.5, y+0.5, z+0.5], [x-0.5, y+0.5, z+0.5]
        ], dtype=np.float32)
        faces = [
            (0, 1, 2, 3),  # Front
            (5, 4, 7, 6),  # Back
            (1, 5, 6, 2),  # Right
            (4, 0, 3, 7),  # Left
            (3, 2, 6, 7),  # Top
            (4, 5, 1, 0)   # Bottom
        ]
        face_normals = [
            [0, 0, -1], [0, 0, 1], [1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0]
        ]
        for face in faces:
            glBegin(GL_QUADS)
            for vertex_idx in face:
                normal = face_normals[faces.index(face)]
                dot = max(0, -np.dot(normal, self.light_dir))
                intensity = self.ambient + (1 - self.ambient) * dot
                face_color = [
                    min(1.0, color[0] * intensity),
                    min(1.0, color[1] * intensity),
                    min(1.0, color[2] * intensity),
                    color[3]
                ]
                glColor4f(*face_color)
                glVertex3fv(vertices[vertex_idx])
            glEnd()
        if is_selected:
            glColor4f(self.ORANGE[0], self.ORANGE[1], self.ORANGE[2], 1.0)
        else:
            glColor4f(0.0, 0.0, 0.0, 1.0)
        glBegin(GL_LINE_LOOP)
        for vertex_idx in face:
            glVertex3fv(vertices[vertex_idx])
        glEnd()

    def draw_ground(self):
        """Draw a checkerboard ground plane at y=-0.5 using OpenGL."""
        grid_size = 20
        tile_size = 1.0
        glBegin(GL_QUADS)
        for i in range(-grid_size, grid_size + 1):
            for j in range(-grid_size, grid_size + 1):
                x = i * tile_size
                z = j * tile_size
                color = self.LIGHT_GRAY if (i + j) % 2 == 0 else self.DARK_GRAY
                glColor4f(color[0], color[1], color[2], color[3])
                glVertex3f(x, -0.5, z)
                glVertex3f(x + tile_size, -0.5, z)
                glVertex3f(x + tile_size, -0.5, z + tile_size)
                glVertex3f(x, -0.5, z + tile_size)
        glEnd()

    def select_block(self, mx, my, camera_pos):
        """Select the closest block to the mouse click."""
        closest = None
        min_dist = float('inf')
        mx -= self.RENDER_X
        my = self.RENDER_HEIGHT - (my - self.RENDER_Y)
        if 0 <= mx < self.RENDER_WIDTH and 0 <= my < self.RENDER_HEIGHT:
            for i, (x, y, z, _) in enumerate(self.blocks):
                dx = x - camera_pos[0]
                dy = y - camera_pos[1]
                dz = z - camera_pos[2]
                dist = math.sqrt(dx*dx + dy*dy + dz*dz)
                if dist < min_dist and dist < 50:
                    min_dist = dist
                    closest = i
        self.selected_block = closest

    def setup(self):
        """Initialize the game."""
        self.init_opengl()

    async def update_loop(self):
        """Main update loop."""
        keys = pygame.key.get_pressed()
        shift = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        move_speed = 0.1 if shift else 0.05
        running = True
        while running:
            camera_pos = self.update_camera()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_i:
                        self.input_active = True
                    elif self.input_active:
                        if event.key == pygame.K_RETURN:
                            try:
                                x, y, z = map(float, self.input_text.split())
                                self.blocks.append((x, y, z, self.current_color))
                                self.input_text = ""
                            except ValueError:
                                self.input_text = "Invalid"
                        elif event.key == pygame.K_BACKSPACE:
                            self.input_text = self.input_text[:-1]
                        else:
                            self.input_text += event.unicode
                    elif event.key in (pygame.K_g, pygame.K_r, pygame.K_b, pygame.K_n):
                        self.current_color = self.color_options[chr(event.key).lower()]
                    elif event.key == pygame.K_p:
                        print("Block coordinates in order of placement:")
                        for i, (x, y, z, _) in enumerate(self.blocks):
                            print(f"{i+1}: ({x}, {y}, {z})")
                        running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if self.RENDER_X <= event.pos[0] < self.RENDER_X + self.RENDER_WIDTH and self.RENDER_Y <= event.pos[1] < self.RENDER_Y + self.RENDER_HEIGHT:
                        if event.button == 1:
                            self.dragging_left = True
                            self.last_mouse_pos = event.pos
                            self.select_block(*event.pos, camera_pos)
                        elif event.button == 2:
                            self.dragging_middle = True
                            self.last_mouse_pos = event.pos
                        elif event.button == 4:
                            self.camera_distance = max(2, self.camera_distance - 0.5)
                        elif event.button == 5:
                            self.camera_distance = min(50, self.camera_distance + 0.5)
                    elif not self.input_active and self.RENDER_X + self.RENDER_WIDTH <= event.pos[0] <= self.WIDTH - 10 and self.HEIGHT - 50 <= event.pos[1] <= self.HEIGHT - 10:
                        if self.input_text:
                            try:
                                x, y, z = map(float, self.input_text.split())
                                self.blocks.append((x, y, z, self.current_color))
                                self.input_text = ""
                            except ValueError:
                                self.input_text = "Invalid"
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        self.dragging_left = False
                    elif event.button == 2:
                        self.dragging_middle = False
                elif event.type == pygame.MOUSEMOTION and self.dragging_left:
                    if self.RENDER_X <= event.pos[0] < self.RENDER_X + self.RENDER_WIDTH and self.RENDER_Y <= event.pos[1] < self.RENDER_Y + self.RENDER_HEIGHT:
                        dx, dy = event.pos[0] - self.last_mouse_pos[0], event.pos[1] - self.last_mouse_pos[1]
                        right, up, _ = self.get_camera_vectors()
                        pan_speed = 0.02
                        self.camera_x -= dx * pan_speed * right[0]
                        self.camera_y -= dx * pan_speed * right[1]
                        self.camera_z -= dx * pan_speed * right[2]
                        self.camera_x += dy * pan_speed * up[0]
                        self.camera_y += dy * pan_speed * up[1]
                        self.camera_z += dy * pan_speed * up[2]
                        self.last_mouse_pos = event.pos
                elif event.type == pygame.MOUSEMOTION and self.dragging_middle:
                    if self.RENDER_X <= event.pos[0] < self.RENDER_X + self.RENDER_WIDTH and self.RENDER_Y <= event.pos[1] < self.RENDER_Y + self.RENDER_HEIGHT:
                        dx, dy = event.pos[0] - self.last_mouse_pos[0], event.pos[1] - self.last_mouse_pos[1]
                        self.camera_yaw += dx * 0.1
                        self.camera_pitch += dy * 0.1
                        self.camera_pitch = max(-89, min(89, self.camera_pitch))
                        self.last_mouse_pos = event.pos

            # WASD controls with Shift
            if shift:
                if keys[pygame.K_w]:
                    self.camera_z -= move_speed
                if keys[pygame.K_s]:
                    self.camera_z += move_speed
                if keys[pygame.K_a]:
                    self.camera_x -= move_speed
                if keys[pygame.K_d]:
                    self.camera_x += move_speed

            # Draw
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            self.draw_ground()
            for i, (x, y, z, color) in enumerate(self.blocks):
                self.draw_block(x, y, z, color, is_selected=(i == self.selected_block))

            # Draw UI outside render region
            self.screen.fill((0.1, 0.1, 0.1))
            instructions = [
                "Press 'i' to input coordinates (x y z)",
                f"Current color: {self.color_names[[k for k, v in self.color_options.items() if v == self.current_color][0]]}",
                "Press 'g' (gray), 'r' (red), 'b' (blue), 'n' (green) to change color",
                "Left click to pan camera, middle click to orbit, scroll to zoom",
                "Hold Shift + WASD to move camera, left click to select (orange outline), 'p' to print and exit"
            ]
            for i, text in enumerate(instructions):
                surface = self.font.render(text, True, self.WHITE)
                self.screen.blit(surface, (10, 10 + i * 30))

            # Draw textbox and button at bottom
            textbox_rect = pygame.Rect(self.RENDER_X, self.HEIGHT - 50, self.RENDER_WIDTH - 100, 40)
            pygame.draw.rect(self.screen, (0.2, 0.2, 0.2), textbox_rect)
            if self.input_active:
                pygame.draw.rect(self.screen, self.WHITE, textbox_rect, 2)
            text_surface = self.font.render(self.input_text if self.input_text else "Enter x y z", True, self.WHITE)
            self.screen.blit(text_surface, (textbox_rect.x + 5, textbox_rect.y + 5))
            button_rect = pygame.Rect(self.RENDER_X + self.RENDER_WIDTH - 90, self.HEIGHT - 50, 90, 40)
            pygame.draw.rect(self.screen, (0.3, 0.3, 0.3), button_rect)
            button_text = self.font.render("Add Block", True, self.WHITE)
            self.screen.blit(button_text, (button_rect.x + 10, button_rect.y + 5))
            if not self.input_active and button_rect.collidepoint(pygame.mouse.get_pos()) and pygame.mouse.get_pressed()[0]:
                if self.input_text:
                    try:
                        x, y, z = map(float, self.input_text.split())
                        self.blocks.append((x, y, z, self.current_color))
                        self.input_text = ""
                    except ValueError:
                        self.input_text = "Invalid"

            pygame.display.flip()
            await asyncio.sleep(1.0 / self.FPS)

    async def main(self):
        self.setup()
        await self.update_loop()

    def get_commands(self):
        commands = []
        for x, y, z, color in self.blocks:
            # Simplify color to block type for command (extend as needed)
            block_type = "minecraft:stone"  # Default
            if color == self.RED:
                block_type = "minecraft:redstone_block"
            elif color == self.BLUE:
                block_type = "minecraft:blue_ice"
            elif color == self.GREEN:
                block_type = "minecraft:lime_concrete"
            commands.append(f"setblock {x} {y} {z} {block_type}")
        return "\n".join(commands)

    def run(self):
        if platform.system() == "Emscripten":
            asyncio.ensure_future(self.main())
        else:
            asyncio.run(self.main())