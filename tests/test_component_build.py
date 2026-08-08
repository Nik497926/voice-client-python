"""Tests for ComponentBuilder / ModalBuilder JSON schema."""

import json

import pytest

from voice.client.components import (
    ButtonStyle,
    ComponentBuilder,
    ModalBuilder,
    TextInputStyle,
)


def test_build_action_row_with_button():
    raw = (
        ComponentBuilder()
        .with_button(lambda b: b.with_style(ButtonStyle.DANGER).with_custom_id("cancel").with_label("Cancel"))
        .build()
    )
    array = json.loads(raw)
    assert len(array) == 1
    row = array[0]
    assert row["type"] == "actionRow"
    component = row["components"][0]
    assert component["type"] == "button"
    assert component["style"] == "danger"
    assert component["customId"] == "cancel"
    assert component["label"] == "Cancel"


def test_link_button_omits_custom_id():
    raw = (
        ComponentBuilder()
        .with_button(lambda b: b.with_style(ButtonStyle.LINK).with_url("https://example.com").with_label("Docs"))
        .build()
    )
    component = json.loads(raw)[0]["components"][0]
    assert component["url"] == "https://example.com"
    assert "customId" not in component


def test_button_requires_custom_id():
    with pytest.raises(ValueError):
        ComponentBuilder().with_button(lambda b: b.with_label("no id")).build()


def test_select_menu():
    raw = (
        ComponentBuilder()
        .with_select_menu(
            lambda s: s.with_custom_id("pick")
            .with_placeholder("Choose one")
            .add_option("Apple", "apple")
            .add_option("Banana", "banana")
            .with_value_range(1, 2)
        )
        .build()
    )
    component = json.loads(raw)[0]["components"][0]
    assert component["type"] == "select"
    assert component["customId"] == "pick"
    assert component["placeholder"] == "Choose one"
    assert len(component["options"]) == 2
    assert component["minValues"] == 1
    assert component["maxValues"] == 2


def test_combo_box_searchable():
    raw = (
        ComponentBuilder()
        .with_combo_box(lambda c: c.with_custom_id("search").add_option("Alpha", "alpha"))
        .build()
    )
    component = json.loads(raw)[0]["components"][0]
    assert component["type"] == "combobox"
    assert component["searchable"] is True


def test_checkbox():
    raw = (
        ComponentBuilder()
        .with_checkbox(lambda c: c.with_custom_id("agree").with_label("I agree").with_checked())
        .build()
    )
    component = json.loads(raw)[0]["components"][0]
    assert component["type"] == "checkbox"
    assert component["checked"] is True
    assert component["label"] == "I agree"


def test_add_row_groups_buttons():
    raw = (
        ComponentBuilder()
        .add_row(
            lambda row: row.add_button(lambda b: b.with_custom_id("a").with_label("A")).add_button(
                lambda b: b.with_custom_id("b").with_label("B")
            )
        )
        .build()
    )
    array = json.loads(raw)
    assert len(array) == 1
    assert len(array[0]["components"]) == 2


def test_modal_builder():
    raw = (
        ModalBuilder()
        .with_title("Feedback")
        .with_custom_id("feedback-modal")
        .add_text_input(
            lambda t: t.with_custom_id("comment")
            .with_label("Comment")
            .with_style(TextInputStyle.PARAGRAPH)
            .with_required()
        )
        .add_checkbox(lambda c: c.with_custom_id("subscribe").with_label("Notify me").with_checked())
        .build()
    )
    root = json.loads(raw)
    assert root["title"] == "Feedback"
    assert root["customId"] == "feedback-modal"
    assert len(root["components"]) == 2
    text_input = root["components"][0]["components"][0]
    assert text_input["type"] == "textInput"
    assert text_input["style"] == "paragraph"
    assert text_input["required"] is True


def test_modal_requires_title():
    with pytest.raises(ValueError):
        ModalBuilder().add_text_input(lambda t: t.with_custom_id("x")).build()
