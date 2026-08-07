---
name: post-change-refactor
description: >-
  Refactor and clean up the uncommitted change before committing. Eliminate
  duplication, rename unclear domain concepts, collapse shotgun surgery when
  another similar change is likely, remove dead / test-only / redundant code,
  split files larger than 250 lines into cohesive modules, and confirm
  related tests still pass. Use after finishing a phase or sub-phase and
  before commit, or whenever the developer asks to clean up the current
  change. Triggers on: refactor change, clean up change, post-change
  refactor, before commit cleanup, tidy current change.
---

# Post-Change Refactor — Clean the Current Change Before Commit

## When to use

- After the implementation of a phase / sub-phase finishes and **before**
  the commit.
- On demand, when the developer asks to clean up or refactor the current
  uncommitted change.

Start with `.cursor/rules/` for project conventions and test practices.

## Scope: "the current change"

The current change = files touched since the last commit (staged + unstaged
+ untracked). Discover the scope:

```bash
git status
git diff
git diff --cached
```

**Git does not use the Nix prefix.** All other repo tooling does.

All refactoring work is scoped to those files and the files that
directly depend on them or are depended on by them. Do **not** sweep
unrelated parts of the repo.

## Decision boundary

Only keep code that is justified by **the current change** or by the
**immediate next phase** in the plan (if one exists).
Anything justified only by a phase further out, or by "we might need it
later", is speculative — remove it.

If there is no plan, justification must come entirely from the current
change.

## Procedure

Run each check below in order. After all checks pass, **hand control back
to the caller** — do **not** commit from inside this skill.

### 1. Duplication

- Look for **new** duplication introduced by the change (copy-pasted
  blocks, parallel structures with cosmetic differences).
- Look for duplication the change made **visible** — the new code repeats
  logic that already existed elsewhere.
- The same concept appearing in two representations counts as duplication,
  not just literal copies.
- **Action**: collapse onto a single representation. Prefer reusing an
  existing helper in the right layer (language reader, extension, shared
  tokenizer utility) over inventing a new one.

### 2. Domain naming

- Read every new or renamed identifier — files, modules, classes,
  functions, variables, tests, fixtures.
- Ask: does the name match what a domain reader expects? Does it match
  Lizard's language (complexity metrics, language readers, tokens, state
  machines, CCN, NLOC, etc.)?
- **Action**: rename when intent is unclear, misleading, mixes layers, or
  leaks phase numbers / sequence info. Names describe **capability**, not
  development history.

### 3. Shotgun surgery

- A change is shotgun surgery when **one logical concept** forces edits
  in many places.
- Estimate the likelihood of another change of the same shape in the
  foreseeable future.
- **Action**:
  - **High likelihood** → consolidate the scattered edits behind a single
    seam (one function, one config, one module) so the next change touches
    one place. Do it now.
  - **Low likelihood** → leave it. Do not preemptively abstract.

### 4. Dead / redundant / cancelling code

Remove aggressively whatever the change introduced or exposed that is not
justified by the current change or the immediate next phase:

- Code with no caller.
- Branches that cannot be reached.
- Pairs of edits that cancel each other (added then immediately worked
  around, flag toggles that never flip, etc.).
- Production code only exercised by unit tests — no real caller from the
  CLI (`lizard` command), `analyze_file` API, language reader pipeline,
  or extension hook.
- Unit tests that overlap with another test on the same observable
  surface (same input/output, same entry point).
- Tests that pin internal structure rather than observable behavior — if
  a test mainly mirrors the code's factoring, drop it in favor of the
  test that drives a high-level entry point (`analyze_file`,
  `analyze_source_code`, CLI output).

When in doubt, **delete**. The next phase, if relevant, will reintroduce
only what it actually needs.

### 5. File size

For every file touched by the change, check line count:

```bash
wc -l <path>
```

- Files **over 250 lines** must be split. This rule is applied to test code as well.
- Split along **cohesive seams** — one concept per module, not arbitrary
  line cuts.
- Update imports. Keep the public API stable for callers outside the
  change.

### 6. Confirm related tests still pass

Run **related** tests for the changed files — not the whole suite. Use
`nix develop -c …` for all commands below except `git`.

| Area touched | Focused command |
|--------------|-----------------|
| Core analyzer (`lizard.py`, `lizard_ext/`) | `nix develop -c python -m pytest test/test_analyzer.py test/testOutput.py` (add other top-level tests if those modules changed) |
| Language reader (`lizard_languages/`) | `nix develop -c python -m pytest test/test_languages/test<Lang>.py` for each affected language |
| Extension (`lizard_ext/`) | `nix develop -c python -m pytest test/test_extensions/test<Name>.py` for each affected extension |
| CLI / options | `nix develop -c python -m pytest test/testApplication.py test/test_options.py` |
| Broad or cross-cutting change | `nix develop -c python -m pytest` |

Prefer `analyze_file` / `analyze_source_code` integration tests and CLI
output tests over tests that only exercise internal helpers.

All related tests must pass before returning. If a test breaks because of
the refactor (not the original change), fix it now.

## Return

Report a short summary to the caller:

1. Which checks led to changes — duplication / naming / shotgun /
   dead code / file size.
2. Files renamed, extracted, split, or deleted.
3. Which related tests were run and confirmed passing.

Then hand control back. **Do not commit from inside this skill** — the
caller commits.

## Out of scope

- Do not redesign code outside the changed files.
- Do not start a new phase or add new behavior. Only restructure and
  remove.
- Do not run the entire test suite or trigger CI from inside this skill
  unless the change is broad enough that focused tests cannot cover it.
