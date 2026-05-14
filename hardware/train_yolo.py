"""YOLO11 Stage 1 training entrypoint for BUSTAGO person detection."""

import argparse


def parse_args():
    parser = argparse.ArgumentParser(description="Train YOLO11 for BUSTAGO person detection")
    parser.add_argument("--epochs", type=int, default=100, help="Training epochs (default: 100)")
    parser.add_argument("--imgsz", type=int, default=960, help="Training image size (default: 960)")
    parser.add_argument("--batch", type=int, default=16, help="Training batch size (default: 16)")
    parser.add_argument("--device", default=0, help="Training device, e.g. 0, cpu, or 0,1 (default: 0)")
    return parser.parse_args()


def main():
    args = parse_args()

    from ultralytics import YOLO

    model = YOLO("yolo11s.pt")
    model.train(
        data="hardware/configs/bustago_person.yaml",
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        pretrained=True,
        cos_lr=True,
        close_mosaic=10,
        project="runs/bustago",
        name="yolo11-person",
    )


if __name__ == "__main__":
    main()
