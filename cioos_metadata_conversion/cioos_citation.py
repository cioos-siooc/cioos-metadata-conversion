"""Citation generation utilities (APA using citeproc-py only).

We rely solely on citeproc-py (CSL processor) with the APA style provided by
citeproc-py-styles. If citeproc processing fails for any reason an empty
string is returned (mimicking the prior citation-js behavior). No manual
fallback formatting is kept to avoid duplicated logic.
"""

from __future__ import annotations
import re

from typing import List

from citeproc import (
    Citation,
    CitationItem,
    CitationStylesBibliography,
    CitationStylesStyle,
    formatter,
)
from citeproc.source.json import CiteProcJSON


def _is_valid_contact_for_citation(contact: dict) -> bool:
    """Return True if usable for citation (org name or both names length >1)."""
    return (
        len(contact.get("givenNames", "")) > 1 and len(contact.get("lastName", "")) > 1
    ) or len(contact.get("orgName", "")) > 1


def _record_to_csl_json(record: dict, language: str) -> list[dict]:
    """Transform internal record to a CSL JSON list (single item).

    We reproduce the selection / filtering semantics from the original JS
    function before handing off to citeproc-py.
    """

    contacts = record.get("contacts") or record.get("contact") or []
    title_map = record.get("title", {}) or {}
    title = title_map.get(language) or next(iter(title_map.values()), "")
    dataset_identifier = record.get("datasetIdentifier", "") or record.get(
        "identification", {}
    ).get("identifier", "")
    created = record.get("created") or record.get("metadata", {}).get("dates", {}).get(
        "publication"
    )
    date_published = record.get("datePublished") or record.get("metadata", {}).get(
        "dates", {}
    ).get("publication")
    date_revised = record.get("dateRevised") or record.get("metadata", {}).get(
        "dates", {}
    ).get("revision")
    issued_date = date_revised or date_published or created
    edition = record.get("edition") or record.get("identification", {}).get("edition")
    metadata_scope = record.get("metadataScope") or record.get("type") or "dataset"

    publishers = [
        c.get("orgName")
        for c in contacts
        if c.get("inCitation")
        and "publisher" in (c.get("role") or [])
        and c.get("orgName")
        and _is_valid_contact_for_citation(c)
    ]

    authors_csl: List[dict] = []
    for c in contacts:
        roles = c.get("role") or []
        if not c.get("inCitation"):
            continue
        if "publisher" in roles and len(roles) == 1:
            # Only publisher -> skip (JS logic)
            continue
        if not _is_valid_contact_for_citation(c):
            continue
        if len(c.get("givenNames", "")) > 1 and len(c.get("lastName", "")) > 1:
            authors_csl.append(
                {
                    "given": c.get("givenNames").strip(),
                    "family": c.get("lastName").strip(),
                }
            )
        else:
            org = c.get("orgName") or c.get("organization", {}).get("name")
            if org:
                # Use as 'family' only -> organization citation
                authors_csl.append({"family": org.strip()})

    # DOI normalization (remove https://doi.org/ prefix)
    doi = ""
    if dataset_identifier:
        if "doi.org/" in dataset_identifier:
            doi = dataset_identifier.split("doi.org/")[-1]
        elif dataset_identifier.upper().startswith("10."):
            doi = dataset_identifier

    csl_item = {
        "id": dataset_identifier or title[:30] or "id",
        "title": title,
        "author": authors_csl,
        "issued": {"raw": issued_date} if issued_date else {"raw": "n.d."},
        "publisher": ", ".join(dict.fromkeys(publishers)),
        "DOI": doi or None,
        "version": f"v{edition}" if edition else None,
        "type": metadata_scope,
    }
    # Remove None values (citeproc can choke on them)
    csl_item = {k: v for k, v in csl_item.items() if v not in (None, "")}
    return [csl_item]


def _generate_with_citeproc(record: dict, language: str, output_format: str) -> str:
    csl_json = _record_to_csl_json(record, language)
    bib_source = CiteProcJSON(csl_json)
    style = CitationStylesStyle("apa", validate=False)
    bibliography = CitationStylesBibliography(style, bib_source, formatter.html)
    citation = Citation([CitationItem(csl_json[0]["id"])])
    bibliography.register(citation)
    rendered = "".join(str(item) for item in bibliography.bibliography())
    if output_format == "text":
        return re.sub(r"<[^>]+>", "", rendered)
    if output_format == "html":
        return f'<span class="citation">{rendered}</span>'
    return rendered


def generate_citation(record: dict, language: str, format: str = "html") -> str:
    """Generate a citation using citeproc-py (APA only).

    Returns empty string if generation fails.
    """
    try:
        return _generate_with_citeproc(record, language, format)
    except Exception:
        return ""


__all__ = ["generate_citation"]
