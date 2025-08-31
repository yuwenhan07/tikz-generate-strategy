# test/generate.py
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
from PIL import Image
import os
import json
import traceback
from tqdm import tqdm
import torch
import yaml
from util.repair_strategy import generate_and_repair
from util.save_and_complie import compile_and_save



def load_config(cfg_path: str = "config.yaml") -> dict:
    if not os.path.exists(cfg_path):
        raise FileNotFoundError(f"未找到配置文件：{cfg_path}")
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    # 给一些可选项设默认值
    cfg.setdefault("model", {})
    cfg["model"].setdefault("device", "cuda")
    cfg["model"].setdefault("dtype", "auto")

    cfg.setdefault("data", {})
    if "metadata_path" not in cfg["data"] or "base_dir" not in cfg["data"]:
        raise ValueError("config.yaml 中 data.metadata_path / data.base_dir 不能为空")

    cfg.setdefault("gen", {})
    cfg["gen"].setdefault("temperature", 0.7)
    cfg["gen"].setdefault("max_new_tokens", 1024)

    cfg.setdefault("run", {})
    cfg["run"].setdefault("max_attempts", 3)
    # limit 可以为 None
    cfg["run"].setdefault("limit", None)

    cfg.setdefault("outputs", {})
    cfg["outputs"].setdefault("json_dir", "output/original-output-inputwithimg")
    cfg["outputs"].setdefault("tex_dir", "output/output-tex-inputwithimg")
    cfg["outputs"].setdefault("pdf_dir", "save/pdf")
    cfg["outputs"].setdefault("png_dir", "save/png")
    cfg["outputs"].setdefault("log_dir", "save/log")
    return cfg


def ensure_dirs(*paths: str):
    for p in paths:
        os.makedirs(p, exist_ok=True)


def main(cfg_path: str = "config.yaml"):
    # 载入配置
    cfg = load_config(cfg_path)
    model_path = cfg["model"]["model_path"]
    device = cfg["model"]["device"]
    dtype = cfg["model"]["dtype"]

    metadata_path = cfg["data"]["metadata_path"]
    base_dir = cfg["data"]["base_dir"]

    temperature = cfg["gen"]["temperature"]
    max_new_tokens = cfg["gen"]["max_new_tokens"]

    max_attempts = cfg["run"]["max_attempts"]
    limit = cfg["run"]["limit"]

    out_json = cfg["outputs"]["json_dir"]
    out_tex  = cfg["outputs"]["tex_dir"]
    out_pdf  = cfg["outputs"]["pdf_dir"]
    out_png  = cfg["outputs"]["png_dir"]
    out_log  = cfg["outputs"]["log_dir"]

    # 1. 加载模型和处理器
    try:
        print("正在加载模型和处理器...")
        # dtype “auto” 就按字符串传递；transformers 会接受 "auto"
        model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            model_path,
            torch_dtype=dtype
        ).to(device)
        processor = AutoProcessor.from_pretrained(model_path)
        print(f"模型加载成功，设备：{model.device}")
    except Exception as e:
        print(f"模型加载失败：{e}")
        traceback.print_exc()
        return

    # 2. 读取数据集
    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    except Exception as e:
        print(f"读取metadata失败：{e}")
        return

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
    ensure_dirs(out_tex, out_json, out_pdf, out_png, out_log)

    # 4. 主循环
    skip_list = []
    try:
        iterable = ds if limit in (None, 0) else ds[:int(limit)]
        for i, example in enumerate(tqdm(iterable, desc="Processing samples")):
            print(f"\n====== 处理样本 {i} ======")
            image = example["image"]
            prompt = example["caption"]

            # 生成+修复（按 YAML 中的参数调整）
            final_doc, all_attempts = generate_and_repair(
                model=model,
                processor=processor,
                image=image,
                prompt=prompt,
                max_attempts=max_attempts,
                return_all=True
            )

            result = {
                "prompt": prompt,
                "final_latex_code": getattr(final_doc, "code", "") if final_doc is not None else "",
                "compiled_successfully": getattr(final_doc, "has_content", False) if final_doc is not None else False,
                "ground_truth": example["code"],
                "attempts": len(all_attempts),
                # 也可以在 util 里暴露 temperature / max_new_tokens，以便记录
                "temperature": temperature,
                "max_new_tokens": max_new_tokens,
                "max_attempts": max_attempts
            }

            # 保存 JSON
            with open(os.path.join(out_json, f"sample_img_{i}.json"), "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            # 保存 TeX / PDF / PNG / LOG
            if final_doc is not None:
                with open(os.path.join(out_tex, f"sample_img_{i}.tex"), "w", encoding="utf-8") as tex_file:
                    tex_file.write(getattr(final_doc, "code", ""))
                print(f"样本 {i} 处理完成，尝试次数：{len(all_attempts)}，编译成功：{getattr(final_doc, 'has_content', False)}")
                compile_and_save(getattr(final_doc, "code", ""), i, out_pdf, out_png, out_log)
            else:
                skip_list.append(i)
                print(f"样本 {i} 处理失败，尝试次数：{len(all_attempts)}，返回结果为 None")
    except Exception as e:
        print(f"主循环出错：{e}")
        traceback.print_exc()

    print(f"============ 所有跳过的条目 {skip_list} ==================")


if __name__ == "__main__":
    # 推荐从项目根目录运行（确保包导入路径正确）：
    #   python -m test.generate
    #
    # 如需指定其他配置文件路径，可改成：
    #   main("path/to/your_config.yaml")
    main("yaml/config.yaml")