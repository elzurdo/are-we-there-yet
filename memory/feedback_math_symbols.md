---
name: feedback-math-symbols
description: Use Unicode math symbols (≤, ≥, etc.) in human-readable strings and docs, not ASCII alternatives like <= or >=
metadata:
  type: feedback
---

Use Unicode math symbols (≤, ≥, ≠, etc.) in all human-readable text: comments, docstrings, UI strings, tutorial text, and documentation files.

**Why:** User explicitly rejected `<=` in strings and asked for `≤` instead. Cleaner and more readable in rendered contexts.

**How to apply:** In Python code logic, use `<=` as normal. In any string that a human reads — comments, docstrings, Streamlit UI text, tutorials, CLAUDE.md — use the Unicode symbol.
