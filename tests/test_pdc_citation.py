"""Tests for aligning PDC contacts with the PDC suggested citation."""

from cioos_metadata_conversion.load_from.pdc_citation import (
    align_contacts_with_citation,
)


def person(given, last, in_citation=True, role="collaborator", org=None):
    return {
        "givenNames": given,
        "lastName": last,
        "indName": f"{given} {last}",
        "orgName": org,
        "inCitation": in_citation,
        "role": [role],
    }


def organisation(name, in_citation=False, role="pointOfContact"):
    return {
        "givenNames": "",
        "lastName": "",
        "indName": "",
        "orgName": name,
        "inCitation": in_citation,
        "role": [role],
    }


def cited(contacts):
    return [
        c["lastName"] or c["orgName"] for c in contacts if c["inCitation"] is True
    ]


def test_trims_reorders_and_adds_missing_authors():
    contacts = [
        organisation("Polar Data Catalogue"),
        person("Louis", "Fortier"),
        person("Delphine", "Benoit"),
        person("Maxime", "Geoffroy"),
        person("Dominique", "Robert"),
    ]
    result = align_contacts_with_citation(
        contacts,
        "Geoffroy M., Robert D., Darnis G., Fortier L. (2011) The aggregation "
        "of polar cod. Polar Biology.",
    )
    assert cited(result) == ["Geoffroy", "Robert", "Darnis", "Fortier"]
    added = next(c for c in result if c["lastName"] == "Darnis")
    assert added["role"] == ["author"]
    # Uncited contacts are kept, never deleted.
    assert {c["lastName"] for c in result} >= {"Benoit"}
    assert len(result) == len(contacts) + 1


def test_tolerates_typos_and_accents():
    contacts = [person("Klaus", "Hocheim"), person("Rémi", "Lévesque")]
    result = align_contacts_with_citation(
        contacts, "Levesque, R. and Hochheim, K. (2010) Sea ice data."
    )
    assert cited(result) == ["Lévesque", "Hocheim"]


def test_et_al_keeps_every_cited_contact():
    contacts = [person("Tim", "Papakyriakou"), person("Brent", "Else")]
    result = align_contacts_with_citation(
        contacts, "Papakyriakou T. et al. (2008) Flux data."
    )
    assert cited(result) == ["Papakyriakou", "Else"]


def test_swaps_given_and_last_names_reversed_in_pdc():
    # PDC wrote "Gratton Yves" / "Rail Marie-Emmanuelle" surname-first.
    contacts = [
        person("Gratton", "Yves"),
        person("Rail", "Marie-Emmanuelle"),
        person("Véronique", "Lago"),  # not cited, so left as-is
    ]
    result = align_contacts_with_citation(
        contacts,
        "Simard, A; Rail, M-E and Gratton, Y (2010): Distribution of "
        "temperature and salinity. https://doi.org/10.5884/80",
    )
    assert cited(result) == ["Simard", "Rail", "Gratton"]
    rail = next(c for c in result if c["lastName"] == "Rail")
    assert (rail["givenNames"], rail["indName"]) == (
        "Marie-Emmanuelle",
        "Marie-Emmanuelle Rail",
    )
    assert next(c for c in result if c["lastName"] == "Lago")["givenNames"] == "Véronique"


def test_keeps_names_already_in_the_right_order():
    contacts = [
        person("Louis", "Fortier"),
        person("Alexandre", "Forest"),
        # "Vonda Wareham Hayes" split on the last word: only part of the
        # given name is a cited surname, so it is not a swap.
        person("Vonda Wareham", "Hayes"),
    ]
    result = align_contacts_with_citation(
        contacts,
        "Fortier, L., Forest, A. and Wareham, V. (2019). Vertical flux data.",
    )
    assert [(c["givenNames"], c["lastName"]) for c in result] == [
        ("Louis", "Fortier"),
        ("Alexandre", "Forest"),
        ("Vonda Wareham", "Hayes"),
    ]


def test_trusted_names_are_not_swapped_by_a_reversed_citation():
    # PDC's citation for ccin-10510 reverses Cyril Aubry as "Cyril, A.".
    contacts = [person("Louis", "Létourneau"), person("Cyril", "Aubry")]
    result = align_contacts_with_citation(
        contacts,
        "Létourneau, L., & Cyril, A. (2018). Mesozooplankton abundance.",
        trusted_names={"Cyril Aubry"},
    )
    aubry = next(c for c in result if c["indName"] == "Cyril Aubry")
    assert (aubry["givenNames"], aubry["lastName"]) == ("Cyril", "Aubry")


def test_boilerplate_citation_leaves_contacts_untouched():
    contacts = [person("David", "Barber"), person("Ryan", "Galley")]
    result = align_contacts_with_citation(contacts, "Unpublished data")
    assert cited(result) == ["Barber", "Galley"]


def test_no_citation_leaves_contacts_untouched():
    contacts = [person("David", "Barber")]
    assert align_contacts_with_citation(contacts, None) == contacts


def test_organisation_citation_adds_the_organisation():
    contacts = [
        person("Alexandre", "Forest"),
        person("Simon", "Morisset"),
        organisation("Canadian Cryospheric Information Network", True, "originator"),
    ]
    result = align_contacts_with_citation(
        contacts,
        "Amundsen Science Data Collection. [YEAR]. MVP data collected by the "
        "CCGS Amundsen. Amundsen Science, Québec, Canada. Archived at "
        "www.polardata.ca, Canadian Cryospheric Information Network.",
    )
    assert cited(result) == ["Amundsen Science Data Collection"]
    assert result[0]["role"] == ["author"]


def test_organisation_citation_reuses_matching_party():
    # PDC parties such as "Amundsen Science" are split like person names.
    amundsen = person("Amundsen", "Science", role="principalInvestigator")
    contacts = [amundsen, person("Dominique", "St-Hilaire")]
    result = align_contacts_with_citation(
        contacts, "Amundsen Science Data Collection (2018): Multibeam Sonar Data."
    )
    assert [c for c in result if c["inCitation"]] == [amundsen]


def test_originator_prefix_and_multiple_organisations():
    result = align_contacts_with_citation(
        [person("John", "Hughes Clarke")],
        "Originator: Ocean Mapping Group (OMG);\r\nPublication_Date: 2003;",
    )
    assert cited(result) == ["Ocean Mapping Group (OMG)"]

    result = align_contacts_with_citation(
        [organisation("ArcticNet", True, "originator")],
        "ArcticNet, & Amundsen Science Mooring Data Collection. (2024). Moorings.",
    )
    assert cited(result) == ["ArcticNet", "Amundsen Science Mooring Data Collection"]
