import pygame
import sys

class PixelDrawer:
    def __init__(self):
        pygame.init()
        self.width, self.height = 800, 600
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("2D Pixel Drawer")
        self.clock = pygame.time.Clock()
        self.pixels = set()

    def run(self):
        running = True
        while running:
            self.clock.tick(60)
            self.screen.fill((30, 30, 30))

            # Draw pixels
            for x, y in self.pixels:
                pygame.draw.rect(self.screen, (255, 255, 255), (x * 10, y * 10, 10, 10))

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = pygame.mouse.get_pos()
                    self.pixels.add((mx // 10, my // 10))

            pygame.display.flip()

        pygame.quit()
        sys.exit()
