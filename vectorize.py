import cv2
import numpy as np
import sys
import os

def create_svg(image_path, output_path):
    # Load image
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not read image {image_path}")
        return

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Thresholding
    # Invert binary threshold so the objects (lines/text) are white and background is black
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

    # Find contours
    contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    height, width = img.shape[:2]

    # Use a list for path data to avoid quadratic string concatenation
    path_data_list = []

    # Iterate through contours and collect path data
    for contour in contours:
            if len(contour) < 3:
                continue

            # Create path string for this contour
            # Start with M (Move to)
            pts = contour.reshape(-1, 2)
            # Create a string like "x,y x,y x,y"
            # Map coords to strings
            coords = [f"{x},{y}" for x, y in pts]
            path_d = "M " + " ".join(coords) + " Z"
            path_data_list.append(path_d)

    full_path_d = " ".join(path_data_list)

    with open(output_path, 'w') as f:
        f.write(f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">\n')
        f.write(f'<path d="{full_path_d}" fill="black" fill-rule="evenodd" />\n')
        f.write('</svg>')

    print(f"Successfully created {output_path}")

if __name__ == "__main__":
    if len(sys.argv) > 2:
        input_file = sys.argv[1]
        output_file = sys.argv[2]
    else:
        # Default fallback if no args provided
        input_file = "Gemini_Generated_Image_1hglyr1hglyr1hgl.png"
        output_file = "Gemini_Generated_Image_1hglyr1hglyr1hgl.svg"

    create_svg(input_file, output_file)
