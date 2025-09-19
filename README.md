# Raspberry-Pi-5-2

## 測試指令

- `make test`：使用預設的 pytest 指令快速驗證程式碼。
- `pytest -q`：直接執行測試套件，適合 CI 或手動檢查。

## .env 設定支援

主程式 `face_recognition_ad_system.py` 現在會自動讀取 `.env` 檔案，
可透過以下環境變數覆寫預設值：

- FACE_AD_DB_HOST / DB_HOST
- FACE_AD_DB_USER / DB_USER
- FACE_AD_DB_PASSWORD / DB_PASSWORD
- FACE_AD_DB_NAME / DB_NAME
- FACE_AD_DB_PORT / DB_PORT
- FACE_AD_CAMERA_SOURCE / CAMERA_SOURCE
- FACE_AD_CAMERA_WIDTH / CAMERA_WIDTH
- FACE_AD_CAMERA_HEIGHT / CAMERA_HEIGHT
- FACE_AD_CAMERA_FPS / CAMERA_FPS
- FACE_AD_RECOGNITION_TOLERANCE / RECOGNITION_TOLERANCE
- FACE_AD_RECOGNITION_MODEL / RECOGNITION_MODEL

將 `.env` 檔案放在專案根目錄即可被自動載入，也可以透過
環境變數 `FACE_AD_ENV_FILE` 指定不同位置的設定檔。
