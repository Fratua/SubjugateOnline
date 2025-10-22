"""
3D Rendering Engine using OpenGL
"""

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class Camera:
    """3D Camera for viewing the world"""

    def __init__(self, position: Tuple[float, float, float] = (0, 5, 10)):
        self.position = list(position)
        self.rotation = [0, 0, 0]  # pitch, yaw, roll
        self.target = [0, 0, 0]
        self.distance = 10.0
        self.min_distance = 3.0
        self.max_distance = 50.0

    def update(self, target_position: Tuple[float, float, float]):
        """Update camera to follow target"""
        self.target = list(target_position)

        # Calculate camera position based on rotation and distance
        yaw = math.radians(self.rotation[1])
        pitch = math.radians(self.rotation[0])

        self.position[0] = self.target[0] + self.distance * math.sin(yaw) * math.cos(pitch)
        self.position[1] = self.target[1] + self.distance * math.sin(pitch)
        self.position[2] = self.target[2] + self.distance * math.cos(yaw) * math.cos(pitch)

    def apply(self):
        """Apply camera transformation"""
        glLoadIdentity()
        gluLookAt(
            self.position[0], self.position[1], self.position[2],
            self.target[0], self.target[1], self.target[2],
            0, 1, 0
        )

    def zoom(self, amount: float):
        """Zoom camera in/out"""
        self.distance = max(self.min_distance, min(self.max_distance, self.distance + amount))

    def rotate(self, pitch: float, yaw: float):
        """Rotate camera"""
        self.rotation[0] = max(-89, min(89, self.rotation[0] + pitch))
        self.rotation[1] = (self.rotation[1] + yaw) % 360


class Renderer:
    """Main 3D renderer"""

    def __init__(self, width: int = 1280, height: int = 720):
        self.width = width
        self.height = height
        self.camera = Camera()

        # Initialize Pygame and OpenGL
        pygame.init()
        pygame.display.set_mode((width, height), DOUBLEBUF | OPENGL)
        pygame.display.set_caption("Subjugate Online")

        # OpenGL setup
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

        # Set up perspective
        glMatrixMode(GL_PROJECTION)
        gluPerspective(45, (width / height), 0.1, 500.0)
        glMatrixMode(GL_MODELVIEW)

        # Lighting setup
        glLight(GL_LIGHT0, GL_POSITION, (0, 100, 0, 1))
        glLight(GL_LIGHT0, GL_AMBIENT, (0.3, 0.3, 0.3, 1))
        glLight(GL_LIGHT0, GL_DIFFUSE, (0.8, 0.8, 0.8, 1))

        logger.info(f"Renderer initialized: {width}x{height}")

    def clear(self):
        """Clear the screen"""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glClearColor(0.2, 0.3, 0.5, 1.0)  # Sky blue background

    def draw_grid(self, size: int = 100, spacing: float = 10.0):
        """Draw a ground grid"""
        glDisable(GL_LIGHTING)
        glColor3f(0.3, 0.3, 0.3)
        glBegin(GL_LINES)

        for i in range(-size, size + 1):
            # Lines parallel to Z axis
            glVertex3f(i * spacing, 0, -size * spacing)
            glVertex3f(i * spacing, 0, size * spacing)

            # Lines parallel to X axis
            glVertex3f(-size * spacing, 0, i * spacing)
            glVertex3f(size * spacing, 0, i * spacing)

        glEnd()
        glEnable(GL_LIGHTING)

    def draw_cube(self, position: Tuple[float, float, float],
                   size: float = 1.0, color: Tuple[float, float, float] = (1, 1, 1)):
        """Draw a cube at position"""
        glPushMatrix()
        glTranslatef(*position)
        glColor3f(*color)

        # Define cube vertices
        vertices = [
            (-size, -size, -size), (size, -size, -size),
            (size, size, -size), (-size, size, -size),
            (-size, -size, size), (size, -size, size),
            (size, size, size), (-size, size, size)
        ]

        # Define cube faces
        faces = [
            (0, 1, 2, 3), (3, 2, 6, 7), (7, 6, 5, 4),
            (4, 5, 1, 0), (1, 5, 6, 2), (4, 0, 3, 7)
        ]

        glBegin(GL_QUADS)
        for face in faces:
            for vertex in face:
                glVertex3fv(vertices[vertex])
        glEnd()

        glPopMatrix()

    def draw_player(self, position: Tuple[float, float, float], name: str,
                    color: Tuple[float, float, float] = (0, 0.8, 1),
                    is_self: bool = False):
        """Draw a player character"""
        # Draw body (larger cube)
        body_color = (1, 1, 0) if is_self else color
        self.draw_cube((position[0], position[1] + 1, position[2]), 0.5, body_color)

        # Draw head (smaller cube on top)
        self.draw_cube((position[0], position[1] + 2, position[2]), 0.3, body_color)

        # Draw name tag (simple for now)
        # In a full implementation, this would use text rendering

    def draw_npc(self, position: Tuple[float, float, float], npc_type: str, level: int):
        """Draw an NPC"""
        # Different colors for different NPC types
        color_map = {
            'dummy': (0.5, 0.5, 0.5),
            'goblin': (0, 1, 0),
            'orc': (1, 0, 0),
            'knight': (0.3, 0.3, 0.3)
        }
        color = color_map.get(npc_type, (1, 1, 1))

        # Draw NPC (cube for now)
        scale = 0.5 + (level * 0.05)
        self.draw_cube((position[0], position[1] + scale, position[2]), scale, color)

    def draw_territory_marker(self, position: Tuple[float, float, float], radius: float,
                             owner_guild_id: Optional[int] = None, is_contested: bool = False):
        """Draw a territory control point"""
        # Draw cylinder-like marker
        if is_contested:
            color = (1, 0.5, 0)  # Orange for contested
        elif owner_guild_id:
            color = (0, 1, 0)  # Green for controlled
        else:
            color = (0.5, 0.5, 0.5)  # Gray for neutral

        # Draw marker cube
        self.draw_cube((position[0], position[1] + 2, position[2]), 1.0, color)

        # Draw radius indicator (circle on ground)
        glDisable(GL_LIGHTING)
        glColor3f(*color)
        glBegin(GL_LINE_LOOP)
        segments = 32
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            x = position[0] + radius * math.cos(angle)
            z = position[2] + radius * math.sin(angle)
            glVertex3f(x, position[1] + 0.1, z)
        glEnd()
        glEnable(GL_LIGHTING)

    def draw_health_bar(self, position: Tuple[float, float, float],
                        current: int, maximum: int, offset_y: float = 3.0):
        """Draw a health bar above entity"""
        if current <= 0 or maximum <= 0:
            return

        glDisable(GL_LIGHTING)
        glPushMatrix()
        glTranslatef(position[0], position[1] + offset_y, position[2])

        # Billboard effect (always face camera)
        # Simplified version - in full implementation would calculate proper rotation

        bar_width = 2.0
        bar_height = 0.2
        health_percentage = current / maximum

        # Background (red)
        glColor3f(1, 0, 0)
        glBegin(GL_QUADS)
        glVertex3f(-bar_width/2, -bar_height/2, 0)
        glVertex3f(bar_width/2, -bar_height/2, 0)
        glVertex3f(bar_width/2, bar_height/2, 0)
        glVertex3f(-bar_width/2, bar_height/2, 0)
        glEnd()

        # Foreground (green)
        glColor3f(0, 1, 0)
        glBegin(GL_QUADS)
        filled_width = bar_width * health_percentage
        glVertex3f(-bar_width/2, -bar_height/2, 0.01)
        glVertex3f(-bar_width/2 + filled_width, -bar_height/2, 0.01)
        glVertex3f(-bar_width/2 + filled_width, bar_height/2, 0.01)
        glVertex3f(-bar_width/2, bar_height/2, 0.01)
        glEnd()

        glPopMatrix()
        glEnable(GL_LIGHTING)

    def draw_scene(self, world_data: Dict):
        """Draw the entire scene"""
        self.clear()
        self.camera.apply()

        # Draw ground grid
        self.draw_grid()

        # Draw players
        players = world_data.get('players', {})
        for entity_id, player_data in players.items():
            pos = player_data['position']
            position = (pos['x'], pos['y'], pos['z'])

            is_self = player_data.get('is_self', False)
            self.draw_player(position, player_data['name'], is_self=is_self)

            # Draw health bar
            self.draw_health_bar(
                position,
                player_data.get('health', 100),
                player_data.get('max_health', 100)
            )

        # Draw NPCs
        npcs = world_data.get('npcs', {})
        for entity_id, npc_data in npcs.items():
            pos = npc_data['position']
            position = (pos['x'], pos['y'], pos['z'])
            self.draw_npc(position, npc_data.get('type', 'dummy'), npc_data.get('level', 1))

        # Draw territory markers
        territories = world_data.get('territories', [])
        for territory in territories:
            pos = territory['center']
            position = (pos['x'], pos['y'], pos['z'])
            self.draw_territory_marker(
                position,
                territory['radius'],
                territory.get('owner_guild_id'),
                territory.get('is_contested', False)
            )

    def flip(self):
        """Swap buffers"""
        pygame.display.flip()


class UIRenderer:
    """UI overlay renderer"""

    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)

    def draw_text(self, text: str, x: int, y: int, color: Tuple[int, int, int] = (255, 255, 255)):
        """Draw 2D text on screen"""
        # Save OpenGL state
        glPushAttrib(GL_ALL_ATTRIB_BITS)
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.screen_width, self.screen_height, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # Render text to texture
        text_surface = self.font.render(text, True, color)
        text_data = pygame.image.tostring(text_surface, "RGBA", True)

        glRasterPos2i(x, y)
        glDrawPixels(text_surface.get_width(), text_surface.get_height(),
                    GL_RGBA, GL_UNSIGNED_BYTE, text_data)

        # Restore state
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopAttrib()

    def draw_hud(self, player_data: Dict):
        """Draw HUD overlay"""
        if not player_data:
            return

        # Draw player stats
        y_offset = 10
        stats_text = [
            f"Name: {player_data.get('name', 'Unknown')}",
            f"Level: {player_data.get('level', 1)}",
            f"HP: {player_data.get('health', 0)}/{player_data.get('max_health', 100)}",
            f"MP: {player_data.get('mana', 0)}/{player_data.get('max_mana', 50)}",
            f"Killstreak: {player_data.get('killstreak', 0)}",
            f"Reincarnations: {player_data.get('reincarnation_count', 0)}",
        ]

        for text in stats_text:
            self.draw_text(text, 10, y_offset, (255, 255, 255))
            y_offset += 25

    def draw_chat(self, messages: List[str]):
        """Draw chat messages"""
        y_offset = self.screen_height - 200
        for message in messages[-8:]:  # Show last 8 messages
            self.draw_text(message, 10, y_offset, (200, 200, 200))
            y_offset += 20

    def draw_fps(self, fps: float):
        """Draw FPS counter"""
        self.draw_text(f"FPS: {fps:.1f}", self.screen_width - 100, 10, (255, 255, 0))
