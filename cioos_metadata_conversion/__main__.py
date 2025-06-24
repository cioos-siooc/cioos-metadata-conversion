from glob import glob
from pathlib import Path

import click
from loguru import logger

from cioos_metadata_conversion import erddap
from cioos_metadata_conversion.converter import OUTPUT_FORMATS, Converter, InputSchemas


def load(file: str, schema: str = "CIOOS"):
    """Load a metadata record from a file or URL."""
    record = (
        Converter(source=file, schema=InputSchemas[schema])
        .load()
        .convert_to_cioos_schema()
    )

    if not record.metadata:
        raise ValueError(f"No metadata record found in file {file}.")

    return record.metadata


@click.group(name="cioos-metadata-conversion")
def cli():
    """CIOOS Metadata Conversion CLI.
    Convert metadata records to different metadata formats or standards.
    """
    pass


cli.add_command(erddap.update, name="erddap-update")


@cli.command(name="convert")
@click.option("--input", "-i", required=True, help="Input file.")
@click.option(
    "--recursive", "-r", is_flag=True, help="Process files recursively.", default=False
)
@click.option(
    "--input-schema",
    required=True,
    default="CIOOS",
    help="Input file format (json or yaml).",
    type=click.Choice(InputSchemas.__members__.keys()),
    show_default=True,
)
@click.option(
    "--encoding",
    default="utf-8",
    help="Encoding of the input file.",
    show_default=True,
)
@click.option(
    "--output-dir",
    "-p",
    type=click.Path(file_okay=False),
    help="Output directory, the original file name will be used.",
    default=".",
    show_default=True,
)
@click.option(
    "--output-file",
    "-o",
    type=click.Path(),
    help="Output file, this will override the output directory and is only valid for a single input file.",
)
@click.option(
    "--output-format",
    "-f",
    required=True,
    help="Output format",
    type=click.Choice(OUTPUT_FORMATS.keys()),
)
@click.option(
    "--output-encoding",
    default="utf-8",
    help="Encoding of the output file.",
    show_default=True,
)
@logger.catch(reraise=True)
def cli_convert(**kwargs):
    """Convert metadata records to different metadata formats or standards."""
    convert(**kwargs)


@logger.catch(reraise=True)
def convert(
    input,
    output_format: str,
    recursive: bool = False,
    input_schema: str = "CIOOS",
    encoding: str = "utf-8",
    output_dir: str = ".",
    output_file: str = None,
    output_encoding: str = "utf-8",
):
    """Convert metadata records to different metadata formats or standards."""

    logger.info("Loading input {}", input)
    if input.startswith("http"):
        files = [input]
    else:
        files = glob(input, recursive=recursive)

    if len(files) > 1 and output_file:
        raise ValueError(
            "Cannot specify output file when processing multiple files. Define an output directory instead."
        )

    logger.debug("Processing {} files", len(files))
    returned_output = ""
    for file in files:
        logger.debug("Processing file {}", file)
        record = (
            Converter(
                source=file,
                schema=InputSchemas[input_schema],
            )
            .load(encoding=encoding)
            .convert_to_cioos_schema()
        )

        if not record.metadata:
            logger.error("No metadata record found in file {}.", file)
            continue

        logger.debug(f"Converting to {output_format}")
        converted_record = record.to(output_format)

        # Generate output file path
        if output_dir and not output_file and record.source_is_path():
            output_file = (
                Path(output_dir) / Path(file).with_suffix(f".{output_format}").name
            )
        elif output_file:
            output_file = Path(output_file)

        # Write to file or return output
        if output_file:
            logger.info("Writing to file {}", output_dir)
            output_file.write_text(converted_record, encoding=output_encoding)
        else:
            returned_output += "\n" + converted_record

    return returned_output


if __name__ == "__main__":
    cli()
