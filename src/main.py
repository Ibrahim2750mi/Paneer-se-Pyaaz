from math import sqrt, sin, cos, pi
from pathlib import Path
import arcade

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
TILE_SIZE = 64
CHUNK_SIZE = 16


def rect2iso(x, y):
    """Convert to isometric"""
    iso_x = x * (sqrt(2) / 2) + y * (sqrt(2) / 2)
    iso_y = -x * (sqrt(2) / 2) + y * (sqrt(2) / 2)
    return iso_x, -iso_y / sqrt(2)


class QuantumState:
    """Minimal quantum simulator for terrain"""

    def __init__(self, x, y):
        self.phase = (x * 0.1 + y * 0.1) % (2 * pi)

    def hadamard(self):
        """Create superposition"""
        self.phase = (self.phase + pi / 4) % (2 * pi)

    def rotate(self, angle):
        """Rotate phase"""
        self.phase = (self.phase + angle) % (2 * pi)

    def measure(self):
        """Get probability (0 to 1)"""
        return (cos(self.phase) + 1) / 2


def quantum_terrain(tile_x, tile_y):
    """Generate terrain using quantum states"""
    # Create quantum state directly from position
    q = QuantumState(tile_x, tile_y)

    # Apply quantum gates
    q.hadamard()  # Superposition
    q.rotate((tile_x * 0.2 + tile_y * 0.3) % (2 * pi))  # Spatial correlation
    q.hadamard()  # Interference

    # Measure
    density = q.measure()

    # Determine terrain feature
    if density < 0.4:
        return None  # Empty
    elif density < 0.5:
        return 'tree_thin'
    elif density < 0.6:
        return 'tree_tall'
    elif density < 0.7:
        return 'tree_fat'
    elif density < 0.8:
        return 'stone_large'
    else:
        return 'log'

class Game(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, "Quantum Terrain")
        arcade.set_background_color(arcade.color.FOREST_GREEN)

        self.camera = arcade.camera.Camera2D()
        self.scene = arcade.Scene()
        self.scene.add_sprite_list("Ground", use_spatial_hash=True)
        self.scene.add_sprite_list("Objects", use_spatial_hash=True)

        # Player
        self.player = arcade.SpriteSolidColor(32, 32, arcade.color.RED)
        self.player.center_x = SCREEN_WIDTH / 2
        self.player.center_y = SCREEN_HEIGHT / 2

        # Load textures
        assets = Path("assets/terrain")
        self.textures = {
            'land': arcade.load_texture(str(assets / "land_NW.png")),
            'tree_thin': arcade.load_texture(str(assets / "tree_thin_fall_NW.png")),
            'tree_tall': arcade.load_texture(str(assets / "tree_tall_fall_NW.png")),
            'tree_fat': arcade.load_texture(str(assets / "tree_fat_fall_NW.png")),
            'stone_large': arcade.load_texture(str(assets / "stone_largeC_NW.png")),
            'log': arcade.load_texture(str(assets / "log_NW.png")),
        }

        self.chunks = {}
        self.keys = {'w': False, 'a': False, 's': False, 'd': False}

        # Generate initial terrain
        self.update_chunks()

    def screen_to_chunk(self, x, y):
        return int(x / (TILE_SIZE * CHUNK_SIZE)), int(y / (TILE_SIZE * CHUNK_SIZE))

    def update_chunks(self):
        cx, cy = self.screen_to_chunk(
            self.camera.position[0] + SCREEN_WIDTH / 2,
            self.camera.position[1] + SCREEN_HEIGHT / 2
        )

        # Keep only nearby chunks
        needed = {(cx + dx, cy + dy) for dx in range(-2, 3) for dy in range(-2, 3)}

        for pos in list(self.chunks.keys()):
            if pos not in needed:
                del self.chunks[pos]

        # Generate new chunks
        for pos in needed:
            if pos not in self.chunks:
                self.generate_chunk(pos[0], pos[1])

    def generate_chunk(self, chunk_x, chunk_y):
        """Generate chunk using quantum terrain"""
        sprites = []

        for x in range(CHUNK_SIZE):
            for y in range(CHUNK_SIZE):
                tile_x = chunk_x * CHUNK_SIZE + x
                tile_y = chunk_y * CHUNK_SIZE + y

                screen_x, screen_y = rect2iso(tile_x * TILE_SIZE, tile_y * TILE_SIZE)

                # Ground (always draw)
                ground = arcade.Sprite()
                ground.texture = self.textures['land']
                ground.center_x = screen_x
                ground.center_y = screen_y
                ground.scale = 1.0
                self.scene.add_sprite("Ground", ground)
                sprites.append(ground)

                # Quantum-generated feature
                feature = quantum_terrain(tile_x, tile_y)
                if feature and feature in self.textures:
                    obj = arcade.Sprite()
                    obj.texture = self.textures[feature]
                    obj.center_x = screen_x
                    obj.center_y = screen_y
                    obj.scale = 1.0
                    self.scene.add_sprite("Objects", obj)
                    sprites.append(obj)

        self.chunks[(chunk_x, chunk_y)] = sprites

    def on_key_press(self, key, mod):
        if key == arcade.key.W: self.keys['w'] = True
        if key == arcade.key.A: self.keys['a'] = True
        if key == arcade.key.S: self.keys['s'] = True
        if key == arcade.key.D: self.keys['d'] = True

    def on_key_release(self, key, mod):
        if key == arcade.key.W: self.keys['w'] = False
        if key == arcade.key.A: self.keys['a'] = False
        if key == arcade.key.S: self.keys['s'] = False
        if key == arcade.key.D: self.keys['d'] = False

    def on_update(self, dt):
        speed = 5
        dx = dy = 0

        if self.keys['w']: dy = speed
        if self.keys['s']: dy = -speed
        if self.keys['a']: dx = -speed
        if self.keys['d']: dx = speed

        if dx or dy:
            self.player.center_x += dx
            self.player.center_y += dy
            self.camera.position = (
                self.camera.position[0] + dx,
                self.camera.position[1] + dy
            )
            self.update_chunks()

    def on_draw(self):
        self.clear()
        self.camera.use()

        self.scene["Ground"].draw()
        self.scene["Objects"].draw()

        # # Sort by depth
        # objects = list(self.scene["Objects"].sprite_list)
        # objects.append(self.player)
        # objects.sort(key=lambda s: -s.center_y)
        #
        # for obj in objects:
        #     arcade.draw_sprite(obj)

        # Show mode
        arcade.draw_text(
            "QUANTUM TERRAIN GENERATION",
            10, SCREEN_HEIGHT - 30,
            arcade.color.CYAN, 14, bold=True
        )


if __name__ == "__main__":
    Game()
    arcade.run()