import cv2
import numpy as np
from pathlib import Path

root = Path(__file__).resolve().parent
image_path = root / "images" / "document.jpg"

img = cv2.imread(str(image_path))

if img is None:
    raise FileNotFoundError("Image not found")

scale = min(1.0, 800 / max(img.shape[:2]))
preview = cv2.resize(img, None, fx=scale, fy=scale)

points = []

def mouse_click(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN and len(points) < 4:
        points.append([x, y])
        cv2.circle(preview, (x, y), 5, (0, 0, 255), -1)
        cv2.imshow("Original", preview)

cv2.imshow("Original", preview)
cv2.setMouseCallback("Original", mouse_click)
print("Select four corners in order:")
print("1. Top-left")
print("2. Top-right")
print("3. Bottom-right")
print("4. Bottom-left")

while len(points) < 4:
    if cv2.waitKey(20) == 27:
        cv2.destroyAllWindows()
        exit()

output_width = 600
output_height = 849

def perspective_transform(image, points, width, height):

    pts1 = np.float32(points)

    pts2 = np.float32([
        [0, 0],
        [width - 1, 0],
        [width - 1, height - 1],
        [0, height - 1]
    ])

    M = cv2.getPerspectiveTransform(pts1, pts2)
    dst = cv2.warpPerspective(image, M, (width, height))
    return dst

# Restore original coordinates
pts1 = np.float32(points) / scale

# Call perspective transformation
dst = perspective_transform(
    img, pts1, output_width, output_height
)

# Create output directory
result_path = root / "results"
result_path.mkdir(exist_ok=True)

# Display and save results
cv2.imshow("Transformed", dst)

cv2.imwrite(str(result_path / "manual_original.png"), preview)
cv2.imwrite(str(result_path / "manual_result.png"), dst)

cv2.waitKey(0)
cv2.destroyAllWindows()