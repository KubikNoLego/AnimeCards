import os
import tempfile
from PIL import Image
from typing import List, Tuple
from app.database.models import Card

CARD_SIZE = (300, 450)

def create_positions(card_size):
    CANVAS_WIDTH = 1920
    CANVAS_HEIGHT = 1080
    CARD_WIDTH, CARD_HEIGHT = card_size
    COLS = 5
    ROWS = 2
    MARGIN_X = 60
    MARGIN_Y = 60

    available_width = CANVAS_WIDTH - 2 * MARGIN_X - COLS * CARD_WIDTH
    gap_x = available_width // (COLS - 1) if COLS > 1 else 0

    available_height = CANVAS_HEIGHT - 2 * MARGIN_Y - ROWS * CARD_HEIGHT
    gap_y = available_height // (ROWS - 1) if ROWS > 1 else 0

    positions = []
    for row in range(ROWS):
        for col in range(COLS):
            x = MARGIN_X + col * (CARD_WIDTH + gap_x)
            y = MARGIN_Y + row * (CARD_HEIGHT + gap_y)
            center_x = x + CARD_WIDTH // 2
            center_y = y + CARD_HEIGHT // 2
            positions.append((center_x, center_y))
    return positions

CARD_POSITIONS = create_positions(CARD_SIZE)

def generate_cards_image(cards: List[Tuple[Card, bool]]) -> str:
    if len(cards) != 10:
        raise ValueError("Должно быть ровно 10 карт")

    card_paths = []
    for card, shiny in cards:
        card_paths.append(card.icon_path(shiny))

    background = Image.open("app/assets/background.png").convert("RGBA")
    cards_layer = Image.new("RGBA", background.size, (0, 0, 0, 0))

    for i, card_path in enumerate(card_paths):
        card_img = Image.open(card_path).convert("RGBA")
        card_img = card_img.resize(CARD_SIZE, Image.LANCZOS)

        center_x, center_y = CARD_POSITIONS[i]
        x = center_x - CARD_SIZE[0] // 2
        y = center_y - CARD_SIZE[1] // 2

        cards_layer.paste(card_img, (x, y), card_img)

    result = Image.alpha_composite(background, cards_layer)

    temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    result.save(temp_file.name, "PNG")
    temp_file.close()

    return temp_file.name