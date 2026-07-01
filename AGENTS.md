# Shared Agent Rules

All agents in this configuration participate in a coordinated workflow.

## Workflow Order

1. **Planner** - Clarifies the request, creates a plan
2. **Debater** - Reviews the plan, suggests improvements
3. **Implementor** - Makes the code changes
4. **Reviewer** - Reviews implementation for correctness
5. **Tester** - Runs relevant tests
6. **Security-reviewer** - Performs security code review
7. **Linter** - Runs formatting/lint checks
8. **Commit-message** - Generates the final commit message

## Shared State Rules

All agents must use `WORKFLOW_STATE.md` as the shared handoff file.

Before starting:
- Read `WORKFLOW_STATE.md`

After finishing:
- Update only the sections relevant to your role
- Preserve existing content unless outdated or incorrect
- Add a short handoff note for the next agent

## Context7 Usage Rules

When working with code, dependencies, libraries, frameworks, or APIs:
- Use context7 before proposing a plan
- Use context7 before implementation if external library behavior is relevant
- Use context7 during review when checking API usage or framework conventions
- Prefer context7 over guessing library behavior from memory
- Record important findings in `WORKFLOW_STATE.md`

## Writing Rules

- Keep entries short and structured
- Prefer bullets over long paragraphs
- Record file paths when discussing code changes
- Record exact test commands and results
- Record unresolved questions under "Open Questions"

## Handoff Rules

- Do not use chat history as the only source of truth
- `WORKFLOW_STATE.md` is the canonical workflow record
- Each agent updates only its own sections
- Set `Next Agent` before finishing to guide the workflow

## Specialized Agents

Beyond the core workflow, these specialized agents are available:
- **Architect** - Deep technical planning and design stress-testing
- **Code Simplifier** - Refactoring and code quality improvements
- **Code Skeptic** - Critical code quality inspection
- **Documentation Specialist** - Writing and maintaining docs
- **Frontend Specialist** - React, TypeScript, CSS expertise
- **Test Engineer** - Test writing and coverage improvement
