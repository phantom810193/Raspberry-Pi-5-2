# 樹莓派人臉辨識客製化廣告系統：從零到一完整教學

## 專案概述

本教學將指導完全未曾接觸過樹莓派的新手，從零開始建構一個符合賣場情境的人臉辨識客製化廣告推播系統。當消費者進入賣場時，樹莓派會透過攝影機進行即時人臉辨識，建立或查詢會員ID，調閱後端資料庫的消費記錄，並針對個人偏好推播客製化廣告至螢幕。

## 學習目標

完成本教學後，您將能夠：
1. 了解樹莓派硬體架構與基礎操作
2. 安裝和設定攝影機模組
3. 建立人臉辨識系統
4. 設計資料庫架構存儲會員資料
5. 實作客製化廣告推播機制
6. 整合完整的零售應用系統

## 第一章：樹莓派硬體準備與初始設定

### 1.1 所需硬體清單

**必要硬體：**
- Raspberry Pi 4 Model B (建議4GB記憶體)
- MicroSD卡 32GB (Class 10以上)
- Raspberry Pi Camera Module v2
- HDMI顯示器或觸控螢幕
- USB電源供應器 (5V 3A)
- HDMI線材
- 鍵盤滑鼠

**可選硬體：**
- 樹莓派外殼
- 散熱片或風扇
- GPIO擴展板

### 1.2 樹莓派作業系統安裝

#### 步驟1：下載並安裝 Raspberry Pi Imager
1. 前往 https://www.raspberrypi.org/software/
2. 下載適合您作業系統的Imager
3. 安裝並開啟Imager

#### 步驟2：燒錄作業系統
1. 插入MicroSD卡到電腦
2. 選擇「Raspberry Pi OS (64-bit)」
3. 選擇您的SD卡
4. 點擊「WRITE」開始燒錄
5. 燒錄完成後，安全移除SD卡

#### 步驟3：首次開機設定
1. 將SD卡插入樹莓派
2. 連接HDMI顯示器、鍵盤滑鼠
3. 連接電源啟動
4. 依照設定精靈完成初始設定：
   - 設定國家/語言/時區
   - 更改預設密碼
   - 連接WiFi網路
   - 更新系統

### 1.3 攝影機模組安裝

#### 硬體安裝步驟：
1. **關閉電源**：確保樹莓派完全斷電
2. **找到CSI接口**：位於HDMI連接埠旁的細長接口
3. **打開接口**：輕輕拉起塑膠卡榫
4. **插入排線**：金屬觸點面向HDMI方向
5. **固定排線**：壓下塑膠卡榫固定

#### 軟體啟用步驟：
```bash
# 開啟設定工具
sudo raspi-config

# 選擇路徑：
# 3 Interface Options -> P1 Camera -> Yes -> Finish

# 重新啟動
sudo reboot
```

#### 測試攝影機：
```bash
# 拍攝測試照片
raspistill -o test.jpg

# 檢查照片是否成功建立
ls -la test.jpg
```

## 第二章：系統環境建置

### 2.1 系統更新與套件安裝

```bash
# 更新套件列表
sudo apt update

# 升級系統套件
sudo apt upgrade -y

# 安裝編譯工具
sudo apt install -y build-essential cmake pkg-config

# 安裝Python開發工具
sudo apt install -y python3-pip python3-dev python3-venv

# 安裝圖像處理相關套件
sudo apt install -y libjpeg-dev libtiff5-dev libjasper-dev libpng-dev
sudo apt install -y libavcodec-dev libavformat-dev libswscale-dev libv4l-dev
sudo apt install -y libxvidcore-dev libx264-dev libfontconfig1-dev libcairo2-dev
sudo apt install -y libgdk-pixbuf2.0-dev libpango1.0-dev
sudo apt install -y libgtk2.0-dev libgtk-3-dev libatlas-base-dev gfortran
sudo apt install -y libhdf5-dev libhdf5-serial-dev libqtgui4 libqtwebkit4
```

### 2.2 資料庫安裝設定

```bash
# 安裝MariaDB (MySQL相容)
sudo apt install -y mariadb-server mariadb-client

# 啟動服務
sudo systemctl enable mariadb
sudo systemctl start mariadb

# 執行安全設定
sudo mysql_secure_installation
```

**資料庫安全設定選項：**
- Enter current password: 直接按Enter
- Set root password: Y (設定root密碼)
- Remove anonymous users: Y
- Disallow root login remotely: Y
- Remove test database: Y
- Reload privilege tables: Y

### 2.3 建立專案環境

```bash
# 建立專案目錄
mkdir ~/face_ad_system
cd ~/face_ad_system

# 建立Python虛擬環境
python3 -m venv face_env

# 啟動虛擬環境
source face_env/bin/activate

# 升級pip
pip install --upgrade pip setuptools wheel
```

### 2.4 Python套件安裝

依序安裝以避免相依性問題：

```bash
# 基礎科學計算套件
pip install numpy

# 電腦視覺套件
pip install opencv-python

# 人臉辨識相關套件（安裝時間較長）
pip install dlib
pip install face-recognition

# 資料庫連接
pip install mysql-connector-python pymysql

# 其他必要套件
pip install pillow flask pandas imutils
```

## 第三章：資料庫架構設計

### 3.1 資料庫建立

```sql
-- 登入MySQL
mysql -u root -p

-- 建立資料庫
CREATE DATABASE face_ad_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 建立使用者
CREATE USER 'pi'@'localhost' IDENTIFIED BY 'raspberry';
GRANT ALL PRIVILEGES ON face_ad_system.* TO 'pi'@'localhost';
FLUSH PRIVILEGES;

-- 使用資料庫
USE face_ad_system;
```

### 3.2 資料表結構

#### 會員資料表
```sql
CREATE TABLE members (
    member_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    phone VARCHAR(20),
    gender ENUM('M', 'F'),
    age_group VARCHAR(20),
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    face_encoding TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    INDEX idx_name (name),
    INDEX idx_active (is_active)
);
```

#### 消費記錄表
```sql
CREATE TABLE purchase_history (
    purchase_id INT PRIMARY KEY AUTO_INCREMENT,
    member_id INT,
    product_category VARCHAR(50),
    product_name VARCHAR(200),
    amount DECIMAL(10,2),
    quantity INT DEFAULT 1,
    purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    store_location VARCHAR(100),
    FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE CASCADE,
    INDEX idx_member_date (member_id, purchase_date),
    INDEX idx_category (product_category)
);
```

#### 廣告內容表
```sql
CREATE TABLE advertisements (
    ad_id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(200) NOT NULL,
    content TEXT,
    image_path VARCHAR(500),
    video_path VARCHAR(500),
    target_category VARCHAR(50),
    target_gender ENUM('M', 'F', 'ALL') DEFAULT 'ALL',
    target_age_group VARCHAR(20),
    priority INT DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    start_date DATE,
    end_date DATE,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 廣告推播記錄表
```sql
CREATE TABLE ad_display_log (
    log_id INT PRIMARY KEY AUTO_INCREMENT,
    member_id INT,
    ad_id INT,
    display_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    display_location VARCHAR(100) DEFAULT 'main_screen',
    display_duration INT DEFAULT 10,
    FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE CASCADE,
    FOREIGN KEY (ad_id) REFERENCES advertisements(ad_id) ON DELETE CASCADE
);
```

### 3.3 初始資料建立

```sql
-- 插入預設廣告
INSERT INTO advertisements (title, content, target_category, target_gender, target_age_group, is_active) VALUES
('新品上市 - 智慧手錶', '最新智慧手錶現正優惠中！', 'electronics', 'ALL', '20-40', TRUE),
('時尚服飾特價', '春季新款服飾全面8折', 'fashion', 'F', '18-35', TRUE),
('運動用品促銷', '運動鞋、運動服飾大特價', 'sports', 'M', '20-45', TRUE),
('美妝保養品', '頂級保養品牌限時優惠', 'beauty', 'F', '25-50', TRUE),
('家電優惠', '生活家電年終大促銷', 'appliances', 'ALL', '30-60', TRUE);

-- 建立範例會員（測試用）
INSERT INTO members (name, email, gender, age_group) VALUES
('張小明', 'ming@example.com', 'M', '25-35'),
('李小華', 'hua@example.com', 'F', '20-30'),
('王大成', 'cheng@example.com', 'M', '35-45');

-- 建立範例消費記錄
INSERT INTO purchase_history (member_id, product_category, product_name, amount) VALUES
(1, 'electronics', '智慧手機', 15000),
(1, 'fashion', '休閒褲', 1200),
(2, 'beauty', '保濕面膜', 800),
(2, 'fashion', '洋裝', 2500),
(3, 'sports', '運動鞋', 3200);
```

## 第四章：人臉辨識系統開發

### 4.1 基礎人臉辨識測試

建立測試程式 `test_face_detection.py`：

```python
#!/usr/bin/env python3
import cv2
import face_recognition
import numpy as np

def test_camera():
    """測試攝影機是否正常運作"""
    print("測試攝影機...")
    
    # 初始化攝影機
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("錯誤：無法開啟攝影機")
        return False
    
    print("攝影機測試成功！按 'q' 結束測試")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("錯誤：無法擷取影像")
            break
            
        cv2.imshow('Camera Test', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    return True

def test_face_detection():
    """測試人臉偵測功能"""
    print("測試人臉偵測...")
    
    cap = cv2.VideoCapture(0)
    
    print("人臉偵測測試中，按 'q' 結束")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # 轉換為RGB格式
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 偵測人臉
        face_locations = face_recognition.face_locations(rgb_frame)
        
        # 繪製人臉框架
        for (top, right, bottom, left) in face_locations:
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
            cv2.putText(frame, "Face Detected", (left, top-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        cv2.imshow('Face Detection Test', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    # 測試攝影機
    if test_camera():
        # 測試人臉偵測
        test_face_detection()
    else:
        print("攝影機測試失敗，請檢查硬體連接")
```

### 4.2 人臉編碼儲存系統

建立 `face_encoder.py`：

```python
#!/usr/bin/env python3
import face_recognition
import json
import mysql.connector
import cv2
import numpy as np
from datetime import datetime

class FaceEncoder:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'user': 'pi',
            'password': 'raspberry',
            'database': 'face_ad_system'
        }
        self.connection = None
        self.connect_database()
    
    def connect_database(self):
        """連接資料庫"""
        try:
            self.connection = mysql.connector.connect(**self.db_config)
            print("資料庫連接成功")
        except mysql.connector.Error as err:
            print(f"資料庫連接失敗: {err}")
    
    def capture_face(self, name):
        """擷取人臉並編碼"""
        print(f"開始擷取 {name} 的人臉資料...")
        print("請面向攝影機，按 's' 儲存人臉，按 'q' 取消")
        
        cap = cv2.VideoCapture(0)
        face_encoding = None
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 人臉偵測
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame)
            
            # 顯示人臉框架
            for (top, right, bottom, left) in face_locations:
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                cv2.putText(frame, f"Ready for {name}", (left, top-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            cv2.imshow('Face Capture', frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('s') and len(face_locations) > 0:
                # 儲存人臉編碼
                face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                if len(face_encodings) > 0:
                    face_encoding = face_encodings[0]
                    print("人臉資料擷取成功！")
                    break
                else:
                    print("無法產生人臉編碼，請重試")
            elif key == ord('q'):
                print("取消擷取")
                break
        
        cap.release()
        cv2.destroyAllWindows()
        
        return face_encoding
    
    def save_face_to_database(self, name, face_encoding, email=None, gender=None, age_group=None):
        """儲存人臉資料到資料庫"""
        if not self.connection or face_encoding is None:
            return False
        
        try:
            cursor = self.connection.cursor()
            
            # 將numpy陣列轉換為JSON字串
            encoding_str = json.dumps(face_encoding.tolist())
            
            # 插入會員資料
            query = """
                INSERT INTO members (name, email, gender, age_group, face_encoding) 
                VALUES (%s, %s, %s, %s, %s)
            """
            values = (name, email, gender, age_group, encoding_str)
            
            cursor.execute(query, values)
            self.connection.commit()
            
            member_id = cursor.lastrowid
            print(f"會員 {name} 註冊成功，ID: {member_id}")
            
            cursor.close()
            return True
            
        except mysql.connector.Error as err:
            print(f"資料庫儲存失敗: {err}")
            return False
    
    def register_member(self):
        """互動式會員註冊"""
        print("=== 會員註冊系統 ===")
        
        # 收集會員資訊
        name = input("請輸入姓名: ").strip()
        if not name:
            print("姓名不能為空")
            return
        
        email = input("請輸入電子郵件 (可選): ").strip()
        email = email if email else None
        
        print("請選擇性別:")
        print("1. 男性 (M)")
        print("2. 女性 (F)")
        print("3. 不指定")
        
        gender_choice = input("選擇 (1-3): ").strip()
        gender_map = {'1': 'M', '2': 'F', '3': None}
        gender = gender_map.get(gender_choice, None)
        
        print("請選擇年齡層:")
        print("1. 18-25")
        print("2. 26-35") 
        print("3. 36-45")
        print("4. 46-55")
        print("5. 56-65")
        print("6. 65+")
        print("7. 不指定")
        
        age_choice = input("選擇 (1-7): ").strip()
        age_map = {
            '1': '18-25', '2': '26-35', '3': '36-45',
            '4': '46-55', '5': '56-65', '6': '65+', '7': None
        }
        age_group = age_map.get(age_choice, None)
        
        # 擷取人臉
        face_encoding = self.capture_face(name)
        
        if face_encoding is not None:
            # 儲存到資料庫
            if self.save_face_to_database(name, face_encoding, email, gender, age_group):
                print("註冊完成！")
            else:
                print("註冊失敗，請重試")
        else:
            print("未擷取到人臉資料，註冊取消")

if __name__ == '__main__':
    encoder = FaceEncoder()
    encoder.register_member()
```

### 4.3 人臉辨識核心模組

建立 `face_recognizer.py`：

```python
#!/usr/bin/env python3
import face_recognition
import cv2
import numpy as np
import mysql.connector
import json
from datetime import datetime

class FaceRecognizer:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'user': 'pi',
            'password': 'raspberry',
            'database': 'face_ad_system'
        }
        
        # 人臉資料
        self.known_face_encodings = []
        self.known_face_names = []
        self.member_data = {}
        
        # 設定參數
        self.tolerance = 0.6
        self.frame_resizing = 0.25
        
        # 連接資料庫並載入人臉資料
        self.connection = mysql.connector.connect(**self.db_config)
        self.load_faces_from_database()
    
    def load_faces_from_database(self):
        """從資料庫載入所有會員人臉資料"""
        print("載入人臉資料...")
        
        cursor = self.connection.cursor()
        query = "SELECT member_id, name, face_encoding FROM members WHERE is_active = TRUE"
        cursor.execute(query)
        
        for (member_id, name, face_encoding_str) in cursor:
            if face_encoding_str:
                try:
                    # 將JSON字串轉換回numpy陣列
                    face_encoding = np.array(json.loads(face_encoding_str))
                    
                    self.known_face_encodings.append(face_encoding)
                    self.known_face_names.append(name)
                    self.member_data[name] = member_id
                    
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"載入 {name} 的人臉資料時發生錯誤: {e}")
        
        cursor.close()
        print(f"成功載入 {len(self.known_face_encodings)} 筆人臉資料")
    
    def recognize_faces(self, frame):
        """辨識影像中的人臉"""
        # 縮小影像以加快處理速度
        small_frame = cv2.resize(frame, (0, 0), fx=self.frame_resizing, fy=self.frame_resizing)
        rgb_small_frame = small_frame[:, :, ::-1]
        
        # 偵測人臉位置和編碼
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
        
        face_names = []
        for face_encoding in face_encodings:
            # 比較人臉
            matches = face_recognition.compare_faces(
                self.known_face_encodings, face_encoding, tolerance=self.tolerance
            )
            name = "Unknown"
            
            # 找到最相似的人臉
            face_distances = face_recognition.face_distance(
                self.known_face_encodings, face_encoding
            )
            
            if len(face_distances) > 0:
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    name = self.known_face_names[best_match_index]
            
            face_names.append(name)
        
        # 將座標放大回原本大小
        face_locations = np.array(face_locations)
        face_locations = face_locations / self.frame_resizing
        
        return face_locations.astype(int), face_names
    
    def get_member_id(self, name):
        """取得會員ID"""
        return self.member_data.get(name, None)
    
    def draw_results(self, frame, face_locations, face_names):
        """在影像上繪製辨識結果"""
        for (top, right, bottom, left), name in zip(face_locations, face_names):
            # 繪製人臉框架
            color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            
            # 繪製標籤背景
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
            
            # 繪製姓名
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(frame, name, (left + 6, bottom - 6), font, 0.6, (255, 255, 255), 1)
        
        return frame

# 測試程式
if __name__ == '__main__':
    recognizer = FaceRecognizer()
    
    print("人臉辨識測試開始，按 'q' 結束")
    cap = cv2.VideoCapture(0)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # 辨識人臉
        face_locations, face_names = recognizer.recognize_faces(frame)
        
        # 繪製結果
        frame = recognizer.draw_results(frame, face_locations, face_names)
        
        # 顯示已知會員
        for name in face_names:
            if name != "Unknown":
                member_id = recognizer.get_member_id(name)
                print(f"辨識到會員: {name} (ID: {member_id})")
        
        cv2.imshow('Face Recognition Test', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
```

## 第五章：廣告推播系統

### 5.1 廣告管理模組

建立 `ad_manager_core.py`：

```python
#!/usr/bin/env python3
import mysql.connector
import random
from datetime import datetime, date

class AdManager:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'user': 'pi',
            'password': 'raspberry',
            'database': 'face_ad_system'
        }
        self.connection = mysql.connector.connect(**self.db_config)
    
    def get_member_profile(self, member_id):
        """取得會員檔案資訊"""
        cursor = self.connection.cursor()
        
        # 取得會員基本資訊
        query = "SELECT name, gender, age_group FROM members WHERE member_id = %s"
        cursor.execute(query, (member_id,))
        member_info = cursor.fetchone()
        
        if not member_info:
            cursor.close()
            return None, []
        
        # 取得近期消費記錄
        query = """
            SELECT product_category, COUNT(*) as frequency, AVG(amount) as avg_amount
            FROM purchase_history 
            WHERE member_id = %s 
            AND purchase_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            GROUP BY product_category
            ORDER BY frequency DESC, avg_amount DESC
            LIMIT 5
        """
        cursor.execute(query, (member_id,))
        purchase_history = cursor.fetchall()
        
        cursor.close()
        return member_info, purchase_history
    
    def get_targeted_advertisement(self, member_id):
        """根據會員檔案選擇目標廣告"""
        member_info, purchase_history = self.get_member_profile(member_id)
        
        if not member_info:
            return self.get_default_advertisement()
        
        name, gender, age_group = member_info
        
        # 建立查詢條件
        conditions = ["is_active = TRUE"]
        params = []
        
        # 檢查廣告是否在有效期間內
        conditions.append("(start_date IS NULL OR start_date <= CURDATE())")
        conditions.append("(end_date IS NULL OR end_date >= CURDATE())")
        
        # 性別條件
        if gender:
            conditions.append("(target_gender = %s OR target_gender = 'ALL')")
            params.append(gender)
        
        # 年齡條件
        if age_group:
            conditions.append("(target_age_group = %s OR target_age_group IS NULL)")
            params.append(age_group)
        
        cursor = self.connection.cursor()
        
        # 優先顯示符合消費記錄的廣告
        if purchase_history:
            preferred_categories = [item[0] for item in purchase_history]
            category_conditions = conditions.copy()
            category_params = params.copy()
            
            placeholders = ','.join(['%s'] * len(preferred_categories))
            category_conditions.append(f"target_category IN ({placeholders})")
            category_params.extend(preferred_categories)
            
            query = f"""
                SELECT ad_id, title, content, image_path, video_path, target_category
                FROM advertisements
                WHERE {' AND '.join(category_conditions)}
                ORDER BY priority DESC, RAND()
                LIMIT 1
            """
            
            cursor.execute(query, category_params)
            result = cursor.fetchone()
            
            if result:
                cursor.close()
                return result
        
        # 如果沒有符合消費記錄的廣告，選擇一般廣告
        query = f"""
            SELECT ad_id, title, content, image_path, video_path, target_category
            FROM advertisements
            WHERE {' AND '.join(conditions)}
            ORDER BY priority DESC, RAND()
            LIMIT 1
        """
        
        cursor.execute(query, params)
        result = cursor.fetchone()
        cursor.close()
        
        return result if result else self.get_default_advertisement()
    
    def get_default_advertisement(self):
        """取得預設廣告"""
        cursor = self.connection.cursor()
        query = """
            SELECT ad_id, title, content, image_path, video_path, target_category
            FROM advertisements
            WHERE is_active = TRUE AND target_gender = 'ALL'
            ORDER BY priority DESC, RAND()
            LIMIT 1
        """
        cursor.execute(query)
        result = cursor.fetchone()
        cursor.close()
        return result
    
    def log_advertisement_display(self, member_id, ad_id, duration=10):
        """記錄廣告顯示"""
        cursor = self.connection.cursor()
        query = """
            INSERT INTO ad_display_log (member_id, ad_id, display_duration)
            VALUES (%s, %s, %s)
        """
        cursor.execute(query, (member_id, ad_id, duration))
        self.connection.commit()
        cursor.close()
    
    def get_advertisement_stats(self):
        """取得廣告統計資料"""
        cursor = self.connection.cursor()
        
        # 今日廣告顯示統計
        query = """
            SELECT a.title, COUNT(*) as display_count,
                   COUNT(DISTINCT adl.member_id) as unique_viewers
            FROM advertisements a
            JOIN ad_display_log adl ON a.ad_id = adl.ad_id
            WHERE DATE(adl.display_time) = CURDATE()
            GROUP BY a.ad_id, a.title
            ORDER BY display_count DESC
        """
        cursor.execute(query)
        today_stats = cursor.fetchall()
        
        # 熱門廣告分類
        query = """
            SELECT a.target_category, COUNT(*) as display_count
            FROM advertisements a
            JOIN ad_display_log adl ON a.ad_id = adl.ad_id
            WHERE DATE(adl.display_time) >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            GROUP BY a.target_category
            ORDER BY display_count DESC
            LIMIT 5
        """
        cursor.execute(query)
        category_stats = cursor.fetchall()
        
        cursor.close()
        return today_stats, category_stats

# 測試程式
if __name__ == '__main__':
    ad_manager = AdManager()
    
    print("=== 廣告系統測試 ===")
    
    # 測試取得預設廣告
    default_ad = ad_manager.get_default_advertisement()
    if default_ad:
        print(f"預設廣告: {default_ad[1]}")
    
    # 測試會員廣告
    member_id = 1  # 假設會員ID為1
    targeted_ad = ad_manager.get_targeted_advertisement(member_id)
    if targeted_ad:
        ad_id, title, content, image_path, video_path, category = targeted_ad
        print(f"會員廣告: {title}")
        print(f"內容: {content}")
        print(f"分類: {category}")
        
        # 記錄顯示
        ad_manager.log_advertisement_display(member_id, ad_id)
        print("廣告顯示已記錄")
    
    # 顯示統計
    today_stats, category_stats = ad_manager.get_advertisement_stats()
    print("\n今日廣告統計:")
    for title, count, unique in today_stats:
        print(f"  {title}: {count} 次顯示, {unique} 位觀看者")
```

### 5.2 顯示控制系統

建立 `display_controller.py`：

```python
#!/usr/bin/env python3
import cv2
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageFont, ImageDraw
import threading
import time
import os

class DisplayController:
    def __init__(self, fullscreen=True):
        self.root = tk.Tk()
        self.root.title("智慧廣告顯示系統")
        
        # 全螢幕設定
        if fullscreen:
            self.root.attributes('-fullscreen', True)
            self.root.configure(bg='black')
            self.screen_width = self.root.winfo_screenwidth()
            self.screen_height = self.root.winfo_screenheight()
        else:
            self.root.geometry("1024x768")
            self.screen_width = 1024
            self.screen_height = 768
        
        # 當前顯示的廣告
        self.current_ad = None
        self.display_start_time = None
        
        # 建立UI元件
        self.setup_ui()
        
        # 綁定按鍵事件
        self.root.bind('<Escape>', self.exit_fullscreen)
        self.root.bind('<F11>', self.toggle_fullscreen)
        
        # 預設顯示
        self.show_waiting_screen()
    
    def setup_ui(self):
        """設定UI元件"""
        # 主框架
        self.main_frame = tk.Frame(self.root, bg='black')
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 廣告顯示區域
        self.ad_frame = tk.Frame(self.main_frame, bg='black')
        self.ad_frame.pack(fill=tk.BOTH, expand=True)
        
        # 廣告標題
        self.title_label = tk.Label(
            self.ad_frame, 
            text="", 
            font=("Arial", 28, "bold"),
            fg='white', 
            bg='black'
        )
        self.title_label.pack(pady=20)
        
        # 廣告內容
        self.content_label = tk.Label(
            self.ad_frame,
            text="",
            font=("Arial", 18),
            fg='white',
            bg='black',
            wraplength=self.screen_width-100,
            justify=tk.CENTER
        )
        self.content_label.pack(pady=10)
        
        # 圖片顯示區域
        self.image_label = tk.Label(self.ad_frame, bg='black')
        self.image_label.pack(pady=20)
        
        # 狀態列
        self.status_frame = tk.Frame(self.root, bg='black', height=30)
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_label = tk.Label(
            self.status_frame,
            text="系統待機中...",
            font=("Arial", 12),
            fg='gray',
            bg='black'
        )
        self.status_label.pack(side=tk.RIGHT, padx=10, pady=5)
        
        # 時間顯示
        self.time_label = tk.Label(
            self.status_frame,
            text="",
            font=("Arial", 12),
            fg='gray',
            bg='black'
        )
        self.time_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        # 開始時間更新
        self.update_time()
    
    def update_time(self):
        """更新時間顯示"""
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=current_time)
        self.root.after(1000, self.update_time)
    
    def show_waiting_screen(self):
        """顯示等待畫面"""
        self.title_label.config(text="智慧廣告系統")
        self.content_label.config(text="請站在攝影機前，系統將為您推薦合適的商品")
        self.image_label.config(image="")
        self.status_label.config(text="等待中...")
    
    def display_advertisement(self, ad_data, member_name=None):
        """顯示廣告"""
        if not ad_data:
            self.show_waiting_screen()
            return
        
        ad_id, title, content, image_path, video_path, category = ad_data
        self.current_ad = ad_data
        self.display_start_time = time.time()
        
        # 更新標題和內容
        display_title = title
        if member_name:
            display_title = f"Hi {member_name}！{title}"
        
        self.title_label.config(text=display_title)
        self.content_label.config(text=content or "")
        
        # 顯示圖片
        if image_path and os.path.exists(image_path):
            self.display_image(image_path)
        else:
            self.image_label.config(image="")
        
        # 更新狀態
        status_text = f"正在顯示廣告: {category}"
        if member_name:
            status_text += f" (會員: {member_name})"
        self.status_label.config(text=status_text)
        
        print(f"顯示廣告: {title}")
    
    def display_image(self, image_path):
        """顯示廣告圖片"""
        try:
            # 載入並調整圖片大小
            pil_image = Image.open(image_path)
            
            # 計算適當的尺寸（保持比例）
            max_width = self.screen_width - 200
            max_height = self.screen_height - 400
            
            pil_image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            # 轉換為Tkinter格式
            photo = ImageTk.PhotoImage(pil_image)
            
            # 顯示圖片
            self.image_label.config(image=photo)
            self.image_label.image = photo  # 保持參考避免被垃圾回收
            
        except Exception as e:
            print(f"載入圖片失敗 {image_path}: {e}")
            self.image_label.config(image="")
    
    def get_display_duration(self):
        """取得當前廣告的顯示時間"""
        if self.display_start_time:
            return int(time.time() - self.display_start_time)
        return 0
    
    def exit_fullscreen(self, event=None):
        """退出全螢幕"""
        self.root.attributes('-fullscreen', False)
    
    def toggle_fullscreen(self, event=None):
        """切換全螢幕模式"""
        current_state = self.root.attributes('-fullscreen')
        self.root.attributes('-fullscreen', not current_state)
    
    def run(self):
        """啟動顯示系統"""
        self.root.mainloop()

# 測試程式
if __name__ == '__main__':
    display = DisplayController(fullscreen=False)
    
    # 測試顯示廣告
    test_ad = (1, "特價活動", "所有商品8折優惠！", None, None, "general")
    
    def test_display():
        time.sleep(3)
        display.display_advertisement(test_ad, "測試會員")
    
    # 在背景執行測試
    test_thread = threading.Thread(target=test_display)
    test_thread.daemon = True
    test_thread.start()
    
    display.run()
```

## 第六章：系統整合

### 6.1 主系統整合

建立完整的系統主程式 `main_system.py`：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
樹莓派人臉辨識客製化廣告系統 - 主程式
整合攝影機、人臉辨識、廣告推播功能
"""

import cv2
import threading
import time
from datetime import datetime
import queue
import sys
import os

# 匯入自定義模組
from face_recognizer import FaceRecognizer
from ad_manager_core import AdManager
from display_controller import DisplayController

class SmartAdSystem:
    def __init__(self):
        print("初始化智慧廣告系統...")
        
        # 系統組件
        self.face_recognizer = None
        self.ad_manager = None
        self.display_controller = None
        self.camera = None
        
        # 系統狀態
        self.running = False
        self.last_recognition_time = {}
        self.recognition_cooldown = 10  # 同一人10秒內不重複觸發
        
        # 訊息佇列
        self.ad_queue = queue.Queue()
        
        # 初始化各組件
        self.initialize_components()
        
    def initialize_components(self):
        """初始化系統組件"""
        try:
            # 初始化人臉辨識器
            print("載入人臉辨識系統...")
            self.face_recognizer = FaceRecognizer()
            
            # 初始化廣告管理器
            print("載入廣告管理系統...")
            self.ad_manager = AdManager()
            
            # 初始化顯示控制器
            print("載入顯示控制系統...")
            self.display_controller = DisplayController(fullscreen=True)
            
            # 初始化攝影機
            print("初始化攝影機...")
            self.camera = cv2.VideoCapture(0)
            if not self.camera.isOpened():
                raise Exception("無法開啟攝影機")
            
            # 設定攝影機參數
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera.set(cv2.CAP_PROP_FPS, 30)
            
            print("系統初始化完成")
            
        except Exception as e:
            print(f"系統初始化失敗: {e}")
            sys.exit(1)
    
    def camera_thread(self):
        """攝影機處理執行緒"""
        print("攝影機執行緒啟動")
        
        while self.running:
            ret, frame = self.camera.read()
            if not ret:
                print("攝影機讀取失敗")
                time.sleep(1)
                continue
            
            try:
                # 人臉辨識
                face_locations, face_names = self.face_recognizer.recognize_faces(frame)
                
                # 處理辨識結果
                for name in face_names:
                    if name != "Unknown":
                        self.handle_recognized_member(name)
                
                # 顯示即時影像（可選，用於調試）
                if os.environ.get('DEBUG_MODE') == '1':
                    debug_frame = self.face_recognizer.draw_results(frame, face_locations, face_names)
                    cv2.imshow('Debug Camera Feed', debug_frame)
                    
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        self.stop_system()
                
            except Exception as e:
                print(f"人臉辨識處理錯誤: {e}")
            
            # 控制處理頻率
            time.sleep(0.1)
        
        print("攝影機執行緒結束")
    
    def handle_recognized_member(self, member_name):
        """處理已辨識的會員"""
        current_time = time.time()
        
        # 檢查冷卻時間
        if member_name in self.last_recognition_time:
            if current_time - self.last_recognition_time[member_name] < self.recognition_cooldown:
                return
        
        self.last_recognition_time[member_name] = current_time
        
        # 取得會員ID
        member_id = self.face_recognizer.get_member_id(member_name)
        
        if member_id:
            print(f"辨識到會員: {member_name} (ID: {member_id})")
            
            # 取得目標廣告
            try:
                ad_data = self.ad_manager.get_targeted_advertisement(member_id)
                if ad_data:
                    # 將廣告資訊加入佇列
                    self.ad_queue.put((ad_data, member_name, member_id))
                
            except Exception as e:
                print(f"取得廣告資料失敗: {e}")
    
    def ad_display_thread(self):
        """廣告顯示處理執行緒"""
        print("廣告顯示執行緒啟動")
        
        while self.running:
            try:
                # 等待廣告請求
                ad_data, member_name, member_id = self.ad_queue.get(timeout=1)
                
                # 顯示廣告
                self.display_controller.display_advertisement(ad_data, member_name)
                
                # 記錄廣告顯示
                ad_id = ad_data[0]
                self.ad_manager.log_advertisement_display(member_id, ad_id)
                
                # 等待顯示時間
                time.sleep(10)  # 廣告顯示10秒
                
                # 回到等待畫面
                self.display_controller.show_waiting_screen()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"廣告顯示處理錯誤: {e}")
        
        print("廣告顯示執行緒結束")
    
    def display_thread(self):
        """顯示系統執行緒"""
        print("顯示系統執行緒啟動")
        
        try:
            self.display_controller.run()
        except Exception as e:
            print(f"顯示系統錯誤: {e}")
        
        # 顯示系統關閉時停止整個系統
        self.stop_system()
        print("顯示系統執行緒結束")
    
    def start_system(self):
        """啟動系統"""
        print("正在啟動智慧廣告系統...")
        self.running = True
        
        # 啟動各執行緒
        threads = [
            threading.Thread(target=self.camera_thread, name="CameraThread"),
            threading.Thread(target=self.ad_display_thread, name="AdDisplayThread"), 
            threading.Thread(target=self.display_thread, name="DisplayThread")
        ]
        
        for thread in threads:
            thread.daemon = True
            thread.start()
        
        print("系統啟動完成！")
        
        try:
            # 主執行緒等待
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("收到中斷信號，正在關閉系統...")
            self.stop_system()
    
    def stop_system(self):
        """停止系統"""
        print("正在關閉系統...")
        self.running = False
        
        # 關閉攝影機
        if self.camera:
            self.camera.release()
        
        # 關閉OpenCV視窗
        cv2.destroyAllWindows()
        
        print("系統已關閉")
    
    def run(self):
        """主要執行方法"""
        try:
            self.start_system()
        except Exception as e:
            print(f"系統執行錯誤: {e}")
        finally:
            self.stop_system()

# 主程式入口
if __name__ == '__main__':
    print("樹莓派智慧廣告系統 v1.0")
    print("按 Ctrl+C 停止系統")
    print("=" * 50)
    
    # 檢查除錯模式
    if len(sys.argv) > 1 and sys.argv[1] == '--debug':
        os.environ['DEBUG_MODE'] = '1'
        print("除錯模式已啟用")
    
    # 啟動系統
    system = SmartAdSystem()
    system.run()
```

### 6.2 系統服務設定

建立系統服務配置檔案 `face-ad-system.service`：

```ini
[Unit]
Description=Face Recognition Advertisement System
After=network.target mariadb.service
Requires=mariadb.service

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/face_ad_system
Environment=PATH=/home/pi/face_ad_system/face_env/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=/home/pi/face_ad_system
ExecStart=/home/pi/face_ad_system/face_env/bin/python /home/pi/face_ad_system/main_system.py
Restart=always
RestartSec=10
KillMode=mixed
KillSignal=SIGTERM

[Install]
WantedBy=multi-user.target
```

### 6.3 啟動腳本

建立啟動腳本 `start_system.sh`：

```bash
#!/bin/bash

# 樹莓派智慧廣告系統啟動腳本

# 設定顏色輸出
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
NC='\\033[0m' # No Color

echo -e "${GREEN}樹莓派智慧廣告系統啟動器${NC}"
echo "=================================="

# 檢查虛擬環境
if [ ! -d "face_env" ]; then
    echo -e "${RED}錯誤: 找不到Python虛擬環境${NC}"
    echo "請先執行安裝腳本"
    exit 1
fi

# 檢查資料庫服務
if ! systemctl is-active --quiet mariadb; then
    echo -e "${YELLOW}警告: MariaDB服務未運行，嘗試啟動...${NC}"
    sudo systemctl start mariadb
    
    if ! systemctl is-active --quiet mariadb; then
        echo -e "${RED}錯誤: 無法啟動MariaDB服務${NC}"
        exit 1
    fi
    echo -e "${GREEN}MariaDB服務已啟動${NC}"
fi

# 檢查攝影機
if [ ! -e "/dev/video0" ]; then
    echo -e "${RED}錯誤: 找不到攝影機設備${NC}"
    echo "請檢查攝影機連接和設定"
    exit 1
fi

# 啟動虛擬環境
source face_env/bin/activate

# 檢查必要模組
python3 -c "import cv2, face_recognition, mysql.connector" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${RED}錯誤: Python模組載入失敗${NC}"
    echo "請檢查虛擬環境和套件安裝"
    exit 1
fi

echo -e "${GREEN}所有檢查通過，啟動系統...${NC}"

# 啟動系統
python3 main_system.py "$@"

echo -e "${YELLOW}系統已退出${NC}"
```

使腳本可執行：
```bash
chmod +x start_system.sh
```

## 第七章：系統測試與調校

### 7.1 單元測試

建立測試程式 `test_system.py`：

```python
#!/usr/bin/env python3
import unittest
import sys
import os
import mysql.connector
import cv2
import json

# 添加專案路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from face_recognizer import FaceRecognizer
from ad_manager_core import AdManager

class TestFaceRecognitionSystem(unittest.TestCase):
    
    def setUp(self):
        """測試前準備"""
        self.db_config = {
            'host': 'localhost',
            'user': 'pi',
            'password': 'raspberry',
            'database': 'face_ad_system'
        }
    
    def test_database_connection(self):
        """測試資料庫連接"""
        try:
            connection = mysql.connector.connect(**self.db_config)
            self.assertTrue(connection.is_connected())
            connection.close()
        except mysql.connector.Error as e:
            self.fail(f"資料庫連接失敗: {e}")
    
    def test_camera_initialization(self):
        """測試攝影機初始化"""
        cap = cv2.VideoCapture(0)
        self.assertTrue(cap.isOpened(), "攝影機無法開啟")
        
        ret, frame = cap.read()
        self.assertTrue(ret, "攝影機無法讀取影像")
        self.assertIsNotNone(frame, "影像為空")
        
        cap.release()
    
    def test_face_recognizer_initialization(self):
        """測試人臉辨識器初始化"""
        try:
            recognizer = FaceRecognizer()
            self.assertIsInstance(recognizer, FaceRecognizer)
            self.assertIsInstance(recognizer.known_face_encodings, list)
        except Exception as e:
            self.fail(f"人臉辨識器初始化失敗: {e}")
    
    def test_ad_manager_initialization(self):
        """測試廣告管理器初始化"""
        try:
            ad_manager = AdManager()
            self.assertIsInstance(ad_manager, AdManager)
        except Exception as e:
            self.fail(f"廣告管理器初始化失敗: {e}")
    
    def test_get_default_advertisement(self):
        """測試取得預設廣告"""
        ad_manager = AdManager()
        ad = ad_manager.get_default_advertisement()
        self.assertIsNotNone(ad, "無法取得預設廣告")

class TestSystemIntegration(unittest.TestCase):
    """整合測試"""
    
    def test_full_workflow(self):
        """測試完整工作流程"""
        # 這裡會測試整個系統流程
        # 由於需要實際的攝影機和人臉資料，這部分在實際環境中測試
        pass

def run_system_check():
    """執行系統檢查"""
    print("執行系統檢查...")
    
    checks = [
        ("檢查Python版本", check_python_version),
        ("檢查必要套件", check_required_packages),
        ("檢查資料庫", check_database),
        ("檢查攝影機", check_camera),
        ("檢查檔案權限", check_file_permissions),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\\n{name}...")
        try:
            result = check_func()
            if result:
                print(f"✓ {name} 通過")
                results.append(True)
            else:
                print(f"✗ {name} 失敗")
                results.append(False)
        except Exception as e:
            print(f"✗ {name} 錯誤: {e}")
            results.append(False)
    
    print(f"\\n檢查完成: {sum(results)}/{len(results)} 項通過")
    return all(results)

def check_python_version():
    """檢查Python版本"""
    import sys
    version = sys.version_info
    return version.major == 3 and version.minor >= 7

def check_required_packages():
    """檢查必要套件"""
    required_packages = [
        'cv2', 'face_recognition', 'mysql.connector', 
        'numpy', 'PIL', 'tkinter'
    ]
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            print(f"缺少套件: {package}")
            return False
    return True

def check_database():
    """檢查資料庫連接和表格"""
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='pi',
            password='raspberry',
            database='face_ad_system'
        )
        
        cursor = connection.cursor()
        
        # 檢查必要表格
        required_tables = ['members', 'advertisements', 'purchase_history', 'ad_display_log']
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        
        for table in required_tables:
            if table not in tables:
                print(f"缺少資料表: {table}")
                return False
        
        cursor.close()
        connection.close()
        return True
        
    except mysql.connector.Error as e:
        print(f"資料庫錯誤: {e}")
        return False

def check_camera():
    """檢查攝影機"""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return False
    
    ret, frame = cap.read()
    cap.release()
    return ret and frame is not None

def check_file_permissions():
    """檢查檔案權限"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 檢查可執行檔案
    executable_files = ['start_system.sh']
    for filename in executable_files:
        filepath = os.path.join(current_dir, filename)
        if os.path.exists(filepath):
            if not os.access(filepath, os.X_OK):
                print(f"檔案不可執行: {filename}")
                return False
    
    return True

if __name__ == '__main__':
    print("樹莓派智慧廣告系統測試程式")
    print("=" * 40)
    
    if len(sys.argv) > 1 and sys.argv[1] == '--check':
        # 執行系統檢查
        if run_system_check():
            print("\\n系統檢查全部通過！可以啟動系統。")
            sys.exit(0)
        else:
            print("\\n系統檢查發現問題，請修正後重新測試。")
            sys.exit(1)
    else:
        # 執行單元測試
        unittest.main()
```

### 7.2 效能調校指南

建立效能調校腳本 `optimize_system.py`：

```python
#!/usr/bin/env python3
"""
樹莓派效能調校工具
"""

import os
import subprocess
import psutil

def optimize_raspberry_pi():
    """樹莓派效能調校"""
    
    print("樹莓派系統效能調校")
    print("=" * 30)
    
    optimizations = [
        ("調整GPU記憶體分割", optimize_gpu_memory),
        ("調整交換檔案", optimize_swap),
        ("停用不必要服務", disable_unused_services),
        ("調整攝影機設定", optimize_camera_settings),
        ("設定CPU調速器", set_cpu_governor),
    ]
    
    for name, func in optimizations:
        print(f"\\n執行: {name}")
        try:
            func()
            print(f"✓ {name} 完成")
        except Exception as e:
            print(f"✗ {name} 失敗: {e}")

def optimize_gpu_memory():
    """調整GPU記憶體分割"""
    config_file = "/boot/config.txt"
    
    # 檢查是否需要調整
    with open(config_file, 'r') as f:
        content = f.read()
    
    if "gpu_mem=128" not in content:
        # 備份原檔案
        subprocess.run(["sudo", "cp", config_file, f"{config_file}.backup"])
        
        # 添加GPU記憶體設定
        with open("/tmp/config_update.txt", 'w') as f:
            f.write("\\n# GPU memory split for camera and graphics\\n")
            f.write("gpu_mem=128\\n")
        
        subprocess.run(["sudo", "sh", "-c", f"cat /tmp/config_update.txt >> {config_file}"])
        print("GPU記憶體已調整為128MB")
    else:
        print("GPU記憶體設定已存在")

def optimize_swap():
    """調整交換檔案大小"""
    swap_file = "/etc/dphys-swapfile"
    
    try:
        # 停止交換服務
        subprocess.run(["sudo", "systemctl", "stop", "dphys-swapfile"])
        
        # 備份設定檔
        subprocess.run(["sudo", "cp", swap_file, f"{swap_file}.backup"])
        
        # 修改交換檔案大小
        subprocess.run([
            "sudo", "sed", "-i", 
            "s/CONF_SWAPSIZE=100/CONF_SWAPSIZE=1024/g", 
            swap_file
        ])
        
        # 重新初始化並啟動交換檔案
        subprocess.run(["sudo", "dphys-swapfile", "setup"])
        subprocess.run(["sudo", "systemctl", "start", "dphys-swapfile"])
        
        print("交換檔案已調整為1024MB")
        
    except Exception as e:
        print(f"交換檔案調整失敗: {e}")

def disable_unused_services():
    """停用不必要的服務"""
    unused_services = [
        "bluetooth",
        "hciuart", 
        "triggerhappy"
    ]
    
    for service in unused_services:
        try:
            result = subprocess.run(
                ["sudo", "systemctl", "disable", service],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                print(f"已停用服務: {service}")
        except Exception as e:
            print(f"停用 {service} 失敗: {e}")

def optimize_camera_settings():
    """調整攝影機設定"""
    config_file = "/boot/config.txt"
    
    camera_settings = [
        "start_x=1",
        "disable_camera_led=1"
    ]
    
    with open(config_file, 'r') as f:
        content = f.read()
    
    new_settings = []
    for setting in camera_settings:
        if setting not in content:
            new_settings.append(setting)
    
    if new_settings:
        with open("/tmp/camera_settings.txt", 'w') as f:
            f.write("\\n# Camera optimizations\\n")
            for setting in new_settings:
                f.write(f"{setting}\\n")
        
        subprocess.run(["sudo", "sh", "-c", f"cat /tmp/camera_settings.txt >> {config_file}"])
        print("攝影機設定已優化")
    else:
        print("攝影機設定已存在")

def set_cpu_governor():
    """設定CPU調速器"""
    try:
        # 設定為performance模式
        subprocess.run([
            "sudo", "sh", "-c", 
            "echo 'performance' > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
        ])
        print("CPU調速器已設定為performance模式")
    except Exception as e:
        print(f"CPU調速器設定失敗: {e}")

def show_system_info():
    """顯示系統資訊"""
    print("\\n系統資訊:")
    print("-" * 20)
    
    # CPU資訊
    print(f"CPU使用率: {psutil.cpu_percent()}%")
    
    # 記憶體資訊
    memory = psutil.virtual_memory()
    print(f"記憶體使用: {memory.percent}% ({memory.used // 1024 // 1024}MB / {memory.total // 1024 // 1024}MB)")
    
    # 磁碟資訊
    disk = psutil.disk_usage('/')
    print(f"磁碟使用: {disk.percent}% ({disk.used // 1024 // 1024 // 1024}GB / {disk.total // 1024 // 1024 // 1024}GB)")
    
    # 溫度資訊（樹莓派特有）
    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temp = int(f.read().strip()) / 1000
        print(f"CPU溫度: {temp}°C")
    except:
        print("無法讀取溫度資訊")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--info':
            show_system_info()
        elif sys.argv[1] == '--optimize':
            optimize_raspberry_pi()
            print("\\n調校完成！建議重新啟動系統。")
        else:
            print("用法:")
            print("  python3 optimize_system.py --info     # 顯示系統資訊")
            print("  python3 optimize_system.py --optimize # 執行效能調校")
    else:
        show_system_info()
```

## 第八章：故障排除與維護

### 8.1 常見問題解決

建立故障診斷工具 `troubleshoot.py`：

```python
#!/usr/bin/env python3
"""
故障診斷工具
"""

import os
import cv2
import mysql.connector
import subprocess
import sys

def diagnose_system():
    """診斷系統問題"""
    print("樹莓派智慧廣告系統故障診斷")
    print("=" * 40)
    
    tests = [
        ("檢查攝影機", test_camera),
        ("檢查資料庫連接", test_database),
        ("檢查Python套件", test_packages),
        ("檢查系統資源", test_resources),
        ("檢查服務狀態", test_services),
    ]
    
    for test_name, test_func in tests:
        print(f"\\n{test_name}...")
        try:
            result, message = test_func()
            status = "✓" if result else "✗"
            print(f"{status} {message}")
        except Exception as e:
            print(f"✗ 錯誤: {e}")

def test_camera():
    """測試攝影機"""
    # 檢查設備檔案
    if not os.path.exists("/dev/video0"):
        return False, "攝影機設備檔案不存在 (/dev/video0)"
    
    # 嘗試初始化攝影機
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return False, "無法開啟攝影機"
    
    # 嘗試讀取影像
    ret, frame = cap.read()
    cap.release()
    
    if not ret or frame is None:
        return False, "無法從攝影機讀取影像"
    
    return True, f"攝影機正常 (解析度: {frame.shape[1]}x{frame.shape[0]})"

def test_database():
    """測試資料庫連接"""
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='pi', 
            password='raspberry',
            database='face_ad_system'
        )
        
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM members")
        member_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM advertisements")
        ad_count = cursor.fetchone()[0]
        
        cursor.close()
        connection.close()
        
        return True, f"資料庫連接正常 (會員: {member_count}, 廣告: {ad_count})"
        
    except mysql.connector.Error as e:
        return False, f"資料庫連接失敗: {e}"

def test_packages():
    """測試Python套件"""
    required_packages = {
        'cv2': 'OpenCV',
        'face_recognition': 'Face Recognition',
        'mysql.connector': 'MySQL Connector',
        'numpy': 'NumPy',
        'PIL': 'Pillow',
        'tkinter': 'Tkinter'
    }
    
    missing_packages = []
    for package, name in required_packages.items():
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(name)
    
    if missing_packages:
        return False, f"缺少套件: {', '.join(missing_packages)}"
    else:
        return True, "所有必要套件已安裝"

def test_resources():
    """測試系統資源"""
    import psutil
    
    # 檢查記憶體
    memory = psutil.virtual_memory()
    if memory.percent > 90:
        return False, f"記憶體使用過高: {memory.percent}%"
    
    # 檢查磁碟空間
    disk = psutil.disk_usage('/')
    if disk.percent > 95:
        return False, f"磁碟空間不足: {disk.percent}%"
    
    # 檢查CPU溫度
    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temp = int(f.read().strip()) / 1000
        if temp > 80:
            return False, f"CPU溫度過高: {temp}°C"
    except:
        pass
    
    return True, f"系統資源正常 (記憶體: {memory.percent}%, 磁碟: {disk.percent}%)"

def test_services():
    """測試系統服務"""
    services_to_check = ['mariadb']
    
    for service in services_to_check:
        result = subprocess.run(
            ['systemctl', 'is-active', service],
            capture_output=True, text=True
        )
        
        if result.returncode != 0:
            return False, f"{service} 服務未運行"
    
    return True, "所有必要服務正在運行"

def fix_common_issues():
    """修復常見問題"""
    print("\\n嘗試修復常見問題...")
    
    fixes = [
        ("重新啟動MariaDB", lambda: subprocess.run(['sudo', 'systemctl', 'restart', 'mariadb'])),
        ("清理暫存檔案", clean_temp_files),
        ("重設攝影機權限", fix_camera_permissions),
    ]
    
    for fix_name, fix_func in fixes:
        print(f"執行: {fix_name}")
        try:
            fix_func()
            print(f"✓ {fix_name} 完成")
        except Exception as e:
            print(f"✗ {fix_name} 失敗: {e}")

def clean_temp_files():
    """清理暫存檔案"""
    import shutil
    
    temp_dirs = ['/tmp', '/var/tmp']
    for temp_dir in temp_dirs:
        if os.path.exists(temp_dir):
            for filename in os.listdir(temp_dir):
                if filename.startswith('opencv') or filename.startswith('face_'):
                    try:
                        filepath = os.path.join(temp_dir, filename)
                        if os.path.isfile(filepath):
                            os.unlink(filepath)
                        elif os.path.isdir(filepath):
                            shutil.rmtree(filepath)
                    except:
                        pass

def fix_camera_permissions():
    """修復攝影機權限"""
    subprocess.run(['sudo', 'usermod', '-a', '-G', 'video', 'pi'])

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--fix':
        fix_common_issues()
    else:
        diagnose_system()
        
        print("\\n如需嘗試修復常見問題，請執行:")
        print("python3 troubleshoot.py --fix")
```

### 8.2 系統維護腳本

建立維護腳本 `maintenance.py`：

```python
#!/usr/bin/env python3
"""
系統維護工具
"""

import mysql.connector
import os
import datetime
import subprocess
import shutil

def database_maintenance():
    """資料庫維護"""
    print("執行資料庫維護...")
    
    connection = mysql.connector.connect(
        host='localhost',
        user='pi',
        password='raspberry', 
        database='face_ad_system'
    )
    
    cursor = connection.cursor()
    
    # 清理舊的廣告顯示記錄（保留30天）
    cursor.execute("""
        DELETE FROM ad_display_log 
        WHERE display_time < DATE_SUB(NOW(), INTERVAL 30 DAY)
    """)
    
    deleted_logs = cursor.rowcount
    print(f"清理了 {deleted_logs} 筆舊的廣告記錄")
    
    # 清理過期廣告
    cursor.execute("""
        UPDATE advertisements 
        SET is_active = FALSE 
        WHERE end_date < CURDATE() AND is_active = TRUE
    """)
    
    disabled_ads = cursor.rowcount
    print(f"停用了 {disabled_ads} 個過期廣告")
    
    # 優化資料表
    tables = ['members', 'advertisements', 'purchase_history', 'ad_display_log']
    for table in tables:
        cursor.execute(f"OPTIMIZE TABLE {table}")
        print(f"優化了資料表: {table}")
    
    connection.commit()
    cursor.close()
    connection.close()
    
    print("資料庫維護完成")

def backup_database():
    """備份資料庫"""
    print("備份資料庫...")
    
    backup_dir = "/home/pi/backups"
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{backup_dir}/face_ad_system_{timestamp}.sql"
    
    # 執行mysqldump
    cmd = [
        'mysqldump',
        '-u', 'pi',
        '-praspberry',  # 注意：-p和密碼之間沒有空格
        'face_ad_system'
    ]
    
    with open(backup_file, 'w') as f:
        subprocess.run(cmd, stdout=f)
    
    print(f"資料庫已備份至: {backup_file}")
    
    # 清理舊備份（保留7個最新備份）
    cleanup_old_backups(backup_dir, 7)

def cleanup_old_backups(backup_dir, keep_count):
    """清理舊備份"""
    backup_files = []
    for filename in os.listdir(backup_dir):
        if filename.startswith('face_ad_system_') and filename.endswith('.sql'):
            filepath = os.path.join(backup_dir, filename)
            backup_files.append((filepath, os.path.getctime(filepath)))
    
    # 按建立時間排序
    backup_files.sort(key=lambda x: x[1], reverse=True)
    
    # 刪除多餘的備份
    for filepath, _ in backup_files[keep_count:]:
        os.unlink(filepath)
        print(f"刪除舊備份: {os.path.basename(filepath)}")

def system_cleanup():
    """系統清理"""
    print("執行系統清理...")
    
    # 清理系統日誌
    subprocess.run(['sudo', 'journalctl', '--vacuum-time=7d'])
    
    # 清理apt快取
    subprocess.run(['sudo', 'apt', 'autoremove', '-y'])
    subprocess.run(['sudo', 'apt', 'autoclean'])
    
    # 清理暫存檔案
    temp_dirs = ['/tmp', '/var/tmp']
    for temp_dir in temp_dirs:
        if os.path.exists(temp_dir):
            for item in os.listdir(temp_dir):
                item_path = os.path.join(temp_dir, item)
                try:
                    if os.path.isfile(item_path):
                        # 只刪除3天前的檔案
                        if os.path.getctime(item_path) < (datetime.datetime.now() - datetime.timedelta(days=3)).timestamp():
                            os.unlink(item_path)
                    elif os.path.isdir(item_path) and item.startswith(('opencv', 'tmp', 'cache')):
                        shutil.rmtree(item_path)
                except:
                    pass
    
    print("系統清理完成")

def generate_report():
    """生成系統報告"""
    print("生成系統報告...")
    
    connection = mysql.connector.connect(
        host='localhost',
        user='pi',
        password='raspberry',
        database='face_ad_system'
    )
    
    cursor = connection.cursor()
    
    report = []
    report.append(f"樹莓派智慧廣告系統報告")
    report.append(f"生成時間: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 50)
    
    # 系統統計
    cursor.execute("SELECT COUNT(*) FROM members WHERE is_active = TRUE")
    active_members = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM advertisements WHERE is_active = TRUE")
    active_ads = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM ad_display_log WHERE DATE(display_time) = CURDATE()")
    today_displays = cursor.fetchone()[0]
    
    report.append("\\n系統統計:")
    report.append(f"  活躍會員數: {active_members}")
    report.append(f"  活躍廣告數: {active_ads}")
    report.append(f"  今日廣告顯示次數: {today_displays}")
    
    # 熱門廣告
    cursor.execute("""
        SELECT a.title, COUNT(*) as display_count
        FROM advertisements a
        JOIN ad_display_log adl ON a.ad_id = adl.ad_id
        WHERE DATE(adl.display_time) >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
        GROUP BY a.ad_id
        ORDER BY display_count DESC
        LIMIT 5
    """)
    
    popular_ads = cursor.fetchall()
    if popular_ads:
        report.append("\\n本週熱門廣告:")
        for i, (title, count) in enumerate(popular_ads, 1):
            report.append(f"  {i}. {title} ({count} 次)")
    
    # 會員統計
    cursor.execute("""
        SELECT gender, COUNT(*) as count
        FROM members 
        WHERE is_active = TRUE AND gender IS NOT NULL
        GROUP BY gender
    """)
    
    gender_stats = cursor.fetchall()
    if gender_stats:
        report.append("\\n會員性別分布:")
        for gender, count in gender_stats:
            report.append(f"  {gender}: {count} 人")
    
    cursor.close()
    connection.close()
    
    # 儲存報告
    report_content = "\\n".join(report)
    
    report_dir = "/home/pi/reports"
    os.makedirs(report_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d")
    report_file = f"{report_dir}/system_report_{timestamp}.txt"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"系統報告已儲存至: {report_file}")
    print("\\n" + "=" * 30)
    print(report_content)

def main():
    """主維護程式"""
    import sys
    
    if len(sys.argv) < 2:
        print("樹莓派智慧廣告系統維護工具")
        print("使用方式:")
        print("  python3 maintenance.py backup    # 備份資料庫")
        print("  python3 maintenance.py cleanup   # 清理系統")
        print("  python3 maintenance.py maintain  # 資料庫維護")
        print("  python3 maintenance.py report    # 生成報告")
        print("  python3 maintenance.py all       # 執行所有維護")
        return
    
    command = sys.argv[1]
    
    if command == 'backup':
        backup_database()
    elif command == 'cleanup':
        system_cleanup()
    elif command == 'maintain':
        database_maintenance()
    elif command == 'report':
        generate_report()
    elif command == 'all':
        backup_database()
        database_maintenance()
        system_cleanup()
        generate_report()
        print("\\n所有維護作業完成！")
    else:
        print(f"未知命令: {command}")

if __name__ == '__main__':
    main()
```

## 結語

本教學提供了從零開始建構樹莓派人臉辨識客製化廣告系統的完整指南。透過循序漸進的學習，您已經掌握了：

1. **硬體設定**：樹莓派和攝影機模組的安裝配置
2. **系統環境**：作業系統、資料庫、Python環境的建置
3. **核心技術**：人臉辨識、資料庫操作、廣告推播的實作
4. **系統整合**：各模組的整合和完整系統的開發
5. **維護管理**：測試、調校、故障排除和日常維護

這個系統可以應用於各種零售場景，為顧客提供個人化的購物體驗，同時為商家提供精準的行銷工具。您可以根據實際需求進一步擴展功能，如：

- 增加語音播報功能
- 整合行動支付系統
- 添加客流分析功能
- 支援多螢幕顯示
- 整合雲端服務

希望這個教學能夠幫助您在物聯網和人工智慧領域的學習旅程中更進一步！