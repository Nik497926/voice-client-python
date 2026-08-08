"""Typed component / modal builders."""

from __future__ import annotations

import json
from enum import Enum
from typing import Callable


class ButtonStyle(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    SUCCESS = "success"
    DANGER = "danger"
    LINK = "link"


class TextInputStyle(str, Enum):
    SHORT = "short"
    PARAGRAPH = "paragraph"


class ButtonBuilder:
    def __init__(self) -> None:
        self._style = ButtonStyle.PRIMARY
        self._custom_id: str | None = None
        self._url: str | None = None
        self._label: str | None = None
        self._emoji: str | None = None
        self._disabled = False

    def with_style(self, style: ButtonStyle) -> ButtonBuilder:
        self._style = style
        return self

    def with_custom_id(self, custom_id: str) -> ButtonBuilder:
        self._custom_id = custom_id
        return self

    def with_url(self, url: str) -> ButtonBuilder:
        self._url = url
        return self

    def with_label(self, label: str) -> ButtonBuilder:
        self._label = label
        return self

    def with_emoji(self, emoji: str) -> ButtonBuilder:
        self._emoji = emoji
        return self

    def with_disabled(self, disabled: bool = True) -> ButtonBuilder:
        self._disabled = disabled
        return self

    def to_dict(self) -> dict:
        if self._style == ButtonStyle.LINK and not self._url:
            raise ValueError("A link-style button requires with_url(...)")
        if self._style != ButtonStyle.LINK and not self._custom_id:
            raise ValueError("A button requires with_custom_id(...) unless it's a link button")
        data: dict = {"type": "button", "style": self._style.value}
        if self._custom_id is not None:
            data["customId"] = self._custom_id
        if self._url is not None:
            data["url"] = self._url
        if self._label is not None:
            data["label"] = self._label
        if self._emoji is not None:
            data["emoji"] = self._emoji
        if self._disabled:
            data["disabled"] = True
        return data


class SelectMenuBuilder:
    def __init__(self) -> None:
        self._options: list[dict[str, str]] = []
        self._custom_id: str | None = None
        self._placeholder: str | None = None
        self._min_values = 1
        self._max_values = 1

    @property
    def component_type(self) -> str:
        return "select"

    def with_custom_id(self, custom_id: str) -> SelectMenuBuilder:
        self._custom_id = custom_id
        return self

    def with_placeholder(self, placeholder: str) -> SelectMenuBuilder:
        self._placeholder = placeholder
        return self

    def add_option(self, label: str, value: str) -> SelectMenuBuilder:
        self._options.append({"label": label, "value": value})
        return self

    def with_value_range(self, min_values: int, max_values: int) -> SelectMenuBuilder:
        self._min_values = min_values
        self._max_values = max_values
        return self

    def to_dict(self) -> dict:
        if not self._custom_id:
            raise ValueError("A select menu requires with_custom_id(...)")
        if not self._options:
            raise ValueError("A select menu requires at least one add_option(...)")
        data: dict = {
            "type": self.component_type,
            "customId": self._custom_id,
            "options": list(self._options),
            "minValues": self._min_values,
            "maxValues": self._max_values,
        }
        if self._placeholder is not None:
            data["placeholder"] = self._placeholder
        return data


class ComboBoxBuilder(SelectMenuBuilder):
    @property
    def component_type(self) -> str:
        return "combobox"

    def to_dict(self) -> dict:
        data = super().to_dict()
        data["searchable"] = True
        return data


class CheckboxBuilder:
    def __init__(self) -> None:
        self._custom_id: str | None = None
        self._label: str | None = None
        self._checked = False

    def with_custom_id(self, custom_id: str) -> CheckboxBuilder:
        self._custom_id = custom_id
        return self

    def with_label(self, label: str) -> CheckboxBuilder:
        self._label = label
        return self

    def with_checked(self, is_checked: bool = True) -> CheckboxBuilder:
        self._checked = is_checked
        return self

    def to_dict(self) -> dict:
        if not self._custom_id:
            raise ValueError("A checkbox requires with_custom_id(...)")
        data: dict = {"type": "checkbox", "customId": self._custom_id, "checked": self._checked}
        if self._label is not None:
            data["label"] = self._label
        return data


class TextInputBuilder:
    def __init__(self) -> None:
        self._custom_id: str | None = None
        self._label: str | None = None
        self._style = TextInputStyle.SHORT
        self._required = False
        self._placeholder: str | None = None
        self._max_length: int | None = None

    def with_custom_id(self, custom_id: str) -> TextInputBuilder:
        self._custom_id = custom_id
        return self

    def with_label(self, label: str) -> TextInputBuilder:
        self._label = label
        return self

    def with_style(self, style: TextInputStyle) -> TextInputBuilder:
        self._style = style
        return self

    def with_required(self, required: bool = True) -> TextInputBuilder:
        self._required = required
        return self

    def with_placeholder(self, placeholder: str) -> TextInputBuilder:
        self._placeholder = placeholder
        return self

    def with_max_length(self, max_length: int) -> TextInputBuilder:
        self._max_length = max_length
        return self

    def to_dict(self) -> dict:
        if not self._custom_id:
            raise ValueError("A text input requires with_custom_id(...)")
        data: dict = {
            "type": "textInput",
            "customId": self._custom_id,
            "style": self._style.value,
            "required": self._required,
        }
        if self._label is not None:
            data["label"] = self._label
        if self._placeholder is not None:
            data["placeholder"] = self._placeholder
        if self._max_length is not None:
            data["maxLength"] = self._max_length
        return data


class ActionRowBuilder:
    def __init__(self) -> None:
        self._elements: list[Callable[[], dict]] = []

    def add_button(self, configure: Callable[[ButtonBuilder], None]) -> ActionRowBuilder:
        b = ButtonBuilder()
        configure(b)
        self._elements.append(b.to_dict)
        return self

    def add_select_menu(self, configure: Callable[[SelectMenuBuilder], None]) -> ActionRowBuilder:
        b = SelectMenuBuilder()
        configure(b)
        self._elements.append(b.to_dict)
        return self

    def add_combo_box(self, configure: Callable[[ComboBoxBuilder], None]) -> ActionRowBuilder:
        b = ComboBoxBuilder()
        configure(b)
        self._elements.append(b.to_dict)
        return self

    def add_checkbox(self, configure: Callable[[CheckboxBuilder], None]) -> ActionRowBuilder:
        b = CheckboxBuilder()
        configure(b)
        self._elements.append(b.to_dict)
        return self

    def add_text_input(self, configure: Callable[[TextInputBuilder], None]) -> ActionRowBuilder:
        b = TextInputBuilder()
        configure(b)
        self._elements.append(b.to_dict)
        return self

    def to_dict(self) -> dict:
        return {"type": "actionRow", "components": [fn() for fn in self._elements]}


class ComponentBuilder:
    def __init__(self) -> None:
        self._rows: list[ActionRowBuilder] = []

    def with_button(self, configure: Callable[[ButtonBuilder], None]) -> ComponentBuilder:
        return self.add_row(lambda row: row.add_button(configure))

    def with_select_menu(self, configure: Callable[[SelectMenuBuilder], None]) -> ComponentBuilder:
        return self.add_row(lambda row: row.add_select_menu(configure))

    def with_combo_box(self, configure: Callable[[ComboBoxBuilder], None]) -> ComponentBuilder:
        return self.add_row(lambda row: row.add_combo_box(configure))

    def with_checkbox(self, configure: Callable[[CheckboxBuilder], None]) -> ComponentBuilder:
        return self.add_row(lambda row: row.add_checkbox(configure))

    def add_row(self, configure: Callable[[ActionRowBuilder], None]) -> ComponentBuilder:
        row = ActionRowBuilder()
        configure(row)
        self._rows.append(row)
        return self

    def build(self) -> str:
        return json.dumps([row.to_dict() for row in self._rows], separators=(",", ":"))


class ModalBuilder:
    def __init__(self) -> None:
        self._rows: list[ActionRowBuilder] = []
        self._title: str | None = None
        self._custom_id: str | None = None

    def with_title(self, title: str) -> ModalBuilder:
        self._title = title
        return self

    def with_custom_id(self, custom_id: str) -> ModalBuilder:
        self._custom_id = custom_id
        return self

    def add_text_input(self, configure: Callable[[TextInputBuilder], None]) -> ModalBuilder:
        return self.add_row(lambda row: row.add_text_input(configure))

    def add_checkbox(self, configure: Callable[[CheckboxBuilder], None]) -> ModalBuilder:
        return self.add_row(lambda row: row.add_checkbox(configure))

    def add_row(self, configure: Callable[[ActionRowBuilder], None]) -> ModalBuilder:
        row = ActionRowBuilder()
        configure(row)
        self._rows.append(row)
        return self

    def build(self) -> str:
        if not self._title:
            raise ValueError("A modal requires with_title(...)")
        if not self._custom_id:
            raise ValueError("A modal requires with_custom_id(...)")
        return json.dumps(
            {
                "title": self._title,
                "customId": self._custom_id,
                "components": [row.to_dict() for row in self._rows],
            },
            separators=(",", ":"),
        )
