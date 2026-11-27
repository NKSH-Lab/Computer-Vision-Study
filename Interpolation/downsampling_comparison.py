import cv2
import matplotlib.pyplot as plt
import time
from skimage.metrics import structural_similarity as ssim
from pathlib import Path

image_path = Path(__file__).resolve().parent / "images" / "keyboard.jpg"
src = cv2.imread(str(image_path))

if src is None:
    raise FileNotFoundError("Image not found")

original = src.copy()

methods = {
    "Nearest": cv2.INTER_NEAREST,
    "Bilinear": cv2.INTER_LINEAR,
    "Bicubic": cv2.INTER_CUBIC,
    "Lanczos4": cv2.INTER_LANCZOS4,
    "Area": cv2.INTER_AREA
}

scale_factors = [2, 4, 8]
h, w = src.shape[:2]

for scale in scale_factors:

    plt.figure(figsize=(12, 8))
    plt.suptitle(f"Downsampling: 1/{scale}")

    target_size = (w // scale, h // scale)

    for i, (name, method) in enumerate(methods.items()):

        # Warm-up
        for _ in range(10):
            dst = cv2.resize(src, target_size,
                             interpolation=method)

        # Benchmark
        start = time.perf_counter()

        for _ in range(100):
            dst = cv2.resize(src, target_size,
                             interpolation=method)

        end = time.perf_counter()

        avg_time = (end - start) * 1000 / 100

        # Reconstruction
        restored = cv2.resize(
            dst, (w, h),
            interpolation=cv2.INTER_LINEAR
        )

        # PSNR
        psnr_value = cv2.PSNR(original, restored)

        # SSIM
        ssim_value = ssim(
            original, restored,
            channel_axis=2,
            data_range=255
        )

        # Print results
        print(f"1/{scale} {name}")
        print(f"Latency: {avg_time:.3f} ms")
        print(f"PSNR: {psnr_value:.3f} dB")
        print(f"SSIM: {ssim_value:.4f}")
        print()

        # Visualization
        plt.subplot(2, 3, i + 1)
        plt.imshow(cv2.cvtColor(dst, cv2.COLOR_BGR2RGB))
        plt.title(name)
        plt.axis("off")

    plt.tight_layout()

plt.show()