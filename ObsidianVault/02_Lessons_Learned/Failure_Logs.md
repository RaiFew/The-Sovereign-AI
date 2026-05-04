# Failure Logs

- **Date**: 2024-05-01
  **Issue**: Agent generated too much fluff for a coding tutorial.
  **Resolution**: Implemented stricter constraints on Agent J (Compressor) to aggressively strip non-code text.

- **Date**: 2024-05-02
  **Issue**: Discord bot hit API limits.
  **Resolution**: Ensure tasks are batched or polled less frequently (every 60s minimum).
