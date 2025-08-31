# TikZ Generator

本项目使用 **Qwen2.5-VL** 模型 + **TikzDocument** 实现从图片自动生成/修复 LaTeX (TikZ) 代码。  
代码分为两个部分：

- `util/latex_utils.py` ：包含核心函数  
  - `generate_and_repair` —— 根据图片和描述生成并递归修复 LaTeX 代码  
  - `compile_and_save` —— 将生成的 LaTeX 编译为 PDF/PNG，并保存日志  
- `test/generate.py` ：主脚本，读取数据集并调用上述函数进行处理  
- `config.yaml` ：配置文件，统一管理模型路径、数据集路径和输出目录

---

## 环境准备

1. 创建并激活虚拟环境：
   ```bash
   conda create -n svgenv python=3.10 -y
   conda activate svgenv
    ```

	2.	安装依赖：
```
pip install torch transformers pillow tqdm automatikz pyyaml
```

其中 automatikz 是提供 TikzDocument 的库，需要你本地已有或可安装；pyyaml 用于加载配置文件。

---

项目结构

```
.
├── config.yaml            # 配置文件
├── test
│   └── generate.py        # 主运行脚本
└── util
    └── latex_utils.py     # 工具函数
```

---

## 配置文件说明

config.yaml 示例：
```
model:
  model_path: /mnt/data/model/Qwen2.5-VL-7B-Instruct
  device: cuda
  dtype: auto

data:
  metadata_path: ../save_eval/datikz_test_data/test_metadata.json
  base_dir: ../save_eval

gen:
  temperature: 0.7
  max_new_tokens: 1024

run:
  max_attempts: 3
  limit: 5   # 仅处理前 5 个样本，设为 null 或删除该项则处理全部

outputs:
  json_dir: output/original-output-inputwithimg
  tex_dir: output/output-tex-inputwithimg
  pdf_dir: save/pdf
  png_dir: save/png
  log_dir: save/log
```

可以根据实际环境修改 model_path、metadata_path、base_dir 和输出目录。

---

## 使用方法

### 1. 在根目录下运行

推荐用 模块运行方式：

```
python -m test.generate
```

这样可以确保 from util.latex_utils import ... 导入正常。
如果直接运行 python test/generate.py，需要在脚本里手动修改 sys.path。

### 2. YAML 控制运行参数

脚本会自动读取根目录下的 config.yaml，你可以修改其中的参数来控制：
	•	模型路径、设备（CPU/GPU）
	•	数据集路径
	•	生成参数（temperature, max_new_tokens）
	•	修复尝试次数、样本数量限制
	•	输出目录

---

## 脚本逻辑
	•	自动加载模型：config.yaml 中的 model.model_path
	•	读取数据集：config.yaml 中的 data.metadata_path
	•	遍历指定数量样本（run.limit），调用 generate_and_repair 生成 LaTeX
	•	将结果保存到以下目录：
	•	outputs.json_dir/*.json
	•	outputs.tex_dir/*.tex
	•	outputs.pdf_dir/*.pdf
	•	outputs.png_dir/*.png
	•	outputs.log_dir/*.log

---

## 核心函数
	•	generate_and_repair(model, processor, image, prompt, max_attempts=5)
根据输入图像 + 描述生成 LaTeX 代码，并在编译失败时递归修复。
	•	compile_and_save(tex_code, sample_id, pdf_dir, png_dir, log_dir)
编译生成的代码，输出 PDF / PNG / 日志。

---

## 示例输出

运行后可以在 save/pdf/ 中找到生成的 PDF，在 save/png/ 中找到渲染好的图片。
同时在 output/ 目录下有对应的 JSON 和 .tex 文件，方便对比和调试。

---

## 注意事项
	•	请确保 GPU 环境可用，否则加载大模型会报错。
	•	max_attempts 参数控制修复次数，过大可能运行较慢。
	•	如果要处理完整数据集，可以在 config.yaml 中修改 run.limit。

---
