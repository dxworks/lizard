# AGENTS Guide for lizard
This file is the default playbook for agentic coding tools in this repository.

## Project Overview
- Language: Python, with legacy compatibility patterns in core modules.
- Main code: `lizard.py`, `lizard_ext/`, `lizard_languages/`.
- Tests: `test/` (mostly `unittest` style, usually run with `pytest`).
- Build/packaging: `setup.py`, `setup.cfg`, `Makefile`.

## Repository Layout
- `lizard.py`: CLI entrypoint and analysis orchestration.
- `lizard_ext/`: extension modules and output backends.
- `lizard_languages/`: parser/readers and language state machines.
- `test/`: analyzer, extension, output, and language tests.
- `dev_requirements.txt`: dev/lint/test dependencies.
- `pylintrc`: style, naming, and lint constraints.

## Environment Setup
Run from repo root:

```bash
python -m pip install -e .
python -m pip install -r dev_requirements.txt
python setup.py build install
```

Optional all-in-one setup:

```bash
bash build.sh
```

## Build/Lint/Test Commands
Canonical `Makefile` targets:

```bash
make            # extensive + pylint
make extensive  # tests + pep8
make tests      # coverage run -m pytest test; coverage report -m
make tests3     # python3 -m unittest test
make pep8       # pycodestyle lizard.py lizard_ext lizard_languages
make pylint     # pylint --exit-zero --rcfile pylintrc lizard.py lizard_ext lizard_languages
make build      # python3 setup.py sdist && python3 setup.py bdist_wheel
```

Direct alternatives:

```bash
pytest test
pytest -q test
python -m unittest test
```

### Running a Single Test
Preferred patterns:

```bash
pytest test/test_analyzer.py::TestWarningFilter::test_should_filter_the_warnings
pytest test/test_analyzer.py -k should_filter_the_warnings
python -m unittest test.test_analyzer.TestWarningFilter.test_should_filter_the_warnings
```

Focused subsets:

```bash
pytest test/test_languages
pytest test/test_extensions
pytest test/test_output.py
```

## CI/Release Context
- Historical CI files exist: `.travis.yml`, `.appveyor.yml`.
- GitHub workflow exists: `.github/workflows/release-voyager.yml` (release tags only).
- There is no current PR-gating CI workflow in this repo.
- Agents should run relevant tests/lint locally before finalizing changes.

## Code Style Guidelines

### Compatibility and Syntax
- Preserve legacy-compatible style in core modules.
- Keep `from __future__` imports when present in a file.
- Avoid Python-3-only syntax in legacy paths unless surrounding code already uses it.
- Avoid introducing annotation syntax that can break older runtime expectations.

### Formatting
- Follow `pylintrc` defaults: 4-space indentation, 80-char line length.
- Wrap long expressions instead of exceeding line limits.
- Keep edits focused; avoid drive-by formatting changes.

### Imports
- Use this import order:
  1. `__future__` imports.
  2. Standard library.
  3. Third-party packages.
  4. Local modules.
- Prefer explicit imports over wildcard imports.
- Match local style in touched files when uncertain.

### Naming Conventions
`pylintrc` naming regexes are authoritative:

- Modules: `([a-z_][a-z0-9_]*)|([A-Z][a-zA-Z0-9]+)`.
- Functions/methods/variables/args: `snake_case` in `[a-z_][a-z0-9_]{2,30}`.
- Classes: `PascalCase` in `[A-Z_][a-zA-Z0-9]+`.
- Constants: `UPPER_CASE` in `[A-Z_][A-Z0-9_]*`.

Additional naming notes:
- Some tests use legacy names (for example `test_OneFile`); follow local file style.
- Prefer descriptive names unless common domain terms already exist (`CCN`, `nloc`).

### Types and Data Structures
- The repo is not heavily type-hinted.
- Prioritize runtime clarity/compatibility over annotation-heavy refactors.
- Reuse established domain classes (`FunctionInfo`, `FileInformation`, etc.).

### Error Handling
- Treat file/read/encoding/parser failures as recoverable where possible.
- Catch specific exceptions before broad ones.
- In CLI flows, align with existing messaging style (`sys.stderr.write(...)`).
- Do not silently swallow exceptions unless behavior intentionally requires it.

### Testing
- Add/update tests for any behavior change.
- Prefer targeted regression tests for bug fixes.
- Keep tests deterministic and scoped.
- If parser logic changes, run relevant tests in `test/test_languages/`.

### Linting
- Run `make pep8` and `make pylint` (or equivalent direct commands) for touched areas.
- Keep pylint suppressions minimal and justified.
- Do not remove existing suppressions unless explicitly part of the task.

## Agent Working Rules
- Read nearby code before editing; mirror local idioms.
- Avoid broad refactors unless explicitly requested.
- Keep CLI options/output behavior backward-compatible unless task requires changes.
- Do not edit vendored assets under `website/static/bower/` unless required.

## Cursor/Copilot Instruction Files
Checked locations:
- `.cursorrules`
- `.cursor/rules/`
- `.github/copilot-instructions.md`

Current status:
- No Cursor rules found.
- No Copilot instruction file found.

If these files appear later, treat them as higher-priority repo instructions and update this guide.

## Quick Agent Checklist

```bash
pytest test
make pep8
make pylint
```

For small scoped changes, run at least one relevant single-test command plus the most relevant lint/test subset.
