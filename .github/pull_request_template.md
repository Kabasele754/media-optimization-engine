## Summary

Describe the change and why it is needed.

## Validation

- [ ] Tests added or updated where appropriate
- [ ] `python -m compileall media_engine` passes
- [ ] Package builds successfully
- [ ] Django migrations reviewed when models changed
- [ ] Documentation updated for public behavior/settings changes
- [ ] No secrets, credentials, private media, or generated local artifacts committed

## Media pipeline checks

- [ ] Originals remain immutable
- [ ] No duplicate image/panorama processing path introduced
- [ ] Local eager mode and production Celery behavior considered
- [ ] Backward compatibility considered
