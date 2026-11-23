"""
Align PDC contacts with the Polar Data Catalogue suggested citation.

PDC lists every ``citedResponsibleParty`` as a citation contact, in file order,
which rarely matches the citation PDC actually displays
(``gmd:otherCitationDetails``). :func:`align_contacts_with_citation` reconciles
the contacts against that text so the generated citation is closer to PDC's:

- Organisation-authored citations (e.g. "Amundsen Science Data Collection
  (2018) ..."): only the matching organisation contact is cited, or the
  organisation is added as a contact when none matches.
- Boilerplate citations (no cited person named, e.g. "Unpublished data"):
  contacts are left untouched.
- Citations with "et al.": every cited contact is kept.
- Otherwise cited contacts not named in the text get ``inCitation: False``.

For real author citations, cited contacts are then reordered to match the
citation and authors missing from the contact list are added as ``author``
contacts. Contacts are only re-flagged or appended, never deleted.

Name matching is accent-, punctuation- and case-insensitive, token-based, and
tolerates a single typo on longer names ("Hoccheim" ~ "Hochheim").
"""

import re
import unicodedata

from loguru import logger

ET_AL_RE = re.compile(r"\bet\.?\s*al\.?", re.IGNORECASE)

# --- citation author parsing (for reordering / adding missing authors) -------
# Markers that end the author segment of a citation (year, "unpublished", etc.).
CUT_RE = re.compile(
    r'\(\s*(?:19|20)\d{2}'
    r'|\(\s*(?:in\s+\w+|n\.?d\.?|un)?published?'
    r'|\(\s*in\s+'
    r'|\bet\s+al'
    r'|(?<!\d)(?:19|20)\d{2}\b'
    r'|\bunpublished\b'
    r'|\d{4}\s*-\s*\d{4}',
    re.IGNORECASE)
LEADING_RE = re.compile(r'^\s*(data\s+)?citation\s*:\s*', re.IGNORECASE)
# FGDC-style "Originator: <org>;" prefix and the "&"/"and" joining organisations.
ORIGINATOR_RE = re.compile(r"^\s*originator\s*:\s*", re.IGNORECASE)
ORG_SPLIT_RE = re.compile(r"\s*(?:,?\s*&|,?\s+and\s)\s*", re.IGNORECASE)
# A surname word starts uppercase and ENDS in a lowercase letter, so a bare
# initial ("A.") is never read as a name; hyphens/apostrophes allowed inside.
_NAME = r"[A-ZÀ-Þ][A-Za-zÀ-ÿ'’.-]*[a-zà-ÿ]"
_INIT = r"(?:[A-ZÀ-Þ]\.?\s*-?\s*){1,4}"
AUTHOR_RE = re.compile(
    rf"(?P<si>(?P<si_last>{_NAME}(?:\s+{_NAME})??)\s*,\s*(?P<si_init>{_INIT})(?![a-zà-ÿ]))"
    rf"|(?P<is>(?P<is_init>(?:[A-ZÀ-Þ]\.\s*){{1,4}})(?P<is_last>{_NAME}))"
    rf"|(?P<sin>(?P<sin_last>{_NAME})\s+(?P<sin_init>(?:[A-ZÀ-Þ]\.?){{1,4}})(?![a-zà-ÿ]))"
)
# Title/geographic words that masquerade as authors when a citation has no year
# before its title. Deliberately excludes real surnames in this corpus
# (e.g. NOT 'Maps'=F. Maps, 'Wang', 'Roy', 'France', 'Bell').
AUTHOR_STOP = {'canadian', 'ipy', 'par', 'uvr', 'underwater', 'southeastern',
               'arctic', 'antarctic', 'beaufort', 'glacier', 'project',
               'downwelling', 'irradiance', 'overview', 'basemaps', 'multibeam'}


def normalize(text):
    """Lower-case, strip accents, and reduce punctuation to spaces.

    Surnames are written inconsistently across citations ("St-Hilaire" vs
    "St. Hilaire", "O'Brien" vs "OBrien"), so we map every non-alphanumeric
    character to a space and collapse runs of whitespace. Both names and the
    citation text go through this, so punctuation differences stop blocking a
    match while word order is preserved for boundary-aware matching.
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^0-9a-zA-Z]+", " ", text.lower())
    return text.strip()


FUZZY_MIN_LEN = 5  # only tokens this long may match with one typo


def tokenize(text):
    """Normalized word tokens of length >= 3 (initials/short words dropped)."""
    return [t for t in normalize(text).split() if len(t) >= 3]


def edit_distance_le1(a, b):
    """True if Levenshtein distance between a and b is at most 1."""
    if a == b:
        return True
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    if la == lb:  # single substitution
        return sum(c1 != c2 for c1, c2 in zip(a, b)) == 1
    # one insertion/deletion: walk the shorter against the longer
    if la > lb:
        a, b = b, a
    i = j = diff = 0
    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            i += 1
            j += 1
        else:
            diff += 1
            if diff > 1:
                return False
            j += 1  # skip the extra char in the longer string
    return True


def token_matches_citation(tok, citation_tokens):
    """Exact match, or a single-typo match for sufficiently long tokens.

    Handles citation spellings like "Guilllot" (-> Guillot) and "Hochheim"
    (-> Hoccheim) without matching unrelated short tokens.
    """
    if tok in citation_tokens:
        return True
    if len(tok) >= FUZZY_MIN_LEN:
        return any(len(ct) >= FUZZY_MIN_LEN and edit_distance_le1(tok, ct)
                   for ct in citation_tokens)
    return False


def person_name_tokens(contact):
    """Name tokens for an individual (given + family name, however recorded).

    The source data is inconsistent: family names may carry middle names
    ("Michelle Seguin"), be misspelled, or be swapped with the given name
    ("Church Ian"). Pooling all name tokens and matching any of them tolerates
    these. Citations write given names as initials, so a spelled-out given name
    in the citation (e.g. a swapped "Cyril, A.") is exactly the case we want to
    catch."""
    tokens = set()
    for key in ("lastName", "givenNames", "indName", "intName"):
        val = contact.get(key)
        if isinstance(val, str):
            tokens.update(tokenize(val))
    return tokens


def is_person(contact):
    """True if the contact represents an individual (has a real last name).

    Organisation/program entries (e.g. an "ArcticNet" contact with an empty
    lastName) are not persons, so a citation that only matches such an entry is
    not a genuine author citation.
    """
    last = contact.get("lastName")
    return isinstance(last, str) and len(last.strip()) >= 2


def is_named_person(contact, citation_tokens):
    """True if any of the individual's name tokens appears in the citation."""
    return any(token_matches_citation(tok, citation_tokens)
               for tok in person_name_tokens(contact))


def is_named(contact, citation_norm, citation_tokens):
    """True if the contact (person or organisation) is named in the citation."""
    if is_named_person(contact, citation_tokens):
        return True
    org = contact.get("orgName")
    if isinstance(org, str) and len(org.strip()) >= 3:
        org_norm = normalize(org)
        if org_norm and re.search(rf"(?<!\w){re.escape(org_norm)}(?!\w)", citation_norm):
            return True
    return False


def clean_citation(cit):
    """Strip a leading 'Citation:' label and re-join hyphenated line-wraps."""
    cit = LEADING_RE.sub('', cit)
    cit = re.sub(r'-\s*[\r\n]+\s*', '-', cit)
    cit = re.sub(r'(?<=[A-Za-zÀ-ÿ])-\s+(?=[A-Z])', '-', cit)
    return cit


def author_segment(cleaned):
    """The leading author portion of a cleaned citation (before year/title)."""
    m = CUT_RE.search(cleaned)
    return (cleaned[:m.start()] if m else cleaned).strip()


def parse_author_units(seg):
    """Parse author entries as (char_offset, lastName, initials) tuples."""
    units = []
    for m in AUTHOR_RE.finditer(seg):
        if m.group('si'):
            last, init = m.group('si_last'), m.group('si_init')
        elif m.group('is'):
            last, init = m.group('is_last'), m.group('is_init')
        else:
            last, init = m.group('sin_last'), m.group('sin_init')
        last = last.strip().strip('.,;')
        init = re.sub(r'\s+', ' ', init.strip()).strip(',;')
        units.append((m.start(), last, init))
    return units


def author_matches_contact(last, contact):
    """True if any significant token of a parsed surname matches the contact.

    Token-based so multi-word surnames ("Moura Neves", "Wareham-Hayes") match a
    contact stored as "de Moura Neves" / "Wareham Hayes" and are not re-added."""
    ptoks = person_name_tokens(contact)
    return any(token_matches_citation(ut, ptoks)
               for ut in tokenize(last) if len(ut) >= 3)


def _pos_string(s):
    """Accent-stripped lower-case copy of s with length preserved (for offsets)."""
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def make_author_contact(last, init):
    """A minimal new contact for an author found only in the citation text."""
    return {
        "givenNames": init,
        "lastName": last,
        "indName": f"{init} {last}".strip(),
        "indOrcid": "",
        "inCitation": True,
        "role": ["author"],
    }


def _reorder_and_augment(contacts, citation):
    """Reorder cited contacts to citation order and add unmatched authors.

    Cited contacts are ordered by where they appear in the citation; authors
    named in the citation but absent from the contact list are inserted as new
    contacts at their citation position. Non-cited contacts keep their original
    order and follow the cited block. Returns (new_contacts, added_names)."""

    cleaned = clean_citation(citation)
    seg = author_segment(cleaned)
    units = parse_author_units(seg)
    pos_str = _pos_string(cleaned)

    cited = [c for c in contacts if c.get("inCitation") is True]
    rest = [c for c in contacts if c.get("inCitation") is not True]
    BIG = len(cleaned) + 1000

    def contact_position(contact):
        # Prefer the offset of the first author unit that matches this contact.
        for start, last, _ in units:
            if author_matches_contact(last, contact):
                return start
        # Fallback: first occurrence of any of the contact's name tokens.
        best = None
        for tok in person_name_tokens(contact):
            if len(tok) < 3:
                continue
            m = re.search(rf"(?<![a-z]){re.escape(tok)}(?![a-z])", pos_str)
            if m:
                best = m.start() if best is None else min(best, m.start())
        return best if best is not None else BIG

    # New authors: units that match no existing contact at all.
    new_items = []
    seen = set()
    for start, last, init in units:
        ln = normalize(last)
        if len(ln) < 3 or ln in seen or ln in AUTHOR_STOP:
            continue
        if any(author_matches_contact(last, c) for c in contacts):
            continue
        seen.add(ln)
        new_items.append((start, make_author_contact(last, init)))

    # Order the cited block by citation position (stable for ties/unknowns).
    front = [(contact_position(c), i, c) for i, c in enumerate(cited)]
    front += [(start, len(cited) + j, c) for j, (start, c) in enumerate(new_items)]
    front.sort(key=lambda t: (t[0], t[1]))
    ordered = [c for _, _, c in front]

    return ordered + rest, [c["indName"] for _, c in new_items]


def _label(contact):
    return (
        contact.get("indName")
        or contact.get("intName")
        or contact.get("orgName")
        or "?"
    )


def _organisation_authors(contacts, citation):
    """Organisation names authoring the citation, or [] if it is not one.

    The author segment must end at a year (so free text such as "ArcticNet
    Basemaps" is not mistaken for an author), contain no parsable person
    author, and name no cited person.
    """
    cleaned = ORIGINATOR_RE.sub("", clean_citation(citation))
    # Templated citations use a "[YEAR]" placeholder instead of a year.
    cleaned = re.sub(r"\[\s*year\s*\]", "(1900)", cleaned, flags=re.IGNORECASE)
    cut = CUT_RE.search(cleaned)
    if not cut or not re.match(r"\(?\s*(?:19|20)\d{2}", cut.group(0)):
        return []
    seg = re.split(r"[;\r\n]", author_segment(cleaned))[0].strip(" .,:;")
    if not seg or parse_author_units(seg):
        return []
    # A cited person named in the segment means a person-authored citation,
    # unless the full "person" name is part of the organisation name (PDC
    # parties such as "Amundsen Science" are split like person names).
    seg_norm = normalize(seg)
    seg_tokens = set(tokenize(seg))
    if any(
        is_person(c)
        and is_named_person(c, seg_tokens)
        and not _named_in(_organisation_name(c), seg_norm)
        for c in contacts
        if c.get("inCitation") is True
    ):
        return []
    return [org for org in ORG_SPLIT_RE.split(seg) if len(org) >= 3]


def _named_in(name_norm, text_norm):
    """True if the normalized name appears as whole words in the text."""
    return bool(name_norm) and bool(
        re.search(rf"(?<!\w){re.escape(name_norm)}(?!\w)", text_norm)
    )


def _organisation_name(contact):
    """Normalized organisation name of an organisation-like contact."""
    return normalize(
        contact.get("indName") or contact.get("intName") or contact.get("orgName")
    )


def _cite_organisations(contacts, organisations):
    """Cite only the contacts naming the citation's organisations, in order.

    Organisations without a matching contact are added as new ``author``
    contacts. Returns (new_contacts, removed_labels, added_names).
    """
    cited, added = [], []
    for org in organisations:
        org_norm = normalize(org)
        match = next(
            (
                c
                for c in contacts
                if _named_in(_organisation_name(c), org_norm)
            ),
            None,
        )
        if match is None:
            match = {
                "givenNames": "",
                "lastName": "",
                "indName": "",
                "indOrcid": "",
                "orgName": org,
                "inCitation": True,
                "role": ["author"],
            }
            added.append(org)
        if all(match is not c for c in cited):
            cited.append(match)
    cited_ids = {id(c) for c in cited}
    removed = []
    for c in contacts:
        if c.get("inCitation") is True and id(c) not in cited_ids:
            c["inCitation"] = False
            removed.append(_label(c))
    for c in cited:
        c["inCitation"] = True
    rest = [c for c in contacts if id(c) not in cited_ids]
    return cited + rest, removed, added


def _trim(contacts, citation):
    """Uncite contacts not named in the citation, in place.

    Returns (action, removed_labels) where action is one of 'boilerplate',
    'et_al', 'trimmed', 'nochange'.
    """
    citation_norm = normalize(citation)
    citation_tokens = set(tokenize(citation))
    cited = [c for c in contacts if c.get("inCitation") is True]

    # Is any cited *person* actually named? If not, the text is not a genuine
    # author citation (e.g. "unpublished", "ArcticNet Basemaps").
    if not any(is_person(c) and is_named_person(c, citation_tokens) for c in cited):
        return "boilerplate", []

    # "et al." implies additional unnamed authors -> keep everyone.
    if ET_AL_RE.search(citation):
        return "et_al", []

    removed = []
    for c in cited:
        if not is_named(c, citation_norm, citation_tokens):
            c["inCitation"] = False
            removed.append(_label(c))
    return ("trimmed" if removed else "nochange"), removed


def _fix_swapped_names(contacts, citation, trusted_names=()):
    """Swap given and last names when the citation shows they are reversed.

    PDC writes ``individualName`` in either order ("Gratton Yves", "Gary
    Stern", "Alexandre, Forest"), so the split into given/last names is a
    guess. The citation's author list gives the surname: when every word of a
    contact's given name is cited as a surname and its last name is nowhere in
    the citation,
    the two are swapped. Contacts the citation does not settle, and those whose
    ``indName`` is in ``trusted_names`` (for citations that reverse a name,
    e.g. "Cyril, A." for Cyril Aubry), are left as-is. Contact dicts are
    updated in place.
    """
    surnames = {
        tok
        for _, last, _ in parse_author_units(author_segment(clean_citation(citation)))
        for tok in tokenize(last)
    }
    citation_tokens = set(tokenize(citation))
    for contact in contacts:
        if not is_person(contact) or contact.get("indName") in trusted_names:
            continue
        given, last = contact.get("givenNames") or "", contact["lastName"]
        given_tokens = tokenize(given)
        if given_tokens and all(
            token_matches_citation(t, surnames) for t in given_tokens
        ) and not any(
            token_matches_citation(t, citation_tokens) for t in tokenize(last)
        ):
            contact["givenNames"], contact["lastName"] = last, given
            contact["indName"] = f"{last} {given}"
            logger.debug("Swapped given/last names of {!r}", f"{given} {last}")


def align_contacts_with_citation(contacts, citation, trusted_names=()):
    """Return contacts aligned with the PDC suggested citation.

    Cited contacts not named in ``citation`` are uncited, the cited ones are
    reordered to the citation order and authors only present in the citation
    are appended as ``author`` contacts. Boilerplate citations leave the
    contacts unchanged. Contact dicts are updated in place.
    """
    if not citation:
        return contacts
    _fix_swapped_names(contacts, citation, trusted_names)
    organisations = _organisation_authors(contacts, citation)
    if organisations:
        contacts, removed, added = _cite_organisations(contacts, organisations)
    else:
        action, removed = _trim(contacts, citation)
        if action == "boilerplate":
            return contacts
        contacts, added = _reorder_and_augment(contacts, citation)
    if removed or added:
        logger.debug(
            "Aligned contacts with citation {!r}: removed={} added={}",
            citation[:120],
            removed,
            added,
        )
    return contacts
