# Android App 設定指南

## 環境需求

| 需求 | 最低版本 | 狀態 |
|------|----------|------|
| Android SDK | 35 | ✅ 已安裝 |
| Java JDK | 17+ | ✅ 已安裝 (OpenJDK 17.0.17) |
| Gradle Wrapper | 8.9 | ✅ 已設定 |

## 設定狀態總結

| 項目 | 狀態 | 說明 |
|------|------|------|
| Android SDK | ✅ | `/Users/johnchen/Library/Android/sdk` |
| Java 17 | ✅ | OpenJDK 17.0.17 via Homebrew |
| Gradle Wrapper | ✅ | 版本 8.9 |
| local.properties | ✅ | 已設定 SDK 路徑和 API URL |
| google-services.json | ⚠️ | Placeholder（可編譯，Firebase 功能需真實設定檔） |
| Debug APK | ✅ | 建置成功 |

## 快速開始

專案已完整設定，可直接開發：

```bash
cd /Users/johnchen/AICoding/homm3-like/utils/sprite_service/android_app

# 建置 Debug APK
./gradlew assembleDebug

# APK 輸出位置
# app/build/outputs/apk/debug/app-debug.apk

# 安裝到裝置
./gradlew installDebug
```

## 使用 Android Studio 開啟

1. 開啟 Android Studio
2. File > Open > 選擇 `/Users/johnchen/AICoding/homm3-like/utils/sprite_service/android_app`
3. 等待 Gradle sync 完成
4. 點擊 Run 按鈕或按 Shift+F10

## Firebase 設定（可選）

目前使用 placeholder 設定檔，Firebase 功能（認證、Analytics）無法使用。

### 正式設定步驟
1. 前往 [Firebase Console](https://console.firebase.google.com/)
2. 建立新專案或選擇現有專案
3. 新增 Android 應用程式:
   - Package name: `com.spriteservice`
   - Debug package name: `com.spriteservice.debug`
4. 下載 `google-services.json` 並取代 `app/google-services.json`

### 啟用認證方式
在 Firebase Console > Authentication > Sign-in method:
- 啟用 Email/Password
- 啟用 Google (需要 SHA-1 憑證)

取得 SHA-1：
```bash
./gradlew signingReport
```

## Google Play Billing 設定（可選）

如果要啟用訂閱功能：

1. 在 Google Play Console 建立應用程式
2. 設定訂閱產品：
   - `sprite_basic_monthly` - 基礎月訂閱
   - `sprite_pro_monthly` - 專業月訂閱
3. 上傳測試版 APK
4. 設定測試帳戶

## 常見問題

### Q: Gradle sync 失敗 - "Unsupported class file major version"
確認使用 Java 17+：
```bash
java -version
echo $JAVA_HOME
```

### Q: 重新載入 Shell 環境
```bash
source ~/.zshrc
```

### Q: Firebase 連線失敗
取代 placeholder `google-services.json` 為真實的設定檔。

## 環境變數設定（已完成）

以下設定已加入 `~/.zshrc`：
```bash
export JAVA_HOME="$(/usr/libexec/java_home -v 17)"
```

## 專案建置命令

```bash
# 清理並建置
./gradlew clean assembleDebug

# 建置 Release 版本
./gradlew assembleRelease

# 執行測試
./gradlew test

# 檢查 lint
./gradlew lint
```
