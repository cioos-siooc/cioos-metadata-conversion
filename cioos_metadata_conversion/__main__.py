import json
from glob import glob
from pathlib import Path

import click
import requests
import yaml
from loguru import logger

from cioos_metadata_conversion import citation_cff, erddap, xml
from cioos_metadata_conversion.cioos import cioos_firebase_to_cioos_schema

output_formats = {
    "json": lambda x: json.dumps(x, indent=2),
    "yaml": lambda x: yaml.dump(x, default_flow_style=False),
    "erddap": erddap.global_attributes,
    "cff": citation_cff.citation_cff,
}

input_formats = ["json", "yaml"]


@logger.catch(reraise=True)
def load(input, format, encoding="utf-8") -> dict:
    """Load a metadata record from a file."""

    if input.startswith("http"):
        response = requests.get(input)
        response.raise_for_status()
        data = response.text
    else:
        data = Path(input).read_text(encoding=encoding)

    if format == "json":
        return json.loads(data, encoding=encoding)
    elif format == "yaml":
        return yaml.safe_load(data)
    else:
        raise ValueError(f"Unsupported input format: {format}. Supported formats are: {list(input_formats)}")



def converter(record, format, schema:str='CIOOS') -> str:
    """Run the conversion to the desired format."""
    if schema == 'firebase':
        record = cioos_firebase_to_cioos_schema(record)
    elif schema == 'CIOOS':
        pass
    else:
        raise ValueError(f"Unsupported schema: {schema}. Supported schemas are: CIOOS, firebase")

    if format == "json":
        return json.dumps(record, indent=2)
    elif format in ("yaml", "yml"):
        return yaml.dump(record)
    elif format == "erddap":
        return erddap.global_attributes(record)
    elif format == "cff":
        return citation_cff.citation_cff(record)
    elif format == "xml":
        return xml.xml(record)
    else:
        raise ValueError(f"Unknown output format: {format}")


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
    "--input-file-format",
    required=True,
    default="yaml",
    help="Input file format (json or yaml).",
    type=click.Choice(list(input_formats)),
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
    type=click.Choice(list(output_formats.keys())),
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
    input_file_format: str = "yaml",
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
        input_file_path = Path(file)

        # Load metadata record
        record = load(file, input_file_format, encoding=encoding)

        if not record:
            logger.error("No metadata record found in file {}.", file)
            continue

        logger.debug(f"Converting to {output_format}")
        converted_record = converter(record, output_format)

        # Generate output file path
        if output_dir and not output_file:
            output_file = (
                Path(output_dir) / input_file_path.with_suffix(f".{output_format}").name
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
