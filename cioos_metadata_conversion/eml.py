from jinja2 import Environment, FileSystemLoader
import json
from cioos_metadata_conversion.cioos_citation import generate_citation

template_env = Environment(
    loader=FileSystemLoader("cioos_metadata_conversion/templates")
)

ROLE_MAPPING = {
    "creator": ["author", "originator"],
    "metadataProvider": ["distributor", "custodian"],
    "associatedParty": ["principalInvestigator", "editor"],
}
LICENSES = json.load(open("cioos_metadata_conversion/references/licenses.json"))


def _arrayOverlap(arr1, arr2):
    return any(item in arr1 for item in arr2)


def eml_xml(record, citation=None, schema: str = "firebase") -> str:
    """Convert a CIOOS firebase record to EML XML string.

    Args:
        record (dict): The record to convert.

    Returns:
        str: The EML XML string.
    """
    if schema != "firebase":
        raise ValueError("Only 'firebase' schema is supported for EML conversion.")
    if not citation:
        citation = generate_citation(
            record, language=record.get("language", "en"), format="text"
        )
    if "hisory" not in record:
        record["history"] = []

    template = template_env.get_template("emlTemplate.j2")
    return template.render(
        record=record,
        licenses=LICENSES,
        roleMapping=ROLE_MAPPING,
        roleMappingKeys=ROLE_MAPPING.keys(),
        citation=citation,
        arrayOverlap=_arrayOverlap,
    )
