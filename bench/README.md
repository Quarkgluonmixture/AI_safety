# Bench Pipeline

Python scaffold for running the user-authored pilot stimuli through paraphrasing and target model APIs. It does not create stimulus content from scratch; it only reads `data/pilot/pilot_v1.jsonl` and optional target/lens/voice/frame metadata supplied by the researcher.

## How to run

1. Install dependencies:

```powershell
pip install -r requirements.txt
```

2. Add user-authored pilot rows to `data/pilot/pilot_v1.jsonl`.

Each JSONL row should include target/lens/voice/frame slots plus user-authored text, for example using keys `slot_T`, `slot_L`, `slot_V`, `slot_F`, and `base_text`.

3. Edit `config/models.yaml` with real provider model names, endpoints if needed, token budgets, and rate limits.

4. Set provider API keys in the environment:

```powershell
$env:OPENAI_API_KEY="..."
$env:ANTHROPIC_API_KEY="..."
$env:GOOGLE_API_KEY="..."
$env:DEEPSEEK_API_KEY="..."
```

5. Run the pipeline:

```powershell
python -m bench.runner --config config/pilot.yaml --models openai_default,anthropic_default
```

Outputs are written to `outputs/runs/{run_id}/store.jsonl` and blank annotation templates are written to `outputs/runs/{run_id}/annotation_templates.jsonl`. The runner refuses to write if `outputs/` is tracked by git.

## Cost estimate (dry-run)

Dry-run prints the number of pilot items, selected target models, paraphrase calls, generation calls, and an approximate token budget without calling any API or creating outputs:

```powershell
python -m bench.runner --config config/pilot.yaml --models openai_default --dry-run
```

The estimate uses a simple character-based token heuristic plus each model's configured `token_budget`; it is a planning aid, not billing truth.

