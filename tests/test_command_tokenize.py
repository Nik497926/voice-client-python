"""Tests for CommandArgumentParser / tokenize."""

from voice.client.commands import tokenize


def test_tokenize_splits_on_whitespace():
    assert tokenize("a b c") == ["a", "b", "c"]


def test_tokenize_collapses_repeated_whitespace():
    assert tokenize("a   b") == ["a", "b"]


def test_tokenize_empty():
    assert tokenize("") == []
    assert tokenize("   ") == []


def test_tokenize_quoted_substring():
    assert tokenize('tag "hello world" 3') == ["tag", "hello world", "3"]


def test_tokenize_unterminated_quote():
    assert tokenize('tag "hello world') == ["tag", "hello world"]
