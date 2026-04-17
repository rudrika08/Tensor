"""
CLIP zero-shot product category classifier.
Uses open_clip (free, local) — no API key needed.
Falls back to heuristic mock when model not available.
"""
import logging
import numpy as np
from typing import List

logger = logging.getLogger(__name__)

PRODUCT_CATEGORIES = [
    "staples like rice wheat flour dal",
    "FMCG packaged goods like soap shampoo toothpaste",
    "snacks like chips biscuits namkeen",
    "beverages like cold drinks juice water bottles",
    "dairy products like milk paneer butter",
    "tobacco and cigarettes",
    "personal care products",
    "household items like detergent",
    "fresh produce vegetables fruits",
]

CATEGORY_KEYS = [
    "staples", "FMCG", "snacks", "beverages",
    "dairy", "tobacco", "personal_care", "household", "fresh_produce"
]

_clip_model = None
_clip_preprocess = None
_clip_tokenizer = None


def _load_clip():
    global _clip_model, _clip_preprocess, _clip_tokenizer
    if _clip_model is not None:
        return True
    try:
        import open_clip
        import torch
        _clip_model, _, _clip_preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32", pretrained="openai"
        )
        _clip_tokenizer = open_clip.get_tokenizer("ViT-B-32")
        _clip_model.eval()
        logger.info("CLIP model loaded (open_clip ViT-B-32)")
        return True
    except Exception as e:
        logger.warning(f"CLIP not available, using mock: {e}")
        return False


def classify_categories(preprocessed_images: List[np.ndarray]) -> dict:
    """
    Zero-shot classify what product categories are visible.
    Returns dict: {category_key: weight (0-1)}, sums to 1.
    """
    if not _load_clip():
        return _mock_categories()

    try:
        import torch
        from PIL import Image

        # Encode text labels once
        text_tokens = _clip_tokenizer(PRODUCT_CATEGORIES)
        with torch.no_grad():
            text_features = _clip_model.encode_text(text_tokens)
            text_features /= text_features.norm(dim=-1, keepdim=True)

        # Average image features across all images
        all_img_features = []
        for img_arr in preprocessed_images:
            pil_img = Image.fromarray(img_arr[..., ::-1])  # BGR→RGB
            img_tensor = _clip_preprocess(pil_img).unsqueeze(0)
            with torch.no_grad():
                img_feat = _clip_model.encode_image(img_tensor)
                img_feat /= img_feat.norm(dim=-1, keepdim=True)
            all_img_features.append(img_feat)

        avg_img_features = torch.stack(all_img_features).mean(dim=0)

        # Cosine similarity → softmax probabilities
        similarity = (100.0 * avg_img_features @ text_features.T).softmax(dim=-1)
        probs = similarity[0].cpu().numpy()

        return {k: round(float(v), 4) for k, v in zip(CATEGORY_KEYS, probs)}

    except Exception as e:
        logger.exception(f"CLIP inference error: {e}")
        return _mock_categories()


def _mock_categories() -> dict:
    import random
    weights = np.array([random.random() for _ in CATEGORY_KEYS])
    weights /= weights.sum()
    return {k: round(float(v), 4) for k, v in zip(CATEGORY_KEYS, weights)}
