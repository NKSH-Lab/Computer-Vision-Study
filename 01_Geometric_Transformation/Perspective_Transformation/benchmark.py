import cv2
import numpy as np
import time
import csv
from pathlib import Path

# Path configuration
# 이미지 및 결과 저장 경로 설정
root = Path(__file__).resolve().parent
image_dir = root / "images"
result_dir = root / "benchmark_results"

result_dir.mkdir(exist_ok=True)

# Benchmark configuration
# 성능 측정 조건 설정
WARMUP = 10
REPEAT = 100

OUTPUT_WIDTH = 600
OUTPUT_HEIGHT = 849

# Algorithm configuration
# 버전별 알고리즘 파라미터 설정
configs = {
    "V1": {
        "resize": False,
        "blur": 13,
        "canny_low": 30,
        "canny_high": 150,
        "closing": 7,
        "min_area": 0.0,
        "top5": True,
        "hull": False,
        "epsilon": 0.02
    },

    "V2": {
        "resize": False,
        "blur": 9,
        "canny_low": 30,
        "canny_high": 100,
        "closing": 7,
        "min_area": 0.05,
        "top5": False,
        "hull": True,
        "epsilon": 0.02
    },

    "V3": {
        "resize": True,
        "blur": 9,
        "canny_low": 30,
        "canny_high": 100,
        "closing": 7,
        "min_area": 0.05,
        "top5": False,
        "hull": True,
        "epsilon": 0.02
    }
}


# Arrange corner points
# 꼭짓점 좌표 정렬
def order_points(points):

    points = points.reshape(4, 2)
    ordered = np.zeros((4, 2), dtype=np.float32)

    s = points.sum(axis=1)
    diff = np.diff(points, axis=1).flatten()

    ordered[0] = points[np.argmin(s)]
    ordered[1] = points[np.argmin(diff)]
    ordered[2] = points[np.argmax(s)]
    ordered[3] = points[np.argmax(diff)]

    return ordered


# Detect document corners
# 버전별 문서 꼭짓점 검출
def detect_document(img, config):

    # Normalize input resolution for V3
    # V3 입력 해상도 표준화
    if config["resize"]:

        scale = min(1.0, 1000 / max(img.shape[:2]))

        resized = cv2.resize(
            img, None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_AREA
        )

    else:
        resized = img

    # Grayscale conversion
    # 흑백 변환
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

    # Gaussian Blur
    # 배경 노이즈 제거
    k = config["blur"]

    blur = cv2.GaussianBlur(gray, (k, k), 0)

    # Canny Edge Detection
    # 경계선 검출
    edges = cv2.Canny(
        blur,
        config["canny_low"],
        config["canny_high"]
    )

    # Morphological Closing
    # 끊어진 경계선 연결
    k = config["closing"]
    kernel = np.ones((k, k), np.uint8)

    closed = cv2.morphologyEx(
        edges, cv2.MORPH_CLOSE, kernel
    )

    # Contour Detection
    # 외부 윤곽선 검출
    contours, _ = cv2.findContours(
        closed,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    # Sort contours by area
    # 윤곽선 면적 기준 내림차순 정렬
    contours = sorted(
        contours,
        key=cv2.contourArea,
        reverse=True
    )

    if config["top5"]:
        contours = contours[:5]

    # Minimum area filtering
    # 최소 면적 필터링
    image_area = resized.shape[0] * resized.shape[1]
    min_area = image_area * config["min_area"]

    for contour in contours:

        area = cv2.contourArea(contour)

        if area < min_area:
            continue

        # Convex Hull for V2 and V3
        # V2 및 V3 볼록 껍질 생성
        if config["hull"]:
            candidate = cv2.convexHull(contour)
        else:
            candidate = contour

        # Polygon approximation
        # 다각형 근사
        perimeter = cv2.arcLength(candidate, True)

        approx = cv2.approxPolyDP(
            candidate,
            config["epsilon"] * perimeter,
            True
        )

        if len(approx) == 4 and cv2.isContourConvex(approx):

            points = order_points(approx)

            # Restore original coordinates
            # 원본 이미지 좌표로 복원
            if config["resize"]:

                points[:, 0] *= (
                    img.shape[1] / resized.shape[1]
                )

                points[:, 1] *= (
                    img.shape[0] / resized.shape[0]
                )

            return points

    return None


# Perspective transformation
# 원근 변환 수행
def perspective_transform(img, points):

    pts1 = np.float32(points)

    pts2 = np.float32([
        [0, 0],
        [OUTPUT_WIDTH - 1, 0],
        [OUTPUT_WIDTH - 1, OUTPUT_HEIGHT - 1],
        [0, OUTPUT_HEIGHT - 1]
    ])

    M = cv2.getPerspectiveTransform(pts1, pts2)

    dst = cv2.warpPerspective(
        img, M, (OUTPUT_WIDTH, OUTPUT_HEIGHT)
    )

    return dst


# Benchmark a single image
# 이미지 한 장에 대한 반복 성능 측정
def benchmark(img, config):

    # Warm-up
    # 초기 실행 오버헤드 감소
    for _ in range(WARMUP):

        points = detect_document(img, config)

        if points is not None:
            perspective_transform(img, points)

    detection_times = []
    warp_times = []
    total_times = []

    # Repeated measurement
    # 100회 반복 시간 측정
    for _ in range(REPEAT):

        start = time.perf_counter()

        points = detect_document(img, config)

        detection_end = time.perf_counter()

        detection_times.append(
            (detection_end - start) * 1000
        )

        if points is not None:

            perspective_transform(img, points)

            end = time.perf_counter()

            warp_times.append(
                (end - detection_end) * 1000
            )

            total_times.append(
                (end - start) * 1000
            )

    detection_mean = np.mean(detection_times)

    warp_mean = (
        np.mean(warp_times) if warp_times else None
    )

    total_mean = (
        np.mean(total_times) if total_times else None
    )

    detection_std = np.std(detection_times)

    return (
        detection_mean,
        warp_mean,
        total_mean,
        detection_std,
        len(warp_times)
    )


# Format measurement results
# 측정값 출력 형식 설정
def format_time(value):

    if value is None:
        return "N/A"

    return f"{value:.4f}"


# Load test images
# 테스트 이미지 목록 불러오기
image_paths = sorted([
    path for path in image_dir.iterdir()
    if path.suffix.lower() in [".jpg", ".jpeg", ".png"]
])

if not image_paths:
    raise FileNotFoundError("No test images found")

results = []

# Benchmark all versions
# 모든 버전에 대한 성능 측정
for version, config in configs.items():

    print("\n" + "=" * 75)
    print(f"Benchmark: {version}")
    print("=" * 75)

    for image_path in image_paths:

        img = cv2.imread(str(image_path))

        if img is None:
            print(f"Failed to load: {image_path.name}")
            continue

        detection, warp, total, std, detected = benchmark(
            img, config
        )

        print(f"\nImage: {image_path.name}")
        print(f"Detection: {format_time(detection)} ms")
        print(f"Warp:      {format_time(warp)} ms")
        print(f"Total:     {format_time(total)} ms")
        print(f"Std:       {format_time(std)} ms")
        print(f"Candidates: {detected}/{REPEAT}")

        results.append([
            version,
            image_path.name,
            detection,
            warp,
            total,
            std,
            detected
        ])


# Save benchmark results
# 성능 측정 결과 CSV 파일 저장
csv_path = result_dir / "latency_results.csv"

with open(csv_path, "w", newline="") as f:

    writer = csv.writer(f)

    writer.writerow([
        "Version",
        "Image",
        "Detection_ms",
        "Warp_ms",
        "Total_ms",
        "Detection_STD_ms",
        "Candidate_Count"
    ])

    writer.writerows(results)

print("\nBenchmark completed")
print(f"Results saved to: {csv_path}")