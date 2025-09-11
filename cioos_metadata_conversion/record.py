import json
from enum import Enum

import requests
import yaml
from loguru import logger

from cioos_metadata_conversion import cioos, citation_cff, datacite, erddap, xml

SOURCE_FILE_EXTENSIONS = (".json", ".yaml", ".yml")

OUTPUT_FORMATS = {
    "json": lambda x: json.dumps(x, indent=2),
    "yaml": lambda x: yaml.dump(x, default_flow_style=False),
    "erddap": erddap.global_attributes,
    "cff": citation_cff.citation_cff,
    "xml": xml.xml,
    "iso19115_xml": xml.xml,
    "iso19115-3_xml": xml.xml,
    "datacite_json": datacite.to_json,
    "datacite_xml": datacite.to_xml,
}


class InputSchemas(Enum):
    """
    Available input schemas for CIOOS metadata conversion.
    """

    CIOOS = "CIOOS"
    firebase = "firebase"


class Record:
    """
    Base class for converters.
    """

    def __init__(
        self, source, metadata=None, schema: InputSchemas | str = InputSchemas.CIOOS
    ):
        self.source = source
        self.schema = schema
        self.metadata = metadata

        if isinstance(schema, str):
            if schema not in InputSchemas.__members__:
                raise ValueError(
                    f"Unsupported schema: {schema}. Supported schemas are: {list(InputSchemas.__members__.keys())}"
                )
            self.schema = InputSchemas[schema]

    def source_is_path(self):
        """
        Check if the source is a file path.
        """
        return isinstance(self.source, str) and self.source.endswith(
            SOURCE_FILE_EXTENSIONS
        )

    def load(self, encoding="utf-8"):
        """
        Load the source data.
        """
        if isinstance(self.source, dict):
            self.metadata = self.source
        elif isinstance(self.source, str) and (
            self.source.startswith("http://") or self.source.startswith("https://")
        ):
            # Load from URL
            self.load_from_url(self.source)
        elif self.source.endswith((".json", ".JSON", ".yaml", ".YAML", ".yml", ".YML")):
            self.load_from_file(self.source, encoding=encoding)
        elif isinstance(self.source, str):
            self.load_from_text(self.source)
        else:
            logger.error("Unsupported source type. Must be a file path or URL.")

        return self

    def load_from_file(self, file_path, encoding="utf-8"):
        """
        Load the source data from a file.
        """
        if file_path.endswith(".json"):
            with open(file_path, "r", encoding=encoding) as f:
                self.metadata = json.load(f)
        elif file_path.endswith(".yaml") or file_path.endswith(".yml"):
            with open(file_path, "r", encoding=encoding) as f:
                self.metadata = yaml.safe_load(f)
        else:
            raise ValueError("Unsupported file format. Must be .json or .yaml/.yml.")

    def load_from_url(self, url):
        """
        Load the source data from a URL.
        """
        response = requests.get(url)
        response.raise_for_status()
        self.load_from_text(response.text)

    def load_from_text(self, text):
        """
        Load the source data from a text string.
        """
        if text.startswith("{") or text.startswith("["):
            self.metadata = json.loads(text)
        else:
            self.metadata = yaml.safe_load(text)

    def convert_to_cioos_schema(self):
        """
        Convert the metadata to the specified schema.
        """
        if self.schema == InputSchemas.CIOOS:
            # Already in CIOOS schema, no conversion needed
            pass
        elif self.schema == InputSchemas.firebase:
            self.metadata = cioos.cioos_firebase_to_cioos_schema(self.metadata)
            self.schema = InputSchemas.CIOOS
        else:
            raise ValueError(
                f"Unsupported schema: {self.schema}. Supported schemas are: {list(InputSchemas.__members__.keys())}"
            )
        return self

    def convert_to(self, output_format):
        """
        Convert the source data to the desired format.
        """
        if output_format not in OUTPUT_FORMATS:
            raise ValueError(
                f"Unsupported output format: {output_format}. Supported formats are: {list(OUTPUT_FORMATS.keys())}"
            )
        if output_format in ("xml", "iso19115_xml"):
            logger.warning(
                f"{output_format} format is deprecated, use 'iso19115-3_xml' instead."
            )

        converter_func = OUTPUT_FORMATS[output_format]
        return converter_func(self.metadata)
