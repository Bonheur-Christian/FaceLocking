#!/usr/bin/env python3
"""
Test script to verify that two different people can be recognized simultaneously.
Simulates face recognition by testing embeddings from the database.
"""

import sys
import numpy as np
from pathlib import Path
import cv2

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src import config
from src.align import FaceAligner
from src.embed import ArcFaceEmbedder


def test_two_person_recognition():
    """Test recognition by loading samples from two different people."""
    
    print("=" * 60)
    print("TWO-PERSON RECOGNITION TEST")
    print("=" * 60)
    
    # Load database
    if not config.DB_NPZ_PATH.exists():
        print("ERROR: Database not found. Run enrollment first.")
        return False
    
    data = np.load(str(config.DB_NPZ_PATH), allow_pickle=True)
    db = {k: data[k].astype(np.float32) for k in data.files}
    
    names = sorted(db.keys())
    print(f"\n✓ Loaded database with {len(db)} identities: {', '.join(names)}\n")
    
    # Test with two different people
    test_pairs = [
        ("Bonheur", "ashraf"),
        ("calvin", "laurent"),
        ("Bonheur", "calvin"),
    ]
    
    aligner = FaceAligner()
    embedder = ArcFaceEmbedder(config.ARCFACE_MODEL_PATH)
    
    print("Testing recognition accuracy with aligned face samples:\n")
    
    threshold = config.DEFAULT_DISTANCE_THRESHOLD
    print(f"Using threshold: {threshold}\n")
    
    for person1, person2 in test_pairs:
        print(f"\n{'='*60}")
        print(f"Test: {person1} vs {person2}")
        print(f"{'='*60}")
        
        # Get samples for person 1
        person1_dir = config.ENROLL_DIR / person1
        person1_samples = sorted(person1_dir.glob("*.jpg"))[:2]  # Take first 2 samples
        
        # Get samples for person 2
        person2_dir = config.ENROLL_DIR / person2
        person2_samples = sorted(person2_dir.glob("*.jpg"))[:2]  # Take first 2 samples
        
        if not person1_samples or not person2_samples:
            print(f"⚠ Missing samples for {person1} or {person2}")
            continue
        
        print(f"\n{person1} samples:")
        person1_recognized_count = 0
        for i, sample_path in enumerate(person1_samples, 1):
            img = cv2.imread(str(sample_path))
            if img is None or img.shape[:2] != config.EMBEDDING_INPUT_SIZE:
                print(f"  Sample {i}: ⚠ Invalid image")
                continue
            
            try:
                emb, _ = embedder.embed(img)
                
                # Recognize against database
                dists = np.array([1.0 - float(np.dot(emb.reshape(-1), db[n].reshape(-1))) 
                                for n in names])
                best_idx = int(np.argmin(dists))
                best_name = names[best_idx]
                best_dist = dists[best_idx]
                
                match = "✓ CORRECT" if best_name == person1 else "✗ WRONG"
                print(f"  Sample {i}: Recognized as '{best_name}' (dist={best_dist:.4f}) {match}")
                
                if best_name == person1:
                    person1_recognized_count += 1
                    
            except Exception as e:
                print(f"  Sample {i}: Error - {e}")
        
        print(f"\n{person2} samples:")
        person2_recognized_count = 0
        for i, sample_path in enumerate(person2_samples, 1):
            img = cv2.imread(str(sample_path))
            if img is None or img.shape[:2] != config.EMBEDDING_INPUT_SIZE:
                print(f"  Sample {i}: ⚠ Invalid image")
                continue
            
            try:
                emb, _ = embedder.embed(img)
                
                # Recognize against database
                dists = np.array([1.0 - float(np.dot(emb.reshape(-1), db[n].reshape(-1))) 
                                for n in names])
                best_idx = int(np.argmin(dists))
                best_name = names[best_idx]
                best_dist = dists[best_idx]
                
                match = "✓ CORRECT" if best_name == person2 else "✗ WRONG"
                print(f"  Sample {i}: Recognized as '{best_name}' (dist={best_dist:.4f}) {match}")
                
                if best_name == person2:
                    person2_recognized_count += 1
                    
            except Exception as e:
                print(f"  Sample {i}: Error - {e}")
        
        # Summary for this pair
        total_person1 = len(person1_samples)
        total_person2 = len(person2_samples)
        person1_acc = (person1_recognized_count / total_person1 * 100) if total_person1 > 0 else 0
        person2_acc = (person2_recognized_count / total_person2 * 100) if total_person2 > 0 else 0
        
        print(f"\nResults:")
        print(f"  {person1}: {person1_recognized_count}/{total_person1} correct ({person1_acc:.0f}%)")
        print(f"  {person2}: {person2_recognized_count}/{total_person2} correct ({person2_acc:.0f}%)")
    
    print("\n" + "="*60)
    print("✓ Test complete!")
    print("="*60)
    print("\nTo test live recognition with two people:")
    print("  1. Run: python -m src.recognize")
    print("  2. When prompted, do NOT lock to a specific person (just press Enter)")
    print("  3. Have two different people appear on camera")
    print("  4. Both should be recognized by name")
    
    return True


if __name__ == "__main__":
    success = test_two_person_recognition()
    sys.exit(0 if success else 1)
