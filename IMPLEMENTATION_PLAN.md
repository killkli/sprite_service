# Text-to-Sprite 功能實作計畫

## 概述

整合 Google Nano Banana Pro API，實現文字描述生成遊戲 Sprite 素材的完整流程。

## Stage 1: 基礎生成功能
**Goal**: 建立核心 AI 生成能力，使用者可輸入文字描述並生成圖片
**Success Criteria**:
- [x] `NanoBananaGenerator` 類別可成功呼叫 API 生成圖片
- [x] `/generate` 端點可接收 prompt 並回傳 task_id
- [x] 前端頁面可輸入文字並顯示生成結果
- [x] 生成的圖片可自動進入 Sprite 處理流程
**Status**: Complete

### 1.1 後端 - NanoBananaGenerator 類別

**檔案**: `worker/image_generator.py`

```python
from google import genai
from google.genai import types
from PIL import Image
import os
from typing import Optional

class NanoBananaGenerator:
    """
    封裝 Google Nano Banana Pro API
    Wrapper for Google Nano Banana Pro API
    """

    MODELS = {
        "nano-banana": "gemini-2.5-flash-image",
        "nano-banana-pro": "gemini-3-pro-image-preview"
    }

    def __init__(self):
        api_key = os.environ.get("GOOGLE_AI_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_AI_API_KEY environment variable not set")
        self.client = genai.Client(api_key=api_key)

    def generate(
        self,
        prompt: str,
        model: str = "nano-banana",
        number_of_images: int = 1
    ) -> list[Image.Image]:
        """
        從文字 prompt 生成圖片
        Generate images from text prompt
        """
        model_id = self.MODELS.get(model, self.MODELS["nano-banana"])

        response = self.client.models.generate_content(
            model=model_id,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"]
            )
        )

        images = []
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                images.append(part.as_image())

        if not images:
            raise ValueError("No image generated from API")

        return images

    def edit(
        self,
        image: Image.Image,
        instruction: str,
        model: str = "nano-banana"
    ) -> Image.Image:
        """
        編輯現有圖片
        Edit existing image with instruction
        """
        model_id = self.MODELS.get(model, self.MODELS["nano-banana"])

        response = self.client.models.generate_content(
            model=model_id,
            contents=[image, instruction],
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"]
            )
        )

        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                return part.as_image()

        raise ValueError("No image generated from edit")
```

### 1.2 後端 - Celery 任務

**檔案**: `worker/tasks.py` (新增)

```python
@app.task(bind=True, name="tasks.generate_image")
def generate_image_task(self, prompt: str, model: str = "nano-banana"):
    """
    生成圖片的 Celery 任務
    Celery task for image generation
    """
    from image_generator import NanoBananaGenerator

    generator = NanoBananaGenerator()
    task_id = self.request.id

    try:
        self.update_state(state="GENERATING", meta={"progress": 10})

        images = generator.generate(prompt, model)

        # 儲存生成的圖片
        task_output_dir = os.path.join(TEMP_DIR, task_id)
        os.makedirs(task_output_dir, exist_ok=True)

        output_path = os.path.join(task_output_dir, "generated.png")
        images[0].save(output_path, "PNG")

        self.update_state(state="GENERATED", meta={"progress": 100})

        return {
            "status": "success",
            "image_path": output_path,
            "task_id": task_id
        }
    except Exception as e:
        return {"status": "failure", "error": str(e)}


@app.task(bind=True, name="tasks.generate_and_process")
def generate_and_process_task(self, prompt: str, model: str = "nano-banana"):
    """
    一條龍任務：生成 → 去背 → 切割 → 多尺寸
    Full pipeline: Generate → Remove BG → Split → Multi-size
    """
    from image_generator import NanoBananaGenerator

    global processor
    generator = NanoBananaGenerator()
    task_id = self.request.id

    try:
        # Step 1: 生成圖片
        self.update_state(state="GENERATING", meta={"progress": 10})
        images = generator.generate(prompt, model)

        # 儲存生成的圖片
        task_output_dir = os.path.join(TEMP_DIR, task_id)
        os.makedirs(task_output_dir, exist_ok=True)
        generated_path = os.path.join(task_output_dir, "generated.png")
        images[0].save(generated_path, "PNG")

        # Step 2: Sprite 處理
        self.update_state(state="PROCESSING", meta={"progress": 50})

        if processor is None:
            processor = IntegratedSpriteProcessor()

        count = processor.process(
            input_image=generated_path,
            output_dir=task_output_dir,
            distance_threshold=80,
            size_ratio_threshold=0.4
        )

        # Step 3: 打包輸出
        self.update_state(state="PACKAGING", meta={"progress": 90})
        zip_base_name = os.path.join(RESULT_DIR, f"sprites_{task_id}")
        shutil.make_archive(zip_base_name, 'zip', task_output_dir)
        zip_path = f"{zip_base_name}.zip"

        return {
            "status": "success",
            "sprite_count": count,
            "zip_path": zip_path,
            "task_id": task_id
        }
    except Exception as e:
        return {"status": "failure", "error": str(e)}
    finally:
        if os.path.exists(task_output_dir):
            shutil.rmtree(task_output_dir)
```

### 1.3 後端 - API 端點

**檔案**: `api/main.py` (新增路由)

```python
from pydantic import BaseModel

class GenerateRequest(BaseModel):
    prompt: str
    model: str = "nano-banana"
    auto_process: bool = True  # 是否自動進入 Sprite 處理

@app.post("/generate")
async def create_generate_task(request: GenerateRequest):
    """
    建立圖片生成任務
    Create image generation task
    """
    if request.auto_process:
        task_name = "tasks.generate_and_process"
    else:
        task_name = "tasks.generate_image"

    task = celery_client.send_task(
        task_name,
        args=[request.prompt, request.model]
    )

    return {
        "task_id": task.id,
        "status": "queued",
        "message": "Generation task submitted. Check status with /status/{task_id}"
    }
```

### 1.4 前端 - Nuxt Server Route

**檔案**: `frontend/server/api/generate.post.ts`

```typescript
export default defineEventHandler(async (event) => {
  const body = await readBody(event);
  const config = useRuntimeConfig();

  const response = await $fetch(`${config.apiInternal}/generate`, {
    method: 'POST',
    body: body,
  });

  return response;
});
```

### 1.5 前端 - 生成頁面

**檔案**: `frontend/pages/generate.vue`

```vue
<template>
  <div class="container mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-8">Text to Sprite</h1>

    <!-- Prompt 輸入區 -->
    <div class="mb-6">
      <label class="block text-sm font-medium mb-2">Describe your sprite</label>
      <textarea
        v-model="prompt"
        rows="4"
        class="w-full p-3 border rounded-lg"
        placeholder="A fantasy knight sprite, pixel art style, transparent background, facing right..."
      />
    </div>

    <!-- 模型選擇 -->
    <div class="mb-6">
      <label class="block text-sm font-medium mb-2">Model</label>
      <select v-model="model" class="w-full p-2 border rounded-lg">
        <option value="nano-banana">Nano Banana (Fast)</option>
        <option value="nano-banana-pro">Nano Banana Pro (Quality)</option>
      </select>
    </div>

    <!-- 生成按鈕 -->
    <button
      @click="generate"
      :disabled="isGenerating || !prompt.trim()"
      class="w-full bg-blue-600 text-white py-3 rounded-lg disabled:opacity-50"
    >
      {{ isGenerating ? 'Generating...' : 'Generate Sprite' }}
    </button>

    <!-- 狀態顯示 -->
    <div v-if="taskId" class="mt-6 p-4 bg-gray-100 rounded-lg">
      <p>Task ID: {{ taskId }}</p>
      <p>Status: {{ status }}</p>
      <a v-if="downloadUrl" :href="downloadUrl" class="text-blue-600 underline">
        Download Result
      </a>
    </div>
  </div>
</template>

<script setup lang="ts">
const prompt = ref('');
const model = ref('nano-banana');
const taskId = ref('');
const status = ref('');
const downloadUrl = ref('');
const isGenerating = ref(false);

let pollInterval: NodeJS.Timeout | null = null;

const generate = async () => {
  isGenerating.value = true;
  status.value = 'Submitting...';

  try {
    const response = await $fetch('/api/generate', {
      method: 'POST',
      body: { prompt: prompt.value, model: model.value },
    });

    taskId.value = response.task_id;
    status.value = 'Queued';
    startPolling();
  } catch (error) {
    status.value = 'Error: ' + error.message;
    isGenerating.value = false;
  }
};

const startPolling = () => {
  pollInterval = setInterval(async () => {
    const response = await $fetch(`/api/status/${taskId.value}`);
    status.value = response.status;

    if (response.status === 'SUCCESS') {
      downloadUrl.value = `/api/download/${taskId.value}`;
      stopPolling();
    } else if (response.status === 'FAILURE') {
      stopPolling();
    }
  }, 2000);
};

const stopPolling = () => {
  if (pollInterval) {
    clearInterval(pollInterval);
    pollInterval = null;
  }
  isGenerating.value = false;
};

onUnmounted(() => stopPolling());
</script>
```

### 1.6 環境設定

**docker-compose.yml** (新增環境變數)

```yaml
services:
  api:
    environment:
      - GOOGLE_AI_API_KEY=${GOOGLE_AI_API_KEY}
  worker:
    environment:
      - GOOGLE_AI_API_KEY=${GOOGLE_AI_API_KEY}
```

**worker/requirements.txt** (新增)
```
google-genai>=1.0.0
```

---

## Stage 1.5: 參考圖片生成功能 (Image-to-Image)
**Goal**: 支援上傳參考圖片，使用 AI 根據指令修改生成新圖片
**Success Criteria**:
- [x] `/generate/with-reference` 端點可接收參考圖片和指令進行生成
- [x] 前端支援切換 Text-to-Image / Image-to-Image 模式
- [x] 參考圖片預覽與清除功能
- [x] 生成結果自動進入 Sprite 處理流程
**Status**: Complete

### 1.5.1 後端 - API 端點

**檔案**: `api/main.py`

```python
@app.post("/generate/with-reference")
async def create_generate_with_reference_task(
    prompt: str = Form(...),
    model: str = Form("nano-banana"),
    auto_process: bool = Form(True),
    reference_image: UploadFile = File(...)
):
    """
    使用參考圖片進行 Image-to-Image 生成
    """
    # 儲存參考圖片到 uploads 目錄
    # 發送任務給 Worker (tasks.generate_with_reference_and_process)
```

### 1.5.2 後端 - Celery 任務

**檔案**: `worker/tasks.py`

```python
@app.task(bind=True, name="tasks.generate_with_reference_and_process")
def generate_with_reference_and_process_task(
    self,
    reference_image_path: str,
    prompt: str,
    model: str = "nano-banana"
):
    """
    使用參考圖片生成並處理成 Sprite 的一條龍任務
    Full pipeline: Edit → Remove BG → Split → Multi-size
    """
    # 載入參考圖片
    # 使用 generator.edit() 進行 Image-to-Image 生成
    # 進入現有 Sprite 處理流程
```

### 1.5.3 前端 - UI 更新

**檔案**: `frontend/app.vue`

- 新增 `useReferenceImage` toggle 切換模式
- 新增參考圖片上傳和預覽區域
- Prompt 說明文字根據模式變化
- 生成按鈕文字根據模式變化

**檔案**: `frontend/server/api/generate/with-reference.post.ts`

- 代理 multipart form data 到內部 API

---

## Stage 1.6: 進階參數與多語系支援
**Goal**: 提供可調整的處理參數和多語系介面
**Success Criteria**:
- [x] 前端可調整生成溫度 (temperature)
- [x] 前端可調整所有 Sprite 處理參數
- [x] 參數說明以繁體中文和英文呈現
- [x] 介面支援繁體中文（預設）和英文切換
**Status**: Complete

### 1.6.1 可調整參數

**生成參數：**
- `temperature` (0.0-2.0): 控制 AI 生成結果的隨機性

**處理參數：**
- `distance_threshold` (10-500): 相鄰元素合併距離（像素）
- `size_ratio_threshold` (0.1-1.0): 元素最小大小比例
- `alpha_threshold` (1-254): Alpha 通道二值化閾值
- `min_area_ratio` (0.0001-0.1): 最小面積比例
- `max_area_ratio` (0.05-0.9): 最大面積比例

### 1.6.2 多語系支援

**設定檔：**
- `frontend/nuxt.config.ts` - 配置 @nuxtjs/i18n
- `frontend/i18n/zh-TW.json` - 繁體中文翻譯
- `frontend/i18n/en.json` - 英文翻譯

**特點：**
- 預設使用繁體中文
- 語言選擇儲存於 Cookie
- 所有參數皆有詳細說明

---

## Stage 2: 編輯與精修功能
**Goal**: 支援多輪對話式圖片編輯，使用者可迭代精修生成結果
**Success Criteria**:
- [ ] Session 機制保存對話歷史
- [ ] 前端支援多輪編輯 UI (ConversationPanel)
- [ ] 可預覽並選擇要處理的版本
**Status**: Not Started

### 待實作項目
- Session 資料結構設計 (Redis 儲存)
- `POST /generate/refine` 端點 (基於 session 繼續編輯)
- `GET /generate/session/{id}` 端點
- 前端 ConversationPanel 組件

---

## Stage 3: 優化與整合
**Goal**: 降低成本、整合訂閱系統
**Success Criteria**:
- [ ] Batch API 整合
- [ ] 訂閱方案限制 (Free/Basic/Pro)
- [ ] 使用量追蹤
**Status**: Not Started

---

## 技術決策記錄

### Model ID 選擇
根據 Google AI 2025 文件，可用的圖片生成模型：
- `gemini-2.5-flash-image` - Nano Banana (快速生成，適合大量生成)
- `gemini-3-pro-image-preview` - Nano Banana Pro (專業級，支援 4K、進階推理)

**決定**: 預設使用 `gemini-2.5-flash-image`（快速），進階使用者可選擇 Pro 版本。

### API 設計
遵循現有 BFF 模式，所有請求經由 Nuxt Server Route 代理。

### 錯誤處理
使用 Celery retry 機制，最多重試 1 次（與現有 process_sprite 一致）。
