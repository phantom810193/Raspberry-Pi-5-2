#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""faceme.py - 人臉註冊介面

提供友善的圖形化介面，協助管理員使用攝影機即時預覽並將人臉資料
儲存至資料庫與本地資料集。此程式可與 :mod:`facegen`、:mod:`facecam`
及 :mod:`rollcall_edge` 等模組共同使用。

功能重點
--------
* 即時攝影機預覽，於畫面中顯示偵測到的人臉框
* 支援輸入會員姓名、性別、年齡層等資訊
* 自動將擷取的圖片與人臉編碼儲存至本地資料集 (CSV + 影像檔)
* 可選擇性地寫入 MySQL 資料庫 (若環境支援)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
import face_recognition
from PIL import Image, ImageTk

try:  # MySQL 為選用元件
    import mysql.connector
except Exception:  # pragma: no cover - 於無 MySQL 套件時觸發
    mysql = None  # type: ignore[assignment]
else:  # pragma: no cover - 測試環境無法驗證
    mysql = mysql.connector

import tkinter as tk
from tkinter import ttk, messagebox

from facegen import FaceEncodingGenerator, FaceEncodingRecord

LOGGER = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path("config.json")
DATASET_DIR = Path("dataset")
ENCODINGS_CSV = Path("encodings.csv")


@dataclass
class MemberInfo:
    name: str
    gender: Optional[str]
    age_group: Optional[str]
    email: Optional[str]


class DatabaseManager:
    """簡易的 MySQL 操作封裝。"""

    def __init__(self, config_path: Path = DEFAULT_CONFIG_PATH) -> None:
        self.config_path = config_path
        self.connection: Optional[mysql.connection.MySQLConnection] = None  # type: ignore[attr-defined]
        self.config = self._load_config()

    def _load_config(self) -> dict:
        if not self.config_path.exists():
            LOGGER.warning("找不到設定檔 %s，將僅使用本地模式", self.config_path)
            return {}
        with self.config_path.open("r", encoding="utf-8") as fp:
            return json.load(fp)

    def connect(self) -> None:
        if mysql is None:
            LOGGER.warning("環境未安裝 mysql-connector-python，僅儲存至本地資料集")
            return
        if not self.config:
            return
        try:
            self.connection = mysql.connect(**self.config.get("database", {}))
        except Exception as exc:  # pragma: no cover - 資料庫連線錯誤較難模擬
            LOGGER.error("資料庫連線失敗: %s", exc)
            messagebox.showwarning("資料庫連線失敗", str(exc))
            self.connection = None

    def close(self) -> None:
        if self.connection:
            self.connection.close()
            self.connection = None

    def insert_member(self, member: MemberInfo, encoding: FaceEncodingRecord) -> Optional[int]:
        if not self.connection:
            return None
        cursor = self.connection.cursor()
        query = (
            "INSERT INTO members (name, gender, age_group, email, face_encoding) "
            "VALUES (%s, %s, %s, %s, %s)"
        )
        encoding_json = encoding.to_csv_row()[2]
        cursor.execute(
            query,
            (
                member.name,
                member.gender,
                member.age_group,
                member.email,
                encoding_json,
            ),
        )
        self.connection.commit()
        member_id = cursor.lastrowid
        cursor.close()
        return int(member_id)


class FaceDatasetManager:
    """負責管理本地影像資料與人臉編碼檔案。"""

    def __init__(self, dataset_dir: Path = DATASET_DIR, csv_path: Path = ENCODINGS_CSV) -> None:
        self.dataset_dir = dataset_dir
        self.csv_path = csv_path
        self.dataset_dir.mkdir(parents=True, exist_ok=True)

    def save_face_image(self, label: str, frame: cv2.Mat) -> Path:
        person_dir = self.dataset_dir / label
        person_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = person_dir / f"{timestamp}.jpg"
        cv2.imwrite(str(filename), frame)
        return filename

    def append_encoding(self, record: FaceEncodingRecord) -> None:
        FaceEncodingGenerator.save_to_csv([record], self.csv_path, append=True)

    def existing_labels(self) -> list[str]:
        if not self.csv_path.exists():
            return []
        records = FaceEncodingGenerator.load_from_csv(self.csv_path)
        return sorted({rec.label for rec in records})


class FaceRegistrationApp:
    """Tkinter 人臉註冊應用程式。"""

    def __init__(
        self,
        config_path: Path = DEFAULT_CONFIG_PATH,
        dataset_dir: Path = DATASET_DIR,
        csv_path: Path = ENCODINGS_CSV,
    ) -> None:
        logging.basicConfig(level=logging.INFO)
        self.root = tk.Tk()
        self.root.title("人臉註冊系統")
        self.root.geometry("960x640")

        self.db_manager = DatabaseManager(config_path)
        self.db_manager.connect()
        self.dataset_manager = FaceDatasetManager(dataset_dir, csv_path)

        self.camera = self._open_camera()
        self.current_frame: Optional[cv2.Mat] = None

        self._build_gui()
        self._update_camera_frame()

    # ------------------------------------------------------------------
    def _open_camera(self) -> cv2.VideoCapture:
        config = self.db_manager.config.get("camera", {}) if self.db_manager else {}
        capture = cv2.VideoCapture(0)
        if capture.isOpened():
            if width := config.get("width"):
                capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            if height := config.get("height"):
                capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        else:
            messagebox.showerror("攝影機錯誤", "無法開啟攝影機，請確認連線")
        return capture

    # ------------------------------------------------------------------
    def _build_gui(self) -> None:
        self.root.columnconfigure(0, weight=3)
        self.root.columnconfigure(1, weight=2)
        self.root.rowconfigure(0, weight=1)

        # 攝影機預覽
        preview_frame = ttk.LabelFrame(self.root, text="攝影機預覽", padding=10)
        preview_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self.video_label = ttk.Label(preview_frame, text="等待攝影機...", anchor="center")
        self.video_label.pack(fill="both", expand=True)

        # 控制面板
        control_frame = ttk.LabelFrame(self.root, text="會員資訊", padding=10)
        control_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        control_frame.columnconfigure(1, weight=1)

        ttk.Label(control_frame, text="姓名").grid(row=0, column=0, sticky="w")
        self.name_var = tk.StringVar()
        ttk.Entry(control_frame, textvariable=self.name_var).grid(row=0, column=1, sticky="ew")

        ttk.Label(control_frame, text="性別").grid(row=1, column=0, sticky="w", pady=5)
        self.gender_var = tk.StringVar()
        gender_combo = ttk.Combobox(control_frame, textvariable=self.gender_var, state="readonly")
        gender_combo["values"] = ("", "M", "F")
        gender_combo.grid(row=1, column=1, sticky="ew")

        ttk.Label(control_frame, text="年齡層").grid(row=2, column=0, sticky="w")
        self.age_var = tk.StringVar()
        age_combo = ttk.Combobox(control_frame, textvariable=self.age_var, state="readonly")
        age_combo["values"] = ("", "18-25", "26-35", "36-45", "46-55", "56-65", "65+")
        age_combo.grid(row=2, column=1, sticky="ew")

        ttk.Label(control_frame, text="電子郵件").grid(row=3, column=0, sticky="w")
        self.email_var = tk.StringVar()
        ttk.Entry(control_frame, textvariable=self.email_var).grid(row=3, column=1, sticky="ew")

        ttk.Label(control_frame, text="既有標籤").grid(row=4, column=0, sticky="nw", pady=(20, 5))
        self.label_list = tk.Listbox(control_frame, height=6)
        self.label_list.grid(row=4, column=1, sticky="nsew")
        self._refresh_label_list()

        button_frame = ttk.Frame(control_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=20)

        ttk.Button(button_frame, text="擷取並儲存", command=self.capture_member).pack(side="left", padx=5)
        ttk.Button(button_frame, text="清除", command=self._clear_form).pack(side="left", padx=5)
        ttk.Button(button_frame, text="退出", command=self.quit).pack(side="left", padx=5)

        self.status_var = tk.StringVar(value="就緒")
        status_label = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor="w")
        status_label.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))

    # ------------------------------------------------------------------
    def _refresh_label_list(self) -> None:
        self.label_list.delete(0, tk.END)
        for label in self.dataset_manager.existing_labels():
            self.label_list.insert(tk.END, label)

    # ------------------------------------------------------------------
    def _clear_form(self) -> None:
        self.name_var.set("")
        self.gender_var.set("")
        self.age_var.set("")
        self.email_var.set("")
        self.status_var.set("就緒")

    # ------------------------------------------------------------------
    def _update_camera_frame(self) -> None:
        if self.camera and self.camera.isOpened():
            ret, frame = self.camera.read()
            if ret:
                self.current_frame = frame
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                face_locations = face_recognition.face_locations(rgb_frame)
                display_frame = frame.copy()
                for top, right, bottom, left in face_locations:
                    cv2.rectangle(display_frame, (left, top), (right, bottom), (0, 255, 0), 2)
                image = Image.fromarray(cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB))
                photo = ImageTk.PhotoImage(image=image)
                self.video_label.configure(image=photo)
                self.video_label.image = photo
        self.root.after(40, self._update_camera_frame)

    # ------------------------------------------------------------------
    def capture_member(self) -> None:
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("錯誤", "請輸入會員姓名")
            return
        if self.current_frame is None:
            messagebox.showerror("錯誤", "尚未取得攝影機影像")
            return

        self.status_var.set("處理中...")
        self.root.update_idletasks()

        rgb_frame = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        if not face_locations:
            messagebox.showerror("錯誤", "未偵測到人臉，請重新調整位置")
            self.status_var.set("未偵測到人臉")
            return
        if len(face_locations) > 1:
            messagebox.showwarning("警告", "偵測到多張人臉，僅使用最清晰的一張")

        face_encodings = face_recognition.face_encodings(rgb_frame, known_face_locations=face_locations)
        encoding_vector = face_encodings[0]

        image_path = self.dataset_manager.save_face_image(name, self.current_frame)
        record = FaceEncodingRecord(label=name, file_path=str(image_path), encoding=encoding_vector.tolist())
        self.dataset_manager.append_encoding(record)

        member = MemberInfo(
            name=name,
            gender=self.gender_var.get() or None,
            age_group=self.age_var.get() or None,
            email=self.email_var.get() or None,
        )

        member_id = self.db_manager.insert_member(member, record) if self.db_manager else None

        if member_id is not None:
            message = f"會員 {name} 註冊成功！ID: {member_id}"
        else:
            message = f"會員 {name} 已儲存（本地模式）"
        self.status_var.set(message)
        messagebox.showinfo("成功", message)
        self._refresh_label_list()
        self._clear_form()

    # ------------------------------------------------------------------
    def quit(self) -> None:
        if self.camera and self.camera.isOpened():
            self.camera.release()
        self.db_manager.close()
        self.root.destroy()

    # ------------------------------------------------------------------
    def run(self) -> None:
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        self.root.mainloop()


def main() -> None:
    app = FaceRegistrationApp()
    app.run()


if __name__ == "__main__":  # pragma: no cover - GUI 入口點
    main()
