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
    elif "xml" in output_format:
        return "application/xml"
    else:
        raise ValueError(f"Unsupported output format: {output_format}")


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
        content = Converter(raw_body, schema=schema).load(encoding=encoding).convert_to_cioos_schema().to(output_format.value)
        return Response(content, media_type=get_media_type(output_format.value))
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
        content = Converter(content, schema=schema).load(encoding=encoding).convert_to_cioos_schema().to(output_format.value)
        return Response(content, media_type=get_media_type(output_format.value))
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
        content = Converter(response.text, schema=schema).load(encoding=encoding).convert_to_cioos_schema().to(output_format.value)
        return Response(content, media_type=get_media_type(output_format.value))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
