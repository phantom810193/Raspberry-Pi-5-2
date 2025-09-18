
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
