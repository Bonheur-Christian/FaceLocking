"""
Face enrollment module.

Captures multiple HIGH-QUALITY face samples, extracts one embedding per sample,
and stores them as a multi-embedding template per person. Quality gates reject
blurry, tiny, partial and extreme-angle faces, and near-duplicate samples are
skipped so the stored set stays diverse. A diverse multi-embedding template is
far more robust at recognition time than a single averaged vector.
"""

import sys
import json
import time
from typing import Dict, List
import cv2
import numpy as np

from . import config
from .haar_5pt import HaarMediaPipeFaceDetector
from .align import FaceAligner
from .embed import ArcFaceEmbedder
from . import quality


def load_existing_db():
    """Load existing face database as {name: (N, 512)}."""
    if not config.DB_NPZ_PATH.exists():
        return {}
    data = np.load(str(config.DB_NPZ_PATH), allow_pickle=True)
    db = {}
    for k in data.files:
        arr = data[k].astype(np.float32)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        db[k] = arr
    return db


def save_db(db: Dict[str, np.ndarray], metadata: dict):
    """Save face database and metadata."""
    config.ensure_dirs()
    np.savez(str(config.DB_NPZ_PATH), **db)
    config.DB_JSON_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def select_diverse(embeddings: List[np.ndarray], max_keep: int) -> np.ndarray:
    """
    Keep at most `max_keep` embeddings, chosen for maximum diversity via
    farthest-point sampling (greedy). Preserves pose/expression variety, which
    is what makes the template generalise.
    """
    E = np.stack([e.reshape(-1) for e in embeddings], axis=0).astype(np.float32)
    n = E.shape[0]
    if n <= max_keep:
        return E

    selected = [0]
    # Cosine distance = 1 - dot (vectors are L2-normalized).
    min_dist = 1.0 - (E @ E[0])
    while len(selected) < max_keep:
        nxt = int(np.argmax(min_dist))
        selected.append(nxt)
        d = 1.0 - (E @ E[nxt])
        min_dist = np.minimum(min_dist, d)
    return E[selected]


def main():
    """Enrollment pipeline with quality filtering and multi-embedding template."""
    config.ensure_dirs()

    name = input("Enter person name to enroll (e.g., Alice): ").strip()
    if not name:
        print("No name provided. Exiting.")
        return False

    detector = HaarMediaPipeFaceDetector(min_size=config.HAAR_MIN_SIZE)
    aligner = FaceAligner()
    embedder = ArcFaceEmbedder(config.ARCFACE_MODEL_PATH)

    person_dir = config.ENROLL_DIR / name
    person_dir.mkdir(parents=True, exist_ok=True)

    db = load_existing_db()

    # Collected embeddings (kept diverse via duplicate rejection).
    samples: List[np.ndarray] = []
    rejected = {"blur": 0, "small": 0, "pose": 0, "dup": 0, "no_face": 0}

    # Load existing aligned crops from disk if re-enrolling.
    existing_paths = sorted(person_dir.glob("*.jpg"))
    if existing_paths:
        print(f"Found existing enrollment for {name}. Loading samples...")
        for img_path in existing_paths[: config.MAX_EXISTING_CROPS_PER_PERSON]:
            img = cv2.imread(str(img_path))
            if img is None or img.shape[:2] != config.EMBEDDING_INPUT_SIZE:
                continue
            if quality.blur_variance(img) < config.ENROLL_BLUR_MIN_VAR:
                continue
            try:
                emb, _ = embedder.embed(img)
            except Exception:
                continue
            if not quality.is_duplicate(emb, samples):
                samples.append(emb)
        print(f"Loaded {len(samples)} usable existing samples.")

    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    if not cap.isOpened():
        print("ERROR: Cannot open camera.")
        return False

    cv2.namedWindow("Enrollment - Main")
    cv2.namedWindow("Enrollment - Aligned")
    cv2.resizeWindow("Enrollment - Aligned", 200, 200)

    status_msg = "Waiting for faces..."
    auto_mode = False
    last_auto_capture = 0.0

    print(f"\nEnrolling: {name}")
    print("Controls:")
    print("  SPACE  - Capture one sample")
    print("  a      - Toggle auto-capture")
    print("  s      - Save enrollment")
    print("  r      - Reset NEW samples")
    print("  q      - Quit")

    t0 = time.time()
    frame_count = 0
    fps = 0

    def try_capture(frame, face, aligned) -> str:
        """Quality-gate + dedup a candidate sample. Returns a status string."""
        bbox = (face.x1, face.y1, face.x2, face.y2)
        ok, reason = quality.assess_enrollment(aligned, face.landmarks, bbox)
        if not ok:
            if "blur" in reason:
                rejected["blur"] += 1
            elif "small" in reason or "far" in reason:
                rejected["small"] += 1
            elif "angle" in reason or "pose" in reason:
                rejected["pose"] += 1
            return f"REJECT: {reason}"
        emb, _ = embedder.embed(aligned)
        if quality.is_duplicate(emb, samples):
            rejected["dup"] += 1
            return "REJECT: too similar to a kept sample"
        samples.append(emb)
        if config.SAVE_ENROLLMENT_CROPS:
            ts = int(time.time() * 1000)
            cv2.imwrite(str(person_dir / f"{ts}.jpg"), aligned)
        return f"Captured {len(samples)} (kept)"

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            elapsed = time.time() - t0
            if elapsed >= 1.0:
                fps = frame_count / elapsed
                frame_count = 0
                t0 = time.time()

            vis = frame.copy()
            aligned_vis = np.zeros(
                (config.ALIGNMENT_OUTPUT_SIZE[1], config.ALIGNMENT_OUTPUT_SIZE[0], 3),
                dtype=np.uint8,
            )

            faces = detector.detect(frame)
            face = faces[0] if faces else None

            if face is not None:
                aligned_vis, _ = aligner.align(frame, face.landmarks)
                # Live quality readout so the user knows when a pose is good.
                qok, qreason = quality.assess_enrollment(
                    aligned_vis,
                    face.landmarks,
                    (face.x1, face.y1, face.x2, face.y2),
                )
                box_color = (0, 255, 0) if qok else (0, 165, 255)
                cv2.rectangle(vis, (face.x1, face.y1), (face.x2, face.y2), box_color, 2)
                for (x, y) in face.landmarks.astype(int):
                    cv2.circle(vis, (int(x), int(y)), 3, box_color, -1)

                if auto_mode and qok and (time.time() - last_auto_capture) >= config.AUTO_CAPTURE_INTERVAL_SECONDS:
                    status_msg = try_capture(frame, face, aligned_vis)
                    last_auto_capture = time.time()
                elif not qok:
                    status_msg = qreason
            else:
                rejected["no_face"] = rejected.get("no_face", 0)

            total_samples = len(samples)
            info_lines = [
                f"ENROLL: {name}",
                f"Kept: {total_samples} / need {config.SAMPLES_NEEDED_FOR_ENROLLMENT}",
                f"Auto: {'ON' if auto_mode else 'OFF'} (a)  FPS: {fps:.1f}",
                f"Rej blur/small/pose/dup: "
                f"{rejected['blur']}/{rejected['small']}/{rejected['pose']}/{rejected['dup']}",
                status_msg,
            ]
            y = 26
            for line in info_lines:
                cv2.putText(vis, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3)
                cv2.putText(vis, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                y += 24

            cv2.imshow("Enrollment - Main", vis)
            cv2.imshow("Enrollment - Aligned", aligned_vis)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key == ord("a"):
                auto_mode = not auto_mode
                status_msg = f"Auto mode {'ON' if auto_mode else 'OFF'}"
            elif key == ord("r"):
                samples.clear()
                status_msg = "New samples reset"
            elif key == ord(" "):
                if face is None:
                    status_msg = "No face detected"
                else:
                    status_msg = try_capture(frame, face, aligned_vis)
            elif key == ord("s"):
                total = len(samples)
                if total < config.MIN_SAMPLES_TO_SAVE:
                    status_msg = f"Need >= {config.MIN_SAMPLES_TO_SAVE} samples (have {total})"
                    continue

                template = select_diverse(samples, config.ENROLL_MAX_EMBEDDINGS)
                db[name] = template.astype(np.float32)

                metadata = {
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "embedding_dim": int(template.shape[1]),
                    "names": sorted(db.keys()),
                    "embeddings_per_person": {k: int(v.shape[0]) for k, v in db.items()},
                    "samples_used": int(template.shape[0]),
                }
                save_db(db, metadata)
                print(
                    f"\n✓ Enrolled '{name}' with {template.shape[0]} diverse embeddings "
                    f"(captured {total}, rejected "
                    f"{rejected['blur']} blur / {rejected['small']} small / "
                    f"{rejected['pose']} pose / {rejected['dup']} dup)"
                )
                return True
    finally:
        cap.release()
        cv2.destroyAllWindows()

    print("Enrollment cancelled.")
    return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
