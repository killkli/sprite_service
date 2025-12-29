"""
Image Generator Module - 圖片生成模組
Wrapper for Google Nano Banana Pro API (Gemini Image Generation)
"""

import os
from typing import Optional
from PIL import Image
from google import genai
from google.genai import types


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
        """
        初始化 API 客戶端
        Initialize API client
        """
        # 支援兩種環境變數名稱
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY environment variable not set")
        self.client = genai.Client(api_key=api_key)

    def generate(
        self,
        prompt: str,
        model: str = "nano-banana",
        number_of_images: int = 1,
        temperature: float = 1.0
    ) -> list[Image.Image]:
        """
        從文字 prompt 生成圖片
        Generate images from text prompt

        Args:
            prompt: 文字描述 / Text description
            model: 模型名稱 / Model name ("nano-banana" or "nano-banana-pro")
            number_of_images: 生成圖片數量 / Number of images to generate
            temperature: 生成溫度 (0.0-2.0) / Generation temperature (0.0-2.0)
                         較低值產生更一致的結果，較高值產生更多變化
                         Lower values produce more consistent results, higher values more variation

        Returns:
            List of PIL Image objects
        """
        model_id = self.MODELS.get(model, self.MODELS["nano-banana"])

        # 為 Sprite 生成優化 prompt
        # Optimize prompt for sprite generation
        optimized_prompt = self._optimize_prompt_for_sprite(prompt)

        print(f"[ImageGen] Calling API with model={model_id}, temp={temperature}, prompt={optimized_prompt[:50]}...")

        response = self.client.models.generate_content(
            model=model_id,
            contents=[optimized_prompt],
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
                temperature=temperature
            )
        )

        print(f"[ImageGen] Response received. Type: {type(response)}")

        images = []

        # 嘗試從 response.parts 取得圖片
        if hasattr(response, 'parts') and response.parts:
            print(f"[ImageGen] Found {len(response.parts)} parts in response.parts")
            for i, part in enumerate(response.parts):
                has_text = hasattr(part, 'text') and part.text
                has_data = hasattr(part, 'inline_data') and part.inline_data is not None
                print(f"[ImageGen]   Part {i}: text={has_text}, inline_data={has_data}")
                if has_data:
                    images.append(part.as_image())
        else:
            print(f"[ImageGen] No parts in response.parts")

        # 備用：從 candidates 取得圖片
        if not images and hasattr(response, 'candidates') and response.candidates:
            print(f"[ImageGen] Checking candidates ({len(response.candidates)} found)")
            for ci, candidate in enumerate(response.candidates):
                print(f"[ImageGen]   Candidate {ci}: finish_reason={candidate.finish_reason}")
                if candidate.content and candidate.content.parts:
                    print(f"[ImageGen]   Candidate {ci} has {len(candidate.content.parts)} parts")
                    for pi, part in enumerate(candidate.content.parts):
                        has_data = hasattr(part, 'inline_data') and part.inline_data is not None
                        print(f"[ImageGen]     Part {pi}: inline_data={has_data}")
                        if has_data:
                            images.append(part.as_image())
                else:
                    print(f"[ImageGen]   Candidate {ci}: no content or parts")

        print(f"[ImageGen] Total images extracted: {len(images)}")

        if not images:
            # 提供更詳細的錯誤訊息
            error_msg = "No image generated from API."
            if hasattr(response, 'candidates') and response.candidates:
                finish_reason = response.candidates[0].finish_reason
                error_msg += f" Finish reason: {finish_reason}"
                # 嘗試取得文字回應
                if response.candidates[0].content and response.candidates[0].content.parts:
                    for part in response.candidates[0].content.parts:
                        if hasattr(part, 'text') and part.text:
                            error_msg += f" Response text: {part.text[:200]}"
            raise ValueError(error_msg)

        return images[:number_of_images]

    def edit(
        self,
        image: Image.Image,
        instruction: str,
        model: str = "nano-banana",
        temperature: float = 1.0
    ) -> Image.Image:
        """
        編輯現有圖片
        Edit existing image with instruction

        Args:
            image: 要編輯的圖片 / Image to edit
            instruction: 編輯指令 / Edit instruction
            model: 模型名稱 / Model name
            temperature: 生成溫度 (0.0-2.0) / Generation temperature (0.0-2.0)

        Returns:
            Edited PIL Image object
        """
        model_id = self.MODELS.get(model, self.MODELS["nano-banana"])

        response = self.client.models.generate_content(
            model=model_id,
            contents=[image, instruction],
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
                temperature=temperature
            )
        )

        for part in response.parts:
            if part.inline_data is not None:
                return part.as_image()

        raise ValueError("No image generated from edit")

    def _optimize_prompt_for_sprite(self, prompt: str) -> str:
        """
        優化 prompt 以生成適合 Sprite 處理的圖片
        Optimize prompt for sprite-friendly image generation

        Args:
            prompt: 原始 prompt / Original prompt

        Returns:
            優化後的 prompt / Optimized prompt
        """
        # 檢查是否已包含關鍵字
        # Check if prompt already contains key terms
        prompt_lower = prompt.lower()

        additions = []

        # 建議加入透明背景
        if "transparent" not in prompt_lower and "background" not in prompt_lower:
            additions.append("with transparent or solid color background")

        # 建議加入清晰邊緣
        if "sprite" not in prompt_lower and "game" not in prompt_lower:
            additions.append("game sprite style")

        # 建議清晰分離
        if "isolated" not in prompt_lower and "separate" not in prompt_lower:
            additions.append("clearly isolated elements")

        if additions:
            return f"{prompt}, {', '.join(additions)}"

        return prompt
