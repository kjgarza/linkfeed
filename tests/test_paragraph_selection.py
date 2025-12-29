"""Tests for improved paragraph selection in GenericParser."""

import pytest
from bs4 import BeautifulSoup

from linkfeed.parsers.generic import GenericParser


class TestExtractBestParagraph:
    """Test the _extract_best_paragraph method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = GenericParser()

    def test_selects_longest_paragraph_from_dict_format(self):
        """Should select the longest paragraph from dict format."""
        plain_text = [
            {"text": "Short paragraph."},
            {"text": "This is a medium length paragraph with enough content to be considered. It has over one hundred characters which makes it a valid candidate for selection as a summary."},
            {"text": "This is the longest paragraph with the most information. It contains significantly more content than the others and should be selected as the best summary. This paragraph has much more detail and context that would be valuable for a summary, making it the ideal choice for representing the content."},
            {"text": "Another short one."},
        ]
        
        result = self.parser._extract_best_paragraph(plain_text)
        
        assert result is not None
        assert "longest paragraph with the most information" in result
        assert len(result) <= 500

    def test_selects_longest_paragraph_from_string_format(self):
        """Should handle plain text as strings."""
        plain_text = [
            "Short.",
            "This is a medium paragraph with enough content to be considered as a candidate for the summary section.",
            "This is the longest paragraph and should be selected because it contains the most information and detail.",
            "Brief.",
        ]
        
        result = self.parser._extract_best_paragraph(plain_text)
        
        assert result is not None
        assert "longest paragraph and should be selected" in result

    def test_ignores_short_paragraphs(self):
        """Should ignore paragraphs shorter than 100 characters."""
        plain_text = [
            {"text": "Short."},
            {"text": "Also short."},
            {"text": "This one is also too short to be selected."},
        ]
        
        result = self.parser._extract_best_paragraph(plain_text)
        
        assert result is None

    def test_only_checks_first_four_paragraphs(self):
        """Should only check the first 4 paragraphs."""
        plain_text = [
            {"text": "First short."},
            {"text": "Second short."},
            {"text": "Third medium paragraph with just enough content to be considered as a valid candidate for summary selection."},
            {"text": "Fourth short."},
            {"text": "This is the fifth paragraph and it's very long with lots of information that would make it an excellent summary but it should be ignored because it's beyond the first four paragraphs limit."},
        ]
        
        result = self.parser._extract_best_paragraph(plain_text)
        
        # Should select the third paragraph, not the fifth
        assert result is not None
        assert "Third medium paragraph" in result
        assert "fifth paragraph" not in result

    def test_truncates_to_500_characters(self):
        """Should truncate result to 500 characters."""
        long_text = "A" * 1000  # Create a 1000 character string
        plain_text = [{"text": long_text}]
        
        result = self.parser._extract_best_paragraph(plain_text)
        
        assert result is not None
        assert len(result) == 500

    def test_handles_empty_list(self):
        """Should handle empty plain_text list."""
        result = self.parser._extract_best_paragraph([])
        assert result is None

    def test_handles_none(self):
        """Should handle None input."""
        result = self.parser._extract_best_paragraph(None)
        assert result is None

    def test_handles_mixed_formats(self):
        """Should handle mix of dicts and strings."""
        plain_text = [
            {"text": "Dict format paragraph."},
            "String format paragraph with enough content to be considered as a valid candidate for the summary selection.",
            {"text": "This is the longest paragraph in dict format with the most comprehensive information and should be selected."},
        ]
        
        result = self.parser._extract_best_paragraph(plain_text)
        
        assert result is not None
        assert "longest paragraph in dict format" in result


class TestExtractFirstParagraphBeautifulSoup:
    """Test the improved _extract_first_paragraph method for BeautifulSoup."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = GenericParser()

    def test_selects_longest_paragraph(self):
        """Should select the longest paragraph from HTML."""
        html = """
        <div>
            <p>Short paragraph.</p>
            <p>This is a medium length paragraph with enough content to be considered for selection.</p>
            <p>This is the longest paragraph with the most comprehensive information and detail. It contains significantly more content than the other paragraphs and should therefore be selected as the best representative summary.</p>
            <p>Another short one.</p>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        
        result = self.parser._extract_first_paragraph(soup)
        
        assert result is not None
        assert "longest paragraph with the most comprehensive" in result
        assert len(result) <= 500

    def test_ignores_short_paragraphs(self):
        """Should ignore paragraphs shorter than 100 characters."""
        html = """
        <div>
            <p>Short.</p>
            <p>Also short.</p>
            <p>Too short to select.</p>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        
        result = self.parser._extract_first_paragraph(soup)
        
        assert result is None

    def test_limits_to_first_four_paragraphs(self):
        """Should only check first 4 paragraphs."""
        html = """
        <div>
            <p>First.</p>
            <p>Second.</p>
            <p>Third medium paragraph with enough content to be considered as a candidate for the summary selection.</p>
            <p>Fourth.</p>
            <p>This is the fifth paragraph with lots of information but it should be ignored because we only check the first four paragraphs in the document.</p>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        
        result = self.parser._extract_first_paragraph(soup)
        
        assert result is not None
        assert "Third medium paragraph" in result
        assert "fifth paragraph" not in result

    def test_truncates_to_500_characters(self):
        """Should truncate to 500 characters."""
        long_text = "A" * 1000
        html = f"<div><p>{long_text}</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        
        result = self.parser._extract_first_paragraph(soup)
        
        assert result is not None
        assert len(result) == 500

    def test_handles_no_paragraphs(self):
        """Should handle HTML with no paragraphs."""
        html = "<div><span>No paragraphs here</span></div>"
        soup = BeautifulSoup(html, "html.parser")
        
        result = self.parser._extract_first_paragraph(soup)
        
        assert result is None

    def test_strips_whitespace(self):
        """Should strip whitespace from paragraphs."""
        html = """
        <div>
            <p>   
                This is a paragraph with lots of whitespace and enough content to be selected as a candidate for summary.
            </p>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        
        result = self.parser._extract_first_paragraph(soup)
        
        assert result is not None
        assert not result.startswith(" ")
        assert not result.endswith(" ")
