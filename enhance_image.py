from PIL import Image, ImageFilter, ImageChops

def trim(im):
    """
    Trims the image by removing the border of the same color as the top-left pixel.
    """
    bg = Image.new(im.mode, im.size, im.getpixel((0,0)))
    diff = ImageChops.difference(im, bg)
    diff = ImageChops.add(diff, diff, 2.0, -100)
    bbox = diff.getbbox()
    if bbox:
        return im.crop(bbox)
    return im # return original if no bbox found

def enhance_image(input_path, output_path):
    print(f"Processing {input_path}...")
    try:
        with Image.open(input_path) as img:
            print(f"Original Mode: {img.mode}")

            # 1. Trim Whitespace/Transparency
            # Check if image is RGBA and fully transparent at 0,0
            # If so, getbbox might just work if the rest is non-transparent content
            # But trim() is safer for general 'background' removal.
            cropped_img = trim(img)
            print(f"Original size: {img.size}, Cropped size: {cropped_img.size}")

            # 2. Sharpen
            # Convert to RGB if necessary for certain filters, but SHARPEN works on RGBA usually.
            sharpened_img = cropped_img.filter(ImageFilter.SHARPEN)
            print("Image sharpened.")

            # 3. Save with DPI 300
            sharpened_img.save(output_path, dpi=(300, 300))
            print(f"Saved to {output_path} with 300 DPI.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    enhance_image("Gemini_Generated_Image_1hglyr1hglyr1hgl.png", "Gemini_Generated_Image_Enhanced.png")
