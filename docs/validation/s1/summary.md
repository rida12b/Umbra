# S1 proof on the Validation Corpus

Reproduce: `python engine/tools/validate_s1.py` (commits pinned in `corpus.json`). Each run indexes from an
empty store. Timings vary by machine and file cache: on the first, cold run (Windows, antivirus on) the
initial index took 8 to 48 s per Project; all stay far under the 2-minute limit.

| Project | Files | Covered / partial / gaps | Facts correct | Initial index | Lines |
|---|---|---|---|---|---|
| [full-stack-fastapi-template](full-stack-fastapi-template.md) | 252 | 162/8/82 | 30/30 | 1.3 s | 21,421 |
| [morphic](morphic.md) | 575 | 493/1/81 | 30/30 | 3.8 s | 86,054 |
| [chatwoot-mobile-app](chatwoot-mobile-app.md) | 775 | 677/0/98 | 30/30 | 3.5 s | 83,900 |
| [gpt-researcher](gpt-researcher.md) | 841 | 494/0/347 | 30/30 | 5.5 s | 102,200 |
| [nba-monte-carlo](nba-monte-carlo.md) | 273 | 14/1/258 | 30/30 | 2.3 s | 25,075 |
| [retail-store-sample-app](retail-store-sample-app.md) | 716 | 373/21/322 | 30/30 | 4.0 s | 139,658 |
| [opentelemetry-demo](opentelemetry-demo.md) | 612 | 303/33/276 | 30/30 | 6.0 s | 151,218 |
| [terraform-aws-eks-blueprints](terraform-aws-eks-blueprints.md) | 393 | 211/11/171 | 30/30 | 1.4 s | 22,549 |
