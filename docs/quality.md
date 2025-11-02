# Code Quality and Security

This document summarizes our quality gates and how we enforce them locally and in CI.

## Quality Gates (Codacy)
- New code: 0 Critical / 0 Major issues.
- Coverage: New code ≥ 90% (Codacy UI quality gate).
- Coverage: Project total ≥ 80% (CI-enforced threshold).

Codacy analyzes pull requests and reports a status check. Please keep PRs green before merging.

## CI Enforcement
- Workflow: `.github/workflows/ci.yml`
  - Lint: Ruff (`ruff check fastapi`)
  - Tests + Coverage: `pytest --cov=fastapi --cov-report=xml`
  - Threshold: `coverage report --fail-under=80` (fails CI if total < 80%)
  - Coverage Upload: Codacy Coverage Reporter (requires `CODACY_PROJECT_TOKEN` secret)

## Branch Protection
- Require PR before merge (CODEOWNERS review önerilir)
- Require status checks: Codacy Quality, (Codacy Coverage), CI, CodeQL
- Require conversation resolution; Linear history; No bypass

## Release Validation
1. Tag `vX.Y.Z` → Release workflow çalışır (build+push+deploy)
2. Sunucu: `docker ps`, `docker inspect docker-api-1 | jq .Config.Labels`
3. `curl 127.0.0.1:8080/health` ve `/ready` kontrolü

## Enable Quality Gates in Codacy (UI)
1. Open the project in Codacy Dashboard.
2. Settings → Quality.
3. Quality gate for “New issues”: set Critical/Major = 0.
4. Coverage: set “New code coverage” ≥ 90%.
5. Save. Ensure GitHub branch protection checks include Codacy status.

## Local Workflow
- Install dev deps: `make dev-install`
- Lint: `make lint`
- Format: `make format`
- Type check: `make typecheck`
- Tests + Coverage: `pytest --cov=fastapi --cov-report=term-missing`

## Tools
- Lint/Format: Ruff (PEP8, isort, bugbear, etc.)
- Types: MyPy (keep clean types where possible)
- Static Analysis: Codacy (pylint, semgrep)
- Dependency/Image Scan: Trivy (pinned in CI)

## Notes
- Secrets must never be committed. Use `.env.example` as a template.
- Production should run with `REQUIRE_API_KEY=true` and a strong `API_KEY`.
- For repositories with external services (OpenAI, Qdrant), integration tests should be marked with `integration`.

If you have questions or want to tune thresholds, open a PR to edit this file and/or the CI workflow.

<!-- e2e: codacy gate test -->
