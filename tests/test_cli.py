import pytest
from glob import glob

from click.testing import CliRunner
from hakai_metadata_conversion.__main__ import cli_main


@pytest.fixture
def runner():
    return CliRunner()


def test_cli_on_test_files(runner, tmpdir):
    input_files = "tests/records/*.yaml"
    n_test_files = len(glob(input_files))
    args = [
        "--input",
        "tests/records/*.yaml",
        "--input-file-format",
        "yaml",
        "--output-format",
        "cff",
        "--output-dir",
        str(tmpdir),
    ]
    result = runner.invoke(cli_main, args)
    assert result.exit_code == 0
    assert result.output == ""
    assert len(tmpdir.listdir()) == n_test_files

