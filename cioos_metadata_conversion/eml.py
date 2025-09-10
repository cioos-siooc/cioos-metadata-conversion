from jinja2 import Environment, FileSystemLoader
import json

template_env = Environment(
    loader=FileSystemLoader("cioos_metadata_conversion/templates")
)

ROLE_MAPPING = {
    "creator": ["author", "originator"],
    "metadataProvider": ["distributor", "custodian"],
    "associatedParty": ["principalInvestigator", "editor"],
}
LICENSES = json.load(open("cioos_metadata_conversion/references/licenses.json"))


def arrayOverlap(arr1, arr2):
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
    
    template = template_env.get_template("emlTemplate.j2")
    return template.render(
        record=record,
        role_mapping=ROLE_MAPPING,
        citation=citation,
        licenses=LICENSES,
        arrayOverlap=arrayOverlap,
    )
