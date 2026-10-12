"""
gerar_icone.py - cria o ícone do atalho (balança da justiça) em assets/direito.ico.
Rode:  python gerar_icone.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DESTINO = Path(__file__).parent / "assets" / "direito.ico"
S = 1024  # desenha grande e reduz (fica nítido)

img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

margem = 16
d.ellipse([margem, margem, S - margem, S - margem], fill=(20, 40, 78, 255))
d.ellipse([margem, margem, S - margem, S - margem], outline=(198, 160, 58, 255), width=20)

font = ImageFont.truetype(r"C:\Windows\Fonts\seguisym.ttf", 700)
glifo = "\u2696"  # ⚖ balança da justiça
cx = (S - (bbox := d.textbbox((0, 0), glifo, font=font))[2] + bbox[0]) / 2 - bbox[0]
cy = (S - bbox[3] + bbox[1]) / 2 - bbox[1]
d.text((cx, cy), glifo, font=font, fill=(224, 188, 92, 255))

final = img.resize((512, 512), Image.LANCZOS)
DESTINO.parent.mkdir(exist_ok=True)
final.save(DESTINO, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("Ícone salvo em:", DESTINO)
