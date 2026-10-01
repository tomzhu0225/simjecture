# Evidence and production ledger

The Chinese and English videos present the **owned 2026-10-01 sweep**, using task pack **0.3.0** and frozen runner **native-public-feedback-v3**. They frame the work as an initial benchmark for AI in fusion/plasma simulation workflows. Actual measured scope: **analysis of recorded diagnostics**, not new solver execution, tokamak/burning-plasma research, physical hypothesis closure, or autonomous research quality.

The narration speaks in the project voice (“we / 我们”). The voices are stock synthetic voices; they do not imitate or represent a named human narrator. Graphics are original and data-driven. The grid diagram is explicitly schematic, not a simulated field image. No private credentials, conversations, raw worker traces, SSH addresses, or grant documents are inputs to this production.

## Primary evidence

- [Measured sweep report](https://github.com/tomzhu0225/simjecture/blob/feature/benchmark-leaderboard/docs/testing/owned-llm-benchmark-20261001.md)
- [Sanitized original host grades](https://github.com/tomzhu0225/simjecture/blob/feature/benchmark-leaderboard/src/conjecture_solver/llm_bench/results/owned-2026-10-01.json)
- [Separate valuation ledger](https://github.com/tomzhu0225/simjecture/blob/feature/benchmark-leaderboard/src/conjecture_solver/llm_bench/results/owned-2026-10-01-valuation.json)
- [Current publication definitions](https://github.com/tomzhu0225/simjecture/blob/feature/benchmark-leaderboard/src/conjecture_solver/llm_bench/official.py)
- [Benchmark protocol and chart guide](https://github.com/tomzhu0225/simjecture/blob/feature/benchmark-leaderboard/docs/how-to/llm-bench.md)
- [Dated price table and vendor source links](https://github.com/tomzhu0225/simjecture/blob/feature/benchmark-leaderboard/src/conjecture_solver/llm_bench/leaderboard.py)

No new paid inference was performed to create these videos. The visuals read the exported dashboard and do not change the host grades. Narration uses measured configuration names; the `deepseek-flash` API identifier is not asserted to prove a particular provider revision.

## Frozen facts and interpretation

| Claim | Evidence / boundary |
| --- | --- |
| 42 configurations, 252 scheduled attempts | Includes repeated effort settings, not 42 distinct weights. CSV: five attempts/configuration. RZ: one/configuration. |
| 24 no-inference observations; 228 graded | Availability exclusions, never numerical-model failures. Interruption after inference stays in the denominator. |
| CSV: 100/188 complete; 161/188 numerical pass | 61 numerical passes missed the complete delivery contract. Findings presence is a delivery check, not a scientific-quality judge. |
| RZ: 34/40 complete; all 19 tested Codex configurations pass | One attempt/configuration; descriptive, provisional. |
| Recorded RZ cases | 64×4 and 128×4 cylindrical grids; 401 HDF5 frames each. Four axial cells, not a qualified full 3D turbulence evaluation. |
| CSV median times | DeepSeek Flash 50.9278576 s, 4/5; GPT 6 Luna medium 74.1923412 s, 5/5; AGY Gemini 3.8 Flash medium 158.335 s, 5/5. Median time conditions on success. |
| RZ frontier | DeepSeek Flash 114.076384 s and $0.043965912; GPT 6 Luna medium 271.591018 s and $0.01161764. Observed time–cost frontier, no statistical superiority claim. |
| High effort vs low effort | Whole model-agent/budget configurations; different tasks and deadlines prevent a clean causal claim that more time alone fixed failures. |
| MiMo | Tested API setup: zero complete passes; Flash CSV numerical pass 4/5, Pro 2/5. Different adapters/history formats are part of measured configuration. |
| Grok 4.7 RZ | All numeric checks pass, full contract incomplete because findings missing. No claim of universal incapability. |
| 5/5 interval | Approximate 95% Wilson interval: 57–100%. Repetitions of one fixed problem do not establish general scientific ability. |
| Price | Dated standard short-context API-equivalent rates, cache-adjusted default; not subscription invoices. AGY ≈ estimates; partial counters ≥ lower bounds, excluded cost rank/frontier. |
| Charts | X cost/log; Y elapsed time increases down; upper left better. Dashed lines: same-model/same-agent efforts. White rings: observed frontier; no line joins different models. Colours identify model family, with an explicit model legend. Top-ten completed video ranks plus two unfinished examples are explicitly labelled subsets of the 42-row publication. |
| Unfinished runs | Red status. No verified finish-time rank; cost bars show recorded nonzero spending or labelled lower bounds. No-inference configurations are omitted from public rankings. |
| Reference repairs | 0.1 equal-radius ordering; 0.2 float32 arithmetic before promotion; repaired fresh 0.3 trials, old qualifications archived separately. |
| Feature availability | `feature/benchmark-leaderboard` development branch, not bundled in published 0.5.3rc2. |

## Production and reproducibility

- Original graphics: Pillow and Matplotlib, 1920×1080; readable scientific plots rather than generated field imagery.
- Narration: `edge-tts`, `en-US-GuyNeural` and `zh-CN-YunxiNeural`, initially −8% rate. [Tool documentation](https://github.com/rany2/edge-tts).
- Encoding: FFmpeg, H.264 + AAC, embedded captions and separate SRT captions.
- Language edit: Chinese science narration skill with an embedded Chinese wording pass; protected numerical facts, project voice, and twelve scene beats preserved.
- The scripts and storyboard each contain twelve matching narrative beats. Machine-readable narration/scene source is `content.json`.
- No background music or third-party stock footage is required. Scripts can be rerecorded with a human narrator and rendered again.

Large generated media lives under `artifacts/benchmark-video-20261001/` and is intentionally excluded from source control. The tracked production source is in this directory.
