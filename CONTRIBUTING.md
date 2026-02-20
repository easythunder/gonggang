# Contributing to Meet-Match

Thank you for your interest in contributing to Meet-Match! This document provides guidelines and instructions for contributing.

## Table of Contents
- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Code Style](#code-style)
- [Documentation](#documentation)

## Code of Conduct

### Our Pledge
We are committed to providing a welcoming and inspiring community for all. Please read and adhere to our Code of Conduct:
- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Report concerns to maintainers

### Expected Behavior
- Use welcoming and inclusive language
- Be respectful of differing opinions and experiences
- Accept constructive criticism gracefully
- Focus on what is best for the community
- Show empathy towards other community members

## Getting Started

### Prerequisites
- Python 3.11+
- PostgreSQL 14+ (for development)
- Git
- Docker (optional, for isolated development)

### Fork and Clone
```bash
# 1. Fork the repository on GitHub
# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/gonggang.git
cd gonggang

# 3. Add upstream remote
git remote add upstream https://github.com/company/gonggang.git

# 4. Keep your fork in sync
git fetch upstream
git checkout main
git merge upstream/main
```

## Development Setup

### 1. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development extras
```

### 3. Setup Database
```bash
# Create database
createdb gonggang_dev

# Set environment variable
export DATABASE_URL=postgresql://localhost/gonggang_dev

# Run migrations
alembic upgrade head
```

### 4. Verify Setup
```bash
# Run tests
pytest tests/ -v

# Start server
python -m gonggang

# Test endpoint
curl http://localhost:8000/health
```

## Making Changes

### 1. Create Feature Branch
```bash
# Update main
git fetch upstream
git checkout main
git merge upstream/main

# Create feature branch
git checkout -b feature/your-feature-name
# or bug/issue-description
# or docs/documentation-improvement
```

### Branch Naming Convention
- `feature/` - New features
- `bug/` - Bug fixes
- `docs/` - Documentation
- `refactor/` - Code refactoring
- `perf/` - Performance improvements
- `chore/` - Build, dependencies, tools

### 2. Make Your Changes
- Keep changes focused and atomic
- Make logical commits with clear messages
- Follow the code style (see below)
- Add/update tests
- Update documentation

### Commit Message Guidelines
```
[TYPE] Short summary (50 chars max)

Longer description explaining the change (72 chars per line).
- Bullet points are OK
- Explain what and why, not how

Fixes #123
```

**Commit Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`

## Testing

### Run All Tests
```bash
# All tests with coverage
pytest tests/ --cov=src --cov-report=html

# Specific test file
pytest tests/unit/services/test_groups.py -v

# Specific test
pytest tests/unit/services/test_groups.py::TestGroupService::test_create_group -v
```

### Test Organization
```
tests/
├── unit/              # Fast, isolated unit tests
│   ├── services/
│   ├── repositories/
│   └── schemas/
├── integration/       # Tests with real DB
│   ├── api/
│   └── services/
└── performance/       # Load/stress tests
    ├── load_test.py
    └── profile_*.py
```

### Testing Requirements
- **New Features**: Must include tests
- **Bug Fixes**: Should include a test that reproduces the bug
- **Coverage Target**: 85%+
- **No Regressions**: All existing tests must pass

### Test Naming Convention
```python
# Unit test
def test_function_name_with_input_produces_expected_output():
    pass

# Integration test  
def test_endpoint_with_valid_data_returns_200():
    pass

# Parameterized test
@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (3, 4),
])
def test_calculation(input, expected):
    pass
```

## Submitting Changes

### 1. Push to Your Fork
```bash
git push origin feature/your-feature-name
```

### 2. Create Pull Request
- Go to GitHub and create a PR
- Use the PR template
- Link related issue with "Fixes #123"
- Describe your changes clearly
- Ensure all CI checks pass

### 3. PR Guidelines
- **Title**: Clear and concise (50 chars max)
  - ✅ `feat: add caching for free-time results`
  - ❌ `updates` or `fixes stuff`
- **Description**: Use the template
- **Tests**: Include tests for all changes
- **Documentation**: Update docs if needed
- **No merge conflicts**: Resolve before submitting

### 4. Code Review Process
- At least 2 approvals required
- Automated checks must pass
- Address feedback promptly
- Maintain respectful discussion

## Code Style

### Python Code Style
We follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) with some modifications:

#### Formatting
```bash
# Format code
black src/ tests/

# Check style
flake8 src/ tests/

# Type checking
mypy src/
```

#### Import Organization
```python
# Standard library
import os
import sys
from typing import Optional, List

# Third-party packages
from fastapi import FastAPI
from sqlalchemy import Column, String

# Local imports
from src.config import settings
from src.models import Group
```

#### Example Code
```python
# Good: Clear, readable, type-hinted
def calculate_free_time(
    intervals: List[Interval],
    display_unit_minutes: int,
) -> List[TimeSlot]:
    """Calculate common free time for multiple participants.
    
    Args:
        intervals: List of availability intervals
        display_unit_minutes: Granularity for time slots
        
    Returns:
        List of common free time slots
        
    Raises:
        ValueError: If intervals are invalid
    """
    if not intervals:
        return []
    
    # Implementation...
    return free_slots
```

#### Naming Conventions
- `ClassName` - CamelCase for classes
- `function_name()` - snake_case for functions
- `CONSTANT_NAME` - UPPER_SNAKE_CASE for constants
- `_private_method()` - Leading underscore for private
- `variable_name` - snake_case for variables

### File Organization
```python
# 1. File docstring
"""Module description."""

# 2. Imports (organized)
import os
from typing import Optional

from fastapi import FastAPI
from sqlalchemy import Column

from src.config import settings

# 3. Constants
MIN_SLOT_MINUTES = 5
MAX_PARTICIPANTS = 100

# 4. Classes
class MyClass:
    pass

# 5. Functions
def my_function():
    pass

# 6. Main block
if __name__ == "__main__":
    pass
```

## Documentation

### Update Guidelines
- Update documentation for any behavior changes
- Add docstrings to all public functions
- Include type hints
- Add examples for new features

### Documentation Files
- **README.md** - Project overview, quick start
- **docs/ARCHITECTURE.md** - Design decisions
- **docs/DEPLOYMENT.md** - Deployment guide
- **docs/RUNBOOKS.md** - Operational procedures
- **docs/MONITORING.md** - Monitoring and alerts
- **Code Comments** - Complex logic explanation

### Example Docstring
```python
def create_group(group_name: str, display_unit_minutes: int) -> Group:
    """Create a new meeting group.
    
    A group can have multiple participants who submit their availability
    schedules. Once submitted, the system calculates their common free time.
    
    Args:
        group_name: Unique identifier for the group
        display_unit_minutes: Time slot granularity (5, 10, 15, 30, 60)
        
    Returns:
        Created Group object with generated UUID
        
    Raises:
        ValueError: If display_unit_minutes not in [5, 10, 15, 30, 60]
        DuplicateError: If group_name already exists
        
    Example:
        >>> group = create_group("study_session", 30)
        >>> print(group.group_id)
        550e8400-e29b-41d4-a716-446655440000
    """
    # Implementation...
    pass
```

## Getting Help

### Communication Channels
- **Issues**: Report bugs and request features
- **Discussions**: Ask questions and discuss ideas
- **Email**: gonggang-support@example.com
- **Slack**: #gonggang channel in company Slack

### Common Questions
See [docs/FAQ.md](../docs/FAQ.md) for common questions and answers.

## License

By contributing to Meet-Match, you agree that your contributions will be licensed under its MIT License.

---

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [pytest Documentation](https://docs.pytest.org/)
- [Architecture Guide](../docs/ARCHITECTURE.md)
- [API Specification](../specs/)

---

**Thank you for contributing! 🎉**
