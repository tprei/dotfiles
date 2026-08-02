---
name: tests-no-opaque-epoch-literals
description: "Use readable constructed timestamps instead of hardcoded Unix-millisecond epochs in tests"
condition: "\\b(?:1699999999999|1700000000000|1782993600000|1782993600001|1782993600002|1782993600003|1782993600123)\\b"
scope: "tool"
---

In test code, do not introduce opaque Unix-millisecond literals such as these. Construct deterministic instants with `time.Date` and derive milliseconds with `UnixMilli()` only at the API boundary; in TypeScript, use a named date helper that makes the intended instant readable.