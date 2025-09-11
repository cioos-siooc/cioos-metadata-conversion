from firebase_to_xml import (
    get_records_from_firebase as firebase_records,
)
from firebase_to_xml import (
    record_json_to_yaml,
)
from loguru import logger


@logger.catch(default={}, reraise=True)
def cioos_firebase_to_cioos_schema(record) -> dict:
    """
    Convert a Firebase record to CIOOS schema.

    Args:
        record_json (dict): The record in JSON format from Firebase.

    Returns:
        str: The converted record in CIOOS Schema format.
    """
    return record_json_to_yaml.record_json_to_yaml(record)


@logger.catch(default=[], reraise=True)
def get_records_from_firebase(
    region, firebase_auth_key, record_url, record_status, database_url
) -> list:
    """
    Fetch records from Firebase and convert them to CIOOS schema.

    Args:
        region (str): The region for which to fetch records.
        firebase_auth_key (str): The Firebase authentication key.
        record_url (str): The URL for the record.
        record_status (str): The status of the record.
        database_url (str): The Firebase database URL.

    Returns:
        list: A list of records in CIOOS Schema format.
    """
    return firebase_records.get_records_from_firebase(
        region, firebase_auth_key, record_url, record_status, database_url
    )
