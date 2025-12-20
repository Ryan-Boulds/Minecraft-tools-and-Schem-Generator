# textures.py - Texture loading logic

import pygame
from OpenGL.GL import *
import os

def load_textures(texture_path, unique_blocks):
    textures = {}
    glEnable(GL_TEXTURE_2D)
    for block_name in unique_blocks:
        texture_name = block_name.split(":")[-1] + ".png"
        full_path = os.path.join(texture_path, texture_name)
        if os.path.exists(full_path):
            try:
                image = pygame.image.load(full_path)
                image = pygame.transform.flip(image, False, True)
                image_data = pygame.image.tostring(image, "RGBA", 1)
                width, height = image.get_size()
                texture_id = glGenTextures(1)
                glBindTexture(GL_TEXTURE_2D, texture_id)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, image_data)
                textures[block_name] = texture_id
                print(f"Loaded texture: {full_path}")
            except Exception as e:
                print(f"Texture load error for {block_name}: {e}")
        else:
            print(f"Texture missing (using grey): {full_path}")
    return textures