import os
import re
import sys


# NOTE: We avoid `pathspec` here because lizard is run from source
# (e.g. `python3 lizard.py ...` in the Voyager instrument) without being
# pip-installed, so its declared dependencies are not available. Using the
# stdlib keeps `.ignore` working in that mode.


def _translate_pattern(pattern):
    '''
    Translate a gitignore-style glob pattern into a regex string.
    Supports the subset used in .ignore: '**', '*', '?' and literal segments.
    The resulting regex is anchored and also matches descendants of a matched
    directory (mimics gitignore's "ignore dir => ignore its contents" rule).
    '''
    out = []
    i = 0
    n = len(pattern)
    while i < n:
        if pattern[i:i+3] == '**/':
            out.append('(?:.*/)?')
            i += 3
        elif pattern[i:i+3] == '/**':
            out.append('(?:/.*)?')
            i += 3
        elif pattern[i:i+2] == '**':
            out.append('.*')
            i += 2
        elif pattern[i] == '*':
            out.append('[^/]*')
            i += 1
        elif pattern[i] == '?':
            out.append('[^/]')
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    # Allow matching descendants of a matched directory.
    return '^' + ''.join(out) + '(?:/.*)?$'


def compile_ignore_patterns(patterns):
    '''Compile a list of .ignore patterns into a list of regex objects.'''
    return [re.compile(_translate_pattern(p)) for p in patterns]


def path_matches(rel_path, compiled_patterns):
    '''Return True if rel_path matches any of the compiled patterns.'''
    rel_path = rel_path.replace(os.sep, '/')
    return any(rx.match(rel_path) for rx in compiled_patterns)


def load_ignore_spec(auto_read_func):
    '''
    Load .ignore file patterns from the current working directory.
    Returns a tuple of (compiled_patterns, base_path) or (None, None) if
    no .ignore file is found.
    '''
    cwd_ignore_path = os.path.join(os.getcwd(), '.ignore')
    if not os.path.exists(cwd_ignore_path):
        sys.stderr.write("No .ignore file found at '%s'\n" % cwd_ignore_path)
        return None, None

    ignore_file = auto_read_func(cwd_ignore_path)
    patterns = [line.strip() for line in ignore_file.splitlines()]
    patterns = [p for p in patterns if p and not p.startswith('#')]
    compiled = compile_ignore_patterns(patterns)
    sys.stderr.write("Loaded .ignore file from '%s' with %d pattern(s): %s\n"
                     % (cwd_ignore_path, len(patterns), ', '.join(patterns)))
    return compiled, os.getcwd()


def should_ignore_file(pathname, ignore_spec, base_path):
    '''
    Check if a file should be ignored based on .ignore patterns.
    Returns True if the file should be ignored, False otherwise.
    '''
    if ignore_spec is None or base_path is None:
        return False
    try:
        rel_path = os.path.relpath(pathname, base_path)
    except ValueError:
        # On Windows, relpath fails when paths are on different drives
        # (e.g., C: vs D:). Fall back to using absolute path for pattern matching.
        rel_path = pathname
    return path_matches(rel_path, ignore_spec)
