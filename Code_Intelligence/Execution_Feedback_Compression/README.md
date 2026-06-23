# Execution Feedback Compression

Experiment workspace for studying how different representations of compiler, runtime, and test feedback affect neural program repair.

## Core Question

Can compressed execution feedback preserve repair-relevant information while reducing prompt/context length and improving repair success?

## Initial Feedback Formats

- `none`: buggy code without feedback
- `raw`: full compiler/runtime/test output
- `categorical`: error type and coarse error class
- `localized`: error type plus line number and nearby code context
- `structured`: machine-readable fields such as error type, line, symbol, and normalized message
- `natural_language`: short human-readable explanation of the failure

## Suggested Layout

- `data/raw`: original buggy/fixed programs and test data
- `data/processed`: normalized records and feedback variants
- `scripts`: extraction, execution, compression, and evaluation scripts
- `configs`: experiment settings
- `results`: metrics, tables, logs, and generated outputs
- `notes`: research notes, paper outline, and observations

## First Milestone

Build a small pilot dataset for one language, preferably Java or Python, with 1,000 to 5,000 buggy programs. For each program, collect execution feedback, generate compressed variants, run repair prompts/models, and compare compile rate, pass rate, feedback length, and repair behavior by error type.
