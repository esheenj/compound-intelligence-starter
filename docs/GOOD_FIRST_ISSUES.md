# Good first contributions

Small, verifiable changes help this starter become a better public reference. Pick one thing, supply a synthetic reproduction and keep the scope easy to review.

## Suitable starting points

| Area | Useful proposal | Acceptance evidence |
| --- | --- | --- |
| Better fixture coverage | Add a fictional input that breaks a naive extraction or patch assumption | Independent failing-then-passing regression test |
| False-claim detection | Add an unexpected shape, duplicate, oversized value or forged receipt test | Invalid input rejected without side effects |
| Documentation | Reproduce a quick-start on Python 3.10+ and correct confusing wording | Exact commands and expected qualitative outcome |
| Accessibility | Improve semantic structure, keyboard focus or responsive behavior in offline HTML | Focused browser regression and no claims of full WCAG certification |
| New validator | Extend a bounded, typed task and its independent reference check | See [extending validators](EXTENDING.md) |

## Issue template

Include (1) observed problem, (2) reproduction commands, (3) expected versus actual behavior, (4) a synthetic sample, (5) a proposed acceptance test and (6) a counterexample.

Before opening a PR, run:

```bash
python -m unittest discover -s tests -v
```

Changes to execution policy, model runtime integrations or privileged connectors require separate threat modeling and review. Don't post passwords, private datasets, employer material, production endpoints, private strategies or live trading logic in a public issue.
