# -*- coding: utf-8 -*-
"""Localized sample CVs from ``ejemplo``: same story in es, en and zh.

The three samples tell the same career story (same dates, links, emails and
entry counts) and only localize the prose, so a change in one language must
not silently change the structure of the others. The samples never include
images. No GUI, no LaTeX, no prefs.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

import ejemplo  # noqa: E402
import latex_gen  # noqa: E402


LANGUAGES = ("es", "en", "zh")

# The nine sections every sample must fill in.
SECTIONS = (
    "summary",
    "education",
    "projects",
    "university_projects",
    "internships",
    "work",
    "skills",
    "languages",
    "references",
)
LIST_SECTIONS = tuple(section for section in SECTIONS if section != "summary")

# Sections with a start/end date and sections with an outbound link.
DATE_SECTIONS = ("work", "internships", "projects", "university_projects", "education")
LINK_SECTIONS = ("projects", "university_projects")
LOGO_SECTIONS = ("work", "internships", "projects", "university_projects", "education")


class _HostileBool:
    """Truthiness blows up before the language can even be read."""

    def __bool__(self):
        raise RuntimeError("boom on bool")


class _HostileStr:
    """Truthy, but converting it to text blows up."""

    def __bool__(self):
        return True

    def __str__(self):
        raise RuntimeError("boom on str")


def _end_kind(end):
    """Normalize the localized "current job" label to a neutral tag."""
    text = str(end or "")
    if not text:
        return ""
    # Past entries end in a numeric year; the current role uses localized prose.
    return text if text.isdigit() else "current"


def _story_shape(data):
    """The parts of the sample that must be identical in every language."""
    return {
        "dates": [
            (entry.get("start", ""), _end_kind(entry.get("end", "")))
            for section in DATE_SECTIONS
            for entry in data[section]
        ],
        "links": [
            entry.get("link", "")
            for section in LINK_SECTIONS
            for entry in data[section]
        ],
        "socials": [social.get("value", "") for social in data["socials"]],
        "emails": [data["email"]]
        + [reference.get("contact", "") for reference in data["references"]],
        "counts": {section: len(data[section]) for section in LIST_SECTIONS},
    }


@pytest.mark.parametrize("lang", LANGUAGES)
def test_sample_data_localizes_the_requested_language(lang):
    data = ejemplo.sample_data(lang)

    assert data["cv_language"] == lang
    assert data["template"] == "classic"
    assert set(data) == set(latex_gen.empty_data())

    assert isinstance(data["summary"], str)
    assert data["summary"].strip()
    for section in LIST_SECTIONS:
        assert isinstance(data[section], list)
        assert data[section], section


def test_samples_share_dates_links_emails_and_entry_counts():
    shapes = {lang: _story_shape(ejemplo.sample_data(lang)) for lang in LANGUAGES}

    assert shapes["es"] == shapes["en"] == shapes["zh"]
    # Guard the comparison itself: the sample is not accidentally empty.
    counts = shapes["es"]["counts"]
    assert counts and all(count > 0 for count in counts.values())
    assert shapes["es"]["dates"]
    assert shapes["es"]["links"]
    assert all(shapes["es"]["emails"])


@pytest.mark.parametrize("lang", LANGUAGES)
def test_sample_uses_the_project_identity(lang):
    """Every language carries the same fictional name and handles, and no website social."""
    data = ejemplo.sample_data(lang)

    assert data["name"] == "ALEJANDRO RUIZ MARTÍN"
    socials = {
        social.get("network"): social.get("value") for social in data["socials"]
    }
    assert socials["github"] == "github.com/example"
    assert socials["linkedin"] == "linkedin.com/in/example"
    assert "website" not in socials
    for project in data["projects"]:
        assert project["link"].startswith("github.com/example/")


@pytest.mark.parametrize("lang", LANGUAGES)
def test_sample_has_no_images(lang):
    data = ejemplo.sample_data(lang)

    assert data.get("photo", "") == ""
    assert data.get("photo_original", "") == ""
    assert data.get("photo_crop") is None
    assert data.get("school_logo", "") == ""
    for section in LOGO_SECTIONS:
        for entry in data[section]:
            assert entry.get("logo", "") == ""


def test_sample_data_defaults_to_spanish():
    data = ejemplo.sample_data()

    assert data["cv_language"] == "es"
    assert data == ejemplo.sample_data("es")


@pytest.mark.parametrize("lang,wrapper", [("zh", "sample_data_zh"), ("en", "sample_data_en")])
def test_language_wrappers_match_sample_data(lang, wrapper):
    assert getattr(ejemplo, wrapper)() == ejemplo.sample_data(lang)


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "   ",
        "fr",
        "de",
        "zh-CN",
        "es-ES",
        0,
        123,
        [],
        {},
        b"en",
        _HostileBool(),
        _HostileStr(),
    ],
)
def test_invalid_languages_fall_back_to_spanish(value):
    data = ejemplo.sample_data(value)

    assert data["cv_language"] == "es"
