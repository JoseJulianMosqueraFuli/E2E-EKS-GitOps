"""
Tests for the main.py entry point module.
"""

import pytest
from unittest.mock import patch

from src.main import main


class TestMainFunction:
    """Tests for the main() entry point."""

    def test_main_is_callable(self):
        """Test that main() function exists and is callable."""
        assert callable(main)

    def test_main_help_flag(self, capsys):
        """Test that --help prints usage and exits cleanly."""
        with patch('sys.argv', ['main', '--help']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_main_no_args_prints_help(self, capsys):
        """Test that calling with no subcommand prints help (no crash)."""
        with patch('sys.argv', ['main']):
            # main() with no subcommand calls print_help()
            # and returns None
            main()

    def test_main_unknown_args_exits(self):
        """Test that unknown arguments cause SystemExit."""
        with patch('sys.argv', ['main', '--nonexistent-flag']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code != 0


class TestSubcommandParsers:
    """Tests for each subcommand's argument parser setup."""

    def test_train_help(self):
        """Test that 'train --help' exits with code 0."""
        with patch('sys.argv', ['main', 'train', '--help']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_inference_help(self):
        """Test that 'inference --help' exits with code 0."""
        with patch('sys.argv', ['main', 'inference', '--help']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_validate_help(self):
        """Test that 'validate --help' exits with code 0."""
        with patch('sys.argv', ['main', 'validate', '--help']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_create_sample_help(self):
        """Test that 'create-sample --help' exits with code 0."""
        with patch('sys.argv', ['main', 'create-sample', '--help']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_setup_help(self):
        """Test that 'setup --help' exits with code 0."""
        with patch('sys.argv', ['main', 'setup', '--help']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0


class TestSubcommandDispatch:
    """Tests verifying subcommands dispatch to the correct function."""

    def test_train_requires_data_path(self):
        """Test that 'train' without data_path causes SystemExit."""
        with patch('sys.argv', ['main', 'train']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code != 0

    def test_inference_requires_data_path(self):
        """Test that 'inference' without data_path causes SystemExit."""
        with patch('sys.argv', ['main', 'inference']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code != 0

    def test_validate_requires_data_path(self):
        """Test that 'validate' without data_path causes SystemExit."""
        with patch('sys.argv', ['main', 'validate']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code != 0

    def test_create_sample_requires_output_path(self):
        """Test that 'create-sample' without output_path causes SystemExit."""
        with patch('sys.argv', ['main', 'create-sample']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code != 0

    def test_verbose_flag_accepted(self):
        """Test that --verbose flag is accepted without error."""
        with patch('sys.argv', ['main', '--verbose']):
            # Should not raise; just prints help since no subcommand
            main()
