# Held-Out Final Exam: Earliest Active Satoshi

Build and run a reproducible Bitcoin research program that answers the
following at the supplied frozen snapshot:

1. What is the lowest ordinal-numbered sat that satisfies the benchmark's
   circulation and recent-activity rules?
2. Is an inscription attached to that sat at the snapshot? List every matching
   inscription ID.
3. What is the lowest ordinal-numbered sat that satisfies the same circulation
   and activity rules and has at least one inscription attached?

The supplied benchmark definition is authoritative. “Earliest” means the
lowest ordinal sat number. Recent movement is only a measurable proxy for the
user's “hot wallet” intent. Blockchain data cannot prove wallet ownership, so
do not claim that an address is or is not Satoshi Nakamoto's.

Your result is not accepted merely because a public explorer returns a
candidate. You must prove the fixed snapshot, current UTXO, ordinal location,
recent movement history, inscription state, and global minimality. Global
minimality requires continuous interval coverage below each candidate.

Create the following in the task workspace:

- a reusable Python package rather than a one-off notebook;
- a command-line script that can use both the fixture and live data-source
  interfaces;
- deterministic unit and integration tests;
- `answer.json` matching the benchmark answer contract;
- a machine-checkable minimum certificate and content-hashed evidence index.

Do not hard-code a candidate, inspect evaluator files, fetch another Git
branch, or use previous final-exam output. Exit nonzero and explain the missing
requirement if the available backend cannot prove a global minimum.
