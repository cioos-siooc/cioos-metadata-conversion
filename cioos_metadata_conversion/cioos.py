from cioos_metadata_conversion.firebase_to_cioos import (
    record_json_to_yaml,
)
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account
from loguru import logger

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

    # Define the required scopes
    scopes = [
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/firebase.database",
    ]

    # Authenticate a credential with the service account
    credentials = service_account.Credentials.from_service_account_file(
        firebase_auth_key, scopes=scopes
    )
    authed_session = AuthorizedSession(credentials)

    # Generate the URL to query
    if record_url:
        logger.info(f"Processing record {record_url}")
        url = f"{database_url}{record_url}.json"
    else:
        logger.info(f"Processing records for {region}")
        url = f"{database_url}{region}/users.json"

    response = authed_session.get(url)
    response.raise_for_status()

    if record_url:
        # Return single url
        return [response.json()]

    # Return all records for this region and status
    return [
        record
        for user in response.json().values()
        for record in user.get("records", {}).values()
        if record.get("status") in record_status
    ]
