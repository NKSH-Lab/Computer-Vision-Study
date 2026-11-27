import cv2
import numpy as np
from pathlib import Path

# Load the original image
# 원본 이미지 불러오기
root = Path(__file__).resolve().parent
image_path = root / "images" / "document_01.jpg"

img = cv2.imread(str(image_path))

if img is None:
    raise FileNotFoundError("Image not found")

# Convert the BGR image to grayscale
# 컬러 이미지를 흑백 이미지로 변환
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# Reduce background noise using Gaussian Blur
# 가우시안 블러를 이용한 배경 노이즈 제거
blur = cv2.GaussianBlur(gray, (13, 13), 0)

# Detect edges using the Canny algorithm
# Canny 알고리즘을 이용한 경계선 검출
edges = cv2.Canny(blur, 30, 150)

# Connect small gaps between detected edges
# 닫힘 연산을 이용하여 끊어진 경계선의 작은 틈 연결
kernel = np.ones((7, 7), np.uint8)
closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

# Thicken edges for visualization
# 시각적 확인을 위해 팽창 연산으로 경계선 두께 증가
dilation_kernel = np.ones((3, 3), np.uint8)
edge_view = cv2.dilate(closed, dilation_kernel, iterations=1)

# Detect external contours
# 이미지의 외부 윤곽선 검출
contours, hierarchy = cv2.findContours(
    closed,
    cv2.RETR_EXTERNAL,
    cv2.CHAIN_APPROX_SIMPLE
)

# Sort contours by area in descending order
# 윤곽선을 면적 기준 내림차순으로 정렬
contours = sorted(
    contours,
    key=cv2.contourArea,
    reverse=True
)

# Search for a convex quadrilateral among the five largest contours
# 면적이 가장 큰 5개의 윤곽선 중 볼록 사각형 탐색
document = None

for contour in contours[:5]:

    # Calculate the contour perimeter
    # 윤곽선의 전체 둘레 계산
    perimeter = cv2.arcLength(contour, True)

    # Approximate the contour as a polygon
    # 윤곽선을 다각형으로 근사
    approx = cv2.approxPolyDP(
        contour, 0.02 * perimeter, True
    )

    # Select a convex polygon with four vertices
    # 꼭짓점이 4개인 볼록 다각형을 문서로 선택
    if len(approx) == 4 and cv2.isContourConvex(approx):
        document = approx
        break

# Draw the detected document boundary
# 검출된 문서의 외곽선을 원본 이미지 복사본에 표시
contour_view = img.copy()

if document is not None:
    cv2.drawContours(
        contour_view, [document], -1, (0, 255, 0), 3
    )
else:
    print("Document not found")



# Display intermediate processing results
# 각 영상 처리 단계의 중간 결과 출력
# cv2.namedWindow("Grayscale", cv2.WINDOW_NORMAL)
# cv2.resizeWindow("Grayscale", 500, 700)
# cv2.imshow("Grayscale", gray)

# cv2.namedWindow("Gaussian Blur", cv2.WINDOW_NORMAL)
# cv2.resizeWindow("Gaussian Blur", 500, 700)
# cv2.imshow("Gaussian Blur", blur)

# cv2.namedWindow("Canny Edge", cv2.WINDOW_NORMAL)
# cv2.resizeWindow("Canny Edge", 500, 700)
# cv2.imshow("Canny Edge", edges)

# cv2.namedWindow("Closing", cv2.WINDOW_NORMAL)
# cv2.resizeWindow("Closing", 500, 700)
# cv2.imshow("Closing", closed)

# cv2.namedWindow("Edge View", cv2.WINDOW_NORMAL)
# cv2.resizeWindow("Edge View", 500, 700)
# cv2.imshow("Edge View", edge_view)

# cv2.namedWindow("Contours", cv2.WINDOW_NORMAL)
# cv2.resizeWindow("Contours", 500, 700)
# cv2.imshow("Contours", contour_view)


# Arrange corner points in a consistent order
# 검출된 꼭짓점 4개를 일정한 순서로 자동 정렬
def order_points(points):

    points = points.reshape(4, 2)

    ordered = np.zeros((4, 2), dtype=np.float32)

    # Calculate coordinate sums and differences
    # 각 꼭짓점의 좌표 합과 차이 계산
    s = points.sum(axis=1)
    diff = np.diff(points, axis=1).flatten()

    # Top-left
    # 좌상단
    ordered[0] = points[np.argmin(s)]

    # Top-right
    # 우상단
    ordered[1] = points[np.argmin(diff)]

    # Bottom-right
    # 우하단
    ordered[2] = points[np.argmax(s)]

    # Bottom-left
    # 좌하단
    ordered[3] = points[np.argmax(diff)]

    return ordered


# Set the output resolution based on the A4 aspect ratio
# A4 용지의 가로세로 비율을 기준으로 출력 해상도 설정
output_width = 600
output_height = 849


# Perform perspective transformation
# 원근 변환 수행 함수
def perspective_transform(image, points, width, height):

    # Source coordinates
    # 원본 이미지의 꼭짓점 좌표 설정
    pts1 = np.float32(points)

    # Destination coordinates
    # 변환할 목표 이미지의 꼭짓점 좌표 설정
    pts2 = np.float32([
        [0, 0],
        [width - 1, 0],
        [width - 1, height - 1],
        [0, height - 1]
    ])

    # Calculate the perspective transformation matrix
    # 3x3 원근 변환 행렬 계산
    M = cv2.getPerspectiveTransform(pts1, pts2)

    # Generate the rectified image
    # 원근 변환을 적용하여 정면 보정 이미지 생성
    dst = cv2.warpPerspective(image, M, (width, height))

    return dst


# Apply automatic perspective correction
# 자동으로 검출된 꼭짓점을 이용하여 원근 보정 수행
if document is not None:

    pts1 = order_points(document)

    dst = perspective_transform(
        img, pts1, output_width, output_height
    )

    cv2.imshow("Transformed", dst)

# Create the output directory
# 결과 이미지 저장 폴더 생성
result_path = root / "v1_results_01"
result_path.mkdir(exist_ok=True)

# Save intermediate processing results
# 각 영상 처리 단계의 중간 결과 이미지 저장
cv2.imwrite(str(result_path / "grayscale.png"), gray)
cv2.imwrite(str(result_path / "gaussian_blur.png"), blur)
cv2.imwrite(str(result_path / "canny_edge.png"), edges)
cv2.imwrite(str(result_path / "closing.png"), closed)
cv2.imwrite(str(result_path / "contours.png"), contour_view)

# Save the final rectified image
# 최종 원근 보정 이미지 저장
if document is not None:
    cv2.imwrite(str(result_path / "automatic_result.png"), dst)

# Wait for user input and close all windows
# 사용자 키 입력 대기 후 모든 출력 창 종료
cv2.waitKey(0)
cv2.destroyAllWindows()