# viewer.py - Main viewer class

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np

from .parser import parse_schematic
from .textures import load_textures


class SchematicViewer:
    def __init__(
        self,
        schem_path,
        texture_path="C:/Users/ryant/Documents/Coding Projects/mc-command-block-modifier-master/src/resource_pack/textures/block"
    ):
        self.schem_path = schem_path
        self.texture_path = texture_path

        self.WIDTH, self.HEIGHT = 800, 600
        pygame.init()
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT), DOUBLEBUF | OPENGL)
        pygame.display.set_caption("Schematic 3D Viewer")
        self.clock = pygame.time.Clock()
        self.FPS = 60

        # Render area
        self.RENDER_WIDTH = 600
        self.RENDER_HEIGHT = 400
        self.RENDER_X = (self.WIDTH - self.RENDER_WIDTH) // 2
        self.RENDER_Y = (self.HEIGHT - self.RENDER_HEIGHT) // 2

        # Camera
        self.camera_distance = 10.0
        self.camera_yaw = 45.0
        self.camera_pitch = 30.0
        self.center = np.array([0.0, 0.0, 0.0], dtype=np.float32)

        # Input
        self.dragging_left = False
        self.dragging_middle = False
        self.last_mouse_pos = (0, 0)

        # Movement
        self.move_speed = 0.05

        # Lighting
        self.light_dir = np.array([0.5, 1.0, -0.5], dtype=np.float32)
        self.light_dir /= np.linalg.norm(self.light_dir)
        self.ambient = 0.4

        self.init_opengl()

        # Load schematic
        self.blocks = parse_schematic(self.schem_path)
        if not self.blocks:
            self.blocks = [(0, 0, 0, "minecraft:stone")]

        unique_blocks = set(b[3] for b in self.blocks)
        self.textures = load_textures(self.texture_path, unique_blocks)

        coords = np.array([[b[0], b[1], b[2]] for b in self.blocks], dtype=np.float32)
        self.center = coords.mean(axis=0)

        size = coords.max(axis=0) - coords.min(axis=0)
        self.camera_distance = max(8.0, np.max(size) * 2.0)

    def init_opengl(self):
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glClearColor(0.15, 0.15, 0.2, 1.0)
        glViewport(self.RENDER_X, self.RENDER_Y, self.RENDER_WIDTH, self.RENDER_HEIGHT)

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(60, self.RENDER_WIDTH / self.RENDER_HEIGHT, 0.1, 1000.0)
        glMatrixMode(GL_MODELVIEW)

    def get_camera_vectors(self):
        yaw = np.radians(self.camera_yaw)
        pitch = np.radians(self.camera_pitch)

        forward = np.array([
            np.cos(pitch) * np.sin(yaw),
            np.sin(pitch),
            -np.cos(pitch) * np.cos(yaw)
        ])
        forward /= np.linalg.norm(forward)

        right = np.cross(forward, np.array([0.0, 1.0, 0.0]))
        right /= np.linalg.norm(right)

        up = np.cross(right, forward)
        return forward, right, up

    def update_camera(self):
        forward, _, _ = self.get_camera_vectors()
        eye = self.center + forward * self.camera_distance

        glLoadIdentity()
        gluLookAt(
            eye[0], eye[1], eye[2],
            self.center[0], self.center[1], self.center[2],
            0, 1, 0
        )

    def draw_block(self, x, y, z, block_name):
        vertices = [
            (x-0.5, y-0.5, z-0.5), (x+0.5, y-0.5, z-0.5),
            (x+0.5, y+0.5, z-0.5), (x-0.5, y+0.5, z-0.5),
            (x-0.5, y-0.5, z+0.5), (x+0.5, y-0.5, z+0.5),
            (x+0.5, y+0.5, z+0.5), (x-0.5, y+0.5, z+0.5)
        ]

        faces = [
            (0,1,2,3),(4,5,6,7),(0,1,5,4),
            (3,2,6,7),(0,3,7,4),(1,2,6,5)
        ]

        texture = self.textures.get(block_name)
        if texture:
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, texture)
        else:
            glDisable(GL_TEXTURE_2D)

        glBegin(GL_QUADS)
        for face in faces:
            for v in face:
                glVertex3fv(vertices[v])
        glEnd()

        glDisable(GL_TEXTURE_2D)
        glColor3f(0, 0, 0)
        glBegin(GL_LINES)
        edges = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]
        for a, b in edges:
            glVertex3fv(vertices[a])
            glVertex3fv(vertices[b])
        glEnd()

    def draw_ground(self):
        glDisable(GL_TEXTURE_2D)
        glBegin(GL_QUADS)
        for x in range(-30, 31):
            for z in range(-30, 31):
                c = 0.7 if (x + z) % 2 == 0 else 0.4
                glColor4f(c, c, c, 0.4)
                glVertex3f(x, -0.01, z)
                glVertex3f(x+1, -0.01, z)
                glVertex3f(x+1, -0.01, z+1)
                glVertex3f(x, -0.01, z+1)
        glEnd()

    def run(self):
        running = True

        while running:
            dt = self.clock.tick(self.FPS) / 1000.0
            speed = self.move_speed * self.camera_distance * dt * 60

            keys = pygame.key.get_pressed()
            forward, right, _ = self.get_camera_vectors()

            if keys[K_w]:
                self.center += forward * speed
            if keys[K_s]:
                self.center -= forward * speed
            if keys[K_a]:
                self.center += right * speed
            if keys[K_d]:
                self.center -= right * speed   

            for event in pygame.event.get():
                if event.type == QUIT:
                    running = False

                if event.type == KEYDOWN and event.key in (K_ESCAPE, K_p):
                    running = False

                if event.type == MOUSEBUTTONDOWN:
                    self.last_mouse_pos = event.pos
                    if event.button == 1:
                        self.dragging_left = True
                    elif event.button in (2, 3):
                        self.dragging_middle = True
                    elif event.button == 4:
                        self.camera_distance = max(3, self.camera_distance - 1.5)
                    elif event.button == 5:
                        self.camera_distance += 1.5

                if event.type == MOUSEBUTTONUP:
                    if event.button == 1:
                        self.dragging_left = False
                    elif event.button in (2, 3):
                        self.dragging_middle = False

                if event.type == MOUSEMOTION and (self.dragging_left or self.dragging_middle):
                    dx = event.pos[0] - self.last_mouse_pos[0]
                    dy = event.pos[1] - self.last_mouse_pos[1]

                    if self.dragging_middle:
                        self.camera_yaw += dx * 0.3
                        self.camera_pitch = np.clip(self.camera_pitch - dy * 0.3, 10, 85)

                    if self.dragging_left:
                        _, right, up = self.get_camera_vectors()
                        pan = self.camera_distance * 0.002
                        self.center += right * dx * pan
                        self.center += up * dy * pan

                    self.last_mouse_pos = event.pos

            self.update_camera()
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

            self.draw_ground()
            for x, y, z, name in self.blocks:
                self.draw_block(x, y, z, name)

            pygame.display.flip()

        for t in self.textures.values():
            glDeleteTextures([t])
        pygame.quit()
