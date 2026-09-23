---
name: tests-no-opaque-epoch-literals
description: "Use readable constructed timestamps instead of hardcoded Unix-millisecond epochs in tests"
condition: "\\b(?:1699999999999|1700000000000|1782993600000|1782993600001|1782993600002|1782993600003|1782993600123)\\b"
scope: "tool"
---

No opaque Unix-millisecond literals in tests. In Go, build instants with `time.Date` and call `UnixMilli()` only at the API boundary. In TypeScript, use a named date helper that makes the instant readable.
