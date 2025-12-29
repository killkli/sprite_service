import os
import shutil
from celery import Celery
from sprite_processor import IntegratedSpriteProcessor
from image_generator import NanoBananaGenerator

# 定義 Celery App
app = Celery(
    "tasks",
    broker=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
)

# 全域變數，確保 Worker 啟動後只載入一次模型
# Global variables for lazy loading models
processor = None
generator = None

# 共享目錄設定 (必須與 docker-compose 和 api 一致)
SHARED_DIR = "/app/data"
RESULT_DIR = os.path.join(SHARED_DIR, "results")
TEMP_DIR = os.path.join(SHARED_DIR, "temp_processing")

# 預設處理參數
# Default processing parameters
DEFAULT_PROCESSING_PARAMS = {
    "distance_threshold": 80,
    "size_ratio_threshold": 0.4,
    "alpha_threshold": 50,
    "min_area_ratio": 0.0005,
    "max_area_ratio": 0.25
}


@app.task(bind=True, name="tasks.process_sprite")
def process_sprite(self, input_path, task_id, processing_params=None):
    """
    處理 Sprite 的 Celery 任務
    Celery task for sprite processing with configurable parameters
    """
    global processor

    # 合併參數 (使用者參數覆蓋預設值)
    params = {**DEFAULT_PROCESSING_PARAMS, **(processing_params or {})}

    # 懶加載模型 (Lazy Loading)
    if processor is None:
        print("Initializing Sprite Processor Model...")
        processor = IntegratedSpriteProcessor()
        print("Model Initialized.")

    # 設定本次任務的輸出路徑
    task_output_dir = os.path.join(TEMP_DIR, task_id)
    os.makedirs(task_output_dir, exist_ok=True)

    try:
        print(f"Processing task {task_id} for image {input_path}")
        print(f"Parameters: {params}")

        # 呼叫原始的核心邏輯
        count = processor.process(
            input_image=input_path,
            output_dir=task_output_dir,
            distance_threshold=params["distance_threshold"],
            size_ratio_threshold=params["size_ratio_threshold"],
            alpha_threshold=params["alpha_threshold"],
            min_area_ratio=params["min_area_ratio"],
            max_area_ratio=params["max_area_ratio"]
        )

        # 將結果打包成 Zip
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
        print(f"Error processing task {task_id}: {str(e)}")
        self.retry(exc=e, countdown=10, max_retries=1)

    finally:
        # 清理暫存的解壓縮/處理資料夾 (保留原始上傳與最終 Zip)
        if os.path.exists(task_output_dir):
            shutil.rmtree(task_output_dir)


@app.task(bind=True, name="tasks.generate_image")
def generate_image_task(
    self,
    prompt: str,
    model: str = "nano-banana",
    temperature: float = 1.0,
    processing_params=None
):
    """
    生成圖片的 Celery 任務 (僅生成，不處理)
    Celery task for image generation only (no sprite processing)
    """
    global generator

    # 懶加載生成器 (Lazy Loading)
    if generator is None:
        print("Initializing Image Generator...")
        generator = NanoBananaGenerator()
        print("Image Generator Initialized.")

    task_id = self.request.id

    try:
        print(f"Generating image for task {task_id} with prompt: {prompt[:50]}..., temp={temperature}")
        self.update_state(state="GENERATING", meta={"progress": 10})

        images = generator.generate(prompt, model, temperature=temperature)

        # 儲存生成的圖片
        task_output_dir = os.path.join(TEMP_DIR, task_id)
        os.makedirs(task_output_dir, exist_ok=True)

        output_path = os.path.join(task_output_dir, "generated.png")
        images[0].save(output_path)

        self.update_state(state="GENERATED", meta={"progress": 100})

        return {
            "status": "success",
            "image_path": output_path,
            "task_id": task_id
        }
    except Exception as e:
        print(f"Error generating image for task {task_id}: {str(e)}")
        return {"status": "failure", "error": str(e)}


@app.task(bind=True, name="tasks.generate_and_process")
def generate_and_process_task(
    self,
    prompt: str,
    model: str = "nano-banana",
    temperature: float = 1.0,
    processing_params=None
):
    """
    一條龍任務：生成 → 去背 → 切割 → 多尺寸
    Full pipeline: Generate → Remove BG → Split → Multi-size
    """
    global processor, generator

    # 合併參數
    params = {**DEFAULT_PROCESSING_PARAMS, **(processing_params or {})}

    # 懶加載生成器 (Lazy Loading)
    if generator is None:
        print("Initializing Image Generator...")
        generator = NanoBananaGenerator()
        print("Image Generator Initialized.")

    task_id = self.request.id
    task_output_dir = os.path.join(TEMP_DIR, task_id)
    os.makedirs(task_output_dir, exist_ok=True)

    try:
        # Step 1: 生成圖片
        print(f"[{task_id}] Step 1: Generating image (temp={temperature})...")
        self.update_state(state="GENERATING", meta={"progress": 10, "step": "generating"})

        images = generator.generate(prompt, model, temperature=temperature)
        generated_path = os.path.join(task_output_dir, "generated.png")
        images[0].save(generated_path)

        # Step 2: Sprite 處理 (去背 + 切割)
        print(f"[{task_id}] Step 2: Processing sprites with params: {params}")
        self.update_state(state="PROCESSING", meta={"progress": 50, "step": "processing"})

        if processor is None:
            print("Initializing Sprite Processor Model...")
            processor = IntegratedSpriteProcessor()
            print("Model Initialized.")

        count = processor.process(
            input_image=generated_path,
            output_dir=task_output_dir,
            distance_threshold=params["distance_threshold"],
            size_ratio_threshold=params["size_ratio_threshold"],
            alpha_threshold=params["alpha_threshold"],
            min_area_ratio=params["min_area_ratio"],
            max_area_ratio=params["max_area_ratio"]
        )

        # Step 3: 打包輸出
        print(f"[{task_id}] Step 3: Packaging results...")
        self.update_state(state="PACKAGING", meta={"progress": 90, "step": "packaging"})

        zip_base_name = os.path.join(RESULT_DIR, f"sprites_{task_id}")
        shutil.make_archive(zip_base_name, 'zip', task_output_dir)
        zip_path = f"{zip_base_name}.zip"

        print(f"[{task_id}] Complete! Generated {count} sprites.")

        return {
            "status": "success",
            "sprite_count": count,
            "zip_path": zip_path,
            "task_id": task_id
        }

    except Exception as e:
        print(f"Error in generate_and_process task {task_id}: {str(e)}")
        self.retry(exc=e, countdown=10, max_retries=1)

    finally:
        # 清理暫存資料夾
        if os.path.exists(task_output_dir):
            shutil.rmtree(task_output_dir)


@app.task(bind=True, name="tasks.generate_with_reference")
def generate_with_reference_task(
    self,
    reference_image_path: str,
    prompt: str,
    model: str = "nano-banana",
    temperature: float = 1.0,
    processing_params=None
):
    """
    使用參考圖片生成新圖片 (Image-to-Image，僅生成不處理)
    Generate new image using reference image (Image-to-Image, no sprite processing)
    """
    global generator
    from PIL import Image

    # 懶加載生成器 (Lazy Loading)
    if generator is None:
        print("Initializing Image Generator...")
        generator = NanoBananaGenerator()
        print("Image Generator Initialized.")

    task_id = self.request.id

    try:
        print(f"[{task_id}] Generating with reference image (temp={temperature}): {reference_image_path}")
        self.update_state(state="GENERATING", meta={"progress": 10})

        # 載入參考圖片
        reference_image = Image.open(reference_image_path)

        # 使用 edit 方法進行 Image-to-Image 生成
        result_image = generator.edit(reference_image, prompt, model, temperature=temperature)

        # 儲存生成的圖片
        task_output_dir = os.path.join(TEMP_DIR, task_id)
        os.makedirs(task_output_dir, exist_ok=True)

        output_path = os.path.join(task_output_dir, "generated.png")
        result_image.save(output_path)

        self.update_state(state="GENERATED", meta={"progress": 100})

        return {
            "status": "success",
            "image_path": output_path,
            "task_id": task_id
        }
    except Exception as e:
        print(f"Error generating with reference for task {task_id}: {str(e)}")
        return {"status": "failure", "error": str(e)}
    finally:
        # 清理參考圖片
        if os.path.exists(reference_image_path):
            os.remove(reference_image_path)


@app.task(bind=True, name="tasks.generate_with_reference_and_process")
def generate_with_reference_and_process_task(
    self,
    reference_image_path: str,
    prompt: str,
    model: str = "nano-banana",
    temperature: float = 1.0,
    processing_params=None
):
    """
    使用參考圖片生成並處理成 Sprite 的一條龍任務
    Full pipeline with reference image: Edit → Remove BG → Split → Multi-size
    """
    global processor, generator
    from PIL import Image

    # 合併參數
    params = {**DEFAULT_PROCESSING_PARAMS, **(processing_params or {})}

    # 懶加載生成器 (Lazy Loading)
    if generator is None:
        print("Initializing Image Generator...")
        generator = NanoBananaGenerator()
        print("Image Generator Initialized.")

    task_id = self.request.id
    task_output_dir = os.path.join(TEMP_DIR, task_id)
    os.makedirs(task_output_dir, exist_ok=True)

    try:
        # Step 1: 使用參考圖片生成
        print(f"[{task_id}] Step 1: Generating with reference image (temp={temperature})...")
        self.update_state(state="GENERATING", meta={"progress": 10, "step": "generating"})

        # 載入參考圖片
        reference_image = Image.open(reference_image_path)

        # 使用 edit 方法進行 Image-to-Image 生成
        result_image = generator.edit(reference_image, prompt, model, temperature=temperature)

        generated_path = os.path.join(task_output_dir, "generated.png")
        result_image.save(generated_path)

        # Step 2: Sprite 處理 (去背 + 切割)
        print(f"[{task_id}] Step 2: Processing sprites with params: {params}")
        self.update_state(state="PROCESSING", meta={"progress": 50, "step": "processing"})

        if processor is None:
            print("Initializing Sprite Processor Model...")
            processor = IntegratedSpriteProcessor()
            print("Model Initialized.")

        count = processor.process(
            input_image=generated_path,
            output_dir=task_output_dir,
            distance_threshold=params["distance_threshold"],
            size_ratio_threshold=params["size_ratio_threshold"],
            alpha_threshold=params["alpha_threshold"],
            min_area_ratio=params["min_area_ratio"],
            max_area_ratio=params["max_area_ratio"]
        )

        # Step 3: 打包輸出
        print(f"[{task_id}] Step 3: Packaging results...")
        self.update_state(state="PACKAGING", meta={"progress": 90, "step": "packaging"})

        zip_base_name = os.path.join(RESULT_DIR, f"sprites_{task_id}")
        shutil.make_archive(zip_base_name, 'zip', task_output_dir)
        zip_path = f"{zip_base_name}.zip"

        print(f"[{task_id}] Complete! Generated {count} sprites from reference image.")

        return {
            "status": "success",
            "sprite_count": count,
            "zip_path": zip_path,
            "task_id": task_id
        }

    except Exception as e:
        print(f"Error in generate_with_reference_and_process task {task_id}: {str(e)}")
        self.retry(exc=e, countdown=10, max_retries=1)

    finally:
        # 清理暫存資料夾和參考圖片
        if os.path.exists(task_output_dir):
            shutil.rmtree(task_output_dir)
        if os.path.exists(reference_image_path):
            os.remove(reference_image_path)
