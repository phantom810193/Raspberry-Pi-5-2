
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
人臉註冊工具 - face_register.py
用於註冊新會員的人臉資料
'''

import cv2
import face_recognition
import mysql.connector
import json
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from PIL import Image, ImageTk
import numpy as np

class FaceRegisterTool:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("人臉註冊工具")
        self.root.geometry("800x600")

        # 資料庫連接
        self.db_connection = None
        self.connect_database()

        # 攝影機
        self.camera = cv2.VideoCapture(0)

        # GUI 元件
        self.setup_gui()

        # 攝影機預覽更新
        self.update_camera()

    def connect_database(self):
        try:
            self.db_connection = mysql.connector.connect(
                host='localhost',
                user='pi',
                password='raspberry',
                database='face_ad_system'
            )
        except mysql.connector.Error as err:
            messagebox.showerror("資料庫錯誤", f"無法連接資料庫: {err}")

    def setup_gui(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 攝影機預覽
        self.camera_label = ttk.Label(main_frame, text="攝影機載入中...")
        self.camera_label.grid(row=0, column=0, columnspan=2, pady=10)

        # 會員資訊輸入
        info_frame = ttk.LabelFrame(main_frame, text="會員資訊", padding="10")
        info_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)

        ttk.Label(info_frame, text="姓名:").grid(row=0, column=0, sticky=tk.W)
        self.name_var = tk.StringVar()
        ttk.Entry(info_frame, textvariable=self.name_var, width=20).grid(row=0, column=1, padx=5)

        ttk.Label(info_frame, text="電子郵件:").grid(row=1, column=0, sticky=tk.W)
        self.email_var = tk.StringVar()
        ttk.Entry(info_frame, textvariable=self.email_var, width=20).grid(row=1, column=1, padx=5)

        ttk.Label(info_frame, text="性別:").grid(row=0, column=2, sticky=tk.W, padx=(20,0))
        self.gender_var = tk.StringVar()
        gender_combo = ttk.Combobox(info_frame, textvariable=self.gender_var, width=10)
        gender_combo['values'] = ('M', 'F')
        gender_combo.grid(row=0, column=3, padx=5)

        ttk.Label(info_frame, text="年齡層:").grid(row=1, column=2, sticky=tk.W, padx=(20,0))
        self.age_group_var = tk.StringVar()
        age_combo = ttk.Combobox(info_frame, textvariable=self.age_group_var, width=10)
        age_combo['values'] = ('18-25', '26-35', '36-45', '46-55', '56-65', '65+')
        age_combo.grid(row=1, column=3, padx=5)

        # 按鈕
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=20)

        ttk.Button(button_frame, text="拍照註冊", command=self.capture_and_register).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="清除", command=self.clear_form).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="退出", command=self.quit_app).pack(side=tk.LEFT, padx=5)

        # 狀態列
        self.status_var = tk.StringVar()
        self.status_var.set("就緒")
        ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN).grid(
            row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5
        )

    def update_camera(self):
        ret, frame = self.camera.read()
        if ret:
            # 調整影像大小
            frame = cv2.resize(frame, (640, 480))

            # 人臉偵測
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame)

            # 繪製人臉框架
            for (top, right, bottom, left) in face_locations:
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                cv2.putText(frame, "Face Detected", (left, top-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # 轉換為 PhotoImage 格式
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            photo = ImageTk.PhotoImage(image=img)

            # 更新顯示
            self.camera_label.configure(image=photo)
            self.camera_label.image = photo

        # 排程下次更新
        self.root.after(50, self.update_camera)

    def capture_and_register(self):
        # 驗證輸入
        if not self.name_var.get().strip():
            messagebox.showerror("錯誤", "請輸入會員姓名")
            return

        # 擷取當前影像
        ret, frame = self.camera.read()
        if not ret:
            messagebox.showerror("錯誤", "無法從攝影機擷取影像")
            return

        self.status_var.set("正在處理人臉資料...")
        self.root.update()

        # 人臉辨識
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_encodings = face_recognition.face_encodings(rgb_frame)

        if len(face_encodings) == 0:
            messagebox.showerror("錯誤", "未偵測到人臉，請調整位置後重試")
            self.status_var.set("就緒")
            return

        if len(face_encodings) > 1:
            messagebox.showwarning("警告", "偵測到多張人臉，將使用第一張")

        # 取得人臉編碼
        face_encoding = face_encodings[0]
        encoding_str = json.dumps(face_encoding.tolist())

        # 儲存到資料庫
        try:
            cursor = self.db_connection.cursor()
            query = '''
                INSERT INTO members (name, email, gender, age_group, face_encoding) 
                VALUES (%s, %s, %s, %s, %s)
            '''
            cursor.execute(query, (
                self.name_var.get().strip(),
                self.email_var.get().strip() if self.email_var.get().strip() else None,
                self.gender_var.get() if self.gender_var.get() else None,
                self.age_group_var.get() if self.age_group_var.get() else None,
                encoding_str
            ))
            self.db_connection.commit()
            member_id = cursor.lastrowid
            cursor.close()

            messagebox.showinfo("成功", f"會員 {self.name_var.get()} 註冊成功！\n會員ID: {member_id}")
            self.clear_form()
            self.status_var.set("註冊成功")

        except mysql.connector.Error as err:
            messagebox.showerror("資料庫錯誤", f"註冊失敗: {err}")
            self.status_var.set("註冊失敗")

    def clear_form(self):
        self.name_var.set("")
        self.email_var.set("")
        self.gender_var.set("")
        self.age_group_var.set("")
        self.status_var.set("就緒")

    def quit_app(self):
        if self.camera:
            self.camera.release()
        if self.db_connection:
            self.db_connection.close()
        self.root.quit()
        self.root.destroy()

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)
        self.root.mainloop()

if __name__ == '__main__':
    app = FaceRegisterTool()
    app.run()
