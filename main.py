import pygame
import random
import math
import sys
import asyncio

# Initialize Pygame
pygame.init()

# Screen Configuration Constants
WIDTH = 800
HEIGHT = 600
FPS = 60

# Vibrant Neon Arcade Palette
BG_COLOR = (10, 5, 25)
ASTEROID_COLOR = (130, 70, 175)
OUTLINE_COLOR = (255, 100, 255)
SHIP_COLOR = (0, 255, 220)
MISSILE_COLOR = (255, 220, 50)
ENEMY_COLOR = (255, 40, 90)
ENEMY_PATROL_COLOR = (50, 255, 150)
DETECTION_CIRCLE_COLOR = (120, 60, 220)
WHITE = (255, 255, 255)
YELLOW = (255, 255, 0)
GREEN = (50, 255, 50)
GRAY = (180, 180, 200)

# Physics Tuning Constants
THRUST = 0.15
REVERSE_THRUST = 0.10
DRAG = 0.99
MAX_SPEED = 7.0
ROTATION_SPEED = 3.5
MISSILE_SPEED = 9

class Spaceship:
    def __init__(self, x, y):
        self.position = pygame.Vector2(x, y)
        self.velocity = pygame.Vector2(0, 0)
        self.acceleration = pygame.Vector2(0, 0)
        self.angle = 0
        self.radius = 20
        self.is_thrusting = False

    def rotate(self, amount):
        self.angle += amount

    def update(self, keys):
        self.acceleration = pygame.Vector2(0, 0)

        radians = math.radians(self.angle)
        forward = pygame.Vector2(math.cos(radians), -math.sin(radians))

        self.is_thrusting = False
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.acceleration = forward * THRUST
            self.is_thrusting = True
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.acceleration = -forward * REVERSE_THRUST

        self.velocity += self.acceleration
        self.velocity *= DRAG

        if self.velocity.length() > MAX_SPEED:
            self.velocity.scale_to_length(MAX_SPEED)

        self.position += self.velocity

        if self.position.x > WIDTH:
            self.position.x = 0
        elif self.position.x < 0:
            self.position.x = WIDTH

        if self.position.y > HEIGHT:
            self.position.y = 0
        elif self.position.y < 0:
            self.position.y = HEIGHT

    def draw(self, surface):
        radians = math.radians(self.angle)
        forward = pygame.Vector2(math.cos(radians), -math.sin(radians))

        if self.is_thrusting:
            back = self.position - forward * 18
            pygame.draw.circle(surface, YELLOW, (int(back.x), int(back.y)), 6)

        tip = self.position + forward * 15
        left_wing = self.position + pygame.Vector2(-forward.y, forward.x) * 10 - forward * 10
        right_wing = self.position + pygame.Vector2(forward.y, -forward.x) * 10 - forward * 10
        pygame.draw.polygon(surface, SHIP_COLOR, [(tip.x, tip.y), (left_wing.x, left_wing.y), (right_wing.x, right_wing.y)])
        pygame.draw.polygon(surface, OUTLINE_COLOR, [(tip.x, tip.y), (left_wing.x, left_wing.y), (right_wing.x, right_wing.y)], 2)


class Missile:
    def __init__(self, x, y, velocity):
        self.position = pygame.Vector2(x, y)
        self.velocity = velocity
        self.radius = 5

    def update(self):
        self.position += self.velocity

    def draw(self, surface):
        pygame.draw.circle(surface, MISSILE_COLOR, (int(self.position.x), int(self.position.y)), self.radius)


class Asteroid:
    def __init__(self, x, y, radius, vx, vy):
        self.position = pygame.Vector2(x, y)
        self.radius = radius
        self.mass = radius ** 2  
        self.velocity = pygame.Vector2(vx, vy)

    def update(self):
        self.position += self.velocity

        if self.position.x - self.radius < 0:
            self.position.x = self.radius
            self.velocity.x *= -1
        elif self.position.x + self.radius > WIDTH:
            self.position.x = WIDTH - self.radius
            self.velocity.x *= -1

        if self.position.y - self.radius < 0:
            self.position.y = self.radius
            self.velocity.y *= -1
        elif self.position.y + self.radius > HEIGHT:
            self.position.y = HEIGHT - self.radius
            self.velocity.y *= -1

    def draw(self, surface):
        pygame.draw.circle(surface, ASTEROID_COLOR, (int(self.position.x), int(self.position.y)), self.radius)
        pygame.draw.circle(surface, OUTLINE_COLOR, (int(self.position.x), int(self.position.y)), self.radius, 2)


class EnemyAI:
    def __init__(self, x, y):
        self.position = pygame.Vector2(x, y)
        self.angle = 0
        self.state = "PATROL"
        self.detection_range = 250
        self.fov_threshold = 0.5
        self.radius = 18

    def update(self, player_pos):
        self.angle += 1.0
        radians = math.radians(self.angle)
        forward = pygame.Vector2(math.cos(radians), -math.sin(radians))

        to_player = player_pos - self.position
        distance = self.position.distance_to(player_pos)
        
        if to_player.length() > 0:
            to_player_norm = to_player.normalize()
        else:
            to_player_norm = pygame.Vector2(0, 0)

        dot = forward.dot(to_player_norm)

        if distance < self.detection_range and dot > self.fov_threshold:
            self.state = "ATTACK"
            detected = True
        else:
            self.state = "PATROL"
            detected = False

        return detected, forward, distance, dot

    def draw(self, surface, detected):
        radians = math.radians(self.angle)
        forward = pygame.Vector2(math.cos(radians), -math.sin(radians))

        pygame.draw.circle(surface, DETECTION_CIRCLE_COLOR, (int(self.position.x), int(self.position.y)), self.detection_range, 1)
        forward_end = self.position + forward * 80
        pygame.draw.line(surface, ENEMY_COLOR if detected else ENEMY_PATROL_COLOR, self.position, forward_end, 2)

        color = ENEMY_COLOR if detected else ENEMY_PATROL_COLOR
        pygame.draw.circle(surface, color, (int(self.position.x), int(self.position.y)), self.radius)
        pygame.draw.circle(surface, OUTLINE_COLOR, (int(self.position.x), int(self.position.y)), self.radius, 2)


def resolve_collision(a1, a2):
    dx = a2.position.x - a1.position.x
    dy = a2.position.y - a1.position.y
    distance = math.hypot(dx, dy)
    min_dist = a1.radius + a2.radius

    if distance < min_dist and distance > 0:
        overlap = 0.5 * (min_dist - distance)
        nx = dx / distance
        ny = dy / distance

        total_mass = a1.mass + a2.mass
        a1.position.x -= nx * overlap * (a2.mass / total_mass) * 2
        a1.position.y -= ny * overlap * (a2.mass / total_mass) * 2
        a2.position.x += nx * overlap * (a1.mass / total_mass) * 2
        a2.position.y += ny * overlap * (a1.mass / total_mass) * 2

        dx = a2.position.x - a1.position.x
        dy = a2.position.y - a1.position.y
        distance = math.hypot(dx, dy)
        if distance == 0:
            return
        nx = dx / distance
        ny = dy / distance

        tx = -ny
        ty = nx

        dp1_n = a1.velocity.x * nx + a1.velocity.y * ny
        dp1_t = a1.velocity.x * tx + a1.velocity.y * ty
        dp2_n = a2.velocity.x * nx + a2.velocity.y * ny
        dp2_t = a2.velocity.x * tx + a2.velocity.y * ty

        m1, m2 = a1.mass, a2.mass
        new_dp1_n = (dp1_n * (m1 - m2) + 2 * m2 * dp2_n) / (m1 + m2)
        new_dp2_n = (dp2_n * (m2 - m1) + 2 * m1 * dp1_n) / (m1 + m2)

        a1.velocity.x = new_dp1_n * nx + dp1_t * tx
        a1.velocity.y = new_dp1_n * ny + dp1_t * ty
        a2.velocity.x = new_dp2_n * nx + dp2_t * tx
        a2.velocity.y = new_dp2_n * ny + dp2_t * ty


async def main():
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Neon Asteroids: Arcade Edition")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 24)

    # Initialize Game Objects
    ship = Spaceship(WIDTH // 2, HEIGHT // 2)
    enemy = EnemyAI(WIDTH // 4, HEIGHT // 4)
    asteroids = []
    missiles = []
    score = 0

    for _ in range(6):
        radius = random.randint(25, 40)
        valid_spawn = False
        while not valid_spawn:
            x = random.randint(radius + 40, WIDTH - radius - 40)
            y = random.randint(radius + 40, HEIGHT - radius - 40)
            valid_spawn = True
            if math.hypot(x - ship.position.x, y - ship.position.y) < radius + ship.radius + 40:
                valid_spawn = False
                continue
            for ast in asteroids:
                if math.hypot(x - ast.position.x, y - ast.position.y) < radius + ast.radius + 15:
                    valid_spawn = False
                    break
        vx = random.uniform(-2.0, 2.0)
        vy = random.uniform(-2.0, 2.0)
        if abs(vx) < 0.5: vx = 1.0
        if abs(vy) < 0.5: vy = -1.0
        asteroids.append(Asteroid(x, y, radius, vx, vy))

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                target = pygame.Vector2(event.pos)
                direction = target - ship.position
                if direction.length() > 0:
                    direction = direction.normalize()
                    missile_velocity = direction * MISSILE_SPEED
                    missiles.append(Missile(ship.position.x, ship.position.y, missile_velocity))

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            ship.rotate(-ROTATION_SPEED)
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            ship.rotate(ROTATION_SPEED)

        ship.update(keys)
        detected, _, distance, dot = enemy.update(ship.position)

        for ast in asteroids:
            ast.update()

        for missile in missiles[:]:
            missile.update()
            if not (0 <= missile.position.x <= WIDTH and 0 <= missile.position.y <= HEIGHT):
                missiles.remove(missile)

        for i in range(len(asteroids)):
            for j in range(i + 1, len(asteroids)):
                resolve_collision(asteroids[i], asteroids[j])

        for missile in missiles[:]:
            for ast in asteroids[:]:
                if missile.position.distance_to(ast.position) < missile.radius + ast.radius:
                    if missile in missiles:
                        missiles.remove(missile)
                    if ast in asteroids:
                        asteroids.remove(ast)
                        score += 10
                    break

        for missile in missiles[:]:
            if missile.position.distance_to(enemy.position) < missile.radius + enemy.radius:
                missiles.remove(missile)
                score += 50
                enemy.position = pygame.Vector2(random.randint(100, WIDTH - 100), random.randint(100, HEIGHT - 100))
                break

        screen.fill(BG_COLOR)

        enemy.draw(screen, detected)
        ship.draw(screen)

        for ast in asteroids:
            ast.draw(screen)
        for missile in missiles:
            missile.draw(screen)

        score_text = font.render(f"Score: {score}", True, WHITE)
        speed_text = font.render(f"Ship Speed: {ship.velocity.length():.2f}", True, WHITE)
        enemy_state_text = font.render(f"Enemy State: {enemy.state} (Dot: {dot:.2f})", True, ENEMY_COLOR if detected else ENEMY_PATROL_COLOR)
        controls_text = font.render("WASD/Arrows to Move & Rotate | Click to Shoot", True, GRAY)

        screen.blit(score_text, (20, 20))
        screen.blit(speed_text, (20, 50))
        screen.blit(enemy_state_text, (20, 80))
        screen.blit(controls_text, (20, HEIGHT - 35))

        pygame.display.flip()
        clock.tick(FPS)
   
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    asyncio.run(main())


