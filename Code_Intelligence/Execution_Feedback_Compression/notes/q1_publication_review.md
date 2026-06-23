# Q1 Publication Readiness Review

Perspective: critical reviewer for a Q1 Software Engineering journal such as Empirical Software Engineering, Automated Software Engineering, Information and Software Technology, or Journal of Systems and Software.

## Bottom Line

The current idea is promising but not yet Q1-ready. The core concept, execution feedback compression for neural program repair, can be publishable if framed as a rigorous empirical study of feedback representations and their effect on repair behavior, not merely as a performance comparison.

At present, the pilot establishes feasibility: feedback can be extracted, compressed, and measured. For Q1-level publication, the study must demonstrate that compression changes repair effectiveness, efficiency, robustness, or generalization in a scientifically convincing way.

## Current Strengths

- The idea addresses a real weakness in neural program repair: raw compiler/runtime/test feedback is often verbose, noisy, and inconsistently structured.
- The dataset is large: 2.22M CodeNet-derived bug-fix records, with tests for most records.
- The setup naturally supports controlled comparison because the same buggy programs can be paired with multiple feedback representations.
- The work connects to execution-grounded software engineering, APR, neural code intelligence, prompt/context optimization, and data-centric AI for code.
- The pilot already revealed an important data-quality issue: online-judge status and locally available sample-test behavior diverge substantially.

## Major Weaknesses in the Current Study Design

### 1. The current contribution is underspecified

`Execution feedback compression` is a good phrase, but it needs a sharper scientific claim. A Q1 reviewer will ask:

- Is this a new repair method?
- A dataset contribution?
- An empirical study?
- A theory of feedback usefulness?
- A prompt/context optimization method?

Right now it risks looking like an engineering comparison of prompt variants.

### 2. Feedback compression is not yet theoretically grounded

The current formats are intuitive but not yet justified by a model of what feedback information is repair-relevant. We need to define feedback dimensions such as:

- failure category,
- localization,
- expected/actual behavioral contrast,
- stack trace depth,
- symbol-level diagnostic,
- execution phase,
- input-output counterexample.

Then each compressed representation should be an ablation over those dimensions.

### 3. Sample tests are insufficient as ground truth

The pilot shows many originally wrong/TLE programs pass embedded sample tests. This is a major validity risk. If only sample tests are used, the paper may measure public-test behavior rather than real repair correctness.

Minimum fix:

- report sample-test correctness separately from dataset online-judge labels,
- use accepted solution as reference,
- evaluate generated repairs on all available tests,
- where hidden tests are unavailable, frame conclusions as sample-test repair behavior.

Stronger fix:

- build additional generated tests using accepted solutions,
- use metamorphic or fuzz testing where problem constraints allow,
- include a benchmark with stronger test suites.

### 4. No repair model result yet

Compression length alone is not enough. A Q1 paper needs evidence that feedback representations affect repair outcomes:

- Pass@1,
- compile/runtime success,
- wrong-answer reduction,
- repair edit distance,
- overfitting behavior,
- context-length efficiency.

### 5. Baselines are currently too weak

The current variants are internal comparisons. Reviewers will expect baselines from APR and LLM/code-model practice:

- no feedback,
- raw feedback,
- compiler/runtime feedback as commonly used in agentic repair,
- problem description only,
- problem description plus raw feedback,
- structured feedback,
- oracle-localized feedback if line information exists,
- accepted-code nearest-neighbor or retrieval baseline,
- simple rule-based repair for common Python errors,
- LLM/API baseline if possible.

### 6. The study currently lacks external validity

CodeNet is useful but competitive programming is not general software engineering. For Q1:

- at least one external benchmark is needed,
- or the paper must be explicitly framed as competitive-programming program repair and not general APR.

External candidates:

- QuixBugs for Python/Java algorithmic bugs,
- HumanEvalFix-like generated repair tasks,
- Defects4J if Java infrastructure becomes available,
- BugsInPy if Python environment can be managed,
- SWE-bench Lite only for analysis or external model comparison, not first-line training.

### 7. Statistical validation needs to be designed now

A single 300-record pilot is not enough. Need:

- multiple random seeds or stratified folds,
- paired tests because each program is evaluated under every feedback variant,
- confidence intervals,
- effect sizes,
- correction for multiple comparisons if many feedback variants are compared.

Recommended tests:

- McNemar's test for paired binary outcomes such as repaired/not repaired,
- bootstrap confidence intervals for Pass@1 differences,
- Wilcoxon signed-rank for paired edit-distance/token-cost comparisons,
- Cliff's delta or odds ratios for effect size.

## Stronger Research Questions

Current RQs should be reframed from generic format comparison to scientific questions:

### RQ1: Information Sufficiency

Which components of execution feedback are necessary and sufficient for neural program repair?

### RQ2: Compression-Efficiency Tradeoff

How much can execution feedback be compressed before repair performance degrades?

### RQ3: Error-Type Dependence

Do different bug categories require different feedback information, such as localization for runtime errors or counterexamples for wrong answers?

### RQ4: Model Dependence

Are feedback-compression effects consistent across model families, such as small fine-tuned models, instruction-tuned code LLMs, and external LLMs?

### RQ5: Generalization

Do feedback-compression effects generalize beyond Project CodeNet to external repair benchmarks?

## Additional Experiments That Would Strengthen the Paper

### A. Feedback Component Ablation

Instead of only comparing named formats, create controlled ablations:

- category only,
- category + line,
- category + line + code context,
- category + expected/actual output,
- category + stack trace,
- category + normalized exception,
- full raw feedback.

Expected impact: very high.

Reason: reveals which information actually matters.

### B. Counterexample Feedback for Wrong Answer

For wrong-answer bugs, compare:

- no feedback,
- expected output only,
- actual output only,
- expected + actual,
- input + expected + actual,
- natural-language counterexample summary.

Expected impact: high.

Reason: wrong-answer repair is behavior-driven; stack traces are irrelevant.

### C. Runtime Error Localization Study

For runtime errors, compare:

- exception type only,
- exception type + line,
- exception type + line + local code window,
- full traceback.

Expected impact: high.

Reason: gives a clear scientific result about localization value.

### D. Cross-Model Robustness

Run the same feedback variants across at least two model types:

- compact fine-tuned model such as CodeT5-small/base,
- instruction-tuned code model if feasible,
- external API model if available.

Expected impact: high, but higher effort.

Reason: prevents the paper from being tied to one model's quirks.

### E. Cross-Dataset Validation

Evaluate on a second benchmark:

- QuixBugs first, because it is much lighter than Defects4J,
- BugsInPy if Python infrastructure is manageable,
- Defects4J later if Java setup succeeds.

Expected impact: very high.

Reason: directly addresses external validity.

### F. Data Quality and Hidden-Test Gap Analysis

Make the mismatch between online-judge labels and sample-test behavior a formal analysis:

- Which status labels most often pass public/sample tests?
- Are TLE and WA particularly under-detected by sample tests?
- How does this affect repair evaluation?

Expected impact: medium to high.

Reason: Q1 empirical journals value data-quality insight, and this is already emerging from the pilot.

### G. Cost-Effectiveness Analysis

Measure:

- token length,
- prompt cost,
- inference time,
- repair success per 1,000 tokens,
- success under context budget.

Expected impact: high.

Reason: compression is only compelling if efficiency is part of the claim.

## Stronger Baselines

Minimum baselines:

- buggy code only,
- buggy code + problem description,
- buggy code + raw feedback,
- buggy code + categorical feedback,
- buggy code + localized feedback,
- buggy code + structured feedback,
- buggy code + natural-language compressed feedback.

Stronger baselines:

- raw feedback truncated to same token budget as compressed feedback,
- random deletion compression at same token budget,
- first-line-only raw feedback,
- last-line-only traceback feedback,
- exception-type-only feedback,
- oracle localization if diff/trace line is available,
- accepted-solution retrieval baseline,
- nearest-neighbor repair baseline using edit similarity.

Reviewer-resistant baselines:

- same model and same token budget across all feedback formats,
- same prompt template except feedback field,
- paired evaluation on identical bug instances.

## Stronger Ablations

Essential ablations:

- remove problem description,
- remove feedback category,
- remove localization,
- remove expected/actual output,
- remove code context window,
- vary context window size: 0, 1, 3, 5 lines,
- vary compression ratio,
- vary timeout threshold,
- test with and without environment-normalization packages such as NumPy/SciPy.

## Novelty Assessment

The idea is moderately novel as currently framed, but not enough if presented only as "compressed feedback helps repair." Reviewers may see it as prompt engineering.

The stronger framing is:

> This paper presents a controlled empirical study of execution feedback as an information channel for neural program repair, quantifying which feedback components are necessary, redundant, or harmful across error types, models, and datasets.

This moves the contribution from "we propose a prompt format" to "we characterize the science of feedback usefulness."

Possible contribution statement:

1. A taxonomy of execution feedback information units for neural repair.
2. A controlled benchmark pipeline for generating paired feedback variants.
3. Empirical evidence showing how compression affects repair accuracy, context cost, and generalization.
4. Error-type-specific findings about what feedback information matters.
5. A replication package with data slices, scripts, configs, and statistical tests.

## Deeper Scientific Analyses

Beyond performance tables, include:

### Error-Type Sensitivity

Analyze separately:

- compile/runtime errors,
- wrong answers,
- timeouts,
- presentation errors.

Expected insight: localization helps runtime errors; counterexamples help wrong answers; categorical feedback may be enough for some presentation errors.

### Feedback Entropy and Redundancy

Measure how much raw feedback is boilerplate versus instance-specific:

- stack trace template repetition,
- common exception names,
- path noise,
- line-number information,
- expected/actual output size.

Expected insight: raw feedback has high syntactic volume but low repair-relevant density.

### Repair Edit-Type Analysis

Classify fixes by diff type:

- single-line replacement,
- insertion,
- deletion,
- import/library fix,
- boundary condition,
- algorithmic change.

Then measure which feedback format helps which edit type.

### Failure Mode Analysis

Manually inspect a statistically meaningful sample:

- cases where compressed feedback succeeds and raw fails,
- cases where raw succeeds and compressed fails,
- cases where all fail,
- cases where no feedback succeeds.

This is particularly important for EMSE/JSS-style empirical depth.

### Calibration Between Dataset Label and Local Execution

Analyze disagreement between original online judge status and local sample-test status.

This can become a methodological contribution about the danger of relying only on public tests.

## Venue Positioning

### Empirical Software Engineering

Best fit if the paper is framed as a rigorous empirical study with replication package, multiple datasets/models, statistical testing, and deep qualitative error analysis. EMSE explicitly values applied software engineering research with strong empirical components and replicable or expandable studies.

Positioning:

> An empirical study of execution feedback representations for neural program repair.

### Automated Software Engineering

Best fit if the compression pipeline is presented as an automated technique/tool that improves repair efficiency or effectiveness. ASE's scope includes tools, AI techniques, software maintenance, testing, reverse engineering, and program understanding.

Positioning:

> An automated execution-feedback compression framework for neural program repair.

### Information and Software Technology

Best fit if the paper emphasizes practical software development/tooling implications, cost-effective repair workflows, and robust empirical validation.

Positioning:

> Efficient feedback representation for practical neural repair systems.

### Journal of Systems and Software

Best fit if the paper broadens to software systems, maintainability, tool integration, and developer-relevant repair behavior.

Positioning:

> Execution-feedback compression for scalable software repair assistance.

## Prioritized Experiment Plan

| Priority | Experiment | Impact | Effort | Why |
|---|---|---:|---:|---|
| P0 | Paired feedback-variant repair on Python pilot | Very high | Medium | Core evidence needed for any claim |
| P0 | Feedback component ablation | Very high | Medium | Converts prompt comparison into scientific insight |
| P0 | Statistical validation with 5 seeds/folds | Very high | Medium | Required for Q1 credibility |
| P1 | Wrong-answer counterexample ablation | High | Medium | Strong error-type insight |
| P1 | Runtime-error localization ablation | High | Medium | Strong error-type insight |
| P1 | Token-cost / compression-efficiency analysis | High | Low | Directly supports "compression" contribution |
| P1 | External benchmark: QuixBugs | Very high | Medium | External validity |
| P2 | External model/API comparison | High | Medium/High | Model robustness |
| P2 | Java pilot with compiler diagnostics | High | High currently | Adds compile-error dimension |
| P3 | Defects4J/BugsInPy | Very high | High | Strong journal validation but heavier infrastructure |

## Minimal Q1-Competitive Package

At minimum, the paper needs:

1. A crisp taxonomy of execution feedback components.
2. At least one substantial dataset, not only 300 pilot records.
3. Paired repair evaluation across feedback variants.
4. At least one trained/local model and one stronger external/instruction model if feasible.
5. Strong baselines: no feedback, raw feedback, same-budget raw truncation, categorical, localized, structured.
6. Statistical validation with confidence intervals and paired tests.
7. Error-type-specific analysis.
8. External validation on at least one benchmark.
9. Qualitative failure-mode analysis.
10. A replication package with scripts, configs, data splits, and logs.

## Current Readiness Assessment

Current state: feasibility prototype.

Q1 readiness: not yet.

Estimated level:

- Workshop/early conference short paper: possible after model-based pilot.
- Solid conference paper: possible after paired repair evaluation and ablations.
- Q1 journal paper: requires external benchmark, statistical validation, deeper analysis, and stronger baselines.

## Recommended Reframing

Use this as the central claim:

> Execution feedback is an information channel for neural program repair. This work decomposes that channel into repair-relevant components and empirically studies how compression affects repair accuracy, context efficiency, and generalization across error types and models.

This is much stronger than:

> We compress feedback and get better results.

## Immediate Action Items

1. Implement repair generation for a small Python pilot.
2. Compare no feedback, raw, categorical, localized, and structured under identical examples.
3. Add same-token-budget raw truncation baseline.
4. Expand to 5 random samples/seeds.
5. Run paired statistical tests.
6. Add QuixBugs as external benchmark.
7. Update manuscript RQs to match the stronger framing.
