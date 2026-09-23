---
name: single-scenario-synthetic-tests
description: "Keep each integration test focused on one user-visible scenario instead of combining unrelated journeys"
condition: "test\\((?:\\\\)?[\"']exports\\s+the\\s+authenticated\\s+search\\s+event\\s+lineage[\"']"
scope: "tool:write(*events.spec.ts)"
---

One integration test, one scenario. Split search submission, result impression, useful action, note opening, and export assertions into separate tests. Share setup, fixtures, request capture, and export parsing through helpers instead of chaining unrelated assertions.
