---
name: ownership-and-security-review
description: Use when implementing or reviewing any endpoint, worker, or
  AI tool that reads/writes user-owned data, or any AI tool-calling code.
---
- Every query touching user-owned data must be scoped by user_id at the
  service layer, not just checked at the route layer.
- Any AI/LLM tool that could produce a numeric claim must call a
  deterministic function for that number — never let the model state a
  figure it computed itself.
- Test cross-user access explicitly: can user A read/modify user B's data
  via this endpoint? Write the test that tries.