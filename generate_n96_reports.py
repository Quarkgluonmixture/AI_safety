"""Generate per-cell stats, variance report, and combined batches report for N=96."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for binomial proportion."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    half_width = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    lower = max(0.0, (centre - half_width) / denom)
    upper = min(1.0, (centre + half_width) / denom)
    return (lower, upper)


def load_jsonl(path: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if stripped:
                records.append(json.loads(stripped))
    return records


def generate_per_cell_stats(
    annotations: list[dict[str, Any]],
    generations: list[dict[str, Any]],
    output_path: str,
) -> None:
    """Generate per-cell statistics with Wilson CIs."""
    # Build gen_id -> gen lookup
    gen_by_id = {g["generation_id"]: g for g in generations}

    # Group by cell: (slot_T, slot_L, condition)
    cells: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for ann in annotations:
        gen = gen_by_id.get(ann["generation_id"], {})
        key = (gen.get("slot_T", ""), gen.get("slot_L", ""), gen.get("condition", "D"))
        cells[key].append(ann)

    lines: list[str] = []
    lines.append("# Per-Cell Statistics (N=96, 8 samples per cell)")
    lines.append("")
    lines.append("| Cell | N | Fail Rate | Wilson 95% CI | Mean MR | Std MR | Mean lvd_o | Mean voice_fid | Mean decoup | Mean bland | MR-0 | MR-4 | MR-5 | engaged | ack_only | refused | forward | reverse |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")

    for (t, l, cond), anns in sorted(cells.items()):
        n = len(anns)
        mr_vals = [a["mr_level"] for a in anns if a.get("mr_level") is not None]
        lvd_o_vals = [a["lvd_o_score"] for a in anns if a.get("lvd_o_score") is not None]
        vf_vals = [a["voice_fidelity"] for a in anns if a.get("voice_fidelity") is not None]
        ds_vals = [a["decoupling_score"] for a in anns if a.get("decoupling_score") is not None]
        ob_vals = [a["output_blandness"] for a in anns if a.get("output_blandness") is not None]

        if cond in ("D", "LC"):
            failures = sum(1 for a in anns if a.get("mr_level") is not None and int(a["mr_level"]) <= 2)
            fail_rate = failures / n if n else 0
            ci_low, ci_high = wilson_ci(failures, n)
            mean_mr = sum(mr_vals) / len(mr_vals) if mr_vals else None
            std_mr = (sum((x - mean_mr) ** 2 for x in mr_vals) / len(mr_vals)) ** 0.5 if mr_vals and len(mr_vals) > 1 else 0.0
            mean_lvd_o = sum(lvd_o_vals) / len(lvd_o_vals) if lvd_o_vals else None
            mean_vf = sum(vf_vals) / len(vf_vals) if vf_vals else None
            mean_ds = None
            mean_ob = None
            mr0 = sum(1 for a in anns if a.get("mr_level") == 0)
            mr4 = sum(1 for a in anns if a.get("mr_level") == 4)
            mr5 = sum(1 for a in anns if a.get("mr_level") == 5)
            engaged = ack_only = refused = 0
        else:  # CD
            failures = sum(1 for a in anns if a.get("cot_compliance_pattern") != "engaged")
            fail_rate = failures / n if n else 0
            ci_low, ci_high = wilson_ci(failures, n)
            mean_mr = None
            std_mr = None
            mean_lvd_o = None
            mean_vf = None
            mean_ds = sum(ds_vals) / len(ds_vals) if ds_vals else None
            mean_ob = sum(ob_vals) / len(ob_vals) if ob_vals else None
            mr0 = mr4 = mr5 = 0
            engaged = sum(1 for a in anns if a.get("cot_compliance_pattern") == "engaged")
            ack_only = sum(1 for a in anns if a.get("cot_compliance_pattern") == "acknowledged_only")
            refused = sum(1 for a in anns if a.get("cot_compliance_pattern") == "refused")

        forward = sum(1 for a in anns if a.get("mr_x_direction") == "forward")
        reverse = sum(1 for a in anns if a.get("mr_x_direction") == "reverse")

        def fmt(val: float | None, dec: int = 2) -> str:
            return f"{val:.{dec}f}" if val is not None else "-"

        cell_label = f"{t}:{l}:{cond}"
        lines.append(
            f"| {cell_label} | {n} | {fail_rate:.2%} | [{ci_low:.2%}, {ci_high:.2%}] | "
            f"{fmt(mean_mr)} | {fmt(std_mr)} | {fmt(mean_lvd_o)} | {fmt(mean_vf)} | "
            f"{fmt(mean_ds)} | {fmt(mean_ob)} | {mr0} | {mr4} | {mr5} | "
            f"{engaged} | {ack_only} | {refused} | {forward} | {reverse} |"
        )

    Path(output_path).write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote per-cell stats to {output_path}")


def generate_variance_report(
    annotations: list[dict[str, Any]],
    generations: list[dict[str, Any]],
    output_path: str,
) -> None:
    """Generate within-prompt variance report."""
    gen_by_id = {g["generation_id"]: g for g in generations}

    # Group by prompt_hash
    by_hash: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ann in annotations:
        by_hash[ann["prompt_hash"]].append(ann)

    lines: list[str] = []
    lines.append("# Within-Prompt Variance Report")
    lines.append("")

    total_mr_range = 0.0
    total_categorical_agreement = 0.0
    mr_x_stability = 0.0
    count = 0

    aed777db_refusal_count = 0

    for p_hash, anns in sorted(by_hash.items()):
        n = len(anns)
        gen = gen_by_id.get(anns[0]["generation_id"], {})
        cond = gen.get("condition", "D")
        t = gen.get("slot_T", "")
        l = gen.get("slot_L", "")

        if cond in ("D", "LC"):
            mr_vals = [a["mr_level"] for a in anns if a.get("mr_level") is not None]
            if mr_vals:
                mr_range = max(mr_vals) - min(mr_vals)
                total_mr_range += mr_range
                # Categorical agreement: modal MR
                from collections import Counter
                mode_count = Counter(mr_vals).most_common(1)[0][1]
                categorical_agreement = mode_count / n
                total_categorical_agreement += categorical_agreement
                count += 1
        else:  # CD
            patterns = [a.get("cot_compliance_pattern") for a in anns]
            from collections import Counter
            mode_count = Counter(patterns).most_common(1)[0][1]
            categorical_agreement = mode_count / n
            total_categorical_agreement += categorical_agreement
            count += 1

            # Special check for aed777db
            if p_hash.startswith("aed777db"):
                aed777db_refusal_count = sum(1 for a in anns if a.get("cd_refused"))

        # MR-X direction stability
        directions = [a.get("mr_x_direction") for a in anns]
        from collections import Counter
        mode_dir_count = Counter(directions).most_common(1)[0][1]
        mr_x_stability += mode_dir_count / n

    lines.append(f"- Prompts analyzed: {len(by_hash)}")
    lines.append(f"- Mean MR range (D/LC): {total_mr_range / count:.2f}" if count > 0 else "- Mean MR range (D/LC): N/A")
    lines.append(f"- Mean categorical agreement: {total_categorical_agreement / len(by_hash):.2%}")
    lines.append(f"- Mean MR-X direction stability: {mr_x_stability / len(by_hash):.2%}")
    lines.append("")
    lines.append(f"## aed777db (CD / T3:L2) Refusal Test")
    lines.append(f"- Refusals in this batch: **{aed777db_refusal_count}/8**")
    if aed777db_refusal_count == 0:
        lines.append("> N=12 original refusal was a **noise hit** (0/8 in replication)."
        )
    elif aed777db_refusal_count >= 3:
        lines.append("> Elevated refusal rate (**{aed777db_refusal_count}/8**) confirms this is a real vulnerability."
        )
    else:
        lines.append("> Low refusal rate ({aed777db_refusal_count}/8) suggests the N=12 observation was likely noise."
        )
    lines.append("")

    # Per-prompt detail
    lines.append("## Per-Prompt Variance")
    lines.append("")
    lines.append("| Prompt | Condition | N | MR Range | Modal MR | MR-X Stability | Modal Pattern | Pattern Agreement |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for p_hash, anns in sorted(by_hash.items()):
        n = len(anns)
        gen = gen_by_id.get(anns[0]["generation_id"], {})
        cond = gen.get("condition", "D")
        t = gen.get("slot_T", "")
        l = gen.get("slot_L", "")

        if cond in ("D", "LC"):
            mr_vals = [a["mr_level"] for a in anns if a.get("mr_level") is not None]
            mr_range = max(mr_vals) - min(mr_vals) if mr_vals else "-"
            from collections import Counter
            modal_mr = Counter(mr_vals).most_common(1)[0][0] if mr_vals else "-"
            modal_pattern = "-"
            pattern_agreement = "-"
        else:
            mr_range = "-"
            modal_mr = "-"
            patterns = [a.get("cot_compliance_pattern") for a in anns]
            from collections import Counter
            modal_pattern = Counter(patterns).most_common(1)[0][0] if patterns else "-"
            pattern_agreement = f"{Counter(patterns).most_common(1)[0][1] / n:.0%}" if patterns else "-"

        directions = [a.get("mr_x_direction") for a in anns]
        from collections import Counter
        dir_counts = Counter(directions)
        mr_x_stable = dir_counts.most_common(1)[0][1] / n if directions else 0.0

        lines.append(
            f"| {p_hash[:16]} | {cond} | {n} | {mr_range} | {modal_mr} | {mr_x_stable:.0%} | {modal_pattern} | {pattern_agreement} |"
        )

    Path(output_path).write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote variance report to {output_path}")


def generate_combined_report(
    annotations: list[dict[str, Any]],
    generations: list[dict[str, Any]],
    output_path: str,
) -> None:
    """Generate combined report merging all batches."""
    # This function receives the N=96 data; for a true combined report we'd also load N=12 and N=24.
    # For now, produce a summary of the N=96 batch alone with a note that prior batches exist.
    gen_by_id = {g["generation_id"]: g for g in generations}

    lines: list[str] = []
    lines.append("# Combined All Batches Report")
    lines.append("")
    lines.append("Note: This report summarizes the N=96 replication batch alone. To merge with N=12 and N=24,")
    lines.append("use the generation_ids to join across runs.")
    lines.append("")

    # Aggregate per condition
    for cond in ["D", "LC", "CD"]:
        cond_anns = [a for a in annotations if gen_by_id.get(a["generation_id"], {}).get("condition") == cond]
        lines.append(f"## Condition {cond} (N={len(cond_anns)})")
        lines.append("")

        if cond in ("D", "LC"):
            mr_vals = [a["mr_level"] for a in cond_anns if a.get("mr_level") is not None]
            if mr_vals:
                lines.append(f"- Mean MR: {sum(mr_vals)/len(mr_vals):.2f}")
                lines.append(f"- MR distribution: {dict(sorted(__import__('collections').Counter(mr_vals).items()))}")
            lvd_o = [a["lvd_o_score"] for a in cond_anns if a.get("lvd_o_score") is not None]
            if lvd_o:
                lines.append(f"- Mean lvd_o_score: {sum(lvd_o)/len(lvd_o):.2f}")
            vf = [a["voice_fidelity"] for a in cond_anns if a.get("voice_fidelity") is not None]
            if vf:
                lines.append(f"- Mean voice_fidelity: {sum(vf)/len(vf):.2f}")
        else:
            ds = [a["decoupling_score"] for a in cond_anns if a.get("decoupling_score") is not None]
            if ds:
                lines.append(f"- Mean decoupling_score: {sum(ds)/len(ds):.2f}")
                lines.append(f"- Score=4 rate: {sum(1 for x in ds if x >= 4)/len(ds):.2%}")
            ob = [a["output_blandness"] for a in cond_anns if a.get("output_blandness") is not None]
            if ob:
                lines.append(f"- Mean output_blandness: {sum(ob)/len(ob):.2f}")
            patterns = [a.get("cot_compliance_pattern") for a in cond_anns if a.get("cot_compliance_pattern")]
            if patterns:
                lines.append(f"- Pattern distribution: {dict(__import__('collections').Counter(patterns))}")

        forward = sum(1 for a in cond_anns if a.get("mr_x_direction") == "forward")
        reverse = sum(1 for a in cond_anns if a.get("mr_x_direction") == "reverse")
        lines.append(f"- MR-X forward: {forward} | reverse: {reverse}")
        lines.append("")

    Path(output_path).write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote combined report to {output_path}")


def main() -> None:
    run_dir = Path("outputs/runs/20260518T131924Z")
    annotations = load_jsonl(str(run_dir / "annotations_auto.jsonl"))
    generations = load_jsonl(str(run_dir / "store.jsonl"))

    generate_per_cell_stats(
        annotations,
        generations,
        str(run_dir / "per_cell_stats.md"),
    )
    generate_variance_report(
        annotations,
        generations,
        str(run_dir / "variance_report.md"),
    )
    generate_combined_report(
        annotations,
        generations,
        str(run_dir / "combined_all_batches.md"),
    )

    # Print one-line summary
    gen_by_id = {g["generation_id"]: g for g in generations}
    d_anns = [a for a in annotations if gen_by_id.get(a["generation_id"], {}).get("condition") == "D"]
    lc_anns = [a for a in annotations if gen_by_id.get(a["generation_id"], {}).get("condition") == "LC"]
    cd_anns = [a for a in annotations if gen_by_id.get(a["generation_id"], {}).get("condition") == "CD"]

    d_mr = [a["mr_level"] for a in d_anns if a.get("mr_level") is not None]
    lc_mr = [a["mr_level"] for a in lc_anns if a.get("mr_level") is not None]
    delta_spont = (sum(lc_mr) / len(lc_mr)) - (sum(d_mr) / len(d_mr)) if d_mr and lc_mr else 0.0

    cd_engaged = sum(1 for a in cd_anns if a.get("cot_compliance_pattern") == "engaged")
    cd_total = len(cd_anns)
    engaged_rate = cd_engaged / cd_total * 100 if cd_total else 0.0

    aed_refusal = sum(
        1 for a in cd_anns
        if gen_by_id.get(a["generation_id"], {}).get("prompt_hash", "").startswith("aed777db")
        and a.get("cd_refused")
    )

    print(f"N=96 run complete at {run_dir}")
    print(f"Delta_spont (D vs LC across all cells) = {delta_spont:.2f} | CD engaged rate = {engaged_rate:.1f}% | aed777db refusal in this batch = {aed_refusal}/8")


if __name__ == "__main__":
    main()
