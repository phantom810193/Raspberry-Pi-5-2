# 建立樹莓派安裝和設定指南
installation_guide = """
# 樹莓派人臉辨識客製化廣告系統安裝指南

## 步驟一：準備樹莓派硬體
1. 樹莓派 4B (建議4GB記憶體以上)
2. MicroSD卡 (32GB以上，Class 10)
3. 樹莓派官方攝影機模組 (Camera Module v2)
4. HDMI顯示器或觸控螢幕
5. 電源供應器 (5V 3A)

## 步驟二：安裝樹莓派作業系統
1. 下載 Raspberry Pi Imager: https://www.raspberrypi.org/software/
2. 選擇 Raspberry Pi OS (64-bit) with desktop
3. 燒錄到SD卡
4. 啟動樹莓派並完成初始設定

## 步驟三：啟用攝影機模組
1. 關閉樹莓派電源
2. 小心連接攝影機模組到CSI介面
3. 開機後執行設定：
   ```bash
   sudo raspi-config
   ```
4. 選擇 "Interfacing Options" → "Camera" → "Enable"
5. 重新啟動樹莓派

## 步驟四：更新系統和安裝基礎套件
```bash
# 更新系統
sudo apt update && sudo apt upgrade -y

# 安裝必要的系統套件
sudo apt install -y python3-pip python3-dev python3-venv
sudo apt install -y cmake build-essential pkg-config
sudo apt install -y libjpeg-dev libtiff5-dev libjasper-dev libpng-dev
sudo apt install -y libavcodec-dev libavformat-dev libswscale-dev libv4l-dev
sudo apt install -y libxvidcore-dev libx264-dev
sudo apt install -y libfontconfig1-dev libcairo2-dev
sudo apt install -y libgdk-pixbuf2.0-dev libpango1.0-dev
sudo apt install -y libgtk2.0-dev libgtk-3-dev
sudo apt install -y libatlas-base-dev gfortran
sudo apt install -y libhdf5-dev libhdf5-serial-dev
sudo apt install -y libqtgui4 libqtwebkit4 libqt4-test python3-pyqt5
```

## 步驟五：安裝 MySQL/MariaDB
```bash
# 安裝 MariaDB (MySQL的開源版本)
sudo apt install -y mariadb-server mariadb-client

# 啟動並設定開機自動啟動
sudo systemctl enable mariadb
sudo systemctl start mariadb

# 執行安全設定
sudo mysql_secure_installation
```

## 步驟六：建立 Python 虛擬環境
```bash
# 建立專案目錄
mkdir ~/face_ad_system
cd ~/face_ad_system

# 建立虛擬環境
python3 -m venv face_env

# 啟動虛擬環境
source face_env/bin/activate

# 升級 pip
pip install --upgrade pip setuptools wheel
```

## 步驟七：安裝 Python 套件
```bash
# 啟動虛擬環境
source face_env/bin/activate

# 安裝必要的套件（按順序安裝以避免相依性問題）
pip install numpy

# 安裝 OpenCV
pip install opencv-python

# 安裝 dlib (這可能需要較長時間)
pip install dlib

# 安裝 face_recognition
pip install face-recognition

# 安裝其他必要套件
pip install mysql-connector-python
pip install pillow
pip install flask
pip install pandas
pip install imutils
```

## 步驟八：設定資料庫
```bash
# 登入 MySQL
sudo mysql -u root -p

# 建立資料庫和使用者
CREATE DATABASE face_ad_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'pi'@'localhost' IDENTIFIED BY 'raspberry';
GRANT ALL PRIVILEGES ON face_ad_system.* TO 'pi'@'localhost';
FLUSH PRIVILEGES;
EXIT;

# 匯入資料庫結構
mysql -u pi -p face_ad_system < database_schema.sql
```

## 步驟九：測試攝影機
```python
# 測試程式 test_camera.py
import cv2

cap = cv2.VideoCapture(0)
if cap.isOpened():
    print("攝影機已正確連接")
    ret, frame = cap.read()
    if ret:
        cv2.imwrite('test_image.jpg', frame)
        print("測試影像已儲存")
    cap.release()
else:
    print("攝影機連接失敗")
```

## 步驟十：效能調校
```bash
# 增加 GPU 記憶體分割
sudo nano /boot/config.txt
# 加入以下行：
# gpu_mem=128

# 調整交換檔案大小
sudo nano /etc/dphys-swapfile
# 修改 CONF_SWAPSIZE=1024

# 重新啟動
sudo reboot
```

## 故障排除

### 攝影機問題
- 確認排線連接正確（金屬接觸面朝向HDMI方向）
- 檢查 raspi-config 中 Camera 是否啟用
- 檢查 /boot/config.txt 中是否有 start_x=1

### 記憶體不足
- 關閉不必要的服務
- 調整 GPU 記憶體分割
- 使用更大的交換檔案

### 套件安裝失敗
- 確保系統已更新
- 檢查網路連接
- 逐一安裝套件而非批次安裝

### 人臉辨識速度緩慢
- 降低影像解析度
- 使用 'hog' 模型而非 'cnn'
- 考慮使用 Coral USB Accelerator

## 自動啟動設定
```bash
# 建立服務檔案
sudo nano /etc/systemd/system/face-ad-system.service
```

服務檔案內容：
```ini
[Unit]
Description=Face Recognition Ad System
After=network.target mysql.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/face_ad_system
Environment=PATH=/home/pi/face_ad_system/face_env/bin
ExecStart=/home/pi/face_ad_system/face_env/bin/python face_recognition_ad_system.py
Restart=always

[Install]
WantedBy=multi-user.target
```

啟用服務：
```bash
sudo systemctl enable face-ad-system.service
sudo systemctl start face-ad-system.service
```
"""

# 儲存安裝指南
with open('installation_guide.md', 'w', encoding='utf-8') as f:
    f.write(installation_guide)

print("安裝指南 'installation_guide.md' 已建立")

# 建立資料庫初始化 SQL 檔案
db_init_sql = """
-- 樹莓派人臉辨識廣告系統資料庫初始化
-- database_init.sql

USE face_ad_system;

-- 會員資料表
CREATE TABLE IF NOT EXISTS members (
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

-- 消費記錄表
CREATE TABLE IF NOT EXISTS purchase_history (
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

-- 廣告內容表
CREATE TABLE IF NOT EXISTS advertisements (
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
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_target (target_category, target_gender, target_age_group),
    INDEX idx_active_date (is_active, start_date, end_date)
);

-- 廣告推播記錄表
CREATE TABLE IF NOT EXISTS ad_display_log (
    log_id INT PRIMARY KEY AUTO_INCREMENT,
    member_id INT,
    ad_id INT,
    display_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    display_location VARCHAR(100) DEFAULT 'main_screen',
    display_duration INT DEFAULT 10,  -- 顯示秒數
    FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE CASCADE,
    FOREIGN KEY (ad_id) REFERENCES advertisements(ad_id) ON DELETE CASCADE,
    INDEX idx_member_time (member_id, display_time),
    INDEX idx_ad_time (ad_id, display_time)
);

-- 系統設定表
CREATE TABLE IF NOT EXISTS system_settings (
    setting_id INT PRIMARY KEY AUTO_INCREMENT,
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT,
    description VARCHAR(500),
    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 插入預設廣告資料
INSERT INTO advertisements (title, content, target_category, target_gender, target_age_group, is_active) VALUES
('新品上市 - 智慧手錶', '最新智慧手錶現正優惠中！', 'electronics', 'ALL', '20-40', TRUE),
('時尚服飾特價', '春季新款服飾全面8折', 'fashion', 'F', '18-35', TRUE),
('運動用品促銷', '運動鞋、運動服飾大特價', 'sports', 'M', '20-45', TRUE),
('美妝保養品', '頂級保養品牌限時優惠', 'beauty', 'F', '25-50', TRUE),
('家電優惠', '生活家電年終大促銷', 'appliances', 'ALL', '30-60', TRUE);

-- 插入系統設定
INSERT INTO system_settings (setting_key, setting_value, description) VALUES
('face_recognition_tolerance', '0.6', '人臉辨識容忍度'),
('ad_display_duration', '10', '廣告顯示時間（秒）'),
('camera_resolution_width', '640', '攝影機解析度寬度'),
('camera_resolution_height', '480', '攝影機解析度高度'),
('unknown_face_threshold', '5', '未知人臉觸發通用廣告的閾值');

-- 建立檢視表：會員消費統計
CREATE OR REPLACE VIEW member_purchase_summary AS
SELECT 
    m.member_id,
    m.name,
    m.gender,
    m.age_group,
    COUNT(ph.purchase_id) as total_purchases,
    SUM(ph.amount) as total_spent,
    AVG(ph.amount) as avg_purchase,
    MAX(ph.purchase_date) as last_purchase_date,
    GROUP_CONCAT(DISTINCT ph.product_category) as preferred_categories
FROM members m
LEFT JOIN purchase_history ph ON m.member_id = ph.member_id
WHERE m.is_active = TRUE
GROUP BY m.member_id;

-- 建立檢視表：廣告效果統計
CREATE OR REPLACE VIEW ad_performance AS
SELECT 
    a.ad_id,
    a.title,
    a.target_category,
    a.target_gender,
    a.target_age_group,
    COUNT(adl.log_id) as display_count,
    COUNT(DISTINCT adl.member_id) as unique_viewers,
    AVG(adl.display_duration) as avg_display_duration,
    DATE(adl.display_time) as display_date
FROM advertisements a
LEFT JOIN ad_display_log adl ON a.ad_id = adl.ad_id
WHERE a.is_active = TRUE
GROUP BY a.ad_id, DATE(adl.display_time);

COMMIT;
"""

with open('database_init.sql', 'w', encoding='utf-8') as f:
    f.write(db_init_sql)

print("資料庫初始化檔案 'database_init.sql' 已建立")

print("\n所有設定和程式碼檔案建立完成！")