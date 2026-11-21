from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

def criar_icone(caminho_ico: Path, caminho_png: Path):
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Sombra sutil atrás do documento
    shadow_offset = 6
    draw.rounded_rectangle(
        [28 + shadow_offset, 20 + shadow_offset, 228 + shadow_offset, 236 + shadow_offset],
        radius=28,
        fill=(15, 23, 42, 40)
    )

    # 2. Fundo principal do documento (Gradiente Indigo / Azul moderno)
    # Desenha retângulo arredondado base
    doc_box = [28, 20, 228, 236]
    draw.rounded_rectangle(doc_box, radius=28, fill=(30, 27, 75, 255)) # Indigo 950

    # 3. Cabeçalho colorido no topo do documento
    draw.rounded_rectangle([28, 20, 228, 90], radius=28, fill=(79, 70, 229, 255)) # Indigo 600
    # Retângulo reto para preencher a parte de baixo do cabeçalho
    draw.rectangle([28, 50, 228, 90], fill=(79, 70, 229, 255))

    # 4. Badge "NF" no topo
    try:
        font_large = ImageFont.truetype("arialbd.ttf", 38)
        font_sub = ImageFont.truetype("arialbd.ttf", 24)
        font_small = ImageFont.truetype("arial.ttf", 16)
    except Exception:
        font_large = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Texto "NF" no topo em branco
    draw.text((128, 55), "NF", fill=(255, 255, 255, 255), anchor="mm", font=font_large)

    # 5. Linhas estilizadas representando itens da nota / boleto
    line_color = (226, 232, 240, 200) # Slate 200
    accent_color = (16, 185, 129, 255) # Emerald 500

    # Linha 1 (Título da linha)
    draw.rounded_rectangle([52, 115, 204, 127], radius=6, fill=line_color)
    # Linha 2
    draw.rounded_rectangle([52, 140, 160, 150], radius=5, fill=(148, 163, 184, 180))
    # Linha 3
    draw.rounded_rectangle([52, 162, 180, 172], radius=5, fill=(148, 163, 184, 180))

    # 6. Selo / Círculo de Validação / Boleto (Verde Esmeralda no canto inferior direito)
    badge_center = (185, 195)
    r = 34
    draw.ellipse(
        [badge_center[0] - r, badge_center[1] - r, badge_center[0] + r, badge_center[1] + r],
        fill=(16, 185, 129, 255), # Emerald
        outline=(255, 255, 255, 255),
        width=4
    )
    # Símbolo de Cifrão $ ou Check dentro do selo
    draw.text(badge_center, "$", fill=(255, 255, 255, 255), anchor="mm", font=font_sub)

    # Salva em PNG
    img.save(caminho_png, format="PNG")

    # Salva em ICO com múltiplos tamanhos
    tamanhos = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(caminho_ico, format="ICO", sizes=tamanhos)
    print("Ícone criado com sucesso em:", caminho_ico)

if __name__ == "__main__":
    pasta = Path(r"C:\Users\Suporte\.gemini\antigravity\scratch\separador_notas")
    criar_icone(pasta / "app_icon.ico", pasta / "app_icon.png")
