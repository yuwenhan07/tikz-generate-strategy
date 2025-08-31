# latex_utils.py
import re
import traceback
from typing import List, Optional, Tuple
from automatikz.infer import TikzDocument  # 还是依赖这个类


def parse_latex_errors(log: str, rootfile: str = "temp.tex") -> dict:
    errors = {}
    error_pattern = re.compile(
        rf"^{re.escape(rootfile)}:(\d+):\s*(.*?)(?=\n[^:]+:|$)",
        re.MULTILINE | re.DOTALL
    )
    for match in error_pattern.finditer(log):
        line = int(match.group(1))
        msg = match.group(2).strip()
        errors[line] = msg
    
    if not errors and re.search(r"Emergency stop|Fatal error", log, re.IGNORECASE):
        errors[0] = "Fatal error during compilation"
    return errors


def generate_and_repair(
    model,
    processor,
    image,
    prompt: str,
    max_attempts: int = 5,
    return_all: bool = False
) -> Tuple[TikzDocument, List[TikzDocument]]:
    """使用TikzDocument进行生成与修复"""
    all_attempts = []

    def _generate(snippet: str = "") -> str:
        try:
            messages = [{
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": (
                        f"Please generate LaTeX code based on the image and description:\n"
                        f"Existing code:\n{snippet}\n"
                        f"Description to be supplemented: {prompt}"
                    )}
                ]
            }]
            text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = processor(text=[text], images=[image], return_tensors="pt", padding=True).to(model.device)

            generated_ids = model.generate(
                **inputs, max_new_tokens=1024, do_sample=True, temperature=0.7
            )
            output_text = processor.batch_decode(
                generated_ids[:, inputs.input_ids.shape[1]:],
                skip_special_tokens=True
            )[0]

            patterns = [
                r"```(?:latex|tex)?\s*(.*?)\s*```",
                r"(\\documentclass{standalone}.*?\\end{document})",
                r"(\\begin{tikzpicture}.*?\\end{tikzpicture})"
            ]
            for pattern in patterns:
                m = re.search(pattern, output_text, re.DOTALL | re.IGNORECASE)
                if m:
                    return m.group(1).strip()
            return output_text.strip()
        except Exception as e:
            traceback.print_exc()
            return ""

    def _recursive_repair(attempts_left: int, snippet: str = "", offset: int = 1, prev_first_error: Optional[int] = None):
        new_code = _generate(snippet)
        full_code = snippet + new_code if snippet else new_code

        try:
            tikz_doc = TikzDocument(code=full_code)
            all_attempts.append(tikz_doc)
        except Exception as e:
            class Dummy: pass
            dummy = Dummy()
            dummy.has_content = False
            dummy.compiled_with_errors = True
            dummy.log = f"TikzDocument error: {e}"
            dummy.code = full_code
            all_attempts.append(dummy)
            return dummy

        if tikz_doc.has_content or attempts_left <= 0:
            return tikz_doc

        errors = parse_latex_errors(tikz_doc.log)
        if not errors:
            return tikz_doc

        first_error = min(errors.keys())
        if first_error != prev_first_error:
            offset = 1
        else:
            offset = min(4 * offset, 4096)

        lines = full_code.splitlines(keepends=True)
        keep_lines = max(first_error - offset, 0)
        new_snippet = "".join(lines[:keep_lines])
        return _recursive_repair(attempts_left - 1, new_snippet, offset, first_error)

    final_doc = _recursive_repair(max_attempts)
    return final_doc, all_attempts