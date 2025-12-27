# Sprite Service with Podman

本專案已配置為支援 Podman 與 Docker。

## 快速開始 (使用 Podman)

### 1. 確保 Podman Machine 運作中
macOS 需要運行 Podman 虛擬機：
```bash
# 檢查狀態
podman machine list

# 如果未啟動
podman machine start

# 如果遇到連線錯誤 (Connection Refused)，嘗試重啟：
podman machine stop && podman machine start
```

### 2. 驗證 Podman 連線
執行以下指令，確保 CLI 能連線到虛擬機：
```bash
podman ps
```
如果看到標題列 (CONTAINER ID...) 即表示連線正常。

### 3. 啟動服務
使用 `podman-compose` 啟動服務。
```bash
cd sprite_service
podman-compose up --build
```
*注意：第一次啟動需要下載基礎映像檔與 PyTorch，可能需要 5-10 分鐘。*

### 4. 服務端點
- **API**: http://localhost:8000
  - POST `/process`: 上傳圖片
  - GET `/status/{task_id}`: 查詢進度
  - GET `/download/{task_id}`: 下載結果
- **Redis**: localhost:6379

## 常見問題

### Podman Socket 連線失敗
如果 `podman-compose` 報錯 `unable to connect to Podman socket`，請嘗試匯出 `DOCKER_HOST` 變數（路徑可能因機器而異，請參考 `podman machine start` 的輸出）：
```bash
export DOCKER_HOST='unix:///var/folders/YOUR_PATH/T/podman/podman-machine-default-api.sock'
podman-compose up --build
```
