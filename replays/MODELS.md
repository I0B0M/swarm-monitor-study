# Models used by the replayed monitors and exploratory games

| Alias | Model | File | Bytes | SHA-256 |
|---|---|---|---|---|
| claude:sonnet | Claude Sonnet 5.5 through `claude -p` (Claude Code 2.1.314), as the frozen monitor; the exact model id is recorded on every call | n/a | n/a | n/a |
| local:agent | gpt-oss-20b, MXFP4 GGUF | gpt-oss-20b-MXFP4.gguf | 12109566624 | 27cd6c432c7672cb812a92f611cf3ba7bbc35928262bb1e1253ff4ee6ae35901 |
| local:coder | Qwen3.8-27B, UD-Q3_K_XL GGUF | Qwen3.8-27B-UD-Q3_K_XL.gguf | 13146393504 | 8c2a45ff85e7674ca185ec8eb6cdeab0e617ed9d8018caed0b64380eb2a67a5e |
| local:chores | Qwen3.5-9B, Q4_K_M GGUF | Qwen3.5-9B-Q4_K_M.gguf | 5680522464 | 03b74727a860a56338e042c4420bb3f04b2fec5734175f4cb9fa853daf52b7e8 |

Local server: llama.cpp 0.7.0 (build 11669, commit 620d2225c) `llama-server` in router mode on 127.0.0.1:8080, OpenAI-compatible `/v1/chat/completions` with `response_format` JSON schema; one model in memory at a time; monitors at temperature 0, seed 7, max_tokens 2048; gpt-oss-20b at reasoning effort low (router preset); Qwen models with reasoning off (router preset). Machine: Apple M5 Pro, 24 GB.

To reproduce with another OpenAI-compatible server, set `REPLAY_LOCAL_URL` and pass `--backend local:<model name on that server>`.
