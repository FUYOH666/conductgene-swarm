- 2026-11-12T03:08Z: A0 base run started before fact verification finished, to overlap compute. Adjudication is done blind to judge outputs; adjudicated cases are re-judged (cassette keyed by case hash).
- 2026-11-12T03:11Z: stopped the overlapping A0 run after 5 cases (two models on one GPU made both slow); A0 resumes after verification, reusing the 5 recorded outputs.
- 2026-11-12: the owner needed the local machine for other work, so the run moved to hosted models via OpenRouter:
  judge Gemma 4 26B (local, MLX) → `deepseek/deepseek-v4.1-flash-1017`; fact verifier and rule drafter
  Qwen 3.8 27B (local GGUF) → `qwen/qwen3.8-27b`. Model families stay separate: GPT writes, Qwen checks
  and drafts, DeepSeek judges. All 240 transcripts are re-verified with the hosted verifier; the partial
  local verification (150 cases) and the 5 local Gemma judgements are kept in `archive/` and not used.
  The data is synthetic, so no confidential text leaves the machine.
