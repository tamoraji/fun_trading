# Handoff Artifacts

Every role handoff should leave behind a concrete artifact. This keeps the process auditable and prevents features from skipping important thinking.

For the visual sprint flow, see [`docs/process/sprint-workflow.md`](/Users/moji/fun_trading/docs/process/sprint-workflow.md).

## Required artifacts by role

### Product Manager

Artifact: feature brief

Minimum content:

- Problem
- Outcome
- Scope and non-goals
- Acceptance criteria

### Quant Researcher

Artifact: research note

Minimum content:

- Strategy hypothesis
- Rule definition
- Assumptions
- Validation metrics and scenarios

### Tech Lead

Artifact: design note

Minimum content:

- Affected modules
- Interface changes
- Risks
- Task breakdown

### Developer

Artifact: implementation package

Minimum content:

- Code changes
- Tests
- Config or docs updates
- Known limitations

### QA and Validation

Artifact: validation report

Minimum content:

- Acceptance results
- Regression results
- Edge-case findings
- Go or no-go recommendation

### Release and Operations

Artifact: release checklist

Minimum content:

- Runtime config changes
- Rollout plan
- Rollback plan
- Monitoring checks

## Sequence rule

Work should normally move through these artifacts in order:

1. Feature brief
2. Research note, if trading logic changes
3. Design note
4. Implementation package
5. Validation report
6. Release checklist

## Exception rule

If a step is intentionally skipped, the owner must write down:

- What was skipped
- Why it was skipped
- What assumption replaces it
