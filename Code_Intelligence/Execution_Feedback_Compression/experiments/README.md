# Experiment Registry

Each experiment should get a subfolder named with a stable run ID, for example:

`pilot_java_compile_001`

Each run folder should contain:

- `config.json`
- `metrics.json`
- `records_sample.jsonl` or a pointer to the dataset slice
- `outputs.jsonl`
- `notes.md`

Do not overwrite previous runs. Create a new run ID when changing data, model, prompt, feedback format, or evaluation settings.
