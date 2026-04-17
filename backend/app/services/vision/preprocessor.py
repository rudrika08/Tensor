"""
Image preprocessor — CLAHE enhancement + resize + numpy conversion.
"""
import cv2
import numpy as np
from pathlib import Path


def preprocess_image(image_path: str, target_size: tuple = (640, 640)) -> np.ndarray:
    """
    Load image from path, apply CLAHE, resize for model input.
    Returns BGR numpy array.
    """
    img = cv2.imread(image_path)
    if img is None:
        # Return blank image on failure
        return np.zeros((*target_size, 3), dtype=np.uint8)

    # CLAHE on L channel
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    img = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)

    # Resize keeping aspect ratio with letterbox padding
    img = letterbox(img, target_size)
    return img


def letterbox(img: np.ndarray, new_shape: tuple = (640, 640), color=(114, 114, 114)) -> np.ndarray:
    """Resize with padding to maintain aspect ratio."""
    h, w = img.shape[:2]
    nh, nw = new_shape
    scale = min(nw / w, nh / h)
    rw, rh = int(w * scale), int(h * scale)
    img = cv2.resize(img, (rw, rh), interpolation=cv2.INTER_LINEAR)
    top = (nh - rh) // 2
    bottom = nh - rh - top
    left = (nw - rw) // 2
    right = nw - rw - left
    img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)
    return img
