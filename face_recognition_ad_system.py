
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
樹莓派人臉辨識客製化廣告系統
主程式 - main.py
'''

import cv2
import face_recognition
import numpy as np
import mysql.connector
from datetime import datetime
import json
import math
import os
import pickle
import shlex
import time
from pathlib import Path
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk

class FaceRecognitionAdSystem:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_names = []
        self.member_data = {}
        self.camera = None
        self.db_connection = None
        self.env_file_path = None
        self.env_settings = {}

        # 載入設定
        self.load_config()

        # 連接資料庫
        self.connect_database()

        # 載入已知人臉資料
        self.load_face_data()

        # 初始化攝影機
        self.init_camera()

    def load_config(self):
        '''載入系統設定'''
        self._load_env_file()
        self.config = {
            'database': {
                'host': 'localhost',
                'user': 'pi',
                'password': 'raspberry',
                'database': 'face_ad_system',
                'port': 3306
            },
            'camera': {
                'source': 0,
                'width': 640,
                'height': 480,
                'fps': 30
            },
            'recognition': {
                'tolerance': 0.6,
                'model': 'hog'  # 或 'cnn' (需要GPU)
            }
        }
        self._apply_env_overrides()

    def _load_env_file(self):
        '''從 .env 載入設定值'''
        env_file_setting = os.getenv('FACE_AD_ENV_FILE', '.env')
        candidate_paths = []

        if os.path.isabs(env_file_setting):
            candidate_paths.append(Path(env_file_setting))
        else:
            base_dir = Path(__file__).resolve().parent
            candidate_paths.extend([
                base_dir / env_file_setting,
                base_dir.parent / env_file_setting,
                Path.cwd() / env_file_setting
            ])

        self.env_file_path = None
        self.env_settings = {}

        seen = set()
        for path in candidate_paths:
            if path in seen:
                continue
            seen.add(path)
            if path.exists():
                self.env_file_path = path
                self.env_settings = self._parse_env_file(path)
                break

    def _parse_env_file(self, path):
        '''解析 .env 檔案''' 
        env_values = {}
        try:
            with path.open('r', encoding='utf-8') as env_file:
                for raw_line in env_file:
                    line = raw_line.strip()
                    if not line or line.startswith('#') or '=' not in line:
                        continue

                    key, value = raw_line.split('=', 1)
                    key = key.strip()
                    if not key:
                        continue

                    value = value.strip()
                    try:
                        tokens = shlex.split(value, comments=True)
                    except ValueError:
                        tokens = [value]

                    env_values[key] = tokens[0] if tokens else ''
        except OSError as exc:
            print(f"讀取環境檔案 {path} 時發生錯誤: {exc}")
        return env_values

    def _get_env_override(self, keys, cast=None, default=None):
        '''取得環境變數覆寫值'''
        if isinstance(keys, str):
            keys = (keys,)

        for key in keys:
            if key is None:
                continue

            raw_value = os.getenv(key)
            if raw_value is None:
                raw_value = self.env_settings.get(key)

            if raw_value is None:
                continue

            if cast:
                try:
                    converted = cast(raw_value)
                except (TypeError, ValueError):
                    print(f"環境變數 {key} 的值 {raw_value} 無法轉換，沿用預設值 {default}。")
                    return default

                if isinstance(converted, float) and math.isnan(converted):
                    print(f"環境變數 {key} 的值 {raw_value} 無法轉換，沿用預設值 {default}。")
                    return default

                return converted

            return raw_value

        return default

    def _convert_camera_source(self, value):
        '''將攝影機來源字串轉換為適當型別'''
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.isdigit() or (stripped.startswith('-') and stripped[1:].isdigit()):
                return int(stripped)
            return stripped
        return value

    def _apply_env_overrides(self):
        '''根據環境變數覆寫預設設定'''
        db_conf = self.config['database']
        db_conf['host'] = self._get_env_override(('FACE_AD_DB_HOST', 'DB_HOST'), default=db_conf['host'])
        db_conf['user'] = self._get_env_override(('FACE_AD_DB_USER', 'DB_USER'), default=db_conf['user'])
        db_conf['password'] = self._get_env_override(('FACE_AD_DB_PASSWORD', 'DB_PASSWORD'), default=db_conf['password'])
        db_conf['database'] = self._get_env_override(('FACE_AD_DB_NAME', 'DB_NAME'), default=db_conf['database'])
        db_conf['port'] = self._get_env_override(('FACE_AD_DB_PORT', 'DB_PORT'), cast=int, default=db_conf['port'])

        camera_conf = self.config['camera']
        source_override = self._get_env_override(('FACE_AD_CAMERA_SOURCE', 'CAMERA_SOURCE'))
        if source_override is not None:
            camera_conf['source'] = self._convert_camera_source(source_override)
        camera_conf['width'] = self._get_env_override(('FACE_AD_CAMERA_WIDTH', 'CAMERA_WIDTH'), cast=int, default=camera_conf['width'])
        camera_conf['height'] = self._get_env_override(('FACE_AD_CAMERA_HEIGHT', 'CAMERA_HEIGHT'), cast=int, default=camera_conf['height'])
        camera_conf['fps'] = self._get_env_override(('FACE_AD_CAMERA_FPS', 'CAMERA_FPS'), cast=int, default=camera_conf['fps'])

        recognition_conf = self.config['recognition']
        recognition_conf['tolerance'] = self._get_env_override(
            ('FACE_AD_RECOGNITION_TOLERANCE', 'RECOGNITION_TOLERANCE'),
            cast=float,
            default=recognition_conf['tolerance']
        )
        recognition_conf['model'] = self._get_env_override(
            ('FACE_AD_RECOGNITION_MODEL', 'RECOGNITION_MODEL'),
            default=recognition_conf['model']
        )

    def connect_database(self):
        '''連接MySQL資料庫'''
        try:
            connection_config = {
                'host': self.config['database']['host'],
                'user': self.config['database']['user'],
                'password': self.config['database']['password'],
                'database': self.config['database']['database']
            }

            port = self.config['database'].get('port')
            if port:
                connection_config['port'] = port

            self.db_connection = mysql.connector.connect(**connection_config)
            print("資料庫連接成功")
        except mysql.connector.Error as err:
            print(f"資料庫連接失敗: {err}")

    def init_camera(self):
        '''初始化攝影機'''
        try:
            source = self.config['camera'].get('source', 0)
            self.camera = cv2.VideoCapture(source)
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.config['camera']['width'])
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config['camera']['height'])
            self.camera.set(cv2.CAP_PROP_FPS, self.config['camera']['fps'])
            print("攝影機初始化成功")
        except Exception as e:
            print(f"攝影機初始化失敗: {e}")

    def load_face_data(self):
        '''從資料庫載入人臉編碼資料'''
        if not self.db_connection:
            return

        cursor = self.db_connection.cursor()
        query = "SELECT member_id, name, face_encoding FROM members WHERE is_active = TRUE"
        cursor.execute(query)

        for (member_id, name, face_encoding) in cursor:
            if face_encoding:
                # 將字串轉換回numpy陣列
                encoding = np.array(json.loads(face_encoding))
                self.known_face_encodings.append(encoding)
                self.known_face_names.append(name)
                self.member_data[name] = member_id

        cursor.close()
        print(f"載入了 {len(self.known_face_encodings)} 個人臉資料")

    def register_new_face(self, name, image):
        '''註冊新人臉'''
        face_encodings = face_recognition.face_encodings(image)

        if len(face_encodings) > 0:
            face_encoding = face_encodings[0]

            # 儲存到資料庫
            cursor = self.db_connection.cursor()
            encoding_str = json.dumps(face_encoding.tolist())

            query = '''INSERT INTO members (name, face_encoding) VALUES (%s, %s)'''
            cursor.execute(query, (name, encoding_str))
            self.db_connection.commit()

            member_id = cursor.lastrowid
            cursor.close()

            # 更新記憶體資料
            self.known_face_encodings.append(face_encoding)
            self.known_face_names.append(name)
            self.member_data[name] = member_id

            return True
        return False

    def recognize_face(self, frame):
        '''辨識人臉'''
        # 縮小影像以加快處理速度
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = small_frame[:, :, ::-1]

        # 尋找人臉
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

        face_names = []
        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(
                self.known_face_encodings, face_encoding, 
                tolerance=self.config['recognition']['tolerance']
            )
            name = "Unknown"

            # 使用最相似的人臉
            face_distances = face_recognition.face_distance(
                self.known_face_encodings, face_encoding
            )
            best_match_index = np.argmin(face_distances)

            if matches[best_match_index]:
                name = self.known_face_names[best_match_index]

            face_names.append(name)

        return face_locations, face_names

    def get_member_preferences(self, member_id):
        '''取得會員偏好和消費記錄'''
        cursor = self.db_connection.cursor()

        # 取得會員基本資料
        query = '''SELECT gender, age_group FROM members WHERE member_id = %s'''
        cursor.execute(query, (member_id,))
        member_info = cursor.fetchone()

        # 取得最近消費記錄
        query = '''
        SELECT product_category, COUNT(*) as frequency, AVG(amount) as avg_amount
        FROM purchase_history 
        WHERE member_id = %s AND purchase_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        GROUP BY product_category
        ORDER BY frequency DESC
        LIMIT 3
        '''
        cursor.execute(query, (member_id,))
        purchase_history = cursor.fetchall()

        cursor.close()

        return member_info, purchase_history

    def get_targeted_ad(self, member_id, member_info, purchase_history):
        '''根據會員資料取得目標廣告'''
        cursor = self.db_connection.cursor()

        gender, age_group = member_info if member_info else (None, None)

        # 建立查詢條件
        conditions = ["is_active = TRUE"]
        params = []

        if gender:
            conditions.append("(target_gender = %s OR target_gender = 'ALL')")
            params.append(gender)

        if age_group:
            conditions.append("target_age_group = %s")
            params.append(age_group)

        # 如果有購買記錄，優先推薦相關商品
        if purchase_history:
            categories = [item[0] for item in purchase_history]
            category_placeholders = ','.join(['%s'] * len(categories))
            conditions.append(f"target_category IN ({category_placeholders})")
            params.extend(categories)

        query = f'''
        SELECT ad_id, title, content, image_path
        FROM advertisements
        WHERE {' AND '.join(conditions)}
        ORDER BY RAND()
        LIMIT 1
        '''

        cursor.execute(query, params)
        ad = cursor.fetchone()
        cursor.close()

        return ad

    def display_ad(self, ad_info, member_id):
        '''顯示廣告'''
        if not ad_info:
            print("沒有找到適合的廣告")
            return

        ad_id, title, content, image_path = ad_info

        # 記錄廣告顯示
        cursor = self.db_connection.cursor()
        query = '''INSERT INTO ad_display_log (member_id, ad_id) VALUES (%s, %s)'''
        cursor.execute(query, (member_id, ad_id))
        self.db_connection.commit()
        cursor.close()

        # 在這裡實作廣告顯示邏輯
        print(f"顯示廣告給會員 {member_id}:")
        print(f"標題: {title}")
        print(f"內容: {content}")
        if image_path and os.path.exists(image_path):
            print(f"圖片: {image_path}")

    def run(self):
        '''主運行迴圈'''
        print("系統啟動中...")

        while True:
            ret, frame = self.camera.read()
            if not ret:
                break

            # 人臉辨識
            face_locations, face_names = self.recognize_face(frame)

            # 繪製辨識結果
            for (top, right, bottom, left), name in zip(face_locations, face_names):
                # 放大座標（因為之前縮小了）
                top *= 4
                right *= 4
                bottom *= 4
                left *= 4

                # 繪製方框
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)

                # 顯示名字
                cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
                font = cv2.FONT_HERSHEY_DUPLEX
                cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

                # 如果辨識到已知會員，推播廣告
                if name != "Unknown" and name in self.member_data:
                    member_id = self.member_data[name]
                    member_info, purchase_history = self.get_member_preferences(member_id)
                    ad = self.get_targeted_ad(member_id, member_info, purchase_history)
                    self.display_ad(ad, member_id)

                    # 暫停一段時間避免重複觸發
                    time.sleep(5)

            # 顯示影像
            cv2.imshow('Face Recognition Ad System', frame)

            # 按 'q' 退出
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        self.cleanup()

    def cleanup(self):
        '''清理資源'''
        if self.camera:
            self.camera.release()
        cv2.destroyAllWindows()
        if self.db_connection:
            self.db_connection.close()
        print("系統已關閉")

if __name__ == '__main__':
    system = FaceRecognitionAdSystem()
    system.run()
