import os
import shutil
from celery import Celery
from sprite_processor import IntegratedSpriteProcessor

# 定義 Celery App
app = Celery(
    "tasks",
    broker=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
)

# 全域變數，確保 Worker 啟動後只載入一次模型
processor = None

# 共享目錄設定 (必須與 docker-compose 和 api 一致)
SHARED_DIR = "/app/data"
RESULT_DIR = os.path.join(SHARED_DIR, "results")
TEMP_DIR = os.path.join(SHARED_DIR, "temp_processing")

@app.task(bind=True, name="tasks.process_sprite")
def process_sprite(self, input_path, task_id):
    """
    處理 Sprite 的 Celery 任務
    """
    global processor
    
    # 懶加載模型 (Lazy Loading)
    if processor is None:
        print("Initializing Sprite Processor Model...")
        # 這裡會觸發 BiRefNet 下載與載入
        processor = IntegratedSpriteProcessor()
        print("Model Initialized.")
    
    # 設定本次任務的輸出路徑
    task_output_dir = os.path.join(TEMP_DIR, task_id)
    os.makedirs(task_output_dir, exist_ok=True)
    
    try:
        print(f"Processing task {task_id} for image {input_path}")
        
        # 呼叫原始的核心邏輯
        count = processor.process(
            input_image=input_path,
            output_dir=task_output_dir,
            distance_threshold=80, # 可參數化
            size_ratio_threshold=0.4
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
        # 讓任務失敗，這樣 API 可以查到錯誤
        self.retry(exc=e, countdown=10, max_retries=1)
        
    finally:
        # 清理暫存的解壓縮/處理資料夾 (保留原始上傳與最終 Zip)
        if os.path.exists(task_output_dir):
            shutil.rmtree(task_output_dir)
