from pathlib import Path
from PIL import Image, ImageDraw

SIZE = 1024
OUT = Path(__file__).parent


def build() -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # fundo: quadrado arredondado com degradê azul
    bg = Image.new("RGBA", (SIZE, SIZE))
    px = bg.load()
    for y in range(SIZE):
        t = y / SIZE
        c = (int(37 + 20 * t), int(99 - 25 * t), int(235 - 60 * t), 255)
        for x in range(SIZE):
            px[x, y] = c
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle((32, 32, SIZE - 32, SIZE - 32), radius=220, fill=255)
    img.paste(bg, (0, 0), mask)

    white = (255, 255, 255, 255)
    soft = (255, 255, 255, 170)

    # onda sonora (barras) na metade superior
    heights = [120, 260, 400, 300, 460, 240, 340, 150]
    bar_w, gap = 62, 34
    total = len(heights) * bar_w + (len(heights) - 1) * gap
    x0 = (SIZE - total) // 2
    cy = 365
    for i, h in enumerate(heights):
        x = x0 + i * (bar_w + gap)
        d.rounded_rectangle((x, cy - h // 2, x + bar_w, cy + h // 2), radius=bar_w // 2, fill=white)

    # linhas de texto na metade inferior
    y = 640
    for x_end, col in [(804, white), (700, soft), (560, soft)]:
        d.rounded_rectangle((220, y, x_end, y + 48), radius=24, fill=col)
        y += 96
    return img


if __name__ == "__main__":
    icon = build()
    icon.resize((512, 512), Image.LANCZOS).save(OUT / "icon.png")
    icon.save(OUT / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("icon.ico e icon.png gerados")
