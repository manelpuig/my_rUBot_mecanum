from pathlib import Path

from ultralytics import YOLO


SCRIPT_DIR = Path(__file__).resolve().parent
MODEL_PATH = SCRIPT_DIR / "yolo11n.pt"
DATASET_YAML = SCRIPT_DIR / "TrainingRoboFlow" / "data.yaml"
OUTPUT_DIR = SCRIPT_DIR / "runs" / "detect"


def main():
    if not DATASET_YAML.is_file():
        raise SystemExit(f"Error: detection dataset configuration not found: {DATASET_YAML}")

    print(f"Loading model: {MODEL_PATH}")
    model = YOLO(str(MODEL_PATH))

    print(f"Starting detection training with: {DATASET_YAML}")
    model.train(
        data=str(DATASET_YAML),
        epochs=50,
        imgsz=640,
        batch=8,
        device="cpu",
        workers=0,
        project=str(OUTPUT_DIR),
        name="train",
        exist_ok=True,
        plots=True,
        save=True,
        verbose=True,
    )

    best_model = OUTPUT_DIR / "train" / "weights" / "best.pt"
    print("Training finished.")
    print(f"Best model: {best_model}")


if __name__ == "__main__":
    main()
