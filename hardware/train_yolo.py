"""YOLO11 Stage 1 training entrypoint for BUSTAGO person detection."""

import argparse


def parse_args():
    parser = argparse.ArgumentParser(description="Train YOLO11 for BUSTAGO person detection")
    parser.add_argument("--epochs", type=int, default=100, help="Training epochs (default: 100)")
    parser.add_argument("--imgsz", type=int, default=960, help="Training image size (default: 960)")
    parser.add_argument("--batch", type=int, default=16, help="Training batch size (default: 16)")
    parser.add_argument("--device", default=0, help="Training device, e.g. 0, cpu, or 0,1 (default: 0)")
    parser.add_argument("--data", default="hardware/configs/bustago_person.yaml",
                        help="Dataset YAML path (default: public baseline config)")
    parser.add_argument("--model", default="yolo11n.pt",
                        help="Pretrained model file. yolo11n.pt 권장 (counter.py 배포와 일치)")
    parser.add_argument("--name", default="yolo11-person",
                        help="Run name written under runs/bustago/")
    return parser.parse_args()


def main():
    args = parse_args()

    from ultralytics import YOLO

    model = YOLO(args.model)
    model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        pretrained=True,
        cos_lr=True,
        close_mosaic=10,
        project="runs/bustago",
        name=args.name,
    )


if __name__ == "__main__":
    main()
