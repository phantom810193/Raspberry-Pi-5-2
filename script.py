# 創建樹莓派人臉辨識系統所需的Python範例程式和設定檔案
import os

# 建立系統架構概覽
system_architecture = """
# 樹莓派人臉辨識客製化廣告系統架構

## 系統組件
1. 樹莓派 (Raspberry Pi)
2. 攝影機模組 (Camera Module)
3. 顯示螢幕 (Display Screen) 
4. 資料庫伺服器 (Database Server)
5. 廣告推播系統

## 系統流程
1. 攝影機擷取影像 → 2. 人臉偵測 → 3. 人臉識別 → 4. 建立會員ID → 
5. 查詢消費記錄 → 6. 生成客製化廣告 → 7. 推播至螢幕

## 技術堆疊
- 硬體: Raspberry Pi 4B, Pi Camera, HDMI顯示器
- 作業系統: Raspberry Pi OS
- 程式語言: Python 3
- 電腦視覺: OpenCV, face_recognition
- 資料庫: MySQL/MariaDB
- 網頁框架: Flask (可選)
- GUI: Tkinter (可選)
"""

print(system_architecture)

# 建立所需的安裝套件列表
required_packages = [
    "opencv-python",
    "face-recognition", 
    "dlib",
    "numpy",
    "mysql-connector-python",
    "pymysql",
    "flask",
    "pillow",
    "pandas"
]

print("\n需要安裝的Python套件:")
for pkg in required_packages:
    print(f"pip install {pkg}")

# 建立資料庫結構
database_schema = """
-- 會員資料表
CREATE TABLE members (
    member_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    phone VARCHAR(20),
    gender ENUM('M', 'F'),
    age_group VARCHAR(20),
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    face_encoding TEXT,
    is_active BOOLEAN DEFAULT TRUE
);

-- 消費記錄表
CREATE TABLE purchase_history (
    purchase_id INT PRIMARY KEY AUTO_INCREMENT,
    member_id INT,
    product_category VARCHAR(50),
    amount DECIMAL(10,2),
    purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    store_location VARCHAR(100),
    FOREIGN KEY (member_id) REFERENCES members(member_id)
);

-- 廣告內容表
CREATE TABLE advertisements (
    ad_id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(200),
    content TEXT,
    image_path VARCHAR(500),
    target_category VARCHAR(50),
    target_gender ENUM('M', 'F', 'ALL'),
    target_age_group VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 廣告推播記錄表
CREATE TABLE ad_display_log (
    log_id INT PRIMARY KEY AUTO_INCREMENT,
    member_id INT,
    ad_id INT,
    display_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    display_location VARCHAR(100),
    FOREIGN KEY (member_id) REFERENCES members(member_id),
    FOREIGN KEY (ad_id) REFERENCES advertisements(ad_id)
);
"""

print("\n資料庫結構 (MySQL):")
print(database_schema)