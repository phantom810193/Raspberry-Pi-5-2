import os, cv2, time, logging, numpy as np, pathlib, subprocess

duration = int(os.getenv("DURATION_SEC", "1800"))        # 預設 30 分鐘
log_dir = pathlib.Path(os.getenv("LOG_DIR","logs")); log_dir.mkdir(parents=True, exist_ok=True)
log_path = log_dir / "cam_stable.log"
logging.basicConfig(filename=str(log_path), level=logging.INFO, format="%(asctime)s %(message)s")

cam_idx = int(os.getenv("CAMERA_INDEX","0"))             # Pi 要接實體相機→0
monitor_iv = int(os.getenv("MONITOR_INTERVAL_SEC","60")) # 每 60 秒記錄一次系統健檢

# --------- 系統監控工具 ---------
def read_soc_temp_c():
    # 1) vcgencmd (Raspberry Pi)
    try:
        out = subprocess.check_output(["vcgencmd","measure_temp"], text=True).strip()
        # e.g. temp=45.2'C
        if "temp=" in out:
            val = out.split("temp=")[1].split("'")[0]
            return float(val)
    except Exception:
        pass
    # 2) /sys/class/thermal/
    try:
        for p in ["/sys/class/thermal/thermal_zone0/temp",
                  "/sys/class/thermal/thermal_zone1/temp"]:
            if os.path.exists(p):
                with open(p) as f:
                    v = f.read().strip()
                    # some systems report in millidegree
                    val = float(v) / (1000.0 if float(v) > 200 else 1.0)
                    return val
    except Exception:
        pass
    return None

def read_throttled():
    # Pi: 0x0 means OK，非零代表曾發生降頻/欠壓等
    try:
        out = subprocess.check_output(["vcgencmd","get_throttled"], text=True).strip()
        # e.g. throttled=0x0
        return out
    except Exception:
        return None

def read_cpu_mem_usage():
    # 優先用 psutil；若未安裝則用 /proc
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory().percent
        return cpu, mem
    except Exception:
        # /proc/stat 簡易估算 CPU
        try:
            def read_stat():
                with open("/proc/stat") as f:
                    for line in f:
                        if line.startswith("cpu "):
                            parts = [float(x) for x in line.split()[1:]]
                            idle = parts[3] + parts[4]  # idle + iowait
                            total = sum(parts)
                            return idle, total
                return 0.0, 0.0
            idle1, total1 = read_stat(); time.sleep(0.1); idle2, total2 = read_stat()
            idle = idle2 - idle1; total = total2 - total1
            cpu = 0.0 if total == 0 else (1.0 - idle/total) * 100.0
        except Exception:
            cpu = None
        # Mem
        try:
            with open("/proc/meminfo") as f:
                info = {}
                for line in f:
                    k,v,*_ = line.replace("kB","").split(":")
                    info[k.strip()] = float(v.strip())
            mem = 100.0 * (1.0 - info.get("MemAvailable",0)/info.get("MemTotal",1))
        except Exception:
            mem = None
        return cpu, mem

last_mon = 0.0
def monitor_tick(frames, start_time):
    global last_mon
    now = time.time()
    if now - last_mon >= monitor_iv:
        elapsed = now - start_time
        fps = frames/elapsed if elapsed>0 else 0.0
        t = read_soc_temp_c()
        thr = read_throttled()
        cpu, mem = read_cpu_mem_usage()
        logging.info(f"[MON] ELAPSED={elapsed:.1f}s FPS={fps:.1f} TEMP={t}C CPU%={cpu} MEM%={mem} THR={thr}")
        last_mon = now

# --------- 影像擷取與穩定度測試 ---------
src = 0 if cam_idx>=0 else os.getenv("TEST_VIDEO","")
cap = cv2.VideoCapture(src) if src!="" or cam_idx>=0 else None

start=time.time(); frames=0
def report_final(frames, start):
    elapsed = time.time()-start
    fps = frames/elapsed if elapsed>0 else 0.0
    logging.info(f"[FINAL] ELAPSED={elapsed:.1f}s FRAMES={frames} FPS={fps:.1f}")

if cap is None or not cap.isOpened():
    # 無相機 fallback：合成影格（確保 CI 或開發環境不會報錯）
    while time.time()-start < duration:
        _ = np.random.randint(0,255,(480,640,3),dtype=np.uint8)
        frames += 1
        if frames % 60 == 0:  # 約每 2 秒記一筆 FPS
            elapsed = time.time()-start
            fps = frames/elapsed if elapsed>0 else 0.0
            logging.info(f"ELAPSED={elapsed:.1f}s FRAMES={frames} FPS={fps:.1f}")
        monitor_tick(frames, start)
    report_final(frames, start)
else:
    while time.time()-start < duration:
        ret,_=cap.read()
        if not ret:
            logging.info("frame read failed; retrying..."); time.sleep(0.1); continue
        frames += 1
        if frames % 300 == 0:   # 約每 10 秒一筆
            elapsed = time.time()-start
            fps = frames/elapsed if elapsed>0 else 0.0
            logging.info(f"ELAPSED={elapsed:.1f}s FRAMES={frames} FPS={fps:.1f}")
        monitor_tick(frames, start)
    cap.release()
    report_final(frames, start)

print(f"cam_stable finished; log: {log_path}")
