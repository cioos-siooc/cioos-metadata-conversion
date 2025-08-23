import os
from enum import Enum
from pathlib import Path

import requests
import sentry_sdk
import tomllib
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from loguru import logger

from cioos_metadata_conversion.converter import (
    Converter,
    InputSchemas,
    OUTPUT_FORMATS,
)

load_dotenv()

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    send_default_pii=True,
)

version = tomllib.loads((Path(__file__).parent / "../pyproject.toml").read_text())[
    "project"
]["version"]

app = FastAPI(
    title="CIOOS Metadata Conversion API",
    description="Convert CIOOS forms to different available formats.",
    version=version,
)

# Example supported formats
SUPPORTED_FORMATS = Enum("OutputFormats", {key: key for key in OUTPUT_FORMATS.keys()})
SOURCE_FORMATS = Enum("InputFormats", {key: key for key in ["yaml", "json"]})


def get_media_type(output_format: str) -> str:
    """Get the media type for the given output format."""
    if "json" in output_format:
        return "application/json"
    elif "yaml" in output_format or "yml" in output_format:
        return "application/x-yaml"
    elif "cff" in output_format:
        return "text/x-cff"
    elif "xml" in output_format or "erddap" in output_format:
        return "application/xml"
    else:
        raise ValueError(f"Unsupported output format: {output_format}")


def convert_and_respond(
    content: str,
    output_format: SUPPORTED_FORMATS,
    schema: InputSchemas,
    encoding: str = "utf-8",
):
    """Convert content to the specified format and return a Response."""
    try:
        converted_content = (
            Converter(content, schema=schema)
            .load(encoding=encoding)
            .convert_to_cioos_schema()
            .to(output_format.value)
        )
        media_type = get_media_type(output_format.value)
        if media_type == "application/json":
            return content
        return Response(converted_content, media_type=media_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/convert/text")
@logger.catch(reraise=True)
def convert_from_text(
    output_format: SUPPORTED_FORMATS,
    request: Request,
    schema: InputSchemas = InputSchemas.CIOOS,
    encoding: str = "utf-8",
):
    """Convert text input containing metadata to a different format."""
    raw_body = request.body()
    try:
        return convert_and_respond(raw_body, output_format, schema, encoding)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/convert/file")
@logger.catch(reraise=True)
def convert_from_file(
    output_format: SUPPORTED_FORMATS,
    file: UploadFile = File(..., description="File containing metadata"),
    schema: InputSchemas = InputSchemas.CIOOS,
    encoding: str = "utf-8",
):
    """Convert a file containing metadata to a different format."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="File must have a filename")

    content = file.file.read().decode(encoding)

    try:
        return convert_and_respond(content, output_format, schema, encoding)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/convert/url")
@logger.catch(reraise=True)
def convert_from_url(
    output_format: SUPPORTED_FORMATS,
    url: str = Query(..., description="URL to fetch metadata from"),
    schema: InputSchemas = InputSchemas.CIOOS,
    encoding: str = "utf-8",
):
    """Convert metadata fetched from a URL to a different format."""
    if not url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=400, detail="URL must start with http:// or https://"
        )

    try:
        response = requests.get(url)
        response.raise_for_status()
        return convert_and_respond(response.text, output_format, schema, encoding)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
