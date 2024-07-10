from glob import glob

import pytest
from click.testing import CliRunner

from hakai_metadata_conversion.__main__ import cli_main


@pytest.fixture
def runner():
    return CliRunner()


def test_cli_no_args(runner):
    result = runner.invoke(cli_main)
    assert result.exit_code == 2
    assert "Error: Missing option '--input'" in result.output


def test_cli_help(runner):
    result = runner.invoke(cli_main, ["--help"])
    assert result.exit_code == 0
    assert "Usage: cli-main [OPTIONS]" in result.output


def test_cli_on_test_files(runner, tmpdir):
    input_files = "tests/records/*.yaml"
    n_test_files = len(glob(input_files))
    args = [
        "--input",
        input_files,
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


def test_cli_output_file(runner, tmpdir):
    args = [
        "--input",
        "tests/records/*.yaml",
        "--input-file-format",
        "yaml",
        "--output-format",
        "cff",
        "--output-file",
        str(tmpdir / "CITATION.cff"),
    ]
    result = runner.invoke(cli_main, args)
    assert result.exit_code == 0
    assert result.output == ""
    assert len(tmpdir.listdir()) == 1
    assert tmpdir.join("CITATION.cff").check(file=True)
    assert "cff-version: 1.2.0" in tmpdir.join("CITATION.cff").read_text(
        encoding="UTF-8"
    )


def test_cli_with_http_input(runner, tmpdir):
    ouput_file = "CITATION.cff"
    args = [
        "--input",
        "https://raw.githubusercontent.com/HakaiInstitute/hakai-metadata-conversion/main/tests/records/test_record1.yaml",
        "--input-file-format",
        "yaml",
        "--output-format",
        "cff",
        "--output-file",
        str(tmpdir / ouput_file),
    ]
    result = runner.invoke(cli_main, args)
    assert result.exit_code == 0
    assert result.output == ""
    assert len(tmpdir.listdir()) == 1
    assert tmpdir.join(ouput_file).check(file=True)
    assert "cff-version: 1.2.0" in tmpdir.join(ouput_file).read_text(encoding="UTF-8")
