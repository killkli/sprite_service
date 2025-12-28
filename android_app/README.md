# Sprite Service Android App

Android 前端應用程式，連接 Sprite Service 後端進行遊戲 Sprite 處理。

## 功能特色

- **圖片上傳處理**: 上傳圖片進行 AI 去背、智慧切割、多尺寸輸出
- **Firebase 認證**: 支援 Email/Password 和 Google 登入
- **訂閱管理**: Google Play Billing 訂閱制度
- **處理歷史**: 本地快取處理記錄

## 技術堆疊

| 組件 | 技術 |
|------|------|
| 語言 | Kotlin |
| UI | Jetpack Compose |
| 架構 | MVVM + Clean Architecture |
| DI | Hilt |
| 網路 | Retrofit + OkHttp |
| 本地儲存 | Room |
| 認證 | Firebase Auth |
| 訂閱 | Google Play Billing |

## 專案結構

```
app/src/main/java/com/spriteservice/
├── di/                    # Hilt 依賴注入模組
├── data/
│   ├── api/               # Retrofit API 定義
│   ├── repository/        # Repository 實作
│   └── local/             # Room 資料庫
├── domain/
│   ├── model/             # 領域模型
│   ├── repository/        # Repository 介面
│   └── usecase/           # 業務邏輯
├── ui/
│   ├── theme/             # Compose 主題
│   ├── auth/              # 登入/註冊
│   ├── home/              # 主畫面
│   ├── upload/            # 上傳處理
│   ├── subscription/      # 訂閱管理
│   └── components/        # 共用元件
├── MainActivity.kt
└── SpriteServiceApp.kt
```

## 環境設定

### 前置需求

- Android Studio Ladybug (2024.2.1) 或更新版本
- JDK 17
- Android SDK 35
- Kotlin 2.0+

### 設定步驟

1. **複製 local.properties 模板**
   ```bash
   cp local.properties.template local.properties
   ```

2. **設定 Android SDK 路徑**
   ```properties
   sdk.dir=/path/to/your/Android/Sdk
   ```

3. **設定 Firebase**
   - 在 Firebase Console 建立專案
   - 下載 `google-services.json` 到 `app/` 目錄
   - 啟用 Authentication (Email/Password, Google)

4. **設定 API Base URL**
   在 `local.properties` 加入:
   ```properties
   API_BASE_URL=https://your-api-domain.com
   ```

## 建置與執行

```bash
# 建置 Debug 版本
./gradlew assembleDebug

# 建置 Release 版本
./gradlew assembleRelease

# 執行測試
./gradlew test
```

## 訂閱方案

| 方案 | 每日限制 | 功能 |
|------|----------|------|
| Free | 3 次 | 基本尺寸、有浮水印 |
| Basic | 30 次 | 全尺寸、無浮水印 |
| Pro | 無限 | 批次處理、優先佇列、API 存取 |

## 開發指南

### 代碼風格

- 使用 `ktlint` 進行代碼格式化
- 遵循 [Kotlin 官方代碼風格](https://kotlinlang.org/docs/coding-conventions.html)
- 註解使用雙語 (English + 繁體中文)

### 提交規範

遵循 Conventional Commits:
- `feat:` 新功能
- `fix:` 錯誤修復
- `docs:` 文件更新
- `refactor:` 重構
- `test:` 測試

## 授權

MIT License
