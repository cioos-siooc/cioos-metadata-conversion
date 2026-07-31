import json
from enum import Enum

import requests
import yaml
from loguru import logger

from cioos_metadata_conversion import (
    acdd,
    citation_cff,
    datacite,
    erddap,
    firebase_to_cioos,
    xml,
)
from cioos_metadata_conversion.load_from import datacite as load_from_datacite
from cioos_metadata_conversion.load_from import obis as load_from_obis
from cioos_metadata_conversion.load_from import pdc as load_from_pdc

SOURCE_FILE_EXTENSIONS = (".json", ".yaml", ".yml", ".xml")

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
    "acdd_json": acdd.acdd_json,
    "acdd_yaml": acdd.acdd_yaml,
}


class InputSchemas(Enum):
    """
    Available input schemas for CIOOS metadata conversion.
    """

    CIOOS = "CIOOS"
    firebase = "firebase"
    doi = "doi"
    obis = "obis"
    pdc = "pdc"


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
        elif self.schema == InputSchemas.pdc:
            # Load from the Polar Data Catalogue (CCIN number, URL or ISO XML file)
            self.load_from_pdc(self.source)
        elif isinstance(self.source, str) and (
            self.source.startswith("http://") or self.source.startswith("https://")
        ):
            # Check if it's a DOI URL
            if "doi.org/" in self.source:
                self.load_from_doi(self.source)
            elif "obis.org/" in self.source:
                # Handle OBIS URLs e.g. https://obis.org/dataset/{id} or API urls
                # Extract ID from URL
                if "dataset/" in self.source:
                    dataset_id = (
                        self.source.split("dataset/")[-1].split("?")[0].strip("/")
                    )
                    self.load_from_obis(dataset_id)
                else:
                    self.load_from_url(self.source)
            elif "polardata.ca/" in self.source:
                self.load_from_pdc(self.source)
            else:
                # Load from URL
                self.load_from_url(self.source)
        elif self.source.endswith((".json", ".JSON", ".yaml", ".YAML", ".yml", ".YML")):
            self.load_from_file(self.source, encoding=encoding)
        elif isinstance(self.source, str) and self._is_valid_doi(self.source):
            # Load from DOI
            self.load_from_doi(self.source)
        elif self.schema == InputSchemas.obis:
            self.load_from_obis(self.source)
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

    def load_from_doi(self, doi):
        """
        Load metadata from a DOI using the DataCite API.

        Args:
            doi: DOI string (e.g., "10.26071/mxtr-gp72" or "https://doi.org/10.26071/mxtr-gp72")
        """
        try:
            self.metadata = load_from_datacite.retrieve_doi_as_firebase_record(doi)
            self.schema = InputSchemas.firebase
            logger.info(f"Successfully loaded metadata from DOI: {doi}")
        except load_from_datacite.DOIRetrievalError as e:
            logger.error(f"Failed to load metadata from DOI: {e}")
            raise

    def load_from_obis(self, obis_id):
        """
        Load metadata from OBIS using the OBIS API.

        Args:
            obis_id: OBIS dataset ID (UUID)
        """
        try:
            self.metadata = load_from_obis.retrieve_obis_metadata(obis_id)
            self.schema = InputSchemas.firebase
            logger.info(f"Successfully loaded metadata from OBIS: {obis_id}")
        except Exception as e:
            logger.error(f"Failed to load metadata from OBIS: {e}")
            raise

    def load_from_pdc(self, source):
        """
        Load metadata from the Polar Data Catalogue.

        Args:
            source: A CCIN reference number (e.g., "13172"), a polardata.ca
                ISO XML URL, or a path to a local PDC ISO XML file.
        """
        try:
            self.metadata = load_from_pdc.retrieve_pdc_as_firebase_record(source)
            self.schema = InputSchemas.firebase
            logger.info(f"Successfully loaded metadata from PDC: {source}")
        except load_from_pdc.PDCRetrievalError as e:
            logger.error(f"Failed to load metadata from PDC: {e}")
            raise

    def _is_valid_doi(self, source):
        """
        Check if the source string is a valid DOI format.

        DOI formats: "10.xxxx/yyyy" or "doi:10.xxxx/yyyy"
        """
        if not isinstance(source, str):
            return False

        # Check for common DOI patterns
        return (
            source.startswith("10.")
            or source.startswith("doi:10.")
            or source.startswith("DOI:10.")
        )

    def convert_to_cioos_schema(self):
        """
        Convert the metadata to the specified schema.
        """
        if self.schema == InputSchemas.CIOOS:
            # Already in CIOOS schema, no conversion needed
            pass
        elif self.schema == InputSchemas.firebase:
            self.metadata = firebase_to_cioos.record_json_to_yaml(self.metadata)
            self.schema = InputSchemas.CIOOS
        elif self.schema in (InputSchemas.doi, InputSchemas.pdc):
            # DOI and PDC metadata are loaded as Firebase, then convert to CIOOS
            self.metadata = firebase_to_cioos.record_json_to_yaml(self.metadata)
            self.schema = InputSchemas.CIOOS
        elif self.schema == InputSchemas.obis:
            # OBIS metadata is loaded as Firebase, then convert to CIOOS
            self.metadata = firebase_to_cioos.record_json_to_yaml(self.metadata)
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
