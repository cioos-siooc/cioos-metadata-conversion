import os
from enum import Enum
import tomllib
from pathlib import Path

import requests
import sentry_sdk
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from loguru import logger


from cioos_metadata_conversion.__main__ import (
    converter,
    input_formats,
    load,
    output_formats,
)

load_dotenv()

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    send_default_pii=True,
)

version = tomllib.loads((Path(__file__).parent / "../pyproject.toml").read_text())["project"]["version"]

app = FastAPI(
    title="CIOOS Metadata Conversion API",
    description="Convert CIOOS forms to different available formats.",
    version=version,
)

# Example supported formats
SUPPORTED_FORMATS = Enum("OutputFormats", {key: key for key in output_formats.keys()})
SOURCE_FORMATS = Enum("InputFormats", {key: key for key in input_formats})
SCHEMA_OPTIONS = Enum("SchemaOptions", {"CIOOS": "CIOOS", "firebase": "firebase"})


@app.post("/convert/text")
@logger.catch(reraise=True)
def convert_from_text(
    output_format: SUPPORTED_FORMATS,
    request: Request,
    source_format: SOURCE_FORMATS = SOURCE_FORMATS.yaml,
    schema: SCHEMA_OPTIONS = SCHEMA_OPTIONS.CIOOS,
    encoding: str = "utf-8",
):
    """Convert text input containing metadata to a different format."""
    raw_body = request.body()
    try:
        record_metadata = load(raw_body, format=source_format.value, encoding=encoding)
        converted = converter(record_metadata, output_format.value, schema=schema.value)
        return converted
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/convert/file")
@logger.catch(reraise=True)
def convert_from_file(
    output_format: SUPPORTED_FORMATS,
    file: UploadFile = File(..., description="File containing metadata"),
    source_format: SOURCE_FORMATS = SOURCE_FORMATS.yaml,
    schema: SCHEMA_OPTIONS = SCHEMA_OPTIONS.CIOOS,
    encoding: str = "utf-8",
):
    """Convert a file containing metadata to a different format."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="File must have a filename")

    try:
        record_metadata = load(
            file.file.read().decode(encoding=encoding), format=source_format.value
        )
        converted = converter(record_metadata, output_format.value, schema=schema.value)
        return converted
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/convert/url")
@logger.catch(reraise=True)
def convert_from_url(
    output_format: SUPPORTED_FORMATS,
    url: str = Query(..., description="URL to fetch metadata from"),
    source_format: SOURCE_FORMATS = SOURCE_FORMATS.yaml,
    schema: SCHEMA_OPTIONS = SCHEMA_OPTIONS.CIOOS,
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
        record_metadata = load(
            response.text, format=source_format.value, encoding=encoding
        )
        converted = converter(record_metadata, output_format.value, schema=schema.value)
        return converted
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
