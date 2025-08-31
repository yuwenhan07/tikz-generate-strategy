好的 ✅ 下面就是一个完整的 Markdown 格式 的 README.md 文件，你可以直接保存为 README.md 使用：

# TikZ Generator

本项目使用 **Qwen2.5-VL** 模型 + **TikzDocument** 实现从图片自动生成/修复 LaTeX (TikZ) 代码。  
代码分为两个部分：

- `util/latex_utils.py` ：包含核心函数  
  - `generate_and_repair` —— 根据图片和描述生成并递归修复 LaTeX 代码  
  - `compile_and_save` —— 将生成的 LaTeX 编译为 PDF/PNG，并保存日志  
- `test/generate.py` ：主脚本，读取数据集并调用上述函数进行处理

---

## 环境准备

1. 创建并激活虚拟环境（可选）：
   ```bash
   conda create -n svgenv python=3.10 -y
   conda activate svgenv
    ```
2.	安装依赖：

```
pip install torch transformers pillow tqdm automatikz
```
其中 automatikz 是提供 TikzDocument 的库，需要你本地已有或可安装。

---

## 项目结构

```
.
├── test
│   └── generate.py        # 主运行脚本
└── util
    └── latex_utils.py     # 工具函数
```

---

## 使用方法

### 1. 在根目录下运行

推荐用 模块运行方式：
```
python -m test.generate
```

这样可以确保 `from util.latex_utils import ...` 导入正常。
如果直接运行 `python test/generate.py`，需要在脚本里手动修改 `sys.path`。

### 2. 脚本逻辑
	•	自动加载模型：`/mnt/data/model/Qwen2.5-VL-7B-Instruct`
	•	读取数据集：`../save_eval/datikz_test_data/test_metadata.json`
	•	遍历前 5 个样本，调用 `generate_and_repair` 生成 LaTeX
	•	将结果保存到以下目录：
    ```
	•	output/original-output-inputwithimg/*.json
	•	output/output-tex-inputwithimg/*.tex
	•	save/pdf/*.pdf
	•	save/png/*.png
	•	save/log/*.log
    ```

### 3. 核心函数
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
	•	如果要处理完整数据集，可以修改 test/generate.py 里的 ds[:5] 限制。

要不要我帮你再加一个 **配置文件 (YAML/JSON)** 示例，这样以后你就不用改 `generate.py`，只需要改配置就能切换模型路径和输出目录？