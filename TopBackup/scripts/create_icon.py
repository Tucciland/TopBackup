"""
TopBackup - Script para criar ícone padrão
Execute este script para gerar o ícone do aplicativo
"""

from PIL import Image, ImageDraw, ImageFont
import os


def create_icon():
    """Cria ícone do aplicativo"""
    # Tamanhos para o ICO
    sizes = [16, 32, 48, 64, 128, 256]

    # Diretório de assets
    script_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(script_dir, '..', 'assets')
    os.makedirs(assets_dir, exist_ok=True)

    images = []

    for size in sizes:
        # Cria imagem
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Fundo arredondado (verde)
        padding = max(1, size // 16)
        draw.rounded_rectangle(
            [padding, padding, size - padding, size - padding],
            radius=size // 8,
            fill=(46, 204, 113, 255)  # Verde
        )

        # Desenha "B" de Backup
        try:
            # Tenta usar fonte do sistema
            font_size = int(size * 0.5)
            font = ImageFont.truetype("arial.ttf", font_size)
        except Exception:
            # Fallback para fonte padrão
            font = ImageFont.load_default()

        text = "B"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x = (size - text_width) // 2
        y = (size - text_height) // 2 - bbox[1]

        draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)

        images.append(img)

    # Salva como ICO
    ico_path = os.path.join(assets_dir, 'icon.ico')
    images[0].save(
        ico_path,
        format='ICO',
        sizes=[(s, s) for s in sizes],
        append_images=images[1:]
    )

    print(f"Ícone criado: {ico_path}")

    # Também salva como PNG para o tray
    png_path = os.path.join(assets_dir, 'icon_tray.png')
    images[-1].save(png_path, format='PNG')
    print(f"Ícone tray criado: {png_path}")


if __name__ == '__main__':
    create_icon()
