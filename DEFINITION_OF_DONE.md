# Definition of Done

A feature or fix is considered **Done** when ALL of the following are true:

## Code

- [ ] Code Review by at least one peer completed
- [ ] All automated tests passing (unit + integration)
- [ ] No new linting or type-check errors introduced
- [ ] Code follows existing patterns and conventions in the repo
- [ ] No `TODO` / `FIXME` / `HACK` comments left without a linked issue

## Testing

- [ ] Unit tests written or updated for all changed components
- [ ] Edge cases covered (invalid input, empty state, error paths)
- [ ] No tests skipped or commented out without justification

## Documentation

- [ ] Public API changes documented (README, inline docs, or relevant `.md`)
- [ ] CHANGELOG updated (if the repo uses one)

## Security

- [ ] No hardcoded secrets, credentials, or sensitive data
- [ ] Input validation in place for any new user-facing inputs
- [ ] Dependencies up-to-date (no newly introduced known vulnerabilities)

## Production Readiness

- [ ] Feature works end-to-end in the main branch
- [ ] No regressions in previously working functionality
- [ ] Deployment/migration steps documented if applicable
