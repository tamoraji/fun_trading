# Agile Operating Model

This project should run as a small, opinionated agile team with role-specific agents. One human or one agent can cover multiple roles, but the responsibilities should stay separate so decisions do not blur together.

Execution assets:

- Role charters: [`docs/agents/README.md`](/Users/moji/fun_trading/docs/agents/README.md)
- Product backlog: [`docs/backlog/product-backlog.md`](/Users/moji/fun_trading/docs/backlog/product-backlog.md)
- Handoff rules: [`docs/process/handoffs.md`](/Users/moji/fun_trading/docs/process/handoffs.md)
- First sprint: [`docs/sprints/sprint-01.md`](/Users/moji/fun_trading/docs/sprints/sprint-01.md)

## Team shape

Use these seven roles as the default operating model:

1. Product Manager
2. Scrum Master
3. Quant Researcher
4. Tech Lead
5. Developer
6. QA and Validation Engineer
7. Release and Operations Engineer

## Role definitions

### Product Manager

Mission: decide what to build and why.

Responsibilities:

- Own the backlog and priority order
- Define user value and business outcome
- Write feature briefs and acceptance criteria
- Decide scope, non-goals, and release priority

Inputs:

- User needs
- Trading opportunities
- Performance gaps in the current framework

Outputs:

- Feature brief
- Acceptance criteria
- Priority decision

### Scrum Master

Mission: keep delivery flowing.

Responsibilities:

- Run planning, standups, review, and retro
- Keep work items small and sequenced
- Track blockers and dependencies
- Enforce workflow limits and delivery discipline

Inputs:

- Sprint backlog
- Team capacity
- Delivery risks

Outputs:

- Sprint plan
- Daily blocker list
- Retro actions

### Quant Researcher

Mission: define and validate trading logic.

Responsibilities:

- Propose strategy ideas and signal rules
- Define indicator parameters and risk assumptions
- Specify evaluation metrics for strategy changes
- Review whether a new feature improves signal quality

Inputs:

- Market hypothesis
- Historical behavior
- Strategy performance observations

Outputs:

- Research note
- Strategy rules
- Validation thresholds

### Tech Lead

Mission: protect architecture and long-term maintainability.

Responsibilities:

- Choose interfaces, boundaries, and implementation approach
- Break features into technical tasks
- Review code for architecture, safety, and extensibility
- Guard non-functional requirements such as reliability and observability

Inputs:

- Feature brief
- Existing architecture
- Operational constraints

Outputs:

- Design note
- Task breakdown
- Review decisions

### Developer

Mission: turn approved work into tested code.

Responsibilities:

- Implement features, refactors, and bug fixes
- Add or update tests
- Keep docs and config examples current
- Raise risks early when the spec is weak

Inputs:

- Ready stories
- Design guidance
- Acceptance criteria

Outputs:

- Code changes
- Tests
- Documentation updates

### QA and Validation Engineer

Mission: prove the change works and does not break signal quality.

Responsibilities:

- Validate feature behavior against acceptance criteria
- Run regression tests
- Define scenario coverage for strategy changes
- Verify config, edge cases, and failure handling

Inputs:

- Acceptance criteria
- Test plan
- Build candidate

Outputs:

- Validation report
- Defect list
- Release recommendation

### Release and Operations Engineer

Mission: run the framework safely in production.

Responsibilities:

- Manage runtime config, schedules, and notification targets
- Define logging, alerting, and monitoring expectations
- Handle rollout, rollback, and operational checks
- Capture incidents and feed them back into the backlog

Inputs:

- Release candidate
- Environment constraints
- Production incidents

Outputs:

- Release checklist
- Runbook
- Incident summary

## Workflow

Use a simple one-week sprint cadence with strict entry and exit gates.

### 1. Intake

- Product Manager opens a feature brief using the template in [`docs/templates/feature-brief.md`](/Users/moji/fun_trading/docs/templates/feature-brief.md).
- Quant Researcher adds strategy hypothesis and measurement criteria if the work touches signals.
- Scrum Master rejects vague work and sends it back for clarification.

### 2. Discovery and sizing

- Tech Lead checks architecture impact, interfaces, and migration risk.
- QA defines how the feature will be verified.
- Scrum Master splits oversized work before it enters the sprint.

Exit gate:

- Problem is clear
- Acceptance criteria are testable
- Dependencies are known
- Work fits into one sprint

### 3. Sprint planning

- Product Manager presents priority order.
- Scrum Master confirms team capacity.
- Tech Lead breaks the feature into implementation tasks.
- Developer and QA commit to delivery and validation scope.

Outputs:

- Sprint goal
- Selected stories
- Owner for each story
- Clear demo target

### 4. Build

- Developer implements the feature in small increments.
- Tech Lead reviews architecture-impacting choices early, not only at the end.
- QA prepares test data and scenario coverage while development is in progress.
- Scrum Master tracks blockers daily.

Engineering rules:

- New features ship with tests
- Risky behavior goes behind config or a safe default
- Docs and examples change with the code

### 5. Review and validation

- Tech Lead performs code review.
- QA validates behavior, regressions, and edge cases.
- Product Manager checks acceptance criteria.
- Quant Researcher signs off if signal logic changed.

Exit gate:

- Acceptance criteria passed
- Tests green
- Signal behavior explained
- Operational impact understood

### 6. Release

- Release and Operations Engineer confirms config, schedule, notifier targets, and rollback path.
- Release is deployed with monitoring in place.
- Early runtime observations are captured within the first trading session.

### 7. Retrospective and improvement

- Scrum Master runs a short retro at the end of each sprint.
- The team keeps only a small set of measurable improvement actions.
- Incidents, false signals, missed signals, latency issues, and manual pain become backlog items.

## Board states

Use these states on the project board:

1. Idea
2. Backlog
3. Ready
4. In Progress
5. In Review
6. In Validation
7. Release Ready
8. Done

Do not move work into `Ready` until the Definition of Ready is satisfied.

## Definition of Ready

A story is ready when:

- The user or business outcome is explicit
- Acceptance criteria are written
- Non-goals are listed
- Dependencies are known
- Validation approach is defined
- The work is small enough for one sprint

## Definition of Done

A story is done when:

- Code is merged
- Tests are added or updated
- Docs or config examples are updated
- QA validation is complete
- Release checks are complete
- Follow-up metrics are known

## Recommended ceremonies

Keep the cadence lightweight:

- Backlog refinement: once per week
- Sprint planning: once per week
- Daily standup: 10 minutes, async or live
- Sprint review: once per week
- Retrospective: once per week

## Metrics that matter

Track a few meaningful metrics instead of many weak ones:

- Signal precision and recall by strategy
- Time from idea to production
- Change failure rate
- Mean time to detect bad behavior
- Mean time to restore after an issue
- Test coverage of critical paths

## Feature example

If the team wants to add an RSI strategy:

1. Product Manager defines why RSI is worth adding and what success means.
2. Quant Researcher defines RSI thresholds, timeframe, and evaluation cases.
3. Tech Lead decides where the new strategy fits in the current strategy interface.
4. Developer implements the strategy, config wiring, and tests.
5. QA validates expected signals and regressions.
6. Release and Operations Engineer updates runtime config and watches the first live runs.

## Practical note

At this stage, the same person can play several roles, but the role handoff still matters. A feature should move through distinct artifacts and decisions instead of jumping straight from idea to code.
