# Pull Request

## Description
<!-- Clear and concise description of your changes -->

Fixes #(issue number)

## Type of Change
- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to change)
- [ ] 📚 Documentation update
- [ ] 🔧 Configuration/Infrastructure change
- [ ] ♻️ Refactoring (no functional changes)
- [ ] 🚀 Performance improvement

## Changes Made
<!-- Bullet point list of what you changed -->
- Change 1
- Change 2
- Change 3

## Related Issues
<!-- Link issues with #123 -->
Closes #123

## Testing
<!-- Describe the tests you ran and how to reproduce them -->

### Test Coverage
- [ ] Added new test cases
- [ ] All existing tests still pass
- [ ] Coverage maintained or improved

### Manual Testing
```bash
# Steps to manually verify the change
1. Start the server: python -m gonggang
2. Run: curl http://localhost:8000/groups
3. Verify: Check response format matches spec
```

### Performance Impact
- [ ] No performance impact
- [ ] Improves performance (by ~X%)
- [ ] Possible performance impact (needs review)

## Breaking Changes?
- [ ] No breaking changes
- [ ] Yes, breaking changes (describe below)

<!-- If breaking, describe migration path for users -->

## Checklist
- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests passed locally with my changes
- [ ] Any dependent changes have been merged and published

## Database Migrations
- [ ] No database schema changes
- [ ] New migration included: `migrations/XXX_description.py`
- [ ] Migration tested with `alembic upgrade head`

## Environment Variables
- [ ] No new environment variables required
- [ ] New variables added to `.env.example` and documented in `docs/DEPLOYMENT.md`

## Deployment Notes
<!-- Any special deployment considerations? -->
- Can be deployed in any order
- Requires database migration before deployment
- Requires configuration change
- Other: _______________

## Screenshots/Evidence
<!-- If applicable, add screenshots, logs, or benchmark results -->

## Reviewer Notes
<!-- Any specific areas you'd like reviewers to focus on? -->

## Related PRs
<!-- Link any related PRs -->

## Additional Context
<!-- Any other context? -->

---

**Thank you for contributing to Meet-Match! 🙏**

Please ensure your PR:
1. Has a descriptive title
2. References the related issue
3. Includes tests for new functionality
4. Updates documentation if needed
5. Follows the [Contributing Guidelines](../CONTRIBUTING.md)
