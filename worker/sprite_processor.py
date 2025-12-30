#!/usr/bin/env python3
"""
Sprite Processor - 一站式 Sprite 處理工具
整合去背景、分割、多尺寸調整功能

使用範例:
    python3 sprite_processor.py input.png
    python3 sprite_processor.py input.png --output my_sprites
    python3 sprite_processor.py input.png --distance 100 --size-ratio 0.5
"""

import os
import sys
import argparse
from pathlib import Path

# 加入這行來啟用 MPS 回退機制
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

import cv2
import torch
import numpy as np
from PIL import Image
from torchvision import transforms
from transformers import AutoModelForImageSegmentation


class IntegratedSpriteProcessor:
    """
    整合式 Sprite 處理器

    功能:
    1. BiRefNet 高精度去背景
    2. OpenCV 智能分割與合併
    3. 多尺寸調整與置中
    4. 格線偵測分割（適用於貼圖表格）
    """

    # 尺寸配置
    SIZE_PRESETS = {
        'large': (260, 280, 280),
        'medium': (220, 240, 240),
        'small': (70, 96, 74)
    }

    def __init__(self):
        """初始化處理器"""
        # 設定裝置
        if torch.backends.mps.is_available():
            self.device = 'mps'
            print("✓ 檢測到 Apple Silicon，啟用 MPS 加速")
        elif torch.cuda.is_available():
            self.device = 'cuda'
            print("✓ 檢測到 NVIDIA GPU，啟用 CUDA 加速")
        else:
            self.device = 'cpu'
            print("⚠ 使用 CPU 模式（較慢）")

        self._init_birefnet()

    def _init_birefnet(self):
        """載入 BiRefNet 模型"""
        print("正在載入 BiRefNet 模型...")
        try:
            # 使用完整版 BiRefNet 以獲得最佳去背品質 (需要 8GB+ RAM)
            self.birefnet = AutoModelForImageSegmentation.from_pretrained(
                'ZhengPeng7/BiRefNet',
                trust_remote_code=True
            )
            self.birefnet.to(self.device)
            self.birefnet.eval()
            print("✓ BiRefNet 載入成功")
        except Exception as e:
            print(f"✗ BiRefNet 載入失敗: {e}")
            raise

        self.transform_biref = transforms.Compose([
            transforms.Resize((1024, 1024)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def remove_background(self, image_path):
        """步驟 1: 去背景"""
        print("\n[步驟 1/4] 執行 BiRefNet 去背景...")
        image = Image.open(image_path).convert("RGB")
        original_size = image.size

        input_tensor = self.transform_biref(image).unsqueeze(0).to(self.device)

        with torch.no_grad():
            preds = self.birefnet(input_tensor)[-1].sigmoid().cpu()

        pred_mask = preds.squeeze()
        mask_pil = transforms.ToPILImage()(pred_mask)
        mask_pil = mask_pil.resize(original_size, Image.Resampling.LANCZOS)

        image.putalpha(mask_pil)
        print("✓ 去背景完成")
        return image, np.array(mask_pil)

    def detect_bboxes_opencv(self, alpha_channel, min_area_ratio=0.0005, max_area_ratio=0.25, alpha_threshold=50):
        """步驟 2: 偵測連通區域"""
        print("\n[步驟 2/4] 使用 OpenCV 偵測連通區域...")

        _, binary = cv2.threshold(alpha_channel, alpha_threshold, 255, cv2.THRESH_BINARY)

        kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_small, iterations=1)

        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)

        h, w = alpha_channel.shape
        min_area = w * h * min_area_ratio
        max_area = w * h * max_area_ratio

        bboxes = []
        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]

            if min_area < area < max_area:
                x = stats[i, cv2.CC_STAT_LEFT]
                y = stats[i, cv2.CC_STAT_TOP]
                bw = stats[i, cv2.CC_STAT_WIDTH]
                bh = stats[i, cv2.CC_STAT_HEIGHT]

                aspect_ratio = float(bw) / bh if bh > 0 else 0

                if 0.05 < aspect_ratio < 20.0:
                    mask = (labels == i).astype(np.uint8) * 255
                    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                    bboxes.append({
                        'bbox': [x, y, bw, bh],
                        'area': area,
                        'contour': contours[0] if contours else None,
                        'centroid': centroids[i]
                    })

        print(f"✓ 偵測到 {len(bboxes)} 個區域")
        return bboxes

    def merge_nearby_small_boxes(self, bboxes, distance_threshold=80, size_ratio_threshold=0.4):
        """步驟 3: 合併鄰近區域"""
        print(f"\n[步驟 3/4] 合併鄰近區域（距離<{distance_threshold}px, 大小比<{size_ratio_threshold}）...")

        if not bboxes:
            return []

        areas = sorted([b['area'] for b in bboxes])
        median_area = areas[len(areas) // 2]
        threshold_area = median_area * size_ratio_threshold

        large_boxes = [b for b in bboxes if b['area'] >= threshold_area]
        small_boxes = [b for b in bboxes if b['area'] < threshold_area]

        print(f"  大型區域: {len(large_boxes)}, 小型區域: {len(small_boxes)}")

        # 使用並查集（Union-Find）來追蹤哪些區域應該合併在一起
        n = len(bboxes)
        parent = list(range(n))

        def find(x):
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        # 為每個 bbox 建立索引對照
        bbox_to_idx = {id(b): i for i, b in enumerate(bboxes)}

        # 1. 先合併大型區域與附近的小型區域
        for large_box in large_boxes:
            lx, ly, lw, lh = large_box['bbox']
            lx_center = lx + lw // 2
            ly_center = ly + lh // 2
            large_idx = bbox_to_idx[id(large_box)]

            for small_box in small_boxes:
                sx, sy, sw, sh = small_box['bbox']
                sx_center = sx + sw // 2
                sy_center = sy + sh // 2

                distance = np.sqrt((lx_center - sx_center)**2 + (ly_center - sy_center)**2)

                if distance < distance_threshold:
                    small_idx = bbox_to_idx[id(small_box)]
                    union(large_idx, small_idx)

        # 2. 合併距離夠近的大型區域（解決文字+人物分離的問題）
        for i, box1 in enumerate(large_boxes):
            x1, y1, w1, h1 = box1['bbox']
            cx1, cy1 = x1 + w1 // 2, y1 + h1 // 2

            for box2 in large_boxes[i+1:]:
                x2, y2, w2, h2 = box2['bbox']
                cx2, cy2 = x2 + w2 // 2, y2 + h2 // 2

                distance = np.sqrt((cx1 - cx2)**2 + (cy1 - cy2)**2)

                if distance < distance_threshold:
                    idx1 = bbox_to_idx[id(box1)]
                    idx2 = bbox_to_idx[id(box2)]
                    union(idx1, idx2)

        # 將同一群組的 boxes 收集在一起
        groups = {}
        for i, bbox in enumerate(bboxes):
            root = find(i)
            if root not in groups:
                groups[root] = []
            groups[root].append(bbox)

        # 合併每個群組
        merged_boxes = []
        for group_boxes in groups.values():
            all_x = []
            all_y = []
            all_contours = []

            for box in group_boxes:
                x, y, w, h = box['bbox']
                all_x.extend([x, x + w])
                all_y.extend([y, y + h])
                all_contours.append(box['contour'])

            merged_x = min(all_x)
            merged_y = min(all_y)
            merged_w = max(all_x) - merged_x
            merged_h = max(all_y) - merged_y

            merged_boxes.append({
                'bbox': [merged_x, merged_y, merged_w, merged_h],
                'area': merged_w * merged_h,
                'merged_from': len(group_boxes),
                'contours': all_contours
            })

        print(f"✓ 合併後剩餘 {len(merged_boxes)} 個 sprites（從 {len(bboxes)} 個區域合併）")
        return merged_boxes

    def split_sprites(self, image_path, output_dir, distance_threshold=80,
                     size_ratio_threshold=0.4, padding=5, alpha_threshold=50,
                     min_area_ratio=0.0005, max_area_ratio=0.25):
        """執行分割流程"""
        print(f"\n{'='*60}")
        print(f"開始處理: {image_path}")
        print(f"{'='*60}")

        # 建立輸出目錄結構
        base_dir = Path(output_dir)
        original_dir = base_dir / "original_sprites"
        original_dir.mkdir(parents=True, exist_ok=True)

        # 1. 去背景
        clean_image, alpha_channel = self.remove_background(image_path)

        # 儲存去背結果
        debug_path = base_dir / "debug_background_removal.png"
        clean_image.save(debug_path)
        print(f"  已儲存去背圖: {debug_path}")

        # 2. 偵測 bboxes
        bboxes = self.detect_bboxes_opencv(alpha_channel, min_area_ratio, max_area_ratio, alpha_threshold)

        # 3. 合併小型 boxes
        merged_boxes = self.merge_nearby_small_boxes(
            bboxes,
            distance_threshold=distance_threshold,
            size_ratio_threshold=size_ratio_threshold
        )

        # 4. 提取並儲存 sprites
        print(f"\n[步驟 4/4] 提取並儲存 sprites...")
        base_name = Path(image_path).stem

        # 視覺化
        img_bgr = cv2.cvtColor(np.array(clean_image.convert("RGB")), cv2.COLOR_RGB2BGR)
        vis = img_bgr.copy()

        sprite_paths = []
        for i, box_data in enumerate(merged_boxes):
            x, y, w, h = box_data['bbox']

            # 添加 padding
            x_start = max(0, x - padding)
            y_start = max(0, y - padding)
            x_end = min(clean_image.width, x + w + padding)
            y_end = min(clean_image.height, y + h + padding)

            # 裁切 sprite
            sprite_crop = clean_image.crop((x_start, y_start, x_end, y_end))

            # 儲存
            filename = f"sprite_{i:03d}.png"
            save_path = original_dir / filename
            sprite_crop.save(save_path)
            sprite_paths.append(save_path)

            # 視覺化
            color = (0, 255, 0) if box_data.get('merged_from', 1) > 1 else (255, 0, 0)
            cv2.rectangle(vis, (x, y), (x + w, y + h), color, 2)

            if box_data.get('merged_from', 1) > 1:
                cv2.putText(vis, f"M{box_data['merged_from']}", (x, y - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

            print(f"  ✓ {filename} ({w}×{h})")

        # 儲存視覺化
        vis_path = base_dir / "detection_visualization.jpg"
        cv2.imwrite(str(vis_path), vis)
        print(f"\n✓ 分割完成，共 {len(merged_boxes)} 個 sprites")
        print(f"  視覺化: {vis_path}")

        return sprite_paths, original_dir

    def resize_sprites(self, sprite_dir, output_base_dir, size_configs=None):
        """調整 sprites 尺寸"""
        print(f"\n{'='*60}")
        print("開始調整尺寸...")
        print(f"{'='*60}")

        if size_configs is None:
            size_configs = self.SIZE_PRESETS

        sprite_files = sorted([f for f in Path(sprite_dir).glob("*.png")])

        if not sprite_files:
            print("找不到 sprite 檔案")
            return

        for size_name, (max_size, canvas_w, canvas_h) in size_configs.items():
            print(f"\n處理尺寸: {size_name} (max_side={max_size}, canvas={canvas_w}×{canvas_h})")

            output_dir = Path(output_base_dir) / size_name
            output_dir.mkdir(parents=True, exist_ok=True)

            for sprite_file in sprite_files:
                try:
                    image = Image.open(sprite_file)

                    if image.mode != 'RGBA':
                        image = image.convert('RGBA')

                    # 調整大小並置中
                    processed = self._resize_and_center(image, max_size, canvas_w, canvas_h)

                    output_path = output_dir / sprite_file.name
                    processed.save(output_path, 'PNG')

                    print(f"  ✓ {sprite_file.name}")

                except Exception as e:
                    print(f"  ✗ 處理 {sprite_file.name} 失敗: {e}")

            print(f"✓ 完成 {size_name} 尺寸 → {output_dir}")

        print(f"\n✓ 所有尺寸調整完成")

    def _resize_and_center(self, image, max_size, canvas_width, canvas_height):
        """調整圖片大小並置中"""
        orig_width, orig_height = image.size
        longer_side = max(orig_width, orig_height)

        if longer_side > max_size:
            scale = max_size / longer_side
            new_width = int(orig_width * scale)
            new_height = int(orig_height * scale)
        else:
            new_width = orig_width
            new_height = orig_height

        resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        canvas = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))

        x_offset = (canvas_width - new_width) // 2
        y_offset = (canvas_height - new_height) // 2

        canvas.paste(resized, (x_offset, y_offset), resized)

        return canvas

    # ==================== 格線分割功能 ====================

    def _cluster_lines(self, positions, distance_threshold):
        """將相近的線條位置聚合"""
        if not positions:
            return []

        positions = sorted(set(positions))
        clusters = []
        current_cluster = [positions[0]]

        for pos in positions[1:]:
            if pos - current_cluster[-1] <= distance_threshold:
                current_cluster.append(pos)
            else:
                clusters.append(int(np.mean(current_cluster)))
                current_cluster = [pos]

        clusters.append(int(np.mean(current_cluster)))
        return clusters

    def detect_grid_lines(self, image_path, line_threshold=50, min_line_length_ratio=0.3,
                         edge_margin=10, cluster_distance=20):
        """
        偵測圖片中的格線
        Detect grid lines in image

        Args:
            image_path: 輸入圖片路徑
            line_threshold: Hough 線偵測閾值
            min_line_length_ratio: 最小線長度比例（相對於圖片寬/高）
            edge_margin: 邊緣忽略距離
            cluster_distance: 線條聚合距離

        Returns:
            (horizontal_lines, vertical_lines): 水平和垂直線的 y/x 座標列表
        """
        print("\n[格線偵測] 分析圖片結構...")

        # 讀取圖片
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"無法讀取圖片: {image_path}")

        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 邊緣偵測
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)

        # 形態學操作增強線條
        kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
        kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25))

        # 分別偵測水平和垂直線
        horizontal_edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel_h)
        vertical_edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel_v)

        # 使用 HoughLinesP 偵測線段
        min_line_length_h = int(w * min_line_length_ratio)
        min_line_length_v = int(h * min_line_length_ratio)

        h_lines = cv2.HoughLinesP(horizontal_edges, 1, np.pi/180, line_threshold,
                                   minLineLength=min_line_length_h, maxLineGap=50)
        v_lines = cv2.HoughLinesP(vertical_edges, 1, np.pi/180, line_threshold,
                                   minLineLength=min_line_length_v, maxLineGap=50)

        # 提取水平線的 y 座標
        horizontal_positions = []
        if h_lines is not None:
            for line in h_lines:
                x1, y1, x2, y2 = line[0]
                # 確認是水平線（角度接近 0 度）
                if abs(y2 - y1) < 20:
                    y_avg = (y1 + y2) // 2
                    # 忽略邊緣附近的線
                    if edge_margin < y_avg < h - edge_margin:
                        horizontal_positions.append(y_avg)

        # 提取垂直線的 x 座標
        vertical_positions = []
        if v_lines is not None:
            for line in v_lines:
                x1, y1, x2, y2 = line[0]
                # 確認是垂直線（角度接近 90 度）
                if abs(x2 - x1) < 20:
                    x_avg = (x1 + x2) // 2
                    # 忽略邊緣附近的線
                    if edge_margin < x_avg < w - edge_margin:
                        vertical_positions.append(x_avg)

        # 聚合相近的線條
        horizontal_lines = self._cluster_lines(horizontal_positions, cluster_distance)
        vertical_lines = self._cluster_lines(vertical_positions, cluster_distance)

        # 添加邊界
        horizontal_lines = [0] + horizontal_lines + [h]
        vertical_lines = [0] + vertical_lines + [w]

        print(f"  偵測到 {len(horizontal_lines)-1} 條水平分隔（{len(horizontal_lines)-2} 條內部線）")
        print(f"  偵測到 {len(vertical_lines)-1} 條垂直分隔（{len(vertical_lines)-2} 條內部線）")
        print(f"  預計格數: {(len(horizontal_lines)-1) * (len(vertical_lines)-1)}")

        return horizontal_lines, vertical_lines

    def detect_grid_by_color_diff(self, image_path, sample_size=5, diff_threshold=30):
        """
        透過顏色差異偵測格線（備用方法）
        Detect grid by color difference (backup method)

        適用於格線不明顯但格子顏色差異大的情況

        Args:
            image_path: 輸入圖片路徑
            sample_size: 採樣大小
            diff_threshold: 顏色差異閾值
        """
        print("\n[格線偵測] 使用顏色差異分析...")

        img = cv2.imread(image_path)
        h, w = img.shape[:2]

        # 計算每列的顏色變化
        col_diffs = []
        for x in range(1, w):
            diff = np.mean(np.abs(img[:, x].astype(float) - img[:, x-1].astype(float)))
            col_diffs.append(diff)

        # 計算每行的顏色變化
        row_diffs = []
        for y in range(1, h):
            diff = np.mean(np.abs(img[y, :].astype(float) - img[y-1, :].astype(float)))
            row_diffs.append(diff)

        # 找出差異峰值
        col_diffs = np.array(col_diffs)
        row_diffs = np.array(row_diffs)

        # 使用閾值找出分隔線位置
        vertical_lines = [0] + [i+1 for i in range(len(col_diffs))
                                if col_diffs[i] > diff_threshold * np.mean(col_diffs)] + [w]
        horizontal_lines = [0] + [i+1 for i in range(len(row_diffs))
                                  if row_diffs[i] > diff_threshold * np.mean(row_diffs)] + [h]

        # 聚合相近的線
        vertical_lines = self._cluster_lines(vertical_lines[1:-1], 20)
        horizontal_lines = self._cluster_lines(horizontal_lines[1:-1], 20)

        vertical_lines = [0] + vertical_lines + [w]
        horizontal_lines = [0] + horizontal_lines + [h]

        return horizontal_lines, vertical_lines

    def split_by_grid(self, image_path, output_dir, padding=2,
                      auto_detect=True, rows=None, cols=None,
                      line_threshold=50, min_line_length_ratio=0.3):
        """
        根據格線分割圖片
        Split image by grid lines

        Args:
            image_path: 輸入圖片路徑
            output_dir: 輸出目錄
            padding: 裁切時的內縮邊距（去除格線）
            auto_detect: 是否自動偵測格線
            rows: 手動指定行數（auto_detect=False 時使用）
            cols: 手動指定列數（auto_detect=False 時使用）
            line_threshold: 線偵測閾值
            min_line_length_ratio: 最小線長比例

        Returns:
            sprite_paths: 分割後的 sprite 路徑列表
        """
        print(f"\n{'='*60}")
        print(f"[格線分割模式] 處理: {image_path}")
        print(f"{'='*60}")

        # 建立輸出目錄
        base_dir = Path(output_dir)
        original_dir = base_dir / "original_sprites"
        original_dir.mkdir(parents=True, exist_ok=True)

        # 讀取圖片
        img = Image.open(image_path)
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        w, h = img.size

        if auto_detect:
            # 自動偵測格線
            try:
                h_lines, v_lines = self.detect_grid_lines(
                    image_path,
                    line_threshold=line_threshold,
                    min_line_length_ratio=min_line_length_ratio
                )

                # 如果偵測結果太少，嘗試備用方法
                if len(h_lines) <= 2 or len(v_lines) <= 2:
                    print("  線條偵測結果不佳，嘗試顏色差異分析...")
                    h_lines, v_lines = self.detect_grid_by_color_diff(image_path)

            except Exception as e:
                print(f"  自動偵測失敗: {e}")
                if rows and cols:
                    print(f"  使用手動指定: {rows}x{cols}")
                    h_lines = [int(i * h / rows) for i in range(rows + 1)]
                    v_lines = [int(i * w / cols) for i in range(cols + 1)]
                else:
                    raise ValueError("自動偵測失敗且未指定 rows/cols")
        else:
            # 使用手動指定的行列數
            if not rows or not cols:
                raise ValueError("非自動模式需要指定 rows 和 cols")
            h_lines = [int(i * h / rows) for i in range(rows + 1)]
            v_lines = [int(i * w / cols) for i in range(cols + 1)]
            print(f"  使用手動分割: {rows} 行 x {cols} 列")

        # 分割圖片
        sprite_paths = []
        sprite_idx = 0
        num_rows = len(h_lines) - 1
        num_cols = len(v_lines) - 1

        print(f"\n[分割] 切割成 {num_rows} x {num_cols} = {num_rows * num_cols} 格...")

        # 建立視覺化圖片
        vis_img = cv2.imread(image_path)

        for row in range(num_rows):
            for col in range(num_cols):
                y1, y2 = h_lines[row], h_lines[row + 1]
                x1, x2 = v_lines[col], v_lines[col + 1]

                # 添加內縮（去除格線邊緣）
                y1_crop = min(y1 + padding, y2)
                y2_crop = max(y2 - padding, y1)
                x1_crop = min(x1 + padding, x2)
                x2_crop = max(x2 - padding, x1)

                # 確保有效尺寸
                if x2_crop <= x1_crop or y2_crop <= y1_crop:
                    continue

                # 裁切
                sprite = img.crop((x1_crop, y1_crop, x2_crop, y2_crop))

                # 儲存
                filename = f"sprite_{sprite_idx:03d}.png"
                save_path = original_dir / filename
                sprite.save(save_path)
                sprite_paths.append(save_path)

                # 視覺化標記
                cv2.rectangle(vis_img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(vis_img, str(sprite_idx), (x1 + 5, y1 + 25),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                print(f"  ✓ {filename} (row={row}, col={col}, size={x2_crop-x1_crop}x{y2_crop-y1_crop})")
                sprite_idx += 1

        # 儲存視覺化
        vis_path = base_dir / "grid_detection_visualization.jpg"
        cv2.imwrite(str(vis_path), vis_img)

        print(f"\n✓ 格線分割完成，共 {len(sprite_paths)} 個 sprites")
        print(f"  視覺化: {vis_path}")

        return sprite_paths, original_dir

    def process_grid(self, input_image, output_dir="output_processed",
                     auto_detect=True, rows=None, cols=None,
                     padding=2, line_threshold=50, min_line_length_ratio=0.3,
                     output_sizes=None):
        """
        格線分割完整處理流程
        Full grid-based processing pipeline

        Args:
            input_image: 輸入圖片路徑
            output_dir: 輸出目錄
            auto_detect: 是否自動偵測格線
            rows: 手動指定行數
            cols: 手動指定列數
            padding: 裁切內縮邊距
            line_threshold: 線偵測閾值
            min_line_length_ratio: 最小線長比例
            output_sizes: 輸出尺寸設定 (dict: name -> (max_size, w, h))
        """
        print(f"\n{'#'*60}")
        print(f"# Sprite Processor - 格線分割模式")
        print(f"{'#'*60}")

        # 執行格線分割
        sprite_paths, original_dir = self.split_by_grid(
            input_image,
            output_dir,
            padding=padding,
            auto_detect=auto_detect,
            rows=rows,
            cols=cols,
            line_threshold=line_threshold,
            min_line_length_ratio=min_line_length_ratio
        )

        # 執行尺寸調整
        self.resize_sprites(original_dir, output_dir, size_configs=output_sizes)

        # 輸出總結
        print(f"\n{'='*60}")
        print(f"格線分割處理完成！")
        print(f"{'='*60}")
        print(f"輸出目錄: {output_dir}/")
        print(f"  ├── original_sprites/  ({len(sprite_paths)} 個原始 sprites)")
        
        # 顯示輸出的尺寸目錄
        sizes = output_sizes if output_sizes else self.SIZE_PRESETS
        for size_name, (max_s, w, h) in sizes.items():
            print(f"  ├── {size_name:<18} ({len(sprite_paths)} 個 {w}x{h}, max={max_s})")

        print(f"  └── grid_detection_visualization.jpg")
        print(f"{'='*60}\n")

        return len(sprite_paths)

    def process(self, input_image, output_dir="output_processed",
                distance_threshold=80, size_ratio_threshold=0.4,
                alpha_threshold=50, min_area_ratio=0.0005, max_area_ratio=0.25,
                output_sizes=None):
        """
        完整處理流程

        Args:
            input_image: 輸入圖片路徑
            output_dir: 輸出目錄
            distance_threshold: 合併距離閾值
            size_ratio_threshold: 大小區分閾值
            alpha_threshold: Alpha 通道二值化閾值
            min_area_ratio: 最小面積比例
            max_area_ratio: 最大面積比例
            output_sizes: 輸出尺寸設定 (dict: name -> (max_size, w, h))
        """
        print(f"\n{'#'*60}")
        print(f"# Sprite Processor - 一站式處理工具")
        print(f"{'#'*60}")

        # 執行分割
        sprite_paths, original_dir = self.split_sprites(
            input_image,
            output_dir,
            distance_threshold=distance_threshold,
            size_ratio_threshold=size_ratio_threshold,
            alpha_threshold=alpha_threshold,
            min_area_ratio=min_area_ratio,
            max_area_ratio=max_area_ratio
        )

        # 執行尺寸調整
        self.resize_sprites(original_dir, output_dir, size_configs=output_sizes)

        # 輸出總結
        print(f"\n{'='*60}")
        print(f"處理完成！")
        print(f"{'='*60}")
        print(f"輸出目錄: {output_dir}/")
        print(f"  ├── original_sprites/  ({len(sprite_paths)} 個原始 sprites)")
        
        # 顯示輸出的尺寸目錄
        sizes = output_sizes if output_sizes else self.SIZE_PRESETS
        for size_name, (max_s, w, h) in sizes.items():
            print(f"  ├── {size_name:<18} ({len(sprite_paths)} 個 {w}x{h}, max={max_s})")

        print(f"  ├── debug_background_removal.png")
        print(f"  └── detection_visualization.jpg")
        print(f"{'='*60}\n")

        return len(sprite_paths)

    def process_directory(self, input_dir, output_base_dir="output_batch",
                         distance_threshold=80, size_ratio_threshold=0.4,
                         alpha_threshold=50, min_area_ratio=0.0005, max_area_ratio=0.25,
                         output_sizes=None):
        """
        批次處理整個目錄

        Args:
            input_dir: 輸入目錄路徑
            output_base_dir: 輸出基礎目錄
            distance_threshold: 合併距離閾值
            size_ratio_threshold: 大小區分閾值
            alpha_threshold: Alpha 通道二值化閾值
            min_area_ratio: 最小面積比例
            max_area_ratio: 最大面積比例
            output_sizes: 輸出尺寸設定 (dict: name -> (max_size, w, h))
        """
        input_path = Path(input_dir)
        output_path = Path(output_base_dir)

        if not input_path.exists():
            print(f"錯誤: 找不到輸入目錄 '{input_dir}'")
            return

        # 支援的圖片格式
        image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp'}

        # 遞迴尋找所有圖片
        image_files = []
        for ext in image_extensions:
            image_files.extend(input_path.rglob(f'*{ext}'))
            image_files.extend(input_path.rglob(f'*{ext.upper()}'))

        if not image_files:
            print(f"在 '{input_dir}' 中找不到圖片檔案")
            return

        print(f"\n{'#'*60}")
        print(f"# 批次處理模式")
        print(f"{'#'*60}")
        print(f"輸入目錄: {input_dir}")
        print(f"輸出目錄: {output_base_dir}")
        print(f"找到 {len(image_files)} 個圖片檔案")
        print(f"{'#'*60}\n")

        total_sprites = 0
        processed_count = 0
        failed_files = []

        for idx, image_file in enumerate(image_files, 1):
            # 計算相對路徑
            rel_path = image_file.relative_to(input_path)
            rel_dir = rel_path.parent
            file_stem = image_file.stem

            # 建立對應的輸出目錄
            # 結構: output_base_dir / 相對目錄 / 檔案名稱 / ...
            output_dir = output_path / rel_dir / file_stem

            print(f"\n{'='*60}")
            print(f"[{idx}/{len(image_files)}] 處理: {rel_path}")
            print(f"{'='*60}")

            try:
                # 處理單一圖片
                sprite_count = self.process(
                    str(image_file),
                    str(output_dir),
                    distance_threshold=distance_threshold,
                    size_ratio_threshold=size_ratio_threshold,
                    alpha_threshold=alpha_threshold,
                    min_area_ratio=min_area_ratio,
                    max_area_ratio=max_area_ratio,
                    output_sizes=output_sizes
                )

                total_sprites += sprite_count
                processed_count += 1

            except KeyboardInterrupt:
                print("\n\n使用者中斷批次處理")
                raise
            except Exception as e:
                print(f"\n✗ 處理失敗: {e}")
                failed_files.append((str(rel_path), str(e)))
                continue

        # 最終總結
        print(f"\n{'#'*60}")
        print(f"# 批次處理完成")
        print(f"{'#'*60}")
        print(f"成功處理: {processed_count}/{len(image_files)} 個檔案")
        print(f"總共產生: {total_sprites} 個 sprites")

        if failed_files:
            print(f"\n失敗的檔案 ({len(failed_files)}):")
            for file_path, error in failed_files:
                print(f"  ✗ {file_path}")
                print(f"    原因: {error}")

        print(f"\n輸出位置: {output_base_dir}")
        print(f"{'#'*60}\n")


def parse_sizes_arg(sizes_str):
    """
    解析尺寸參數字串
    Format: name:max:w:h,name2:max:w:h
    Example: large:260:280:280,custom:100:100:100
    """
    if not sizes_str:
        return None
        
    sizes = {}
    try:
        for item in sizes_str.split(','):
            parts = item.split(':')
            if len(parts) != 4:
                raise ValueError(f"Invalid format for size item: {item}")
            
            name = parts[0]
            max_size = int(parts[1])
            w = int(parts[2])
            h = int(parts[3])
            
            sizes[name] = (max_size, w, h)
        return sizes
    except Exception as e:
        print(f"Error parsing sizes argument: {e}")
        print("Format should be: name:max_size:width:height,name2:...")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='一站式 Sprite 處理工具：去背景 → 分割 → 多尺寸調整',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用範例:
  單一檔案處理:
    %(prog)s input.png
    %(prog)s input.png --output my_output
    %(prog)s input.png --distance 100 --size-ratio 0.5

  自訂輸出尺寸:
    %(prog)s input.png --sizes "icon:64:64:64,card:200:200:300"

  批次處理目錄:
    %(prog)s --batch input_dir
    %(prog)s --batch input_dir --output output_dir
    %(prog)s --batch ART_ASSETS --output processed_sprites
        """
    )

    parser.add_argument(
        'input_image',
        nargs='?',
        help='輸入圖片路徑（單一檔案模式）'
    )
    parser.add_argument(
        '--batch', '-b',
        metavar='DIR',
        help='批次處理模式：處理指定目錄下所有圖片'
    )
    parser.add_argument(
        '--output', '-o',
        help='輸出目錄 (單一檔案預設: output_processed, 批次預設: output_batch)'
    )
    parser.add_argument(
        '--distance',
        type=int,
        default=80,
        help='小區域合併到大區域的最大距離（像素），預設: 80'
    )
    parser.add_argument(
        '--size-ratio',
        type=float,
        default=0.4,
        help='區分大小區域的面積比例閾值，預設: 0.4'
    )
    parser.add_argument(
        '--alpha-threshold',
        type=int,
        default=50,
        help='Alpha 通道二值化閾值（0-255），較低值可偵測更透明的區域，預設: 50'
    )
    parser.add_argument(
        '--min-area-ratio',
        type=float,
        default=0.0005,
        help='最小面積比例閾值，過濾掉太小的區域，預設: 0.0005'
    )
    parser.add_argument(
        '--max-area-ratio',
        type=float,
        default=0.25,
        help='最大面積比例閾值，過濾掉太大的區域，預設: 0.25'
    )
    parser.add_argument(
        '--sizes',
        help='自訂輸出尺寸 (格式: name:max_size:width:height,name2:...)，例如: large:260:280:280,icon:64:64:64'
    )

    args = parser.parse_args()

    # 檢查模式
    if args.batch and args.input_image:
        print("錯誤: 不能同時使用單一檔案模式和批次模式")
        print("請使用 --batch DIR 進行批次處理，或直接指定檔案進行單一處理")
        sys.exit(1)

    if not args.batch and not args.input_image:
        parser.print_help()
        sys.exit(1)
        
    # 解析尺寸參數
    output_sizes = parse_sizes_arg(args.sizes)

    try:
        # 建立處理器
        processor = IntegratedSpriteProcessor()

        if args.batch:
            # 批次處理模式
            if not os.path.exists(args.batch):
                print(f"錯誤: 找不到輸入目錄 '{args.batch}'")
                sys.exit(1)

            output_dir = args.output if args.output else 'output_batch'

            processor.process_directory(
                args.batch,
                output_dir,
                distance_threshold=args.distance,
                size_ratio_threshold=args.size_ratio,
                alpha_threshold=args.alpha_threshold,
                min_area_ratio=args.min_area_ratio,
                max_area_ratio=args.max_area_ratio,
                output_sizes=output_sizes
            )
        else:
            # 單一檔案模式
            if not os.path.exists(args.input_image):
                print(f"錯誤: 找不到輸入圖片 '{args.input_image}'")
                sys.exit(1)

            output_dir = args.output if args.output else 'output_processed'

            processor.process(
                args.input_image,
                output_dir,
                distance_threshold=args.distance,
                size_ratio_threshold=args.size_ratio,
                alpha_threshold=args.alpha_threshold,
                min_area_ratio=args.min_area_ratio,
                max_area_ratio=args.max_area_ratio,
                output_sizes=output_sizes
            )

    except KeyboardInterrupt:
        print("\n\n使用者中斷")
        sys.exit(1)
    except Exception as e:
        print(f"\n錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
