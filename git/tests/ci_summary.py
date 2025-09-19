#!/usr/bin/env python3
# tests/ci_summary.py
# Parse logs in ./logs and write a Markdown summary to $GITHUB_STEP_SUMMARY
import os, re, statistics, sys, pathlib, io

LOG_DIR = pathlib.Path("logs")
summary_path = os.environ.get("GITHUB_STEP_SUMMARY")

def read_lines(p):
    try:
        return p.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return []

def parse_fps(lines):
    fps_vals = []
    for ln in lines:
        # Matches "FPS~ 12.3" or "FPS=12.3" or "FPS= 12.3"
        m = re.search(r"FPS[~=:\s]+([0-9]+\.[0-9]+|[0-9]+)", ln)
        if m:
            try: fps_vals.append(float(m.group(1)))
            except: pass
    if fps_vals:
        return {
            "count": len(fps_vals),
            "avg": statistics.mean(fps_vals),
            "min": min(fps_vals),
            "max": max(fps_vals),
            "p95": statistics.quantiles(fps_vals, n=20)[-1] if len(fps_vals)>=20 else max(fps_vals)
        }
    return None

def parse_acc(lines):
    acc = None
    for ln in lines[::-1]:
        m = re.search(r"ACC\s*=\s*([0-9]*\.?[0-9]+)", ln)
        if m:
            try:
                acc = float(m.group(1))
                break
            except: pass
    return acc

def parse_api_latency(lines):
    # lines like: "/detect_face faces=1 time=0.123s"
    vals = []
    for ln in lines:
        m = re.search(r"time=([0-9]*\.?[0-9]+)\s*s", ln)
        if m:
            try: vals.append(float(m.group(1)))
            except: pass
    if vals:
        return {
            "count": len(vals),
            "avg": statistics.mean(vals),
            "min": min(vals),
            "max": max(vals),
            "p95": statistics.quantiles(vals, n=20)[-1] if len(vals)>=20 else max(vals)
        }
    return None

def parse_e2e(lines):
    heartbeats = sum(1 for ln in lines if "E2E heartbeat" in ln or "push ad" in ln)
    return {"heartbeats": heartbeats}

def parse_pi_monitor(lines):
    # Parse last [MON] line for TEMP/CPU/MEM/THR
    last = None
    for ln in lines:
        if "[MON]" in ln:
            last = ln
    if not last:
        return None
    out = {}
    for key in ["TEMP","CPU%","MEM%","THR","FPS"]:
        m = re.search(key+r"\s*=\s*([^\s]+)", last)
        if m:
            out[key] = m.group(1)
    return out

def md_table(headers, rows):
    md = "| " + " | ".join(headers) + " |\n"
    md += "| " + " | ".join("---" for _ in headers) + " |\n"
    for r in rows:
        md += "| " + " | ".join(str(x) for x in r) + " |\n"
    return md



# ---------- Thresholds & gating (can be overridden by env) ----------
MIN_FPS = float(os.environ.get("THRESH_MIN_FPS", "10"))          # e.g., >10
MIN_ACC = float(os.environ.get("THRESH_MIN_ACC", "0.80"))        # e.g., >=0.80
MAX_API_P95 = float(os.environ.get("THRESH_MAX_API_P95", "1.0")) # e.g., <1.0s
MIN_E2E_HEARTBEATS = int(os.environ.get("THRESH_E2E_MIN_HEARTBEATS", "1"))

def badge(ok):
    return "✅ PASS" if ok else "❌ FAIL"


def main():
    parts = []
    parts.append("# ✅ Test Summary\n")

    # cam.log
    cam_p = LOG_DIR/"cam.log"
    if cam_p.exists():
        fps = parse_fps(read_lines(cam_p))
        if fps:
            parts.append("## Camera FPS (`cam.log`)")
            parts.append(md_table(["samples","avg","p95","min","max"], [[fps["count"], f'{fps["avg"]:.1f}', f'{fps["p95"]:.1f}', f'{fps["min"]:.1f}', f'{fps["max"]:.1f}']]))
            parts.append("")

    # cam_stable.log
    cam_stable_p = LOG_DIR/"cam_stable.log"
    if cam_stable_p.exists():
        lines = read_lines(cam_stable_p)
        fps = parse_fps(lines) or {}
        mon = parse_pi_monitor(lines) or {}
        parts.append("## 30‑min Stability (`cam_stable.log`)")
        rows = [["samples", fps.get("count",0), "avgFPS", f'{fps.get("avg",0):.1f}', "p95", f'{fps.get("p95",0):.1f}']]
        parts.append(md_table(["key","val","key","val","key","val"], rows))
        if mon:
            parts.append(f"- Last monitor: `TEMP={mon.get('TEMP','?')}C`, `CPU%={mon.get('CPU%','?')}`, `MEM%={mon.get('MEM%','?')}`, `THR={mon.get('THR','?')}`, `FPS={mon.get('FPS','?')}`")
        parts.append("")

    # id_test.log
    id_p = LOG_DIR/"id_test.log"
    if id_p.exists():
        acc = parse_acc(read_lines(id_p))
        if acc is not None:
            parts.append("## Face ID Accuracy (`id_test.log`)")
            parts.append(md_table(["ACC"], [[f"{acc:.3f}"]]))
            parts.append("")

    # api_test.log
    api_p = LOG_DIR/"api_test.log"
    if api_p.exists():
        lat = parse_api_latency(read_lines(api_p))
        if lat:
            parts.append("## API Latency (`api_test.log`)")
            parts.append(md_table(["samples","avg(s)","p95(s)","min(s)","max(s)"], [[lat["count"], f'{lat["avg"]:.3f}', f'{lat["p95"]:.3f}', f'{lat["min"]:.3f}', f'{lat["max"]:.3f}']]))
            parts.append("")

    # e2e.log
    e2e_p = LOG_DIR/"e2e.log"
    if e2e_p.exists():
        e2e = parse_e2e(read_lines(e2e_p))
        parts.append("## E2E (`e2e.log`)")
        parts.append(f"- Heartbeats (or pushes): **{e2e['heartbeats']}**")
        parts.append("")

    # ---------- Gating results ----------
    failures = []

    # Gate cam.log FPS
    if cam_p.exists():
        fps = parse_fps(read_lines(cam_p))
        if fps and fps.get("avg", 0) < MIN_FPS:
            failures.append(f"Camera FPS avg {fps.get('avg',0):.1f} < MIN_FPS {MIN_FPS}")

    # Gate cam_stable.log FPS
    if cam_stable_p.exists():
        fps2 = parse_fps(read_lines(cam_stable_p))
        if fps2 and fps2.get("avg", 0) < MIN_FPS:
            failures.append(f"Stability FPS avg {fps2.get('avg',0):.1f} < MIN_FPS {MIN_FPS}")

    # Gate id_test.log ACC
    if id_p.exists():
        acc = parse_acc(read_lines(id_p))
        if acc is not None and acc < MIN_ACC:
            failures.append(f"Accuracy ACC {acc:.3f} < MIN_ACC {MIN_ACC}")

    # Gate api_test.log latency p95
    if api_p.exists():
        lat = parse_api_latency(read_lines(api_p))
        if lat and lat.get("p95", 0) > MAX_API_P95:
            failures.append(f"API p95 {lat.get('p95',0):.3f}s > MAX_API_P95 {MAX_API_P95}s")

    # Gate e2e heartbeats
    if e2e_p.exists():
        e = parse_e2e(read_lines(e2e_p))
        if e.get("heartbeats", 0) < MIN_E2E_HEARTBEATS:
            failures.append(f"E2E heartbeats {e.get('heartbeats',0)} < MIN_E2E_HEARTBEATS {MIN_E2E_HEARTBEATS}")

    # Add final status section
    parts.append("## Build Gate")
    parts.append(md_table(["Metric","Threshold","Status"], [
        ["Cam avg FPS", f">= {MIN_FPS}", badge(not cam_p.exists() or (parse_fps(read_lines(cam_p)) or {}).get("avg",0) >= MIN_FPS)],
        ["Stable avg FPS", f">= {MIN_FPS}", badge(not cam_stable_p.exists() or (parse_fps(read_lines(cam_stable_p)) or {}).get("avg",0) >= MIN_FPS)],
        ["Accuracy ACC", f">= {MIN_ACC}", badge(not id_p.exists() or (parse_acc(read_lines(id_p)) or 0) >= MIN_ACC)],
        ["API p95 (s)", f"<= {MAX_API_P95}", badge(not api_p.exists() or (parse_api_latency(read_lines(api_p)) or {}).get("p95",0) <= MAX_API_P95)],
        ["E2E heartbeats", f">= {MIN_E2E_HEARTBEATS}", badge(not e2e_p.exists() or (parse_e2e(read_lines(e2e_p)) or {}).get("heartbeats",0) >= MIN_E2E_HEARTBEATS)],
    ]))
    parts.append("")

    md = "\n".join(parts) if parts else "No logs found."

    # If any gating failures, exit 1 to fail the workflow
    if failures:
        fail_md = "**❌ FAILED GATES:**\\n- " + "\\n- ".join(failures)
        if summary_path:
            with open(summary_path, "a", encoding="utf-8") as f:
                f.write(fail_md + "\\n")
        else:
            print(fail_md)
        # ensure non-zero exit
        sys.exit(1)

    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write(md+"\n")
    else:
        print(md)

if __name__ == "__main__":
    main()
