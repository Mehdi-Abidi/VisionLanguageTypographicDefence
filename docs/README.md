# Project documents

Read them in this order. Each one takes about 15 minutes.

| # | File | What it is | Read it when |
| --- | --- | --- | --- |
| 1 | [research-plan.md](research-plan.md) | The research plan by Ali Sobaan: the claim, the 2×2 design, hypotheses, method, risks and paper outline | First. It explains what we are testing and why |
| 2 | [evaluation-and-proposal.md](evaluation-and-proposal.md) | A check of the plan with five corrections, the final problem statement and abstract, the architecture with stage tables, the revised compute budget and the verified references | Second. Where it disagrees with the plan, it wins |
| 3 | [task-board.md](task-board.md) ([PDF](task-board.pdf)) | 40 tickets across three lanes with dates, step-by-step instructions, what each ticket needs, and the two gates | Every day. Find your lane, find today's date, do the ticket |
| 4 | [architecture/](architecture/) | The pipeline diagram as PNG, SVG and an editable Excalidraw file | When you need to see how your part connects to the others |

## Who does what

| Lane | Person | Tickets |
| --- | --- | --- |
| A. Images and defences | Mufeed | A1 to A12 |
| B. Models and runs | Mehdi | B1 to B12 |
| C. Scoring and writing | Ali Sobaan | C1 to C13 |
| Shared | all three | ALL-1 to ALL-4 |

## Key dates

| Date | What |
| --- | --- |
| Mon Nov 9 | Kickoff (ALL-1) |
| Sun Nov 15 | Pilot gate (ALL-2). The whole pipeline must run on 20 images |
| Tue Nov 24 | Results freeze (ALL-3). No new runs after this |
| Sat Nov 28 | Draft v1 (ALL-4) |

## Rules we all follow

- Do not start a ticket before the tickets in its "needs" list are done.
- Every ticket ends in a file. Commit the file, not a message saying it is done.
- Model outputs in `runs/` are never edited by hand.
- Hypotheses H1 to H4 are committed before the full runs and are not changed afterwards.
- If you are more than one day behind on a ticket, say so at the daily check-in.
