"""Minimal APA citation generation using citeproc-py.

Assumptions:
 - Dates always ISO (YYYY / YYYY-MM / YYYY-MM-DD / full timestamp with time + Z).
 - Single item bibliography.
 - Return empty string on error.
"""

from __future__ import annotations

from citeproc import Citation, CitationItem, CitationStylesBibliography, CitationStylesStyle, formatter
from citeproc.source.json import CiteProcJSON


def _valid(c: dict) -> bool:
	return (
		(len(c.get("givenNames", "")) > 1 and len(c.get("lastName", "")) > 1)
		or len(c.get("orgName", "")) > 1
	)


def _record_to_csl_json(record: dict, language: str) -> list[dict]:
	contacts = record.get("contacts") or record.get("contact") or []
	title_map = record.get("title", {}) or {}
	title = title_map.get(language) or next(iter(title_map.values()), "")
	identifier = record.get("datasetIdentifier") or record.get("identification", {}).get("identifier", "")
	date = record.get("dateRevised") or record.get("datePublished") or record.get("created") or record.get("metadata", {}).get("dates", {}).get("publication")
	edition = record.get("edition") or record.get("identification", {}).get("edition")
	scope = record.get("metadataScope") or record.get("type") or "dataset"

	pubs = [c.get("orgName") for c in contacts if c.get("inCitation") and "publisher" in (c.get("role") or []) and c.get("orgName") and _valid(c)]
	authors = []
	for c in contacts:
		if not c.get("inCitation"):
			continue
		roles = c.get("role") or []
		if "publisher" in roles and len(roles) == 1:
			continue
		if not _valid(c):
			continue
		if len(c.get("givenNames", "")) > 1 and len(c.get("lastName", "")) > 1:
			authors.append({"given": c["givenNames"].strip(), "family": c["lastName"].strip()})
		else:
			org = c.get("orgName") or c.get("organization", {}).get("name")
			if org:
				authors.append({"family": org.strip()})

	doi = ""
	if identifier:
		if "doi.org/" in identifier:
			doi = identifier.split("doi.org/")[-1]
		elif identifier.upper().startswith("10."):
			doi = identifier

	parts = []
	if date and len(date) >= 4:
		try:
			parts.append(int(date[0:4]))
			if len(date) >= 7 and date[4] == '-':
				parts.append(int(date[5:7]))
				if len(date) >= 10 and date[7] == '-':
					parts.append(int(date[8:10]))
		except ValueError:
			parts = []
	issued = {"date-parts": [parts]} if parts else {"literal": "n.d."}

	item = {
		"id": identifier or title[:30] or "id",
		"title": title,
		"author": authors,
		"issued": issued,
		"publisher": ", ".join(dict.fromkeys(pubs)),
		"DOI": doi or None,
		"version": f"v{edition}" if edition else None,
		"type": scope,
	}
	return [{k: v for k, v in item.items() if v not in (None, "")}]


def generate_citation(record: dict, language: str, format: str = "html") -> str:  # noqa: A002
	try:
		data = _record_to_csl_json(record, language)
		src = CiteProcJSON(data)
		style = CitationStylesStyle("apa", validate=False)
		bib = CitationStylesBibliography(style, src, formatter.html)
		cit = Citation([CitationItem(data[0]["id"])])
		bib.register(cit)
		rendered = "".join(str(i) for i in bib.bibliography())
		if format == "text":
			import re as _r
			return _r.sub(r"<[^>]+>", "", rendered)
		if format == "html":
			return f'<span class="citation">{rendered}</span>'
		return rendered
	except Exception:
		return ""


__all__ = ["generate_citation"]

