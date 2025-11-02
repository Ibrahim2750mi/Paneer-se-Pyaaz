import arcade
import random
import math
from math import sin, cos, pi

# Constants
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
SCREEN_TITLE = "Procedural Forest Terrain - Infinite Runner"

# Tile settings
TILE_WIDTH = 128
TILE_HEIGHT = 64

# Camera movement speed
CAMERA_SPEED = 10

# Character settings
CHARACTER_SPEED = 8  # Constant forward speed
TURN_SPEED = 0.1  # How fast the character rotates
CHARACTER_SCALE = 1.0

# Chunk settings
CHUNK_SIZE = 16
RENDER_DISTANCE = 4

# Master seed for reproducible terrain
MASTER_SEED = 12345

# Scene layer names
LAYER_NAME_GROUND = "Ground"
LAYER_NAME_OBJECTS = "Objects"
LAYER_NAME_WALLS = "Walls"
LAYER_NAME_CHARACTERS = "Characters"


class QuantumState:
    """Minimal quantum simulator for terrain"""

    def __init__(self, x, y):
        self.phase = (x * 0.1234 + y * 0.4321 + sin(x * 0.1) * cos(y * 0.1)) % (2 * pi)

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
    q = QuantumState(tile_x, tile_y)
    q.hadamard()
    angle = (tile_x * 0.314 + tile_y * 0.271 + sin(tile_x * 0.05) * 3.14) % (2 * pi)
    q.rotate(angle)
    q.hadamard()
    q.rotate((tile_x * tile_y * 0.001) % (2 * pi))
    density = q.measure()

    q2 = QuantumState(tile_y, tile_x)
    q2.hadamard()
    q2.rotate(tile_x * 0.1)
    variation = q2.measure()

    combined = (density + variation * 0.5) / 1.5

    if combined < 0.65:
        return None
    elif combined < 0.68:
        return 'tree_thin_fall'
    elif combined < 0.70:
        return 'tree_default_fall'
    elif combined < 0.72:
        return 'tree_oak_fall'
    elif combined < 0.75:
        return 'stone_large'
    elif combined < 0.77:
        return 'log'
    else:
        return 'stone_tall' if (tile_x + tile_y) % 3 == 0 else 'bush_small'


class Character(arcade.Sprite):
    """Character with animation support"""

    def __init__(self, character_folder="character_run"):
        super().__init__()

        # Load character textures
        self.idle_textures = []
        self.run_textures = []

        try:
            # Load idle animations (try character_idle folder)
            for i in range(1, 9):
                for pattern in [f"assets/characters/character_idle/character_{i}-3.png",
                                f"assets/characters/character_idle/character_{i}-2.png"]:
                    try:
                        texture = arcade.load_texture(pattern)
                        self.idle_textures.append(texture)
                        break
                    except:
                        continue

            # Load run animations from specified folder
            if character_folder == "assets/characters/character_run":
                # Original character uses sprite_3_X.png format
                for i in range(8):
                    try:
                        texture = arcade.load_texture(f"{character_folder}/sprite_3_{i}.png")
                        self.run_textures.append(texture)
                    except:
                        pass
            elif character_folder == "assets/characters/character2_run":
                patterns = [
                    f"{character_folder}/character_1-4.png",
                    f"{character_folder}/character_2-3.png",
                    f"{character_folder}/character_3-3.png",
                    f"{character_folder}/character_4-3.png",
                    f"{character_folder}/character_5-3.png",
                    f"{character_folder}/character_6-3.png",
                    f"{character_folder}/character_7-3.png",
                    f"{character_folder}/character_8-4.png"
                ]
                for pattern in patterns:
                    try:
                        texture = arcade.load_texture(pattern)
                        self.run_textures.append(texture)
                    except Exception as e:
                        print(f"Could not load {pattern}: {e}")
        except Exception as e:
            print(f"Error loading character textures: {e}")

        # Fallback if no textures loaded
        if not self.idle_textures:
            self.idle_textures = [arcade.make_soft_square_texture(32, arcade.color.BLUE, 255, 255)]
        if not self.run_textures:
            self.run_textures = self.idle_textures

        # Set initial texture
        self.texture = self.run_textures[0] if self.run_textures else self.idle_textures[0]
        self.scale = CHARACTER_SCALE

        # Animation state
        self.current_frame = 0
        self.frame_counter = 0

        # Movement direction (in radians)
        self.direction = 0  # 0 = right, pi/2 = up, pi = left, 3pi/2 = down

        # Isometric position tracking
        self.iso_x = 0
        self.iso_y = 0

    def update_animation(self, delta_time=1 / 60):
        """Update character animation - always running"""
        self.frame_counter += 1

        # Change frame every 6 updates (faster animation for runner feel)
        if self.frame_counter >= 6:
            self.frame_counter = 0
            if self.run_textures:
                self.current_frame = (self.current_frame + 1) % len(self.run_textures)
                self.texture = self.run_textures[self.current_frame]


class ProceduralForestTerrain(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
        arcade.set_background_color(arcade.color.SKY_BLUE)

        # Camera setup - using modern Camera2D
        self.camera = arcade.camera.Camera2D()

        # Scene to manage all sprites
        self.scene = None

        # Load textures
        self.textures = {}
        self.load_textures()

        # Store active chunks {(chunk_x, chunk_y): chunk_data}
        self.chunks = {}

        # Character
        self.character = None

        # Physics engine
        self.physics_engine = None

        # Turn direction: -1 for left, 1 for right, 0 for straight
        self.turn_direction = 0

        # Terrain generation mode: 'random' or 'quantum'
        self.terrain_mode = 'quantum'

        # Game state
        self.game_over = False
        self.distance_traveled = 0

    def load_textures(self):
        """Load all forest-themed textures"""
        try:
            # Ground tiles
            self.textures['grass'] = arcade.load_texture("assets/terrain/ground_grass_NE.png")

            # Trees (various types for variety)
            self.textures['tree_blocks_fall'] = arcade.load_texture("assets/terrain/tree_blocks_fall_NE.png")
            self.textures['tree_default_fall'] = arcade.load_texture("assets/terrain/tree_default_fall_NE.png")
            self.textures['tree_fat_fall'] = arcade.load_texture("assets/terrain/tree_fat_fall_NE.png")
            self.textures['tree_thin_fall'] = arcade.load_texture("assets/terrain/tree_thin_fall_NE.png")
            self.textures['tree_oak_fall'] = arcade.load_texture("assets/terrain/tree_oak_fall_NE.png")

            # Rocks and details
            self.textures['stone_tall'] = arcade.load_texture("assets/terrain/stone_tallG_NE.png")
            self.textures['stone_large'] = arcade.load_texture("assets/terrain/stone_largeC_NE.png")

            # Plants
            self.textures['bush_small'] = arcade.load_texture("assets/terrain/plant_bushSmall_NE.png")

            # Logs
            self.textures['log'] = arcade.load_texture("assets/terrain/log_NE.png")
            self.textures['log_large'] = arcade.load_texture("assets/terrain/log_large_NE.png")

        except Exception as e:
            print(f"Error loading textures: {e}")
            # Create a fallback texture
            self.textures['grass'] = arcade.load_texture(":resources:images/tiles/grassCenter.png")

    def setup(self):
        """Set up initial scene, chunks and character"""
        # Create the Scene with organized layers
        self.scene = arcade.Scene()

        # Add sprite lists for different layers
        self.scene.add_sprite_list(LAYER_NAME_GROUND, use_spatial_hash=True)
        self.scene.add_sprite_list(LAYER_NAME_OBJECTS, use_spatial_hash=True)
        self.scene.add_sprite_list(LAYER_NAME_WALLS, use_spatial_hash=True)
        self.scene.add_sprite_list(LAYER_NAME_CHARACTERS)

        # Create character
        self.character = Character()
        self.character.center_x = SCREEN_WIDTH / 2
        self.character.center_y = SCREEN_HEIGHT / 2
        self.character.iso_x = 0
        self.character.iso_y = 0
        self.character.direction = pi / 4  # Start moving diagonally up-right

        # Add character to scene
        self.scene.add_sprite(LAYER_NAME_CHARACTERS, self.character)

        # Generate initial chunks
        self.update_chunks()

        # Initialize physics engine with walls from scene
        self.physics_engine = arcade.PhysicsEngineSimple(
            self.character,
            self.scene[LAYER_NAME_WALLS]
        )

        # Reset game state
        self.game_over = False
        self.distance_traveled = 0

    def iso_to_screen(self, iso_x, iso_y):
        """Convert isometric grid coordinates to screen coordinates"""
        screen_x = (iso_x - iso_y) * (TILE_WIDTH / 2)
        screen_y = (iso_x + iso_y) * (TILE_HEIGHT / 2)
        return screen_x, screen_y

    def screen_to_chunk(self, screen_x, screen_y):
        """Convert screen coordinates to chunk coordinates"""
        tiles_per_chunk = CHUNK_SIZE
        chunk_x = int(screen_x / (TILE_WIDTH * tiles_per_chunk / 2))
        chunk_y = int(screen_y / (TILE_HEIGHT * tiles_per_chunk / 2))
        return chunk_x, chunk_y

    def get_chunk_seed(self, chunk_x, chunk_y):
        """Generate a unique seed for each chunk using activation function"""
        center_x = chunk_x * CHUNK_SIZE + CHUNK_SIZE // 2
        center_y = chunk_y * CHUNK_SIZE + CHUNK_SIZE // 2

        combined = MASTER_SEED * math.sin(center_x * 0.1) * math.cos(center_y * 0.1)
        combined += (center_x * 73856093) ^ (center_y * 19349663)

        activated_seed = int(abs(combined * 1000) % (2 ** 31 - 1))
        return activated_seed

    def get_hitbox_for_element(self, element):
        """Get custom hitbox for specific elements with directional extensions"""
        hitbox_width = TILE_WIDTH * 0.3
        hitbox_height = TILE_HEIGHT * 0.3

        # Trees need extended hitboxes towards the bottom (where trunk appears visually)
        if 'tree' in element:
            return [
                (-hitbox_width * 0.45, -hitbox_height * 3.0),
                (hitbox_width * 0.45, -hitbox_height * 3.0),
                (hitbox_width * 0.45, hitbox_height * 0.8),
                (-hitbox_width * 0.45, hitbox_height * 0.8)
            ]

        # Large rocks get slightly extended hitbox
        elif element == 'stone_large':
            return [
                (-hitbox_width * 0.8, -hitbox_height * 1.2),
                (hitbox_width * 0.8, -hitbox_height * 1.2),
                (hitbox_width * 0.8, hitbox_height * 0.6),
                (-hitbox_width * 0.8, hitbox_height * 0.6)
            ]

        # Logs and stumps
        elif element in ['log', 'log_large']:
            return [
                (-hitbox_width * 0.9, -hitbox_height * 1.0),
                (hitbox_width * 0.9, -hitbox_height * 1.0),
                (hitbox_width * 0.9, hitbox_height * 0.5),
                (-hitbox_width * 0.9, hitbox_height * 0.5)
            ]

        # Stone tall
        elif element == 'stone_tall':
            return [
                (-hitbox_width * 0.6, -hitbox_height * 0.8),
                (hitbox_width * 0.6, -hitbox_height * 0.8),
                (hitbox_width * 0.6, hitbox_height * 0.4),
                (-hitbox_width * 0.6, hitbox_height * 0.4)
            ]

        # Default hitbox
        else:
            return [
                (-hitbox_width / 2, -hitbox_height / 2),
                (hitbox_width / 2, -hitbox_height / 2),
                (hitbox_width / 2, hitbox_height / 2),
                (-hitbox_width / 2, hitbox_height / 2)
            ]

    def has_collision(self, element_type):
        """Determine if an element should have collision"""
        collision_types = {
            'tree_blocks_fall', 'tree_fat_fall', 'tree_thin_fall', 'tree_tall_fall',
            'tree_default_fall', 'tree_oak_fall',
            'stone_tall', 'stone_large', 'log', 'log_large'
        }
        return element_type in collision_types

    def generate_terrain_element(self, tile_x, tile_y, rng):
        """Determine what terrain element to place at this position"""
        # Use quantum terrain if enabled
        if self.terrain_mode == 'quantum':
            return quantum_terrain(tile_x, tile_y)

        # Otherwise use random generation
        noise = rng.random()

        if noise < 0.35:
            tree_type = rng.random()
            if tree_type < 0.3:
                return 'tree_blocks_fall'
            elif tree_type < 0.5:
                return 'tree_oak_fall'
            elif tree_type < 0.7:
                return 'tree_default_fall'
            elif tree_type < 0.85:
                return 'tree_fat_fall'
            else:
                return 'tree_thin_fall'
        elif noise < 0.40:
            return 'stone_tall' if rng.random() < 0.7 else 'stone_large'
        elif noise < 0.43:
            return 'log' if rng.random() < 0.6 else 'log_large'
        elif noise < 0.48:
            return 'bush_small'
        else:
            return None

    def create_chunk(self, chunk_x, chunk_y):
        """Create a chunk of tiles and add to scene"""
        chunk_seed = self.get_chunk_seed(chunk_x, chunk_y)
        rng = random.Random(chunk_seed)

        start_tile_x = chunk_x * CHUNK_SIZE
        start_tile_y = chunk_y * CHUNK_SIZE

        # Store sprites for this chunk so we can remove them later
        chunk_sprites = {
            'ground': [],
            'objects': [],
            'walls': []
        }

        for x in range(CHUNK_SIZE):
            for y in range(CHUNK_SIZE):
                tile_x = start_tile_x + x
                tile_y = start_tile_y + y

                screen_x, screen_y = self.iso_to_screen(tile_x, tile_y)

                # Create ground sprite
                grass_sprite = arcade.Sprite()
                grass_sprite.texture = self.textures['grass']
                grass_sprite.center_x = screen_x
                grass_sprite.center_y = screen_y
                self.scene.add_sprite(LAYER_NAME_GROUND, grass_sprite)
                chunk_sprites['ground'].append(grass_sprite)

                # Generate terrain element
                element = self.generate_terrain_element(tile_x, tile_y, rng)
                if element and element in self.textures:
                    detail_sprite = arcade.Sprite()
                    detail_sprite.texture = self.textures[element]
                    detail_sprite.center_x = screen_x
                    detail_sprite.center_y = screen_y
                    detail_sprite.iso_x = tile_x
                    detail_sprite.iso_y = tile_y

                    # Set up hitbox for collision objects
                    if self.has_collision(element):
                        hitbox_points = self.get_hitbox_for_element(element)
                        detail_sprite.hit_box = arcade.hitbox.HitBox(
                            hitbox_points,
                            position=(detail_sprite.center_x, detail_sprite.center_y)
                        )
                        # Add to walls layer
                        self.scene.add_sprite(LAYER_NAME_WALLS, detail_sprite)
                        chunk_sprites['walls'].append(detail_sprite)
                    else:
                        # Non-collision objects go to objects layer
                        self.scene.add_sprite(LAYER_NAME_OBJECTS, detail_sprite)
                        chunk_sprites['objects'].append(detail_sprite)

        return chunk_sprites

    def update_chunks(self):
        """Update chunks based on camera position"""
        center_chunk_x, center_chunk_y = self.screen_to_chunk(
            self.camera.position[0] + SCREEN_WIDTH / 2,
            self.camera.position[1] + SCREEN_HEIGHT / 2
        )

        chunks_needed = set()
        for dx in range(-RENDER_DISTANCE, RENDER_DISTANCE + 1):
            for dy in range(-RENDER_DISTANCE, RENDER_DISTANCE + 1):
                chunks_needed.add((center_chunk_x + dx, center_chunk_y + dy))

        # Remove chunks that are too far
        chunks_to_remove = []
        for chunk_pos in self.chunks.keys():
            if chunk_pos not in chunks_needed:
                chunks_to_remove.append(chunk_pos)

        for chunk_pos in chunks_to_remove:
            del self.chunks[chunk_pos]

        # Create new chunks
        for chunk_pos in chunks_needed:
            if chunk_pos not in self.chunks:
                self.chunks[chunk_pos] = self.create_chunk(*chunk_pos)

    def on_key_press(self, key, modifiers):
        """Handle key press - only turn left or right"""
        if self.game_over:
            if key == arcade.key.R:
                self.setup()
            return

        if key == arcade.key.LEFT or key == arcade.key.A:
            self.turn_direction = -1
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            self.turn_direction = 1
        elif key == arcade.key.Q:
            # Toggle terrain generation mode
            if self.terrain_mode == 'quantum':
                self.terrain_mode = 'random'
                print("Switched to Random Terrain Generation")
            else:
                self.terrain_mode = 'quantum'
                print("Switched to Quantum Terrain Generation")

    def on_key_release(self, key, modifiers):
        """Handle key release"""
        if key == arcade.key.LEFT or key == arcade.key.A:
            if self.turn_direction == -1:
                self.turn_direction = 0
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            if self.turn_direction == 1:
                self.turn_direction = 0

    def on_update(self, delta_time):
        """Update camera position and character"""
        if self.game_over:
            return

        # Update character direction based on turn input
        if self.turn_direction != 0:
            self.character.direction += self.turn_direction * TURN_SPEED

        # Always move forward in current direction
        self.character.change_x = math.cos(self.character.direction) * CHARACTER_SPEED
        self.character.change_y = math.sin(self.character.direction) * CHARACTER_SPEED

        # Store old position
        old_x = self.character.center_x
        old_y = self.character.center_y

        # Update physics for player
        self.physics_engine.update()

        # Check if character hit something (didn't move as expected)
        expected_x = old_x + self.character.change_x
        expected_y = old_y + self.character.change_y
        actual_move_x = self.character.center_x - old_x
        actual_move_y = self.character.center_y - old_y

        # If movement was blocked significantly, game over
        if abs(actual_move_x) < abs(self.character.change_x) * 0.5 or \
                abs(actual_move_y) < abs(self.character.change_y) * 0.5:
            self.game_over = True
            print(f"Game Over! Distance traveled: {int(self.distance_traveled)}")
            return

        # Calculate movement delta for camera
        move_x = self.character.center_x - old_x
        move_y = self.character.center_y - old_y

        # Update distance traveled
        self.distance_traveled += math.sqrt(move_x ** 2 + move_y ** 2)

        # Update camera to follow character
        current_pos = self.camera.position
        self.camera.position = (current_pos[0] + move_x, current_pos[1] + move_y)
        self.update_chunks()

        # Update animations
        self.character.update_animation(delta_time)

    def on_draw(self):
        """Render the screen with proper layering"""
        self.clear()

        self.camera.use()

        # Draw ground layer (no sorting needed)
        self.scene[LAYER_NAME_GROUND].draw()

        # Draw static objects that don't need frequent re-sorting
        self.scene[LAYER_NAME_OBJECTS].draw()

        # Only sort walls and characters for proper depth
        dynamic_objects = []
        dynamic_objects.extend(self.scene[LAYER_NAME_WALLS])
        dynamic_objects.extend(self.scene[LAYER_NAME_CHARACTERS])

        # Sort by Y position
        dynamic_objects.sort(key=lambda s: -s.center_y)

        sprite_list = arcade.SpriteList(use_spatial_hash=True)
        sprite_list.extend(dynamic_objects)
        sprite_list.draw()

        # Draw UI (distance and instructions)
        arcade.camera.Camera2D().use()  # Switch to screen coordinates

        # Display distance
        arcade.draw_text(
            f"Distance: {int(self.distance_traveled)}",
            10, SCREEN_HEIGHT - 30,
            arcade.color.WHITE, 20,
            bold=True
        )

        # Display controls
        arcade.draw_text(
            "LEFT/A: Turn Left  |  RIGHT/D: Turn Right  |  Q: Toggle Terrain Mode",
            10, 10,
            arcade.color.WHITE, 14
        )

        # Game over message
        if self.game_over:
            arcade.draw_text(
                "GAME OVER!",
                SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 30,
                arcade.color.RED, 60,
                anchor_x="center", bold=True
            )
            arcade.draw_text(
                f"Final Distance: {int(self.distance_traveled)}",
                SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 30,
                arcade.color.WHITE, 30,
                anchor_x="center", bold=True
            )
            arcade.draw_text(
                "Press R to Restart",
                SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 70,
                arcade.color.WHITE, 24,
                anchor_x="center"
            )


def main():
    window = ProceduralForestTerrain()
    window.setup()
    arcade.run()


if __name__ == "__main__":
    main()