from PIL import Image, ImageDraw, ImageFont

# You might need to provide the full path to a font file
# On Unix systems, you can download a font (like DejaVuSans) and provide its path
#font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size=45)
font = ImageFont.load_default()

for i in range(1, 1001):
    # Create a new white image
    img = Image.new('RGB', (200, 200), color = (255, 255, 255))

    d = ImageDraw.Draw(img)
    
    # Draw the number on the image
    d.text((50,50), str(i), font=font, fill=(0,0,0))
    
    # Save the image as JPEG
    img.save(f'./output/numbered/capture/image_{i}.jpg')
