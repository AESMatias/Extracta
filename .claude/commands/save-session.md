---
description: "Force a local deterministic session checkpoint."
argument-hint: "[arguments]"
---
Invoke memory:save with the current local session identifiers: $ARGUMENTS
Run `npx @ericrisco/rsc memory save --session <id>`. Persist only allowed git and SDD ledger metadata; never include conversation or file content.
