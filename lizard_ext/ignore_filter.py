import os


def load_ignore_spec(paths, auto_read_func):
    '''
    Load .ignore file patterns from the given paths.
    Returns a tuple of (ignore_spec, base_path) or (None, None) if no .ignore file found.
    '''
    try:
        import pathspec
        for path in paths:
            ignore_path = os.path.join(path, '.ignore')
            if os.path.exists(ignore_path):
                ignore_file = auto_read_func(ignore_path)
                patterns = [line.strip() for line in ignore_file.splitlines()]
                patterns = [p for p in patterns if p and not p.startswith('#')]
                ignore_spec = pathspec.PathSpec.from_lines('gitignore', patterns)
                print("Loaded .ignore file from '%s' with %d pattern(s): %s" % (ignore_path, len(patterns), ', '.join(patterns)))
                return ignore_spec, path
    except ImportError:
        pass
    return None, None


def should_ignore_file(pathname, ignore_spec, base_path):
    '''
    Check if a file should be ignored based on .ignore patterns.
    Returns True if the file should be ignored, False otherwise.
    '''
    if ignore_spec is not None and base_path is not None:
        rel_path = os.path.relpath(pathname, base_path)
        rel_path = rel_path.replace(os.sep, '/')
        if ignore_spec.match_file(rel_path):
            return True
    return False
