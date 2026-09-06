# Acceptance 25K

Status: NOT COMPLETE. All 131 requested acceptance steps remain subject to
current-sprint execution, including the four category LOC gates. The complete
source-linked checklist is TASKS_25K.md, section 29. No live-provider success,
production-readiness, or full Docker health is inferred from a mock or a build.

Every completed milestone must link its implementation, integration path,
test command, exit status, counts, commit and LOC report. Corrections to prior
evidence are recorded explicitly. Baseline behavior remains a regression gate.

Security invariants: no broker write capability; private API access separated
from public content; scoped/revocable agent credentials; raw files immutable;
broker/reference balances distinct; DEMO/FILE/EOD/STALE/LIVE states never conflated.

Primary method references: [Decimal contexts](https://docs.python.org/3/library/decimal.html),
[GIPS handbook](https://www.gipsstandards.org/standards/gips-standards-for-firms/gips-standards-handbook-for-firms/).
The application is not claiming GIPS compliance. Transaction costs remain
deducted from economic returns regardless of cost-basis capitalization policy.
