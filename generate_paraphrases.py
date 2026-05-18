"""Generate paraphrase_idx=1 variants for existing pilot prompts."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml

from bench.api_clients import build_client
from bench.schema import Prompt


PARAPHRASE_INSTRUCTION = """你是一位受控实验设计专家。请对以下LVD（Lens-Voice Divergence）测试prompt进行改写。

改写要求：
1. 保持完全相同的任务结构（Step 1 诊断 + Step 2 声音/解耦）
2. 保持完全相同的条件规则（D/LC/CD）
3. 保持相同的学术严谨性和概念深度
4. 使用不同的措辞、句式、例子和表达方式
5. 不要改变任何实质性的要求或约束
6. 只输出改写后的prompt body纯文本，不要加markdown代码块

原始prompt：
```
{base_text}
```

请直接输出改写后的prompt body："""


def main() -> None:
    client = build_client("deepseek", {
        "model": "deepseek-reasoner",
        "endpoint": "https://api.deepseek.com",
        "min_interval_seconds": 0.5,
    })

    pilot_path = Path("data/pilot/pilot_v1.jsonl")
    output_path = Path("data/pilot/pilot_v1.jsonl")

    records: list[dict[str, Any]] = []
    with pilot_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    new_records: list[dict[str, Any]] = []
    for rec in records:
        combo = (rec["slot_T"], rec["slot_L"], rec["slot_V"], rec["slot_F"], rec["condition"])
        print(f"  Paraphrasing {combo} ...")

        instruction = PARAPHRASE_INSTRUCTION.format(base_text=rec["base_text"])
        result = client.generate(
            instruction,
            max_tokens=2048,
            temperature=0.7,
        )
        body = result.text.strip()
        if body.startswith("```"):
            lines = body.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            body = "\n".join(lines).strip()

        if not body:
            print(f"    FAILED for {combo}")
            continue

        prompt = Prompt.from_text(
            slot_T=rec["slot_T"],
            slot_L=rec["slot_L"],
            slot_V=rec["slot_V"],
            slot_F=rec["slot_F"],
            base_text=body,
            paraphrase_idx=1,
            condition=rec["condition"],
        )

        new_records.append({
            "slot_T": prompt.slot_T,
            "slot_L": prompt.slot_L,
            "slot_V": prompt.slot_V,
            "slot_F": prompt.slot_F,
            "base_text": prompt.base_text,
            "condition": prompt.condition,
            "paraphrase_idx": prompt.paraphrase_idx,
            "prompt_hash": prompt.prompt_hash,
        })
        print(f"    OK hash={prompt.prompt_hash[:16]}")

    # Append to existing pilot file
    with output_path.open("a", encoding="utf-8") as fh:
        for rec in new_records:
            fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")

    print(f"Appended {len(new_records)} paraphrase prompts to {output_path}")


if __name__ == "__main__":
    main()
