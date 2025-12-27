# Sprite Service | 自動化 Sprite 處理服務

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[English Documentation](#english-documentation) | [繁體中文說明](#繁體中文說明)

---

## English Documentation

### 1. Overview
**Sprite Service** is a microservice-based application designed to automate the processing of game assets (sprites). It leverages AI to remove backgrounds, intelligently splits connected regions into individual sprites, and resizes them into multiple standard formats.

The project features a secure **Backend-for-Frontend (BFF)** architecture, where the core API is isolated from the public network and accessible only through a secure Nuxt 3 frontend gateway.

### 2. Key Features
*   **AI Background Removal**: Uses **BiRefNet (Lite)** for high-precision, edge-preserving background removal (optimized for low-memory environments).
*   **Smart Splitting**: Automatically detects and separates multiple sprite elements from a single source image using OpenCV.
*   **Multi-Size Generation**: Auto-resizes sprites into standard presets (Large, Medium, Small) with proper centering and padding.
*   **Secure Architecture**:
    *   **BFF Pattern**: The Python API is hidden inside the Docker network.
    *   **Proxy Gateway**: All external requests go through the Nuxt 3 frontend.
*   **User-Friendly Interface**: Modern Web UI built with **Nuxt UI** supporting drag-and-drop uploads and real-time status polling.
*   **Asynchronous Processing**: Uses **Celery + Redis** to handle heavy image processing tasks in the background without blocking the UI.

### 3. System Architecture

```mermaid
graph LR
    User[Browser] -- Port 3000 --> Frontend[Nuxt 3 Frontend]
    subgraph "Internal Docker Network"
        Frontend -- Proxy Request --> API[Python FastAPI]
        API -- Enqueue Task --> Redis[(Redis)]
        Worker[Celery Worker] -- Dequeue Task --> Redis
        Worker -- Save Result --> SharedVol[Shared Volume]
    end
```

### 4. Tech Stack
*   **Frontend**: Nuxt 3, Nuxt UI, TypeScript, Tailwind CSS.
*   **Backend API**: Python 3.9, FastAPI/Uvicorn.
*   **Worker**: Celery, PyTorch, BiRefNet (HuggingFace), OpenCV.
*   **Infrastructure**: Podman/Docker Compose.

### 5. Getting Started

#### Prerequisites
*   **Podman** (recommended) or **Docker**.
*   **Podman Compose** or **Docker Compose**.
*   Git.

#### Installation & Running
1.  **Clone the repository**:
    ```bash
    git clone <repository_url>
    cd sprite_service
    ```

2.  **Start Services**:
    ```bash
    # Using Podman
    podman-compose up -d --build

    # Using Docker
    docker-compose up -d --build
    ```
    *Note: The first launch will download the AI model and base images, which may take a few minutes.*

3.  **Access the Application**:
    *   Open your browser and navigate to: **http://localhost:3000**
    *   (The internal API at port 8000 is intentionally unreachable directly).

### 6. Development Guide

#### Directory Structure
```
sprite_service/
├── api/                # FastAPI Backend Service
├── worker/             # Celery Worker (AI Processing)
│   ├── checkpoints/    # Model weights
│   └── sprite_processor.py # Core logic
├── frontend/           # Nuxt 3 Frontend Application
├── docker-compose.yml  # Container Orchestration
└── api_test_script.py  # Automation Test Script
```

#### Running Tests
An automated script is provided to verify the full pipeline (upload -> process -> download):
```bash
python3 api_test_script.py
```

#### Troubleshooting
*   **Memory Issues**: The worker is configured to use `BiRefNet_lite` to run efficiently on 4GB RAM environments (like default Podman machines).
*   **Connection Refused**: Ensure you are accessing port `3000`, not `8000`.

---

## 繁體中文說明

### 1. 專案概述
**Sprite Service** 是一個基於微服務架構的自動化圖像處理系統，專為遊戲開發資產 (Sprite) 設計。它利用 AI 技術自動移除背景、智慧切割連通區域，並將圖片輸出為多種標準尺寸。

本專案採用安全的 **Backend-for-Frontend (BFF)** 架構，核心 API 隱藏於內部網路，僅能透過 Nuxt 3 前端介面進行存取，確保系統安全性。

### 2. 功能特色
*   **AI 智慧去背**: 採用 **BiRefNet (Lite)** 模型，提供高精度的邊緣去背能力（已針對低記憶體環境最佳化）。
*   **智慧切割**: 使用 OpenCV 自動偵測並分離單張圖片中的多個 Sprite 元素。
*   **多尺寸輸出**: 自動將切割後的 Sprite 調整為標準尺寸 (大/中/小) 並置中補白。
*   **安全架構**:
    *   **BFF 模式**: Python API 隱藏於 Docker 內部網路，不對外公開。
    *   **代理閘道**: 所有外部請求皆需經過 Nuxt 3 前端進行驗證與轉發。
*   **現代化介面**: 使用 **Nuxt UI** 打造的 Web 介面，支援拖曳上傳與即時進度顯示。
*   **非同步處理**: 使用 **Celery + Redis** 佇列處理耗時的影像運算，確保介面操作流暢。

### 3. 系統架構

| 服務組件 | 技術堆疊 | 說明 |
| :--- | :--- | :--- |
| **Frontend** | Nuxt 3, Vue 3 | 提供使用者介面與 API 安全代理 (Port 3000)。 |
| **API** | Python FastAPI | 接收內部請求並派發任務 (內部 Port 8000)。 |
| **Worker** | Celery, PyTorch | 執行實際的 AI 去背與影像處理運算。 |
| **Broker** | Redis | 負責任務排程與狀態同步。 |

### 4. 快速開始

#### 事前準備
*   安裝 **Podman** (推薦 macOS 使用) 或 **Docker**。
*   安裝 **Podman Compose** 或 **Docker Compose**。
*   安裝 Git。

#### 安裝與執行
1.  **取得專案代碼**:
    ```bash
    git clone <repository_url>
    cd sprite_service
    ```

2.  **啟動服務**:
    ```bash
    # 使用 Podman
    podman-compose up -d --build

    # 使用 Docker
    docker-compose up -d --build
    ```
    *注意：首次啟動需要下載 AI 模型與基礎映像檔，可能需要 5-10 分鐘。*

3.  **使用服務**:
    *   開啟瀏覽器並前往: **http://localhost:3000**
    *   (基於安全考量，Port 8000 的 API 無法直接連線，請務必透過前端操作)。

### 5. 開發指南

#### 專案結構說明
```
sprite_service/
├── api/                # FastAPI 後端服務 (僅限內部存取)
├── worker/             # Celery Worker (核心 AI 處理邏輯)
│   ├── checkpoints/    # 模型權重檔
│   └── sprite_processor.py # 影像處理核心程式碼
├── frontend/           # Nuxt 3 前端應用程式 (包含 UI 與 Server Proxy)
├── docker-compose.yml  # 容器編排設定檔
└── api_test_script.py  # 自動化測試腳本
```

#### 測試方式
專案內附帶一個自動化測試腳本，可用於驗證完整流程 (上傳 -> 處理 -> 下載)：
```bash
python3 api_test_script.py
```
該腳本會透過前端 API (Port 3000) 發送請求，模擬真實使用者行為。

#### 常見問題排除
*   **記憶體不足 (OOM)**: Worker 已設定使用 `BiRefNet_lite` 輕量版模型，可於 4GB RAM 的環境 (如預設的 Podman Machine) 穩定執行。
*   **無法連線到 API**: 這是正常的安全設計。請不要嘗試連線 `localhost:8000`，所有請求都應發送至 `localhost:3000`。
