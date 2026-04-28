import unittest
import platform
from unittest.mock import patch
from lizard import get_all_source_files
import os


def which_system():
    return platform.system()


class TestIgnoreFile(unittest.TestCase):
    def _setup_mocks(self, mock_exists, mock_relpath):
        def exists_side_effect(path):
            return path.endswith('.ignore')
        mock_exists.side_effect = exists_side_effect
        
        def relpath_side_effect(path, start):
            if path.startswith('./'):
                path = path[2:]
            return path.replace(os.sep, '/')
        mock_relpath.side_effect = relpath_side_effect

    def _assert_files(self, actual_files, expected_files):
        if which_system() == "Windows":
            expected = [f".\\{f}" for f in expected_files]
        else:
            expected = [f"./{f}" for f in expected_files]
        self.assertEqual(expected, list(actual_files))

    @patch.object(os.path, "exists")
    @patch.object(os.path, "relpath")
    @patch.object(os, "walk")
    @patch("lizard.auto_read")
    def test_ignore_file_filters_node_modules(self, mock_auto_read, mock_os_walk, mock_relpath, mock_exists):
        self._setup_mocks(mock_exists, mock_relpath)
        mock_os_walk.return_value = (['.',
                                    None,
                                    ['temp.c', 'node_modules/file.js', 'useful.cpp']], )
        mock_auto_read.return_value = "**node_modules**\n"
        
        files = get_all_source_files(["dir"], [], [])
        self._assert_files(files, ['temp.c', 'useful.cpp'])

    @patch.object(os.path, "exists")
    @patch.object(os.path, "relpath")
    @patch.object(os, "walk")
    @patch("lizard.auto_read")
    def test_ignore_file_filters_multiple_patterns(self, mock_auto_read, mock_os_walk, mock_relpath, mock_exists):
        self._setup_mocks(mock_exists, mock_relpath)
        mock_os_walk.return_value = (['.',
                                    None,
                                    ['Form1.Designer.cs', 'app.min.js', 'bin/Debug/app.exe', 'src/main.cpp', 'obj/Release/temp.o']], )
        mock_auto_read.return_value = "**.Designer.cs**\n**.min.js**\n**/bin/Debug/**\n**/obj/Release/**\n"
        
        files = get_all_source_files(["dir"], [], [])
        self._assert_files(files, ['src/main.cpp'])

    @patch.object(os.path, "exists")
    @patch.object(os.path, "relpath")
    @patch.object(os, "walk")
    @patch("lizard.auto_read")
    def test_project_ignore_file_filters_all_patterns(self, mock_auto_read, mock_os_walk, mock_relpath, mock_exists):
        self._setup_mocks(mock_exists, mock_relpath)
        # One file per pattern in the real .ignore, plus a few that must NOT be filtered.
        # All entries below use source-code extensions so lizard's own
        # extension filter does not interfere; only the .ignore filter
        # decides whether they are kept or dropped.
        mock_os_walk.return_value = (['.',
                                    None,
                                    [
                                        'repo/node_modules/file.js',     # **node_modules**
                                        'repo/.git/config.cs',           # **.git**
                                        'src/Form1.Designer.cs',         # **.Designer.cs**
                                        'src/Form1.Designer.vb',         # **.Designer.vb**
                                        'static/app.min.js',             # **.min.js**
                                        'static/app.min.ts',             # **.min.ts**
                                        'proj/bin/Debug/app.cs',         # **/bin/Debug/**
                                        'proj/bin/Release/app.cs',       # **/bin/Release/**
                                        'proj/bin/x64/Debug/file.cs',    # **/bin/x64/Debug
                                        'proj/bin/x64/Release/app.cs',   # **/bin/x64/Release/**
                                        'proj/obj/Debug/temp.cpp',       # **/obj/Debug/**
                                        'proj/obj/Release/temp.cpp',     # **/obj/Release/**
                                        'proj/obj/x64/Debug/temp.cpp',   # **/obj/x64/Debug/**
                                        'proj/obj/x64/Release/temp.cpp', # **/obj/x64/Release/**
                                        'src/main.cpp',                  # kept
                                        'lib/util.py',                   # kept
                                        'Form1.cs',                      # kept (not Designer.cs)
                                    ]], )
        mock_auto_read.return_value = (
            "**node_modules**\n"
            "**.git**\n"
            "**.Designer.cs**\n"
            "**.Designer.vb**\n"
            "**.min.js**\n"
            "**.min.ts**\n"
            "**/bin/Debug/**\n"
            "**/bin/Release/**\n"
            "**/bin/x64/Debug\n"
            "**/bin/x64/Release/**\n"
            "**/obj/Debug/**\n"
            "**/obj/Release/**\n"
            "**/obj/x64/Debug/**\n"
            "**/obj/x64/Release/**\n"
        )

        files = get_all_source_files(["dir"], [], [])
        self._assert_files(files, [
            'src/main.cpp',
            'lib/util.py',
            'Form1.cs',
        ])
