# 在樹莓派5安裝 GitHub 自架 Runner（self-hosted）

1. 在你的 GitHub 專案頁 → **Settings → Actions → Runners → New self-hosted runner**。
2. 選 `Linux`、`ARM64`，複製指令到樹莓派終端機執行，例：
   ```bash
   mkdir -p ~/actions-runner && cd ~/actions-runner
   curl -o actions-runner-linux-arm64-<VER>.tar.gz -L https://github.com/actions/runner/releases/download/v<VER>/actions-runner-linux-arm64-<VER>.tar.gz
   tar xzf actions-runner-linux-arm64-<VER>.tar.gz
   ./config.sh --url https://github.com/<OWNER>/<REPO> --token <TOKEN>
   sudo ./svc.sh install
   sudo ./svc.sh start
   ```
3. 在 Runner 設定時加上 **labels**：`linux, arm64, rpi5`（或修改 workflow 的 `runs-on` 以你設定的 labels 為準）。
4. 接好相機（`libcamera-hello` 能正常）後，在 GitHub → Actions 觸發 `pi-stability-30min` 工作流。
