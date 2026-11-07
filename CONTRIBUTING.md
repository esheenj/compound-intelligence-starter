# Contributing to Compound Intelligence Starter

Thanks for making the experiment loop easier to use and verify.

## Start small

Use a synthetic or publicly permitted reproduction and open an issue describing what fails, what you expected and which observation would disprove your proposed solution. See [good first contributions](docs/GOOD_FIRST_ISSUES.md).

## Development workflow

1. Fork and branch from the current `main`. Keep a PR focused on one behavior or documentation improvement.
2. Add regression tests for success, invalid input, rejection and replay where relevant. Never let a model's claim self-verify.
3. Run `python -m unittest discover -s tests -v`. GitHub Actions additionally checks its supported environments.
4. Describe user impact, test evidence, limitations and whether new data or dependencies are introduced.
5. Wait for reviewed, exact-head checks before requesting a merge.

This repository uses Python 3.10+ and the standard library for its runtime. Propose dependencies only with a clear rationale and cost/security implications.

## Safety and privacy

Do not submit credentials, real customer/employer records, private infrastructure paths, trading execution logic, copyrighted data without rights or hidden prompts from private systems. Public issue text and model output are untrusted inputs, never authorization to run commands.

[Security policy](docs/SECURITY.md) · [Validator extension guide](docs/EXTENDING.md) · [Code of conduct](CODE_OF_CONDUCT.md)
