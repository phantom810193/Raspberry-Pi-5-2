#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rollcall_edge.py - 邊緣運算點名系統

結合人臉辨識、MQTT 與圖形化介面，適用於樹莓派等邊緣裝置，
可即時辨識進出人員並同步資料至資料庫與雲端平台。
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import cv2
import face_recognition
import numpy as np
from PIL import Image, ImageTk

try:  # MQTT 為選用元件
    import paho.mqtt.client as mqtt
except Exception:  # pragma: no cover - 測試環境無法驗證
    mqtt = None  # type: ignore[assignment]

try:
    import mysql.connector
except Exception:  # pragma: no cover - 測試環境無法驗證
    mysql = None  # type: ignore[assignment]
else:  # pragma: no cover
    mysql = mysql.connector

import tkinter as tk
from tkinter import ttk, messagebox

from facegen import FaceEncodingGenerator

LOGGER = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path("config.json")
ENCODINGS_CSV = Path("encodings.csv")


@dataclass
class RecognizedFace:
    name: str
    location: Tuple[int, int, int, int]
    distance: float

    @property
    def confidence(self) -> float:
        return float(np.clip(1.0 - self.distance, 0.0, 1.0))


@dataclass
class AttendanceRecord:
    name: str
    confidence: float
    timestamp: datetime
    member_id: Optional[int] = None
    status: str = "present"

    def to_payload(self) -> dict:
        return {
            "name": self.name,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "member_id": self.member_id,
            "status": self.status,
        }


class FaceRecognitionEngine:
    """封裝人臉辨識流程，提供辨識與繪製標註功能。"""

    def __init__(self, csv_path: Path, tolerance: float, model: str, scale: float) -> None:
        self.csv_path = csv_path
        self.tolerance = tolerance
        self.model = model
        self.scale = max(0.1, min(scale, 1.0))
        self.known_encodings: List[np.ndarray] = []
        self.known_labels: List[str] = []
        self._load_encodings()

    def _load_encodings(self) -> None:
        self.known_encodings.clear()
        self.known_labels.clear()
        if not self.csv_path.exists():
            LOGGER.warning("找不到編碼檔 %s，請先使用 facegen.py 產生", self.csv_path)
            return
        records = FaceEncodingGenerator.load_from_csv(self.csv_path)
        for record in records:
            self.known_encodings.append(np.array(record.encoding, dtype="float32"))
            self.known_labels.append(record.label)
        LOGGER.info("載入 %d 筆已知人臉資料", len(self.known_labels))

    def recognize(self, frame: np.ndarray) -> List[RecognizedFace]:
        small_frame = cv2.resize(frame, (0, 0), fx=self.scale, fy=self.scale)
        rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(rgb_small, model=self.model)
        encodings = face_recognition.face_encodings(rgb_small, locations)
        results: List[RecognizedFace] = []
        for (top, right, bottom, left), encoding in zip(locations, encodings):
            if not self.known_encodings:
                name = "Unknown"
                distance = 1.0
            else:
                distances = face_recognition.face_distance(self.known_encodings, encoding)
                best_index = int(np.argmin(distances))
                distance = float(distances[best_index])
                name = self.known_labels[best_index] if distance <= self.tolerance else "Unknown"
            scale_factor = 1.0 / self.scale
            results.append(
                RecognizedFace(
                    name=name,
                    distance=distance,
                    location=(
                        int(top * scale_factor),
                        int(right * scale_factor),
                        int(bottom * scale_factor),
                        int(left * scale_factor),
                    ),
                )
            )
        return results

    @staticmethod
    def draw(frame: np.ndarray, results: Iterable[RecognizedFace]) -> np.ndarray:
        annotated = frame.copy()
        for result in results:
            top, right, bottom, left = result.location
            cv2.rectangle(annotated, (left, top), (right, bottom), (0, 128, 255), 2)
            label = f"{result.name} ({result.confidence*100:.1f}%)"
            cv2.rectangle(annotated, (left, bottom - 25), (right, bottom), (0, 128, 255), cv2.FILLED)
            cv2.putText(
                annotated,
                label,
                (left + 6, bottom - 8),
                cv2.FONT_HERSHEY_DUPLEX,
                0.5,
                (255, 255, 255),
                1,
            )
        return annotated


class DatabaseManager:
    """管理資料庫連線與考勤紀錄寫入。"""

    def __init__(self, config: dict) -> None:
        self.config = config
        self.connection: Optional[mysql.connection.MySQLConnection] = None  # type: ignore[attr-defined]
        self.member_lookup: Dict[str, int] = {}
        self.device_id = config.get("device", {}).get("id", "edge-node")

    def connect(self) -> None:
        if mysql is None:
            LOGGER.warning("未安裝 mysql-connector-python，資料僅儲存在記憶體")
            return
        db_config = self.config.get("database")
        if not db_config:
            LOGGER.info("未設定資料庫連線，跳過")
            return
        try:
            self.connection = mysql.connect(**db_config)
            self._ensure_tables()
            self.refresh_member_lookup()
            LOGGER.info("資料庫連線成功")
        except Exception as exc:  # pragma: no cover - 實際連線錯誤難以模擬
            LOGGER.error("資料庫連線失敗: %s", exc)
            self.connection = None

    def close(self) -> None:
        if self.connection:
            self.connection.close()
            self.connection = None

    def _ensure_tables(self) -> None:
        if not self.connection:
            return
        cursor = self.connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS attendance_log (
                log_id INT PRIMARY KEY AUTO_INCREMENT,
                member_id INT NULL,
                name VARCHAR(100) NOT NULL,
                confidence FLOAT,
                status VARCHAR(20) DEFAULT 'present',
                device_id VARCHAR(100),
                captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE SET NULL
            )
            """
        )
        self.connection.commit()
        cursor.close()

    def refresh_member_lookup(self) -> None:
        if not self.connection:
            return
        cursor = self.connection.cursor()
        cursor.execute("SELECT member_id, name FROM members WHERE is_active = TRUE")
        self.member_lookup = {name: member_id for member_id, name in cursor.fetchall()}
        cursor.close()

    def resolve_member_id(self, name: str) -> Optional[int]:
        return self.member_lookup.get(name)

    def log_attendance(self, record: AttendanceRecord) -> None:
        if not self.connection:
            return
        cursor = self.connection.cursor()
        query = (
            "INSERT INTO attendance_log (member_id, name, confidence, status, device_id) "
            "VALUES (%s, %s, %s, %s, %s)"
        )
        cursor.execute(
            query,
            (
                record.member_id,
                record.name,
                record.confidence,
                record.status,
                self.device_id,
            ),
        )
        self.connection.commit()
        cursor.close()


class MQTTClient:
    """管理 MQTT 發佈的輔助類別。"""

    def __init__(self, config: dict) -> None:
        self.config = config
        self.client: Optional[mqtt.Client] = None  # type: ignore[type-arg]
        self.topic = config.get("mqtt", {}).get("topic", "face_ad_system/attendance")

    def connect(self) -> None:
        if mqtt is None:
            LOGGER.warning("未安裝 paho-mqtt，將停用 MQTT 功能")
            return
        mqtt_config = self.config.get("mqtt")
        if not mqtt_config:
            LOGGER.info("未設定 MQTT 參數，跳過")
            return
        self.client = mqtt.Client()
        if username := mqtt_config.get("username"):
            self.client.username_pw_set(username, mqtt_config.get("password"))
        try:
            self.client.connect(mqtt_config.get("host", "localhost"), mqtt_config.get("port", 1883))
            self.client.loop_start()
            LOGGER.info("MQTT 連線成功：%s", mqtt_config.get("host"))
        except Exception as exc:  # pragma: no cover
            LOGGER.error("MQTT 連線失敗: %s", exc)
            self.client = None

    def publish_attendance(self, record: AttendanceRecord) -> None:
        if not self.client:
            return
        payload = json.dumps(record.to_payload())
        try:
            self.client.publish(self.topic, payload, qos=1)
        except Exception as exc:  # pragma: no cover
            LOGGER.error("MQTT 發佈失敗: %s", exc)

    def close(self) -> None:
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.client = None


class RollCallEdgeApp:
    """結合 GUI 與人臉辨識的點名系統。"""

    def __init__(
        self,
        config_path: Path = DEFAULT_CONFIG_PATH,
        encodings_csv: Path = ENCODINGS_CSV,
        tolerance: float = 0.6,
        model: str = "hog",
        scale: float = 0.25,
        frame_skip: int = 2,
        cooldown: int = 30,
    ) -> None:
        logging.basicConfig(level=logging.INFO)
        self.config = self._load_config(config_path)

        self.db_manager = DatabaseManager(self.config)
        self.db_manager.connect()
        self.mqtt_client = MQTTClient(self.config)
        self.mqtt_client.connect()

        self.engine = FaceRecognitionEngine(encodings_csv, tolerance, model, scale)
        self.frame_skip = max(1, frame_skip)
        self.cooldown = timedelta(seconds=max(1, cooldown))
        self.last_seen: Dict[str, datetime] = {}
        self.recognized_count = 0
        self.unknown_count = 0

        self.camera = self._open_camera()
        self.frame_index = 0

        self.root = tk.Tk()
        self.root.title("智慧點名系統")
        self.root.geometry("1200x720")

        self._build_gui()
        self._update_loop()

    # ------------------------------------------------------------------
    def _load_config(self, path: Path) -> dict:
        if not path.exists():
            LOGGER.warning("找不到設定檔 %s，將使用預設值", path)
            return {}
        with path.open("r", encoding="utf-8") as fp:
            return json.load(fp)

    # ------------------------------------------------------------------
    def _open_camera(self) -> cv2.VideoCapture:
        camera_config = self.config.get("camera", {})
        capture = cv2.VideoCapture(camera_config.get("index", 0))
        if capture.isOpened():
            if width := camera_config.get("width"):
                capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            if height := camera_config.get("height"):
                capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            if fps := camera_config.get("fps"):
                capture.set(cv2.CAP_PROP_FPS, fps)
        else:
            messagebox.showerror("攝影機錯誤", "無法開啟攝影機，請確認裝置連線")
        return capture

    # ------------------------------------------------------------------
    def _build_gui(self) -> None:
        self.root.columnconfigure(0, weight=3)
        self.root.columnconfigure(1, weight=2)
        self.root.rowconfigure(0, weight=1)

        preview_frame = ttk.LabelFrame(self.root, text="即時畫面", padding=10)
        preview_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.video_label = ttk.Label(preview_frame)
        self.video_label.pack(fill="both", expand=True)

        side_frame = ttk.Frame(self.root, padding=10)
        side_frame.grid(row=0, column=1, sticky="nsew")
        side_frame.columnconfigure(0, weight=1)
        side_frame.rowconfigure(1, weight=1)

        status_frame = ttk.LabelFrame(side_frame, text="狀態", padding=10)
        status_frame.grid(row=0, column=0, sticky="ew")
        self.status_var = tk.StringVar()
        self._update_status()
        ttk.Label(status_frame, textvariable=self.status_var, anchor="w").pack(fill="x")

        log_frame = ttk.LabelFrame(side_frame, text="點名記錄", padding=10)
        log_frame.grid(row=1, column=0, sticky="nsew", pady=10)
        columns = ("time", "name", "confidence", "status")
        self.tree = ttk.Treeview(log_frame, columns=columns, show="headings", height=15)
        for col, label in zip(columns, ("時間", "姓名", "信心度", "狀態")):
            self.tree.heading(col, text=label)
            self.tree.column(col, width=120, anchor="center")
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill="both", expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        stats_frame = ttk.Frame(side_frame)
        stats_frame.grid(row=2, column=0, sticky="ew")
        self.stats_var = tk.StringVar()
        self._update_stats()
        ttk.Label(stats_frame, textvariable=self.stats_var, anchor="w").pack(fill="x")

        control_frame = ttk.Frame(side_frame)
        control_frame.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        ttk.Button(control_frame, text="重新載入資料", command=self._reload_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="退出", command=self.quit).pack(side=tk.LEFT, padx=5)

    # ------------------------------------------------------------------
    def _update_status(self) -> None:
        db_status = "已連線" if self.db_manager.connection else "離線"
        mqtt_status = "已連線" if self.mqtt_client.client else "離線"
        self.status_var.set(f"資料庫: {db_status} | MQTT: {mqtt_status}")

    # ------------------------------------------------------------------
    def _update_stats(self) -> None:
        self.stats_var.set(f"已點名: {self.recognized_count} 人 | 未知: {self.unknown_count}")

    # ------------------------------------------------------------------
    def _reload_data(self) -> None:
        self.db_manager.refresh_member_lookup()
        self.engine._load_encodings()
        self._update_status()
        messagebox.showinfo("已重新載入", "已更新會員資料與人臉編碼")

    # ------------------------------------------------------------------
    def _update_loop(self) -> None:
        if self.camera and self.camera.isOpened():
            ret, frame = self.camera.read()
            if ret:
                self.frame_index += 1
                if self.frame_index % self.frame_skip == 0:
                    results = self.engine.recognize(frame)
                    self._handle_recognition(results)
                    annotated = FaceRecognitionEngine.draw(frame, results)
                else:
                    annotated = frame
                image = Image.fromarray(cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB))
                photo = ImageTk.PhotoImage(image=image)
                self.video_label.configure(image=photo)
                self.video_label.image = photo
        self.root.after(30, self._update_loop)

    # ------------------------------------------------------------------
    def _handle_recognition(self, results: Iterable[RecognizedFace]) -> None:
        now = datetime.now()
        for result in results:
            if result.name == "Unknown":
                self.unknown_count += 1
                continue
            last_seen = self.last_seen.get(result.name)
            if last_seen and now - last_seen < self.cooldown:
                continue
            member_id = self.db_manager.resolve_member_id(result.name)
            record = AttendanceRecord(
                name=result.name,
                confidence=result.confidence,
                timestamp=now,
                member_id=member_id,
            )
            self.last_seen[result.name] = now
            self.recognized_count += 1
            self._append_record(record)
            self.db_manager.log_attendance(record)
            self.mqtt_client.publish_attendance(record)
        self._update_stats()

    # ------------------------------------------------------------------
    def _append_record(self, record: AttendanceRecord) -> None:
        self.tree.insert(
            "",
            0,
            values=(
                record.timestamp.strftime("%H:%M:%S"),
                record.name,
                f"{record.confidence*100:.1f}%",
                record.status,
            ),
        )

    # ------------------------------------------------------------------
    def quit(self) -> None:
        if self.camera and self.camera.isOpened():
            self.camera.release()
        self.db_manager.close()
        self.mqtt_client.close()
        self.root.destroy()

    # ------------------------------------------------------------------
    def run(self) -> None:
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        self.root.mainloop()


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="邊緣點名系統")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="系統設定檔")
    parser.add_argument("--encodings", default=str(ENCODINGS_CSV), help="人臉編碼 CSV")
    parser.add_argument("--tolerance", type=float, default=0.6, help="人臉辨識容忍度")
    parser.add_argument("--model", choices=["hog", "cnn"], default="hog", help="人臉偵測模型")
    parser.add_argument("--scale", type=float, default=0.25, help="影像縮放比例")
    parser.add_argument("--frame-skip", type=int, default=2, help="辨識時跳過的影格數")
    parser.add_argument("--cooldown", type=int, default=30, help="同一人員再次點名的冷卻時間（秒）")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO)

    app = RollCallEdgeApp(
        config_path=Path(args.config),
        encodings_csv=Path(args.encodings),
        tolerance=args.tolerance,
        model=args.model,
        scale=args.scale,
        frame_skip=args.frame_skip,
        cooldown=args.cooldown,
    )
    app.run()
    return 0


if __name__ == "__main__":  # pragma: no cover - GUI 入口點
    raise SystemExit(main())
