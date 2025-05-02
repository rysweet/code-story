import os
from code_story.cli import main

def test_cli_main_output(capsys):
    # Test that main prints the CLI usage message
    main()
    captured = capsys.readouterr()
    assert "Code-Story CLI" in captured.out


def test_project_files_exist():
    # Check that essential scaffolding files exist
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    assert os.path.exists(os.path.join(project_root, 'README.md'))
    assert os.path.exists(os.path.join(project_root, 'LICENSE'))
    assert os.path.exists(os.path.join(project_root, 'pyproject.toml'))
    assert os.path.exists(os.path.join(project_root, 'package.json'))
    assert os.path.exists(os.path.join(project_root, 'docker-compose.yml'))
