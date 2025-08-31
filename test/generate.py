# main.py
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
from PIL import Image
import os
import re
import json
import traceback
from tqdm import tqdm
import torch
from typing import List, Optional, Tuple
from automatikz.infer import TikzDocument  # 导入TikzDocument类

# ✅ 只需这一行导入你拆分出去的函数
from util.repair_strategy import generate_and_repair
from util.save_and_complie import compile_and_save


def main():
    # 1. 加载模型和处理器
    try:
        print("正在加载模型和处理器...")
        model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            "/mnt/data/model/Qwen2.5-VL-7B-Instruct",
            torch_dtype="auto"
        ).to("cuda")
        processor = AutoProcessor.from_pretrained("/mnt/data/model/Qwen2.5-VL-7B-Instruct")
        print(f"模型加载成功，设备：{model.device}")
    except Exception as e:
        print(f"模型加载失败：{e}")
        traceback.print_exc()
        return

    # 2. 读取数据集
    metadata_path = "../evaluate/save_eval/datikz_test_data/test_metadata.json"
    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    except Exception as e:
        print(f"读取metadata失败：{e}")
        return

    base_dir = "../evaluate/save_eval/"
    ds = []
    for item in metadata:
        img_abs_path = os.path.join(base_dir, item["image_path"])
        if not os.path.exists(img_abs_path):
            print(f"Warning: 图片不存在 {img_abs_path}，已跳过")
            continue
        try:
            image = Image.open(img_abs_path).convert("RGB")
            ds.append({
                "image": image,
                "caption": item.get("caption", ""),
                "code": item.get("code", "")
            })
        except Exception as e:
            print(f"Error: 读取图片 {img_abs_path} 失败: {e}，已跳过")
            continue

    if len(ds) == 0:
        print("无有效样本，程序退出")
        return

    # 3. 输出目录
    output_tex_dir = "output/output-tex-inputwithimg"
    output_json_dir = "output/original-output-inputwithimg"
    save_png_dir = "save/png"
    save_pdf_dir = "save/pdf"
    save_log_dir = "save/log"
    os.makedirs(output_tex_dir, exist_ok=True)
    os.makedirs(output_json_dir, exist_ok=True)
    os.makedirs(save_pdf_dir, exist_ok=True)
    os.makedirs(save_png_dir, exist_ok=True)
    os.makedirs(save_log_dir, exist_ok=True)

    # 4. 主循环
    skip_list = []
    try:
        # 只处理前5个样本便于测试
        for i, example in enumerate(tqdm(ds[:5], desc="Processing samples")):
            print(f"\n====== 处理样本 {i} ======")
            image = example["image"]
            prompt = example["caption"]

            final_doc, all_attempts = generate_and_repair(
                model=model,
                processor=processor,
                image=image,
                prompt=prompt,
                max_attempts=3,
                return_all=True
            )

            result = {
                "prompt": prompt,
                "final_latex_code": getattr(final_doc, "code", "") if final_doc is not None else "",
                "compiled_successfully": getattr(final_doc, "has_content", False) if final_doc is not None else False,
                "ground_truth": example["code"],
                "attempts": len(all_attempts)
            }

            # 保存 JSON
            with open(f"{output_json_dir}/sample_img_{i}.json", "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            # 保存 TeX / PDF / PNG / LOG
            if final_doc is not None:
                with open(f"{output_tex_dir}/sample_img_{i}.tex", "w", encoding="utf-8") as tex_file:
                    tex_file.write(getattr(final_doc, "code", ""))
                print(f"样本 {i} 处理完成，尝试次数：{len(all_attempts)}，编译成功：{getattr(final_doc, 'has_content', False)}")
                compile_and_save(getattr(final_doc, "code", ""), i, save_pdf_dir, save_png_dir, save_log_dir)
            else:
                skip_list.append(i)
                print(f"样本 {i} 处理失败，尝试次数：{len(all_attempts)}，返回结果为 None")
    except Exception as e:
        print(f"主循环出错：{e}")
        traceback.print_exc()

    print(f"============ 所有跳过的条目 {skip_list} ==================")


if __name__ == "__main__":
    main()