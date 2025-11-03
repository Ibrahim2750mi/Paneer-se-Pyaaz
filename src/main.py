"""Main game loop and window management."""
import time
import math
import random
import arcade
from math import pi, cos, sin

from constants import *
from character import Character
from terrain_generation import hybrid_terrain
from utils import (iso_to_screen, screen_to_chunk, get_chunk_seed,
                   get_hitbox_for_element, has_collision)


class ProceduralForestTerrain(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
        arcade.set_background_color(arcade.color.SKY_BLUE)

        # Camera setup
        self.camera = arcade.camera.Camera2D()

        # Scene to manage all sprites
        self.scene = None

        # Load textures
        self.textures = {}

        # Store active chunks
        self.chunks = {}

        # Character
        self.character = None

        # Physics engine
        self.physics_engine = None

        # Turn direction
        self.turn_direction = 0

        # Terrain generation mode
        self.terrain_mode = 'quantum'

        # Game state
        self.game_over = False
        self.score = 0
        self.penalty = 0
        self.start_x = 0
        self.start_y = 0
        self.collision_cooldown = 0

        # Quantum wave mode state
        self.wave_mode_active = False
        self.quantum_energy = MAX_QUANTUM_ENERGY
        self.wave_particles = []

        # Text objects for UI
        self.score_text = None
        self.displacement_text = None
        self.energy_label = None
        self.collision_text = None
        self.wave_text = None
        self.controls_text = None
        self.game_over_text = None
        self.final_score_text = None
        self.restart_text = None
        self.health_label = None

        # Health
        self.health = MAX_HEALTH
        self.last_damage_time = 0

        # Audio
        self.bg_ambient_music = None
        self.coin_music = None
        self.running_music = None
        self.bg_player = None
        self.running_player = None
        self.coin_player = None

    def load_textures(self):
        """Load all forest-themed textures"""
        try:
            self.textures['grass'] = arcade.load_texture("assets/terrain/ground_grass_NE.png")
            self.textures['tree_blocks_fall'] = arcade.load_texture("assets/terrain/tree_blocks_fall_NE.png")
            self.textures['tree_default_fall'] = arcade.load_texture("assets/terrain/tree_default_fall_NE.png")
            self.textures['tree_fat_fall'] = arcade.load_texture("assets/terrain/tree_fat_fall_NE.png")
            self.textures['tree_thin_fall'] = arcade.load_texture("assets/terrain/tree_thin_fall_NE.png")
            self.textures['tree_oak_fall'] = arcade.load_texture("assets/terrain/tree_oak_fall_NE.png")
            self.textures['stone_tall'] = arcade.load_texture("assets/terrain/stone_tallG_NE.png")
            self.textures['stone_large'] = arcade.load_texture("assets/terrain/stone_largeC_NE.png")
            self.textures['bush_small'] = arcade.load_texture("assets/terrain/plant_bushSmall_NE.png")
            self.textures['log'] = arcade.load_texture("assets/terrain/log_NE.png")
            self.textures['log_large'] = arcade.load_texture("assets/terrain/log_large_NE.png")
            self.textures['coin'] = arcade.load_texture("assets/terrain/skull-fotor-bg-remover-2025110325712.png")
        except Exception as e:
            print(f"Error loading textures: {e}")
            self.textures['grass'] = arcade.load_texture(":resources:images/tiles/grassCenter.png")

    def setup(self):
        """Set up initial scene, chunks and character"""
        self.scene = arcade.Scene()
        self.load_textures()

        # Load audio
        self.bg_ambient_music = arcade.load_sound("assets/music/bg.mp3")
        self.coin_music = arcade.load_sound("assets/music/coin_collect.mp3")
        self.running_music = arcade.load_sound("assets/music/running.mp3")

        self.bg_player = arcade.play_sound(self.bg_ambient_music, volume=0.2, loop=True)
        self.running_player = arcade.play_sound(self.running_music, volume=1, loop=True)

        # Add sprite lists for different layers
        self.scene.add_sprite_list(LAYER_NAME_GROUND, use_spatial_hash=True)
        self.scene.add_sprite_list(LAYER_NAME_OBJECTS, use_spatial_hash=True)
        self.scene.add_sprite_list(LAYER_NAME_WALLS, use_spatial_hash=True)
        self.scene.add_sprite_list(LAYER_NAME_COINS, use_spatial_hash=True)
        self.scene.add_sprite_list(LAYER_NAME_CHARACTERS)

        # Create character
        self.character = Character()
        self.character.center_x = SCREEN_WIDTH / 2
        self.character.center_y = SCREEN_HEIGHT / 2
        self.character.iso_x = 0
        self.character.iso_y = 0
        self.character.direction = pi / 4

        self.start_x = self.character.center_x
        self.start_y = self.character.center_y

        self.scene.add_sprite(LAYER_NAME_CHARACTERS, self.character)

        # Generate initial chunks
        self.update_chunks()

        # Initialize physics engine
        self.physics_engine = arcade.PhysicsEngineSimple(
            self.character,
            self.scene[LAYER_NAME_WALLS]
        )

        # Reset game state
        self.game_over = False
        self.score = 0
        self.penalty = 0
        self.collision_cooldown = 0
        self.wave_mode_active = False
        self.quantum_energy = MAX_QUANTUM_ENERGY
        self.wave_particles = []
        self.health = MAX_HEALTH
        self.last_damage_time = 0

        # Initialize UI text objects
        self._init_ui_text()

    def _init_ui_text(self):
        """Initialize all UI text objects"""
        self.score_text = arcade.Text(
            "Score: 0", 10, SCREEN_HEIGHT - 30,
            arcade.color.WHITE, 20, bold=True
        )

        self.displacement_text = arcade.Text(
            "Displacement: 0", 10, SCREEN_HEIGHT - 60,
            arcade.color.LIGHT_GRAY, 16
        )

        self.energy_label = arcade.Text(
            f"Quantum Energy: {MAX_QUANTUM_ENERGY}%",
            10, SCREEN_HEIGHT - 140,
            arcade.color.CYAN, 14, bold=True
        )

        self.collision_text = arcade.Text(
            f"COLLISION! -{COLLISION_PENALTY}",
            SCREEN_WIDTH / 2, SCREEN_HEIGHT - 40,
            arcade.color.RED, 24,
            anchor_x="center", bold=True
        )

        self.wave_text = arcade.Text(
            "⚛ WAVE MODE ACTIVE ⚛",
            SCREEN_WIDTH / 2, SCREEN_HEIGHT - 80,
            arcade.color.CYAN, 20,
            anchor_x="center", bold=True
        )

        self.controls_text = arcade.Text(
            "LEFT/A: Turn Left  |  RIGHT/D: Turn Right  |  HOLD W: Wave Mode  |  Q: Toggle Terrain",
            10, 10,
            arcade.color.WHITE, 14
        )

        self.game_over_text = arcade.Text(
            "GAME OVER!",
            SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 30,
            arcade.color.RED, 60,
            anchor_x="center", bold=True
        )

        self.final_score_text = arcade.Text(
            "Final Score: 0",
            SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 30,
            arcade.color.WHITE, 30,
            anchor_x="center", bold=True
        )

        self.restart_text = arcade.Text(
            "Press R to Restart",
            SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 70,
            arcade.color.WHITE, 24,
            anchor_x="center"
        )

        self.health_label = arcade.Text(
            f"Health: {MAX_HEALTH}%",
            10, SCREEN_HEIGHT - 170,
            arcade.color.LIGHT_GREEN, 14, bold=True
        )

    def generate_terrain_element(self, tile_x, tile_y, rng):
        """Determine what terrain element to place at this position"""
        if self.terrain_mode == 'quantum':
            return hybrid_terrain(tile_x, tile_y, self.wave_mode_active)

        # Random generation fallback
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
        chunk_seed = get_chunk_seed(chunk_x, chunk_y)
        rng = random.Random(chunk_seed)

        start_tile_x = chunk_x * CHUNK_SIZE
        start_tile_y = chunk_y * CHUNK_SIZE

        chunk_sprites = {
            'ground': [],
            'objects': [],
            'walls': [],
            'coins': []
        }

        for x in range(CHUNK_SIZE):
            for y in range(CHUNK_SIZE):
                tile_x = start_tile_x + x
                tile_y = start_tile_y + y

                screen_x, screen_y = iso_to_screen(tile_x, tile_y)

                # Create ground sprite
                grass_sprite = arcade.Sprite()
                grass_sprite.texture = self.textures['grass']
                grass_sprite.center_x = screen_x
                grass_sprite.center_y = screen_y
                grass_sprite.scale = 0.5
                self.scene.add_sprite(LAYER_NAME_GROUND, grass_sprite)
                chunk_sprites['ground'].append(grass_sprite)

                # Generate terrain element
                element = self.generate_terrain_element(tile_x, tile_y, rng)
                if element and element in self.textures:
                    detail_sprite = arcade.Sprite()
                    detail_sprite.texture = self.textures[element]
                    detail_sprite.center_x = screen_x
                    detail_sprite.center_y = screen_y
                    detail_sprite.scale = 0.4
                    detail_sprite.iso_x = tile_x
                    detail_sprite.iso_y = tile_y

                    if has_collision(element):
                        hitbox_points = get_hitbox_for_element(element)
                        detail_sprite.hit_box = arcade.hitbox.HitBox(
                            hitbox_points,
                            position=(detail_sprite.center_x, detail_sprite.center_y)
                        )
                        self.scene.add_sprite(LAYER_NAME_WALLS, detail_sprite)
                        chunk_sprites['walls'].append(detail_sprite)
                    else:
                        self.scene.add_sprite(LAYER_NAME_OBJECTS, detail_sprite)
                        chunk_sprites['objects'].append(detail_sprite)

                if element is None and rng.random() < COIN_SPAWN_CHANCE:
                    coin_sprite = arcade.Sprite()
                    coin_sprite.texture = self.textures['coin']
                    coin_sprite.center_x = screen_x
                    coin_sprite.center_y = screen_y + 10
                    coin_sprite.scale = 0.1
                    self.scene.add_sprite(LAYER_NAME_COINS, coin_sprite)
                    chunk_sprites['coins'].append(coin_sprite)

        return chunk_sprites

    def update_chunks(self):
        """Update chunks based on camera position"""
        center_chunk_x, center_chunk_y = screen_to_chunk(
            self.camera.position[0] + SCREEN_WIDTH / 2,
            self.camera.position[1] + SCREEN_HEIGHT / 2
        )

        chunks_needed = set()
        for dx in range(-RENDER_DISTANCE, RENDER_DISTANCE + 1):
            for dy in range(-RENDER_DISTANCE, RENDER_DISTANCE + 1):
                chunks_needed.add((center_chunk_x + dx, center_chunk_y + dy))

        # Remove far chunks
        chunks_to_remove = [pos for pos in self.chunks.keys() if pos not in chunks_needed]
        for chunk_pos in chunks_to_remove:
            del self.chunks[chunk_pos]

        # Create new chunks
        for chunk_pos in chunks_needed:
            if chunk_pos not in self.chunks:
                self.chunks[chunk_pos] = self.create_chunk(*chunk_pos)

    def on_key_press(self, key, modifiers):
        """Handle key press"""
        if self.game_over:
            if key == arcade.key.R:
                self.setup()
            return

        if key == arcade.key.LEFT or key == arcade.key.A:
            self.turn_direction = -1
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            self.turn_direction = 1
        elif key == arcade.key.W:
            if self.quantum_energy > 0:
                self.wave_mode_active = True
                self.character.set_wave_mode(True)
        elif key == arcade.key.Q:
            self.terrain_mode = 'random' if self.terrain_mode == 'quantum' else 'quantum'
            print(f"Switched to {'Random' if self.terrain_mode == 'random' else 'Quantum'} Terrain Generation")

    def on_key_release(self, key, modifiers):
        """Handle key release"""
        if key == arcade.key.LEFT or key == arcade.key.A:
            if self.turn_direction == -1:
                self.turn_direction = 0
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            if self.turn_direction == 1:
                self.turn_direction = 0
        elif key == arcade.key.W:
            self.wave_mode_active = False
            self.character.set_wave_mode(False)

    def update_wave_particles(self):
        """Update quantum wave visual effect particles"""
        if self.wave_mode_active and random.random() < 0.3:
            angle = random.uniform(0, 2 * pi)
            distance = random.uniform(10, 30)
            self.wave_particles.append({
                'x': self.character.center_x + cos(angle) * distance,
                'y': self.character.center_y + sin(angle) * distance,
                'life': 30,
                'size': random.uniform(3, 8),
                'color': random.choice([
                    arcade.color.CYAN,
                    arcade.color.LIGHT_BLUE,
                    arcade.color.ELECTRIC_BLUE,
                    arcade.color.SKY_BLUE
                ])
            })

        self.wave_particles = [p for p in self.wave_particles if p['life'] > 0]
        for particle in self.wave_particles:
            particle['life'] -= 1

    def take_damage(self, amount: int):
        """Reduce health, trigger Game Over if needed"""
        self.health = max(0, self.health - amount)
        self.last_damage_time = time.time()

        if self.health <= 0:
            self.game_over = True
            self.wave_mode_active = False

    def on_update(self, delta_time):
        """Update camera position and character"""
        if self.game_over:
            return

        if self.collision_cooldown > 0:
            self.collision_cooldown -= 1

        # Update quantum energy
        if self.wave_mode_active:
            self.quantum_energy -= QUANTUM_DRAIN_RATE
            if self.quantum_energy <= 0:
                self.quantum_energy = 0
                self.wave_mode_active = False
                self.character.set_wave_mode(False)
        else:
            self.quantum_energy = min(self.quantum_energy + QUANTUM_RECHARGE_RATE, MAX_QUANTUM_ENERGY)

        self.update_wave_particles()

        # Update character direction
        if self.turn_direction != 0:
            self.character.direction += self.turn_direction * TURN_SPEED

        # Move forward
        self.character.change_x = math.cos(self.character.direction) * CHARACTER_SPEED
        self.character.change_y = math.sin(self.character.direction) * CHARACTER_SPEED

        old_x = self.character.center_x
        old_y = self.character.center_y

        # Update physics
        if not self.wave_mode_active:
            self.physics_engine.update()
        else:
            self.character.center_x += self.character.change_x
            self.character.center_y += self.character.change_y

        # Check collision
        if not self.wave_mode_active:
            actual_move_x = self.character.center_x - old_x
            actual_move_y = self.character.center_y - old_y

            if abs(actual_move_x) < abs(self.character.change_x) * 0.5 or \
                    abs(actual_move_y) < abs(self.character.change_y) * 0.5:
                if self.collision_cooldown == 0:
                    self.penalty -= COLLISION_PENALTY
                    self.collision_cooldown = COLLISION_COOLDOWN
                    self.take_damage(HEALTH_PENALTY)

        # Calculate displacement
        displacement = math.sqrt(
            (self.character.center_x - self.start_x) ** 2 +
            (self.character.center_y - self.start_y) ** 2
        )

        self.score = int(displacement) + self.penalty

        # Update camera
        move_x = self.character.center_x - old_x
        move_y = self.character.center_y - old_y
        current_pos = self.camera.position
        self.camera.position = (current_pos[0] + move_x, current_pos[1] + move_y)
        self.update_chunks()

        self.character.update_animation(delta_time, self.turn_direction)

        # Coin collection
        coin_hits = arcade.check_for_collision_with_list(
            self.character,
            self.scene[LAYER_NAME_COINS]
        )
        for coin in coin_hits:
            self.coin_player = arcade.play_sound(self.coin_music, volume=0.1)
            coin.remove_from_sprite_lists()
            self.score += COIN_VALUE

    def on_draw(self):
        """Render the screen"""
        self.clear()
        self.camera.use()

        # Draw layers
        self.scene[LAYER_NAME_GROUND].draw()
        self.scene[LAYER_NAME_OBJECTS].draw()

        # Sort dynamic objects
        dynamic_objects = []
        dynamic_objects.extend(self.scene[LAYER_NAME_WALLS])
        dynamic_objects.extend(self.scene[LAYER_NAME_COINS])
        dynamic_objects.extend(self.scene[LAYER_NAME_CHARACTERS])
        dynamic_objects.sort(key=lambda s: -s.center_y)

        sprite_list = arcade.SpriteList(use_spatial_hash=True)
        sprite_list.extend(dynamic_objects)
        sprite_list.draw()

        # Draw wave particles
        for particle in self.wave_particles:
            alpha = int((particle['life'] / 30) * 200)
            color = (*particle['color'][:3], alpha)
            arcade.draw_circle_filled(
                particle['x'],
                particle['y'],
                particle['size'],
                color
            )

        # Draw UI
        arcade.camera.Camera2D().use()

        displacement = math.sqrt(
            (self.character.center_x - self.start_x) ** 2 +
            (self.character.center_y - self.start_y) ** 2
        )

        # Draw energy bar
        self._draw_energy_bar()

        # Update and draw text
        self._update_and_draw_ui()

    def _draw_energy_bar(self):
        """Draw the quantum energy bar"""
        bar_width = 200
        bar_height = 20
        bar_x = 10
        bar_y = SCREEN_HEIGHT - 120

        arcade.draw_lbwh_rectangle_filled(
            bar_x, bar_y + bar_height / 2,
            bar_width, bar_height,
            arcade.color.DARK_GRAY
        )

        energy_width = (self.quantum_energy / MAX_QUANTUM_ENERGY) * bar_width
        energy_color = arcade.color.CYAN if self.quantum_energy > 20 else arcade.color.RED
        arcade.draw_lbwh_rectangle_filled(
            bar_x, bar_y + bar_height / 2,
            energy_width, bar_height,
            energy_color
        )

        arcade.draw_lbwh_rectangle_outline(
            bar_x, bar_y + bar_height / 2,
            bar_width, bar_height,
            arcade.color.WHITE, 2
        )

    def _update_and_draw_ui(self):
        """Update and draw all UI text elements"""
        displacement = math.sqrt(
            (self.character.center_x - self.start_x) ** 2 +
            (self.character.center_y - self.start_y) ** 2
        )

        self.score_text.text = f"Score: {self.score}"
        self.displacement_text.text = f"Displacement: {int(displacement)}"
        self.energy_label.text = f"Quantum Energy: {int(self.quantum_energy)}%"
        self.energy_label.color = arcade.color.YELLOW if self.wave_mode_active else arcade.color.CYAN

        self.health_label.text = f"Health: {int(self.health)}%"
        if time.time() - self.last_damage_time < 0.3:
            self.health_label.color = arcade.color.RED
        else:
            self.health_label.color = arcade.color.LIGHT_GREEN

        self.score_text.draw()
        self.displacement_text.draw()
        self.energy_label.draw()
        self.controls_text.draw()
        self.health_label.draw()

        if self.collision_cooldown > 0:
            self.collision_text.draw()

        if self.wave_mode_active:
            self.wave_text.draw()

        if self.game_over:
            self.final_score_text.text = f"Final Score: {self.score}"
            self.game_over_text.draw()
            self.final_score_text.draw()
            self.restart_text.draw()


def main():
    window = ProceduralForestTerrain()
    window.setup()
    arcade.run()


if __name__ == "__main__":
    main()