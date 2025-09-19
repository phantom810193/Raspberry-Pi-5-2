#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""facecam.py - 即時人臉辨識

此模組提供樹莓派、Jetson Nano 及 Windows 等平台使用的即時人臉辨識工具，
可將由 :mod:`facegen` 產生的人臉編碼載入後，透過攝影機或靜態圖片進行辨識。

功能特色
---------
* 支援 USB 攝影機、樹莓派 CSI 攝影機或 GStreamer 管線
* 內建影像縮放加速機制，適合在資源受限裝置上使用
* 可於命令列指定靜態圖片進行辨識
* 透過 CSV 檔案載入既有人臉編碼
* 可輸出辨識結果（名稱與信心度）

範例::

    # 使用預設攝影機進行即時辨識
    python facecam.py --encodings encodings.csv

    # 指定圖片檔案進行辨識
    python facecam.py --encodings encodings.csv --image ./test.jpg

    # 指定相機來源與縮放倍率
    python facecam.py --encodings encodings.csv --video-source 1 --scale 0.33
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple, Union

import cv2
import numpy as np

try:
    import face_recognition
except ImportError as exc:  # pragma: no cover - 執行環境缺套件時才觸發
    raise ImportError(
        "facecam.py 需要 face_recognition 套件，請先安裝：pip install face-recognition"
    ) from exc

LOGGER = logging.getLogger(__name__)


@dataclass
class RecognizedFace:
    """儲存單一人臉辨識結果。"""

    name: str
    location: Tuple[int, int, int, int]
    distance: float

    @property
    def confidence(self) -> float:
        """依據距離推估的信心度 (0.0~1.0)。"""

        # face_recognition 距離範圍大約 0.0 ~ 1.0，值越小表示越相似
        return float(np.clip(1.0 - self.distance, 0.0, 1.0))


class KnownFacesStore:
    """管理已知人臉編碼的輔助類別。"""

    def __init__(self, tolerance: float = 0.6) -> None:
        self.tolerance = tolerance
        self.encodings: List[np.ndarray] = []
        self.labels: List[str] = []

    # ------------------------------------------------------------------
    def load_from_csv(self, csv_path: Path) -> None:
        csv_path = csv_path.expanduser().resolve()
        if not csv_path.exists():
            raise FileNotFoundError(f"找不到編碼檔案: {csv_path}")

        with csv_path.open("r", newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                encoding = np.array(json.loads(row["encoding"]), dtype="float32")
                self.encodings.append(encoding)
                self.labels.append(row["label"])
        LOGGER.info("載入 %d 筆已知人臉資料", len(self.labels))

    # ------------------------------------------------------------------
    def recognize(self, face_encoding: np.ndarray) -> RecognizedFace:
        if not self.encodings:
            return RecognizedFace(name="Unknown", location=(0, 0, 0, 0), distance=1.0)

        distances = face_recognition.face_distance(self.encodings, face_encoding)
        best_index = int(np.argmin(distances))
        name = "Unknown"
        distance = float(distances[best_index])
        if distance <= self.tolerance:
            name = self.labels[best_index]
        return RecognizedFace(name=name, location=(0, 0, 0, 0), distance=distance)


class FaceRecognitionCamera:
    """即時人臉辨識引擎。"""

    def __init__(
        self,
        encodings_store: KnownFacesStore,
        scale: float = 0.25,
        model: str = "hog",
        frame_skip: int = 1,
    ) -> None:
        self.encodings_store = encodings_store
        self.scale = max(0.1, min(scale, 1.0))
        self.model = model
        self.frame_skip = max(1, int(frame_skip))

    # ------------------------------------------------------------------
    def recognize_frame(self, frame: np.ndarray) -> List[RecognizedFace]:
        """對單張影格執行人臉辨識。"""

        small_frame = cv2.resize(frame, (0, 0), fx=self.scale, fy=self.scale)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        face_locations = face_recognition.face_locations(rgb_small_frame, model=self.model)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

        results: List[RecognizedFace] = []
        for location, encoding in zip(face_locations, face_encodings):
            recognized = self.encodings_store.recognize(encoding)
            top, right, bottom, left = location
            scale_factor = 1.0 / self.scale
            scaled_location = (
                int(top * scale_factor),
                int(right * scale_factor),
                int(bottom * scale_factor),
                int(left * scale_factor),
            )
            results.append(
                RecognizedFace(
                    name=recognized.name,
                    location=scaled_location,
                    distance=recognized.distance,
                )
            )
        return results

    # ------------------------------------------------------------------
    def draw_annotations(self, frame: np.ndarray, results: Iterable[RecognizedFace]) -> np.ndarray:
        for result in results:
            top, right, bottom, left = result.location
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
            label = f"{result.name} ({result.confidence*100:.1f}%)"
            cv2.rectangle(frame, (left, bottom - 25), (right, bottom), (0, 0, 255), cv2.FILLED)
            cv2.putText(
                frame,
                label,
                (left + 6, bottom - 6),
                cv2.FONT_HERSHEY_DUPLEX,
                0.5,
                (255, 255, 255),
                1,
            )
        return frame

    # ------------------------------------------------------------------
    def run_camera(
        self,
        video_source: Union[int, str] = 0,
        window_name: str = "FaceCam",
        display: bool = True,
        output_path: Optional[Path] = None,
    ) -> None:
        capture = self._create_capture(video_source)
        if not capture or not capture.isOpened():
            raise RuntimeError(f"無法開啟攝影機來源: {video_source}")

        writer: Optional[cv2.VideoWriter] = None
        if output_path is not None:
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            fps = capture.get(cv2.CAP_PROP_FPS) or 15
            frame_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            writer = cv2.VideoWriter(str(output_path), fourcc, fps, (frame_width, frame_height))

        frame_index = 0
        while True:
            ret, frame = capture.read()
            if not ret:
                LOGGER.warning("攝影機回傳空影格，結束辨識")
                break

            frame_index += 1
            if frame_index % self.frame_skip != 0:
                if display:
                    cv2.imshow(window_name, frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                if writer:
                    writer.write(frame)
                continue

            results = self.recognize_frame(frame)
            annotated = self.draw_annotations(frame.copy(), results)

            for result in results:
                LOGGER.debug("偵測到 %s (confidence=%.2f)", result.name, result.confidence)

            if display:
                cv2.imshow(window_name, annotated)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            if writer:
                writer.write(annotated)

        capture.release()
        if writer:
            writer.release()
        if display:
            cv2.destroyWindow(window_name)

    # ------------------------------------------------------------------
    def recognize_image(self, image_path: Path) -> List[RecognizedFace]:
        image_path = image_path.expanduser().resolve()
        if not image_path.exists():
            raise FileNotFoundError(f"找不到圖片檔案: {image_path}")
        frame = cv2.imread(str(image_path))
        if frame is None:
            raise RuntimeError(f"無法讀取圖片: {image_path}")
        return self.recognize_frame(frame)

    # ------------------------------------------------------------------
    @staticmethod
    def _create_capture(source: Union[int, str]) -> cv2.VideoCapture:
        system = platform.system()
        if isinstance(source, str) and not source.isdigit():
            LOGGER.info("使用 GStreamer 管線: %s", source)
            return cv2.VideoCapture(source, cv2.CAP_GSTREAMER)

        try:
            index = int(source)
        except (TypeError, ValueError):
            index = 0

        if system == "Windows":
            return cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if system == "Linux":
            return cv2.VideoCapture(index, cv2.CAP_V4L2)
        return cv2.VideoCapture(index)


# ----------------------------------------------------------------------
# 命令列處理
# ----------------------------------------------------------------------

def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="即時人臉辨識工具")
    parser.add_argument("--encodings", required=True, help="facegen 產生的編碼 CSV 檔")
    parser.add_argument("--video-source", default="0", help="攝影機來源索引或 GStreamer 字串")
    parser.add_argument("--image", help="指定圖片檔案進行辨識")
    parser.add_argument("--scale", type=float, default=0.25, help="辨識前的影像縮放比例 (0~1)")
    parser.add_argument("--tolerance", type=float, default=0.6, help="辨識容忍度，值越小越嚴格")
    parser.add_argument("--model", choices=["hog", "cnn"], default="hog", help="人臉偵測模型")
    parser.add_argument("--frame-skip", type=int, default=1, help="處理時跳過的影格數，可降低運算負擔")
    parser.add_argument("--output", help="將辨識結果錄製為影片檔")
    parser.add_argument("--no-display", action="store_true", help="不顯示影像（適合遠端或無螢幕環境）")
    parser.add_argument("--log-level", default="INFO", help="記錄器等級，例如 INFO、DEBUG")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))

    store = KnownFacesStore(tolerance=args.tolerance)
    store.load_from_csv(Path(args.encodings))

    engine = FaceRecognitionCamera(
        encodings_store=store,
        scale=args.scale,
        model=args.model,
        frame_skip=args.frame_skip,
    )

    if args.image:
        results = engine.recognize_image(Path(args.image))
        if not results:
            print("未偵測到任何人臉")
        else:
            for result in results:
                print(f"{result.name}\tconfidence={result.confidence:.2f}")
        return 0

    output_path = Path(args.output) if args.output else None
    engine.run_camera(
        video_source=args.video_source,
        window_name="Face Recognition",
        display=not args.no_display,
        output_path=output_path,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - 命令列執行點
    raise SystemExit(main())
