#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""facegen.py - 人臉編碼生成器

此模組負責將靜態人臉圖片轉換為可儲存的人臉特徵向量，
支援單一圖片或整個資料夾的批次處理，並可匯出為 CSV 檔案。

範例使用方式::

    # 由單一圖片產生人臉編碼
    python facegen.py --input ./images/alice.jpg --label Alice --output encodings.csv

    # 批次處理整個資料夾，並根據資料夾名稱當作標籤
    python facegen.py --input ./dataset --recursive --output encodings.csv

本模組也可於其他程式中匯入使用::

    from facegen import FaceEncodingGenerator

    generator = FaceEncodingGenerator(model="hog")
    records = generator.process_directory("./dataset")
    generator.save_to_csv(records, "encodings.csv")
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Sequence

try:
    import face_recognition
except ImportError as exc:  # pragma: no cover - 環境未安裝套件時才會執行
    raise ImportError(
        "facegen.py 需要 face_recognition 套件，請先安裝：pip install face-recognition"
    ) from exc

LOGGER = logging.getLogger(__name__)
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


@dataclass
class FaceEncodingRecord:
    """代表一筆人臉編碼資料。"""

    label: str
    file_path: str
    encoding: Sequence[float]

    def to_csv_row(self) -> List[str]:
        """轉換為可寫入 CSV 的列資料。"""

        return [self.label, self.file_path, json.dumps(list(self.encoding))]


class FaceEncodingGenerator:
    """將影像資料轉換為人臉特徵向量的工具類別。"""

    def __init__(
        self,
        model: str = "hog",
        upsample_times: int = 1,
        num_jitters: int = 1,
        allow_multiple_faces: bool = False,
    ) -> None:
        """初始化編碼器。

        Args:
            model: face_recognition 使用的偵測模型，`"hog"` 或 `"cnn"`。
            upsample_times: 偵測人臉時影像上採樣次數。
            num_jitters: 人臉編碼抖動次數，可提升精準度但增加運算量。
            allow_multiple_faces: 是否在單張圖片上儲存多張人臉編碼。
        """

        self.model = model
        self.upsample_times = max(0, int(upsample_times))
        self.num_jitters = max(1, int(num_jitters))
        self.allow_multiple_faces = allow_multiple_faces

    # ------------------------------------------------------------------
    # 影像處理邏輯
    # ------------------------------------------------------------------
    def process_image(self, image_path: Path, label: Optional[str] = None) -> List[FaceEncodingRecord]:
        """處理單一影像並回傳人臉編碼紀錄列表。"""

        image_path = image_path.expanduser().resolve()
        LOGGER.debug("Processing image: %s", image_path)

        if not image_path.exists():
            raise FileNotFoundError(f"影像檔案不存在: {image_path}")

        image = face_recognition.load_image_file(str(image_path))
        face_locations = face_recognition.face_locations(
            image,
            number_of_times_to_upsample=self.upsample_times,
            model=self.model,
        )

        if not face_locations:
            LOGGER.warning("未在圖片 %s 偵測到人臉", image_path)
            return []

        encodings = face_recognition.face_encodings(
            image,
            known_face_locations=face_locations,
            num_jitters=self.num_jitters,
        )

        records: List[FaceEncodingRecord] = []
        for index, encoding in enumerate(encodings):
            if not self.allow_multiple_faces and index > 0:
                LOGGER.info("圖片 %s 偵測到多張人臉，只保留第一張", image_path)
                break

            encoding_label = label or self._infer_label(image_path, index)
            records.append(
                FaceEncodingRecord(
                    label=encoding_label,
                    file_path=str(image_path),
                    encoding=encoding.tolist(),
                )
            )

        LOGGER.info("圖片 %s 產生 %d 筆編碼", image_path, len(records))
        return records

    def process_directory(
        self,
        directory: Path,
        recursive: bool = True,
        label_from_parent: bool = True,
    ) -> Iterator[FaceEncodingRecord]:
        """批次處理整個資料夾並回傳紀錄產生器。"""

        directory = directory.expanduser().resolve()
        if not directory.exists():
            raise FileNotFoundError(f"資料夾不存在: {directory}")

        pattern = "**/*" if recursive else "*"
        for path in sorted(directory.glob(pattern)):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue

            label = path.parent.name if label_from_parent else path.stem
            for record in self.process_image(path, label=label):
                yield record

    def generate_from_path(
        self,
        input_path: Path,
        recursive: bool = True,
        label: Optional[str] = None,
    ) -> List[FaceEncodingRecord]:
        """根據輸入路徑（檔案或資料夾）產生人臉編碼紀錄。"""

        input_path = input_path.expanduser()
        if input_path.is_file():
            return self.process_image(input_path, label=label)
        if input_path.is_dir():
            return list(self.process_directory(input_path, recursive=recursive))
        raise FileNotFoundError(f"找不到指定的輸入路徑: {input_path}")

    # ------------------------------------------------------------------
    # 輸出與資料儲存
    # ------------------------------------------------------------------
    @staticmethod
    def save_to_csv(
        records: Iterable[FaceEncodingRecord],
        output_path: Path,
        append: bool = False,
    ) -> int:
        """將編碼結果儲存為 CSV 檔案。

        Args:
            records: 可迭代的 :class:`FaceEncodingRecord` 物件。
            output_path: 輸出檔案路徑。
            append: 若為 ``True`` 則採附加模式，否則覆寫檔案。

        Returns:
            寫入的紀錄數量。
        """

        output_path = output_path.expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        mode = "a" if append and output_path.exists() else "w"
        count = 0
        with output_path.open(mode, newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            if mode == "w":
                writer.writerow(["label", "file_path", "encoding"])

            for record in records:
                writer.writerow(record.to_csv_row())
                count += 1

        LOGGER.info("已將 %d 筆資料寫入 %s", count, output_path)
        return count

    @staticmethod
    def load_from_csv(csv_path: Path) -> List[FaceEncodingRecord]:
        """從既有的 CSV 檔案載入人臉編碼資料。"""

        csv_path = csv_path.expanduser().resolve()
        if not csv_path.exists():
            raise FileNotFoundError(f"找不到 CSV 檔案: {csv_path}")

        records: List[FaceEncodingRecord] = []
        with csv_path.open("r", newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                encoding = json.loads(row["encoding"])
                records.append(
                    FaceEncodingRecord(
                        label=row["label"],
                        file_path=row["file_path"],
                        encoding=encoding,
                    )
                )
        LOGGER.debug("從 %s 載入 %d 筆資料", csv_path, len(records))
        return records

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------
    @staticmethod
    def _infer_label(image_path: Path, index: int) -> str:
        """依據檔名推論標籤。"""

        if index == 0:
            return image_path.stem
        return f"{image_path.stem}_{index}"


# ----------------------------------------------------------------------
# 命令列介面
# ----------------------------------------------------------------------

def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="人臉編碼生成工具")
    parser.add_argument("--input", required=True, help="圖片檔案或資料夾路徑")
    parser.add_argument("--output", default="encodings.csv", help="輸出 CSV 檔案路徑")
    parser.add_argument("--label", help="單張圖片的標籤名稱")
    parser.add_argument("--model", default="hog", choices=["hog", "cnn"], help="人臉偵測模型")
    parser.add_argument("--upsample", type=int, default=1, help="偵測人臉時的上採樣次數")
    parser.add_argument("--jitters", type=int, default=1, help="產生人臉編碼時的抖動次數")
    parser.add_argument("--allow-multi", action="store_true", help="允許單張圖片儲存多張人臉")
    parser.add_argument("--recursive", action="store_true", help="遞迴處理子資料夾")
    parser.add_argument("--append", action="store_true", help="以附加模式寫入 CSV")
    parser.add_argument("--log-level", default="INFO", help="記錄器等級，例如 INFO 或 DEBUG")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))

    generator = FaceEncodingGenerator(
        model=args.model,
        upsample_times=args.upsample,
        num_jitters=args.jitters,
        allow_multiple_faces=args.allow_multi,
    )

    input_path = Path(args.input)
    records = generator.generate_from_path(input_path, recursive=args.recursive, label=args.label)

    if not records:
        LOGGER.warning("沒有產生任何人臉編碼，請確認輸入資料")
        return 1

    output_path = Path(args.output)
    FaceEncodingGenerator.save_to_csv(records, output_path, append=args.append)
    return 0


if __name__ == "__main__":  # pragma: no cover - 命令列執行點
    raise SystemExit(main())
