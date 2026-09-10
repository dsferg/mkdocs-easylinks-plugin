"""Tests for the EasyLinks plugin."""

import pytest
from mkdocs_easylinks.plugin import EasyLinksPlugin
from mkdocs.structure.pages import Page
from mkdocs.structure.files import File, Files
from unittest.mock import MagicMock


class TestEasyLinksPlugin:
    """Test cases for EasyLinksPlugin."""

    def setup_method(self):
        """Set up test fixtures."""
        self.plugin = EasyLinksPlugin()
        self.plugin.config = {
            "warn_on_missing": False,
            "warn_on_ambiguous": False,
            "ignore_files": [],
            "exclude_dirs": [],
            "show_stats": False,
            "protect_code_fences": True,
            "protect_html_comments": True,
            "protect_inline_code": True,
        }

    def create_mock_file(self, src_path: str, is_documentation=True):
        """Helper to create a mock File object."""
        mock_file = MagicMock(spec=File)
        mock_file.src_path = src_path
        mock_file.is_documentation_page.return_value = is_documentation
        return mock_file

    def create_mock_page(self, src_path: str):
        """Helper to create a mock Page object."""
        mock_page = MagicMock(spec=Page)
        mock_page.file = self.create_mock_file(src_path)
        return mock_page

    def test_relative_path_same_directory(self):
        """Test relative path calculation for files in same directory."""
        result = self.plugin._get_relative_path("dir/file1.md", "dir/file2.md")
        assert result == "file2.md"

    def test_relative_path_parent_directory(self):
        """Test relative path calculation for file in parent directory."""
        result = self.plugin._get_relative_path("dir/subdir/file1.md", "dir/file2.md")
        assert result == "../file2.md"

    def test_relative_path_nested_up(self):
        """Test relative path calculation going up multiple levels."""
        result = self.plugin._get_relative_path(
            "dir/sub1/sub2/file1.md", "dir/file2.md"
        )
        assert result == "../../file2.md"

    def test_relative_path_down(self):
        """Test relative path calculation going down into subdirectory."""
        result = self.plugin._get_relative_path("dir/file1.md", "dir/subdir/file2.md")
        assert result == "subdir/file2.md"

    def test_relative_path_different_trees(self):
        """Test relative path calculation for different directory trees."""
        result = self.plugin._get_relative_path(
            "dir1/subdir/file1.md", "dir2/subdir/file2.md"
        )
        assert result == "../../dir2/subdir/file2.md"

    def test_simple_link_replacement(self):
        """Test basic filename link replacement."""
        self.plugin.file_map = {"target.md": "docs/target.md"}

        page = self.create_mock_page("docs/source.md")
        markdown = "[Link text](target.md)"

        result = self.plugin._process_links(markdown, page)
        assert result == "[Link text](target.md)"

    def test_link_with_anchor(self):
        """Test link replacement with anchor preservation."""
        self.plugin.file_map = {"target.md": "docs/guides/target.md"}

        page = self.create_mock_page("docs/index.md")
        markdown = "[Link](target.md#section)"

        result = self.plugin._process_links(markdown, page)
        assert result == "[Link](guides/target.md#section)"

    def test_external_links_unchanged(self):
        """Test that external links are not modified."""
        page = self.create_mock_page("docs/index.md")

        test_cases = [
            "[Link](https://example.com)",
            "[Link](http://example.com)",
            "[Link](//example.com)",
            "[Link](mailto:test@example.com)",
        ]

        for markdown in test_cases:
            result = self.plugin._process_links(markdown, page)
            assert result == markdown

    def test_anchor_only_links_unchanged(self):
        """Test that anchor-only links are not modified."""
        page = self.create_mock_page("docs/index.md")
        markdown = "[Link](#section)"

        result = self.plugin._process_links(markdown, page)
        assert result == markdown

    def test_explicit_relative_paths_unchanged(self):
        """Test that explicit relative paths are not modified."""
        page = self.create_mock_page("docs/index.md")

        test_cases = [
            "[Link](../other/file.md)",
            "[Link](./file.md)",
            "[Link](subdir/file.md)",
        ]

        for markdown in test_cases:
            result = self.plugin._process_links(markdown, page)
            assert result == markdown

    def test_absolute_paths_unchanged(self):
        """Test that absolute paths are not modified."""
        page = self.create_mock_page("docs/index.md")
        markdown = "[Link](/docs/file.md)"

        result = self.plugin._process_links(markdown, page)
        assert result == markdown

    def test_multiple_links_in_page(self):
        """Test processing multiple links in a single page."""
        self.plugin.file_map = {
            "file1.md": "docs/file1.md",
            "file2.md": "docs/guides/file2.md",
        }

        page = self.create_mock_page("docs/index.md")
        markdown = """
        [First link](file1.md)
        Some text
        [Second link](file2.md)
        """

        result = self.plugin._process_links(markdown, page)
        assert "[First link](file1.md)" in result
        assert "[Second link](guides/file2.md)" in result

    def test_ambiguous_file_resolution(self):
        """Test that ambiguous files resolve to the first occurrence indexed.

        Driven through on_files rather than by hand: an ambiguous_files entry
        only ever exists for a name already in file_map, so setting one without
        the other would assert against a state the plugin cannot reach.
        """
        mock_files = MagicMock(spec=Files)
        mock_files.__iter__ = MagicMock(return_value=iter([
            self.create_mock_file("docs/index.md"),
            self.create_mock_file("docs/guides/index.md"),
        ]))

        self.plugin.on_files(mock_files, config=MagicMock())

        assert self.plugin.ambiguous_files["index.md"] == [
            "docs/index.md",
            "docs/guides/index.md",
        ]
        assert self.plugin._resolve_filename("index.md") == "docs/index.md"

    def test_first_occurrence_invariant_holds(self):
        """file_map must agree with the head of every ambiguous_files entry."""
        mock_files = MagicMock(spec=Files)
        mock_files.__iter__ = MagicMock(return_value=iter([
            self.create_mock_file("a/dup.md"),
            self.create_mock_file("b/dup.md"),
            self.create_mock_file("c/dup.md"),
            self.create_mock_file("a/unique.md"),
        ]))

        self.plugin.on_files(mock_files, config=MagicMock())

        for filename, paths in self.plugin.ambiguous_files.items():
            assert self.plugin.file_map[filename] == paths[0]

    def test_ambiguous_file_per_page_warning(self, caplog):
        """Test that using an ambiguous filename on a page emits a per-page warning."""
        import logging
        self.plugin.config["warn_on_ambiguous"] = True
        self.plugin.file_map = {"index.md": "docs/index.md"}
        self.plugin.ambiguous_files = {
            "index.md": ["docs/index.md", "docs/guides/index.md"]
        }

        page = self.create_mock_page("docs/about.md")
        markdown = "[Home](index.md)"

        with caplog.at_level(logging.WARNING, logger="mkdocs.plugins.easylinks"):
            self.plugin._process_links(markdown, page)

        assert any("docs/about.md" in msg and "index.md" in msg for msg in caplog.messages)

    def test_ambiguous_files_counted_in_indexed_stats(self):
        """Test that duplicate filenames are counted in files_ambiguous, not files_indexed."""
        mock_config = MagicMock()
        mock_files = MagicMock(spec=Files)

        file1 = self.create_mock_file("docs/index.md")
        file2 = self.create_mock_file("docs/guides/index.md")  # duplicate basename
        file3 = self.create_mock_file("docs/about.md")

        mock_files.__iter__ = MagicMock(return_value=iter([file1, file2, file3]))

        self.plugin.on_files(mock_files, config=mock_config)

        assert self.plugin.stats["total_files_scanned"] == 3
        assert self.plugin.stats["files_indexed"] == 2    # unique filenames only
        assert self.plugin.stats["files_ambiguous"] == 1  # duplicates tracked separately
        assert self.plugin.stats["files_ignored"] == 0
        assert "index.md" in self.plugin.ambiguous_files

    def test_missing_file_returns_none(self):
        """Test that missing files return None."""
        self.plugin.file_map = {}

        resolved = self.plugin._resolve_filename("nonexistent.md")

        assert resolved is None

    def test_dotfiles_ignored(self):
        """Test that files starting with a dot are ignored."""
        mock_config = MagicMock()
        mock_files = MagicMock(spec=Files)

        # Create mock files including some that start with a dot
        regular_file = self.create_mock_file("docs/regular.md")
        dotfile = self.create_mock_file("docs/.hidden.md")
        another_regular = self.create_mock_file("docs/another.md")

        mock_files.__iter__ = MagicMock(return_value=iter([
            regular_file,
            dotfile,
            another_regular,
        ]))

        self.plugin.on_files(mock_files, config=mock_config)

        # Verify that regular files are in the map
        assert "regular.md" in self.plugin.file_map
        assert "another.md" in self.plugin.file_map

        # Verify that dotfiles are NOT in the map
        assert ".hidden.md" not in self.plugin.file_map

    def test_protect_code_fences_disabled(self):
        """Test that links in code fences are processed when protect_code_fences is false."""
        self.plugin.config["protect_code_fences"] = False
        self.plugin.file_map = {"target.md": "reference/target.md"}

        page = self.create_mock_page("docs/index.md")
        markdown = """
```
[Link in fence](target.md)
```
"""
        result = self.plugin._process_links(markdown, page)
        assert "../reference/target.md" in result

    def test_protect_html_comments_disabled(self):
        """Test that links in HTML comments are processed when protect_html_comments is false."""
        self.plugin.config["protect_html_comments"] = False
        self.plugin.file_map = {"target.md": "reference/target.md"}

        page = self.create_mock_page("docs/index.md")
        markdown = "<!-- [Link in comment](target.md) -->"

        result = self.plugin._process_links(markdown, page)
        assert "../reference/target.md" in result

    def test_links_in_code_fences_ignored(self):
        """Test that links inside code fences are not processed."""
        self.plugin.file_map = {"target.md": "docs/guides/target.md"}

        page = self.create_mock_page("docs/index.md")
        markdown = """
Some text with a [working link](target.md).

```markdown
This is example code with [a link](target.md) that should not be processed.
```

Another [working link](target.md) outside the fence.
"""

        result = self.plugin._process_links(markdown, page)

        # Links outside code fences should be processed
        assert "guides/target.md" in result

        # The code fence should remain unchanged
        assert "```markdown" in result
        assert "This is example code with [a link](target.md)" in result

    def test_links_in_html_comments_ignored(self):
        """Test that links inside HTML comments are not processed."""
        self.plugin.file_map = {"target.md": "docs/guides/target.md"}

        page = self.create_mock_page("docs/index.md")
        markdown = """
Before comment [working link](target.md).

<!-- This is a comment with [a link](target.md) that should not be processed -->

After comment [working link](target.md).
"""

        result = self.plugin._process_links(markdown, page)

        # Links outside comments should be processed
        assert "guides/target.md" in result

        # The HTML comment should remain unchanged
        assert "<!-- This is a comment with [a link](target.md)" in result

    def test_multiple_code_fences_and_comments(self):
        """Test handling multiple code fences and HTML comments."""
        self.plugin.file_map = {"target.md": "docs/guides/target.md"}

        page = self.create_mock_page("docs/index.md")
        markdown = """
[Link 1](target.md)

```python
# [Link in code](target.md)
```

[Link 2](target.md)

<!-- [Link in comment](target.md) -->

```bash
echo "[Another link in code](target.md)"
```

[Link 3](target.md)
"""

        result = self.plugin._process_links(markdown, page)

        # Count how many times the processed link appears (should be 3)
        processed_count = result.count("guides/target.md")
        assert processed_count == 3

        # Verify code fences are preserved
        assert "[Link in code](target.md)" in result
        assert "[Another link in code](target.md)" in result

        # Verify HTML comment is preserved
        assert "[Link in comment](target.md)" in result

    def test_image_with_empty_alt_text(self):
        """![](image.png) must resolve — empty alt is the form for decorative images."""
        self.plugin.file_map = {"diagram.png": "images/diagram.png"}

        page = self.create_mock_page("docs/index.md")

        result = self.plugin._process_links("![](diagram.png)", page)

        assert result == "![](../images/diagram.png)"

    def test_link_with_title_preserved(self):
        """A link title must be preserved and must not block resolution."""
        self.plugin.file_map = {"guide.md": "docs/guides/guide.md"}

        page = self.create_mock_page("docs/index.md")

        result = self.plugin._process_links('[Guide](guide.md "The Guide")', page)

        assert result == '[Guide](guides/guide.md "The Guide")'

    def test_link_with_title_not_warned_as_missing(self, caplog):
        """A titled link must not be reported as unresolvable."""
        import logging
        self.plugin.config["warn_on_missing"] = True
        self.plugin.file_map = {"guide.md": "docs/guides/guide.md"}

        page = self.create_mock_page("docs/index.md")

        with caplog.at_level(logging.WARNING, logger="mkdocs.plugins.easylinks"):
            self.plugin._process_links("[Guide](guide.md 'The Guide')", page)

        assert caplog.messages == []
        assert self.plugin.stats["links_resolved"] == 1

    def test_linked_image_badge_pattern(self):
        """[![alt](icon.png)](target.md) must resolve both the image and the link."""
        self.plugin.file_map = {
            "logo.png": "images/logo.png",
            "api.md": "reference/api.md",
        }

        page = self.create_mock_page("docs/index.md")

        result = self.plugin._process_links("[![Logo](logo.png)](api.md)", page)

        assert result == "[![Logo](../images/logo.png)](../reference/api.md)"

    def test_nested_image_resolved_under_external_link(self):
        """A nested image resolves even when the outer target is left alone."""
        self.plugin.file_map = {"logo.png": "images/logo.png"}

        page = self.create_mock_page("docs/index.md")
        markdown = "[![Logo](logo.png)](https://example.com)"

        result = self.plugin._process_links(markdown, page)

        assert result == "[![Logo](../images/logo.png)](https://example.com)"

    def test_bracketed_link_text_preserved(self):
        """Bracket nesting in link text must not cut the match short."""
        self.plugin.file_map = {"api.md": "reference/api.md"}

        page = self.create_mock_page("docs/index.md")

        result = self.plugin._process_links("[see [the] docs](api.md)", page)

        assert result == "[see [the] docs](../reference/api.md)"

    def test_unrelated_brackets_near_link(self):
        """A bare [bracketed] phrase must not swallow a following link."""
        self.plugin.file_map = {"api.md": "reference/api.md"}

        page = self.create_mock_page("docs/index.md")

        result = self.plugin._process_links("See [foo] and [bar](api.md).", page)

        assert result == "See [foo] and [bar](../reference/api.md)."

    def test_anchor_containing_colon(self):
        """A colon inside a fragment must not read as a URL scheme."""
        self.plugin.file_map = {"api.md": "reference/api.md"}

        page = self.create_mock_page("docs/index.md")

        result = self.plugin._process_links("[API](api.md#section:sub)", page)

        assert result == "[API](../reference/api.md#section:sub)"

    def test_angle_bracketed_destination(self):
        """<...> destinations resolve and keep their brackets."""
        self.plugin.file_map = {"api.md": "reference/api.md"}

        page = self.create_mock_page("docs/index.md")

        result = self.plugin._process_links("[API](<api.md>)", page)

        assert result == "[API](<../reference/api.md>)"

    def test_destination_surrounding_whitespace_preserved(self):
        """Whitespace around a destination is tolerated and preserved."""
        self.plugin.file_map = {"api.md": "reference/api.md"}

        page = self.create_mock_page("docs/index.md")

        result = self.plugin._process_links("[API]( api.md )", page)

        assert result == "[API]( ../reference/api.md )"

    def test_empty_destination_unchanged(self):
        """An empty destination must be left exactly as written."""
        page = self.create_mock_page("docs/index.md")

        for markdown in ["[text]()", "[text](   )"]:
            assert self.plugin._process_links(markdown, page) == markdown

    def test_unterminated_angle_destination_unchanged(self):
        """A malformed angle-bracket destination must be left alone."""
        self.plugin.file_map = {"api.md": "reference/api.md"}

        page = self.create_mock_page("docs/index.md")
        markdown = "[API](<api.md)"

        assert self.plugin._process_links(markdown, page) == markdown

    def test_dangerous_schemes_still_blocked_in_new_syntaxes(self):
        """The scheme guard must hold for angle brackets, titles and nesting."""
        # A matching basename is indexed to prove the scheme wins regardless.
        self.plugin.file_map = {"passwd": "etc/passwd", "x.md": "docs/x.md"}
        page = self.create_mock_page("docs/index.md")

        dangerous = [
            "[XSS](<javascript:alert(1)>)",
            '[XSS](javascript:alert(1) "title")',
            "[XSS]( javascript:alert(1) )",
            "[XSS](javascript:alert(1)#frag)",
            "[Secret](<file:///etc/passwd>)",
            "[VB](vbscript:msgbox(1))",
            "[Data](data:text/html,<h1>hi</h1>)",
        ]

        for markdown in dangerous:
            result = self.plugin._process_links(markdown, page)
            assert result == markdown, f"Expected unchanged: {markdown}"

    def test_links_in_inline_code_ignored(self):
        """A link inside a backtick code span must not be rewritten."""
        self.plugin.file_map = {"api.md": "reference/api.md"}

        page = self.create_mock_page("docs/index.md")
        markdown = "Write `[x](api.md)` to link, as in [this](api.md)."

        result = self.plugin._process_links(markdown, page)

        assert "`[x](api.md)`" in result
        assert "[this](../reference/api.md)" in result

    def test_protect_inline_code_disabled(self):
        """Code spans are processed when protect_inline_code is false."""
        self.plugin.config["protect_inline_code"] = False
        self.plugin.file_map = {"api.md": "reference/api.md"}

        page = self.create_mock_page("docs/index.md")
        markdown = "Write `[x](api.md)` to link."

        result = self.plugin._process_links(markdown, page)

        assert "`[x](../reference/api.md)`" in result

    def test_multi_backtick_code_span(self):
        """A span opened with several backticks closes on the same count."""
        self.plugin.file_map = {"api.md": "reference/api.md"}

        page = self.create_mock_page("docs/index.md")
        markdown = "Inline ``a `[x](api.md)` b`` and [real](api.md)."

        result = self.plugin._process_links(markdown, page)

        assert "``a `[x](api.md)` b``" in result
        assert "[real](../reference/api.md)" in result

    def test_unmatched_backtick_is_literal_text(self):
        """A lone backtick protects nothing — it is literal text, per CommonMark."""
        self.plugin.file_map = {"api.md": "reference/api.md"}

        page = self.create_mock_page("docs/index.md")
        markdown = "A stray ` backtick and [a link](api.md)."

        result = self.plugin._process_links(markdown, page)

        assert "[a link](../reference/api.md)" in result

    def test_code_span_does_not_cross_blank_line(self):
        """A stray backtick must not pair across a paragraph break."""
        self.plugin.file_map = {"api.md": "reference/api.md"}

        page = self.create_mock_page("docs/index.md")
        markdown = "Stray ` here.\n\n[middle](api.md)\n\nAnother ` there.\n"

        result = self.plugin._process_links(markdown, page)

        assert "[middle](../reference/api.md)" in result

    def test_fence_delimiter_not_treated_as_code_span(self):
        """With fences unprotected, ``` lines stay inert rather than pairing as a span."""
        self.plugin.config["protect_code_fences"] = False
        self.plugin.file_map = {"api.md": "reference/api.md"}

        page = self.create_mock_page("docs/index.md")
        markdown = "```\n[x](api.md)\n```\n"

        result = self.plugin._process_links(markdown, page)

        assert "[x](../reference/api.md)" in result

    def test_inline_code_inside_fence_not_double_claimed(self):
        """Backticks inside a fence belong to the fence, not to a code span."""
        self.plugin.file_map = {"api.md": "reference/api.md"}

        page = self.create_mock_page("docs/index.md")
        markdown = "```python\nx = `[a](api.md)`\n```\n\n[after](api.md)\n"

        result = self.plugin._process_links(markdown, page)

        assert "x = `[a](api.md)`" in result
        assert "[after](../reference/api.md)" in result

    def test_longer_fence_contains_shorter_fence(self):
        """A ```` fence must not be closed by an inner ``` fence."""
        self.plugin.file_map = {"api.md": "reference/api.md"}

        page = self.create_mock_page("docs/index.md")
        markdown = (
            "````markdown\n"
            "```\n"
            "[inside](api.md)\n"
            "```\n"
            "````\n"
            "\n"
            "Prose [outside](api.md)\n"
        )

        result = self.plugin._process_links(markdown, page)

        # Everything within the outer fence is code, including the inner fence
        assert "[inside](api.md)" in result
        # ...and the document continues normally afterwards
        assert "[outside](../reference/api.md)" in result

    def test_fence_closer_must_be_alone_on_its_line(self):
        """An opener like '```python' must not act as a closer for an open fence."""
        self.plugin.file_map = {"api.md": "reference/api.md"}

        page = self.create_mock_page("docs/index.md")
        markdown = "```\n[a](api.md)\n```python\n[b](api.md)\n```\n\n[c](api.md)\n"

        result = self.plugin._process_links(markdown, page)

        assert "[a](api.md)" in result
        assert "[b](api.md)" in result
        assert "[c](../reference/api.md)" in result

    def test_tilde_fence_not_closed_by_backticks(self):
        """A ~~~ fence must only be closed by tildes."""
        self.plugin.file_map = {"api.md": "reference/api.md"}

        page = self.create_mock_page("docs/index.md")
        markdown = "~~~\n[a](api.md)\n```\n[b](api.md)\n~~~\n\n[c](api.md)\n"

        result = self.plugin._process_links(markdown, page)

        assert "[a](api.md)" in result
        assert "[b](api.md)" in result
        assert "[c](../reference/api.md)" in result

    def test_indented_fence_in_list_item_protected(self):
        """A fence indented to a list item's content column is still a fence."""
        self.plugin.file_map = {"api.md": "reference/api.md"}

        page = self.create_mock_page("docs/index.md")
        markdown = "- item:\n\n    ```\n    [x](api.md)\n    ```\n\n[after](api.md)\n"

        result = self.plugin._process_links(markdown, page)

        assert "[x](api.md)" in result
        assert "[after](../reference/api.md)" in result

    def test_indented_fence_in_admonition_protected(self):
        """A fence inside an admonition is protected; the admonition's prose is not."""
        self.plugin.file_map = {"guide.md": "reference/guide.md"}

        page = self.create_mock_page("docs/index.md")
        markdown = (
            "!!! note\n"
            "    ```\n"
            "    [code](guide.md)\n"
            "    ```\n"
            "\n"
            "    See the [guide](guide.md).\n"
        )

        result = self.plugin._process_links(markdown, page)

        assert "[code](guide.md)" in result                   # fence protected
        assert "[guide](../reference/guide.md)" in result     # prose still processed

    def test_unclosed_fence_protects_rest_of_document(self):
        """An unclosed fence runs to end of document, as CommonMark specifies."""
        self.plugin.file_map = {"api.md": "reference/api.md"}

        page = self.create_mock_page("docs/index.md")
        markdown = "Prose [a](api.md)\n\n```python\n[b](api.md)\n"

        result = self.plugin._process_links(markdown, page)

        assert "[a](../reference/api.md)" in result   # before the fence
        assert "[b](api.md)" in result                # inside the unclosed fence

    def test_unclosed_html_comment_protects_rest_of_document(self):
        """An unterminated comment likewise extends to the end of the document."""
        self.plugin.file_map = {"api.md": "reference/api.md"}

        page = self.create_mock_page("docs/index.md")
        markdown = "Prose [a](api.md)\n\n<!-- [b](api.md)\n"

        result = self.plugin._process_links(markdown, page)

        assert "[a](../reference/api.md)" in result
        assert "[b](api.md)" in result

    def test_code_fence_inside_html_comment_restored(self):
        """A fence nested in a comment must be restored, not left as a placeholder.

        Extracting fences and comments in two passes stored the fence's
        placeholder inside the comment's saved text. The restore pass does not
        rescan its own replacements, so the placeholder reached the page
        verbatim and the fence content was lost.
        """
        self.plugin.file_map = {"guide.md": "reference/guide.md"}

        page = self.create_mock_page("docs/index.md")
        markdown = "<!--\n```\n[x](guide.md)\n```\n-->\n"

        result = self.plugin._process_links(markdown, page)

        assert result == markdown
        assert "EASYLINKS_" not in result

    def test_html_comment_inside_code_fence_restored(self):
        """The mirror case: a comment nested in a fence must survive intact."""
        self.plugin.file_map = {"guide.md": "reference/guide.md"}

        page = self.create_mock_page("docs/index.md")
        markdown = "```html\n<!-- [x](guide.md) -->\n```\n"

        result = self.plugin._process_links(markdown, page)

        assert result == markdown
        assert "EASYLINKS_" not in result

    def test_fence_inside_comment_when_comments_unprotected(self):
        """With comment protection off, a fence inside a comment is still protected."""
        self.plugin.config["protect_html_comments"] = False
        self.plugin.file_map = {"guide.md": "reference/guide.md"}

        page = self.create_mock_page("docs/index.md")
        markdown = "<!-- intro [a](guide.md)\n```\n[b](guide.md)\n```\n-->\n"

        result = self.plugin._process_links(markdown, page)

        assert "[b](guide.md)" in result                 # fence still protected
        assert "[a](../reference/guide.md)" in result    # comment prose processed
        assert "EASYLINKS_" not in result

    def test_more_than_ten_protected_blocks_restored_exactly(self):
        """Pages with more than ten protected blocks must restore each block intact.

        Placeholders are numbered, so 'EASYLINKS_<hex>_1' is a textual prefix of
        'EASYLINKS_<hex>_10'. Restoring via an alternation over the raw keys
        matches the shorter key first and splices block 1's content in where
        block 10 belonged, silently corrupting the page.
        """
        self.plugin.file_map = {"target.md": "reference/target.md"}

        page = self.create_mock_page("docs/index.md")
        markdown = "\n\n".join(f"```\nfence {i}\n```" for i in range(12))

        result = self.plugin._process_links(markdown, page)

        assert result == markdown
        for i in range(12):
            assert f"fence {i}\n" in result
        assert "EASYLINKS_" not in result

    def test_many_mixed_protected_blocks_restored_exactly(self):
        """Fences and HTML comments share one counter; both kinds must survive past ten."""
        self.plugin.file_map = {"target.md": "reference/target.md"}

        page = self.create_mock_page("docs/index.md")
        blocks = []
        for i in range(8):
            blocks.append(f"```\nfence {i} [x](target.md)\n```")
            blocks.append(f"<!-- comment {i} [x](target.md) -->")
        markdown = "\n\n".join(blocks)

        result = self.plugin._process_links(markdown, page)

        # 16 protected blocks, none processed and none swapped for another
        assert result == markdown
        assert "EASYLINKS_" not in result

    def test_placeholder_lookalike_text_left_alone(self):
        """Authored text shaped like a placeholder must not be swallowed on restore."""
        self.plugin.file_map = {"target.md": "reference/target.md"}

        page = self.create_mock_page("docs/index.md")
        lookalike = "EASYLINKS_" + "a" * 32 + "_9_"
        markdown = f"```\ncode\n```\n\nProse mentioning {lookalike} verbatim.\n"

        result = self.plugin._process_links(markdown, page)

        assert lookalike in result
        assert "```\ncode\n```" in result

    def test_code_fence_with_backticks(self):
        """Test code fences using backticks."""
        self.plugin.file_map = {"api.md": "reference/api.md"}

        page = self.create_mock_page("docs/index.md")
        markdown = """
[Normal link](api.md)

```
[Link in fence](api.md)
```

[Another normal link](api.md)
"""

        result = self.plugin._process_links(markdown, page)

        # Should have exactly 2 processed links (outside the fence)
        assert result.count("../reference/api.md") == 2

        # Code fence content should be unchanged
        assert "[Link in fence](api.md)" in result

    def test_code_fence_with_tildes(self):
        """Test code fences using tildes."""
        self.plugin.file_map = {"test.md": "reference/test.md"}

        page = self.create_mock_page("docs/index.md")
        markdown = """
[Normal link](test.md)

~~~
[Link in fence](test.md)
~~~

[Another normal link](test.md)
"""

        result = self.plugin._process_links(markdown, page)

        # Should have exactly 2 processed links (outside the fence)
        assert result.count("../reference/test.md") == 2

        # Code fence content should be unchanged
        assert "[Link in fence](test.md)" in result

    def test_nested_structures(self):
        """Test complex nested structures with code and comments."""
        self.plugin.file_map = {
            "guide.md": "docs/guide.md",
            "api.md": "docs/reference/api.md"
        }

        page = self.create_mock_page("docs/index.md")
        markdown = """
# Documentation

[Link to guide](guide.md)

## Code Example

```python
def example():
    # See [guide.md](guide.md) for details
    # Also check [api.md](api.md)
    pass
```

<!--
Commented section with code:
```
[guide.md](guide.md)
```
And a [link](api.md) in the comment
-->

Final link to [API](api.md).
"""

        result = self.plugin._process_links(markdown, page)

        # Regular links should be processed
        assert "[Link to guide](docs/guide.md)" in result or "[Link to guide](guide.md)" in result
        assert "[API](reference/api.md)" in result

        # Code fence content should be unchanged
        assert "# See [guide.md](guide.md) for details" in result
        assert "# Also check [api.md](api.md)" in result

        # HTML comment should be unchanged including its nested code fence
        assert "And a [link](api.md) in the comment" in result
        assert "Commented section with code:\n```\n[guide.md](guide.md)\n```" in result
        assert "EASYLINKS_" not in result

    def test_image_link_simple(self):
        """Test that image links are processed."""
        self.plugin.file_map = {"diagram.png": "assets/images/diagram.png"}

        page = self.create_mock_page("docs/index.md")
        markdown = "![Diagram](diagram.png)"

        result = self.plugin._process_links(markdown, page)
        assert result == "![Diagram](../assets/images/diagram.png)"

    def test_image_link_same_directory(self):
        """Test image link in same directory."""
        self.plugin.file_map = {"logo.svg": "docs/logo.svg"}

        page = self.create_mock_page("docs/index.md")
        markdown = "![Logo](logo.svg)"

        result = self.plugin._process_links(markdown, page)
        assert result == "![Logo](logo.svg)"

    def test_multiple_image_links(self):
        """Test multiple image links in one page."""
        self.plugin.file_map = {
            "header.jpg": "images/header.jpg",
            "footer.png": "images/footer.png",
            "icon.svg": "assets/icon.svg"
        }

        page = self.create_mock_page("docs/index.md")
        markdown = """
![Header](header.jpg)

Some content

![Footer](footer.png)

![Icon](icon.svg)
"""

        result = self.plugin._process_links(markdown, page)

        assert "![Header](../images/header.jpg)" in result
        assert "![Footer](../images/footer.png)" in result
        assert "![Icon](../assets/icon.svg)" in result

    def test_mixed_links_and_images(self):
        """Test processing both regular links and images together."""
        self.plugin.file_map = {
            "guide.md": "docs/guides/guide.md",
            "diagram.png": "images/diagram.png"
        }

        page = self.create_mock_page("docs/index.md")
        markdown = """
See the [guide](guide.md) for details.

![Architecture Diagram](diagram.png)

Read more in the [guide](guide.md).
"""

        result = self.plugin._process_links(markdown, page)

        # Both links should be processed
        assert "[guide](guides/guide.md)" in result
        # Image should be processed
        assert "![Architecture Diagram](../images/diagram.png)" in result

    def test_image_with_external_url(self):
        """Test that external image URLs are not modified."""
        page = self.create_mock_page("docs/index.md")

        test_cases = [
            "![Logo](https://example.com/logo.png)",
            "![Icon](http://example.com/icon.svg)",
            "![Badge](//cdn.example.com/badge.png)",
        ]

        for markdown in test_cases:
            result = self.plugin._process_links(markdown, page)
            assert result == markdown

    def test_image_with_absolute_path(self):
        """Test that images with absolute paths are not modified."""
        page = self.create_mock_page("docs/index.md")
        markdown = "![Image](/static/image.png)"

        result = self.plugin._process_links(markdown, page)
        assert result == markdown

    def test_images_in_code_fences_ignored(self):
        """Test that image links in code fences are not processed."""
        self.plugin.file_map = {"diagram.png": "images/diagram.png"}

        page = self.create_mock_page("docs/index.md")
        markdown = """
![Working image](diagram.png)

```markdown
![Example image](diagram.png)
```

![Another working image](diagram.png)
"""

        result = self.plugin._process_links(markdown, page)

        # Images outside code fences should be processed
        assert result.count("../images/diagram.png") == 2

        # Image in code fence should be unchanged
        assert "![Example image](diagram.png)" in result

    def test_all_file_types_included(self):
        """Test that all file types (not just documentation) are mapped."""
        mock_config = MagicMock()
        mock_files = MagicMock(spec=Files)

        # Create various file types
        md_file = self.create_mock_file("docs/page.md")
        png_file = self.create_mock_file("images/photo.png", is_documentation=False)
        jpg_file = self.create_mock_file("assets/banner.jpg", is_documentation=False)
        svg_file = self.create_mock_file("icons/logo.svg", is_documentation=False)

        # Mock the Files object to be iterable
        mock_files.__iter__ = MagicMock(return_value=iter([
            md_file,
            png_file,
            jpg_file,
            svg_file,
        ]))

        self.plugin.on_files(mock_files, config=mock_config)

        # Verify all files are in the map
        assert "page.md" in self.plugin.file_map
        assert "photo.png" in self.plugin.file_map
        assert "banner.jpg" in self.plugin.file_map
        assert "logo.svg" in self.plugin.file_map

    def test_ignore_files_config(self):
        """Test that files in ignore_files list are not mapped."""
        self.plugin.config["ignore_files"] = ["draft.md", "temp.png"]

        mock_config = MagicMock()
        mock_files = MagicMock(spec=Files)

        # Create files including some that should be ignored
        regular_file = self.create_mock_file("docs/regular.md")
        ignored_file = self.create_mock_file("docs/draft.md")
        regular_image = self.create_mock_file("images/photo.png")
        ignored_image = self.create_mock_file("images/temp.png")

        mock_files.__iter__ = MagicMock(return_value=iter([
            regular_file,
            ignored_file,
            regular_image,
            ignored_image,
        ]))

        self.plugin.on_files(mock_files, config=mock_config)

        # Verify regular files are in the map
        assert "regular.md" in self.plugin.file_map
        assert "photo.png" in self.plugin.file_map

        # Verify ignored files are NOT in the map
        assert "draft.md" not in self.plugin.file_map
        assert "temp.png" not in self.plugin.file_map

    def test_ignore_files_empty_list(self):
        """Test that empty ignore_files list allows all files."""
        self.plugin.config["ignore_files"] = []

        mock_config = MagicMock()
        mock_files = MagicMock(spec=Files)

        file1 = self.create_mock_file("docs/file1.md")
        file2 = self.create_mock_file("docs/file2.md")

        mock_files.__iter__ = MagicMock(return_value=iter([file1, file2]))

        self.plugin.on_files(mock_files, config=mock_config)

        # All files should be in the map
        assert "file1.md" in self.plugin.file_map
        assert "file2.md" in self.plugin.file_map

    def test_ignore_files_with_dotfiles(self):
        """Test that ignore_files works alongside dotfile filtering."""
        self.plugin.config["ignore_files"] = ["temp.md"]

        mock_config = MagicMock()
        mock_files = MagicMock(spec=Files)

        regular_file = self.create_mock_file("docs/regular.md")
        ignored_file = self.create_mock_file("docs/temp.md")
        dotfile = self.create_mock_file("docs/.hidden.md")

        mock_files.__iter__ = MagicMock(return_value=iter([
            regular_file,
            ignored_file,
            dotfile,
        ]))

        self.plugin.on_files(mock_files, config=mock_config)

        # Only regular file should be in the map
        assert "regular.md" in self.plugin.file_map
        assert "temp.md" not in self.plugin.file_map
        assert ".hidden.md" not in self.plugin.file_map

    def test_ignore_files_link_resolution(self):
        """Test that ignored files cannot be linked."""
        self.plugin.config["ignore_files"] = ["draft.md"]
        self.plugin.file_map = {
            "published.md": "docs/published.md"
            # draft.md is not in the map because it's ignored
        }

        page = self.create_mock_page("docs/index.md")
        markdown = """
[Published link](published.md)
[Draft link](draft.md)
"""

        result = self.plugin._process_links(markdown, page)

        # Published link should be processed
        assert "[Published link](published.md)" in result

        # Draft link should NOT be processed (stays as-is)
        assert "[Draft link](draft.md)" in result

    def test_ignore_files_glob_pattern(self):
        """Test that glob patterns work in ignore_files."""
        self.plugin.config["ignore_files"] = ["draft-*.md", "*.tmp", "test_*"]

        mock_config = MagicMock()
        mock_files = MagicMock(spec=Files)

        # Create files with various names
        regular_file = self.create_mock_file("docs/article.md")
        draft1 = self.create_mock_file("docs/draft-article.md")
        draft2 = self.create_mock_file("docs/draft-notes.md")
        tmp_file = self.create_mock_file("images/temp.tmp")
        test_file = self.create_mock_file("docs/test_data.csv")
        another_regular = self.create_mock_file("docs/guide.md")

        mock_files.__iter__ = MagicMock(return_value=iter([
            regular_file,
            draft1,
            draft2,
            tmp_file,
            test_file,
            another_regular,
        ]))

        self.plugin.on_files(mock_files, config=mock_config)

        # Regular files should be indexed
        assert "article.md" in self.plugin.file_map
        assert "guide.md" in self.plugin.file_map

        # Files matching patterns should NOT be indexed
        assert "draft-article.md" not in self.plugin.file_map
        assert "draft-notes.md" not in self.plugin.file_map
        assert "temp.tmp" not in self.plugin.file_map
        assert "test_data.csv" not in self.plugin.file_map

    def test_ignore_files_exact_and_pattern_mix(self):
        """Test mixing exact matches and glob patterns."""
        self.plugin.config["ignore_files"] = ["exact.md", "pattern-*.md"]

        mock_config = MagicMock()
        mock_files = MagicMock(spec=Files)

        exact_match = self.create_mock_file("docs/exact.md")
        pattern_match = self.create_mock_file("docs/pattern-test.md")
        no_match = self.create_mock_file("docs/regular.md")

        mock_files.__iter__ = MagicMock(return_value=iter([
            exact_match,
            pattern_match,
            no_match,
        ]))

        self.plugin.on_files(mock_files, config=mock_config)

        assert "regular.md" in self.plugin.file_map
        assert "exact.md" not in self.plugin.file_map
        assert "pattern-test.md" not in self.plugin.file_map

    def test_exclude_dirs(self):
        """Test that exclude_dirs excludes entire directories."""
        self.plugin.config["exclude_dirs"] = ["drafts/", "templates/"]

        mock_config = MagicMock()
        mock_files = MagicMock(spec=Files)

        regular_file = self.create_mock_file("docs/index.md")
        draft_file1 = self.create_mock_file("drafts/article.md")
        draft_file2 = self.create_mock_file("drafts/notes/ideas.md")
        template_file = self.create_mock_file("templates/page.md")
        another_regular = self.create_mock_file("guides/tutorial.md")

        mock_files.__iter__ = MagicMock(return_value=iter([
            regular_file,
            draft_file1,
            draft_file2,
            template_file,
            another_regular,
        ]))

        self.plugin.on_files(mock_files, config=mock_config)

        # Files in regular directories should be indexed
        assert "index.md" in self.plugin.file_map
        assert "tutorial.md" in self.plugin.file_map

        # Files in excluded directories should NOT be indexed
        assert "article.md" not in self.plugin.file_map
        assert "ideas.md" not in self.plugin.file_map
        assert "page.md" not in self.plugin.file_map

    def test_exclude_dirs_without_trailing_slash(self):
        """Test that exclude_dirs works with or without trailing slash."""
        self.plugin.config["exclude_dirs"] = ["drafts", "templates/"]

        mock_config = MagicMock()
        mock_files = MagicMock(spec=Files)

        draft_file = self.create_mock_file("drafts/article.md")
        template_file = self.create_mock_file("templates/page.md")
        regular_file = self.create_mock_file("docs/index.md")

        mock_files.__iter__ = MagicMock(return_value=iter([
            draft_file,
            template_file,
            regular_file,
        ]))

        self.plugin.on_files(mock_files, config=mock_config)

        assert "index.md" in self.plugin.file_map
        assert "article.md" not in self.plugin.file_map
        assert "page.md" not in self.plugin.file_map

    def test_exclude_dirs_nested_paths(self):
        """Test excluding nested directory paths."""
        self.plugin.config["exclude_dirs"] = ["docs/internal/"]

        mock_config = MagicMock()
        mock_files = MagicMock(spec=Files)

        regular_doc = self.create_mock_file("docs/index.md")
        internal_doc = self.create_mock_file("docs/internal/notes.md")
        nested_internal = self.create_mock_file("docs/internal/drafts/ideas.md")

        mock_files.__iter__ = MagicMock(return_value=iter([
            regular_doc,
            internal_doc,
            nested_internal,
        ]))

        self.plugin.on_files(mock_files, config=mock_config)

        assert "index.md" in self.plugin.file_map
        assert "notes.md" not in self.plugin.file_map
        assert "ideas.md" not in self.plugin.file_map

    def test_exclude_dirs_no_partial_name_match(self):
        """Test that excluding 'api' does not exclude 'apidocs' or 'myapi'."""
        self.plugin.config["exclude_dirs"] = ["api"]

        mock_config = MagicMock()
        mock_files = MagicMock(spec=Files)

        in_api = self.create_mock_file("api/exact.md")
        in_apidocs = self.create_mock_file("apidocs/extended.md")
        in_myapi = self.create_mock_file("myapi/prefixed.md")

        mock_files.__iter__ = MagicMock(return_value=iter([in_api, in_apidocs, in_myapi]))

        self.plugin.on_files(mock_files, config=mock_config)

        assert "exact.md" not in self.plugin.file_map      # excluded
        assert "extended.md" in self.plugin.file_map       # NOT excluded
        assert "prefixed.md" in self.plugin.file_map       # NOT excluded

    def test_statistics_tracking(self):
        """Test that statistics are tracked correctly."""
        self.plugin.config["ignore_files"] = ["draft.md"]
        self.plugin.config["exclude_dirs"] = ["templates/"]

        mock_config = MagicMock()
        mock_files = MagicMock(spec=Files)

        # Create various files
        regular1 = self.create_mock_file("docs/page1.md")
        regular2 = self.create_mock_file("docs/page2.md")
        dotfile = self.create_mock_file("docs/.hidden.md")
        ignored = self.create_mock_file("docs/draft.md")
        excluded = self.create_mock_file("templates/template.md")

        mock_files.__iter__ = MagicMock(return_value=iter([
            regular1,
            regular2,
            dotfile,
            ignored,
            excluded,
        ]))

        self.plugin.on_files(mock_files, config=mock_config)

        # Check statistics
        assert self.plugin.stats["total_files_scanned"] == 5
        assert self.plugin.stats["files_indexed"] == 2
        assert self.plugin.stats["files_ignored"] == 3  # dotfile, ignored, excluded

    def test_stats_reset_on_rebuild(self):
        """Test that stats and link_counts reset on each on_files call (e.g. during live reload)."""
        mock_config = MagicMock()
        mock_files = MagicMock(spec=Files)
        file1 = self.create_mock_file("docs/page.md")
        mock_files.__iter__ = MagicMock(return_value=iter([file1]))

        self.plugin.on_files(mock_files, config=mock_config)
        assert self.plugin.stats["total_files_scanned"] == 1

        # Simulate a second build (live reload)
        mock_files.__iter__ = MagicMock(return_value=iter([file1]))
        self.plugin.on_files(mock_files, config=mock_config)

        # Stats should reflect only the second build, not accumulate
        assert self.plugin.stats["total_files_scanned"] == 1

    def test_link_counts_reset_on_rebuild(self):
        """Test that link_counts reset on each on_files call."""
        mock_config = MagicMock()
        mock_files = MagicMock(spec=Files)
        mock_files.__iter__ = MagicMock(return_value=iter([]))

        self.plugin.link_counts["docs/api.md"] = 99

        self.plugin.on_files(mock_files, config=mock_config)

        assert len(self.plugin.link_counts) == 0

    def test_link_counting_statistics(self):
        """Test that link counts are tracked."""
        self.plugin.file_map = {
            "api.md": "docs/api.md",
            "guide.md": "docs/guide.md",
        }

        page = self.create_mock_page("docs/index.md")
        markdown = """
[Link to API](api.md)
[Another API link](api.md)
[Guide link](guide.md)
[Yet another API link](api.md)
"""

        self.plugin._process_links(markdown, page)

        # Check link counts
        assert self.plugin.link_counts["docs/api.md"] == 3
        assert self.plugin.link_counts["docs/guide.md"] == 1

    def test_image_embeds_counted_in_link_counts(self):
        """Image embeds must be counted as references, like ordinary links."""
        self.plugin.file_map = {"diagram.png": "images/diagram.png"}

        page = self.create_mock_page("docs/index.md")
        markdown = "![A](diagram.png)\n![B](diagram.png)"

        self.plugin._process_links(markdown, page)

        assert self.plugin.link_counts["images/diagram.png"] == 2

    def test_embedded_image_not_reported_as_orphaned(self, caplog):
        """An image that is embedded somewhere must not appear under Orphaned files."""
        import logging
        self.plugin.config["show_stats"] = True
        self.plugin.file_map = {
            "used.png": "images/used.png",
            "unused.png": "images/unused.png",
        }

        page = self.create_mock_page("docs/index.md")
        self.plugin._process_links("![Used](used.png)", page)

        with caplog.at_level(logging.INFO, logger="mkdocs.plugins.easylinks"):
            self.plugin.on_post_build(config=MagicMock())

        joined = "\n".join(caplog.messages)
        assert "images/unused.png" in joined      # genuinely orphaned
        assert "images/used.png" not in joined.split("Orphaned")[1]

    def test_statistics_unresolved_links(self):
        """Test that unresolved links are counted."""
        self.plugin.file_map = {"exists.md": "docs/exists.md"}

        page = self.create_mock_page("docs/index.md")
        markdown = """
[Exists](exists.md)
[Missing](missing.md)
[Another missing](notfound.md)
"""

        self.plugin._process_links(markdown, page)

        assert self.plugin.stats["links_resolved"] == 1
        assert self.plugin.stats["links_unresolved"] == 2

    def test_statistics_images_vs_links(self):
        """Test that images and links are counted separately."""
        self.plugin.file_map = {
            "guide.md": "docs/guide.md",
            "diagram.png": "images/diagram.png",
        }

        page = self.create_mock_page("docs/index.md")
        markdown = """
[Link](guide.md)
![Image](diagram.png)
[Another link](guide.md)
"""

        self.plugin._process_links(markdown, page)

        assert self.plugin.stats["links_processed"] == 2
        assert self.plugin.stats["links_resolved"] == 2
        assert self.plugin.stats["images_processed"] == 1
        assert self.plugin.stats["images_resolved"] == 1

    def test_statistics_unresolved_images(self):
        """Test that unresolved images increment images_unresolved, not links_unresolved."""
        self.plugin.file_map = {"exists.png": "images/exists.png"}

        page = self.create_mock_page("docs/index.md")
        markdown = """
![Found](exists.png)
![Missing](missing.png)
"""

        self.plugin._process_links(markdown, page)

        assert self.plugin.stats["images_resolved"] == 1
        assert self.plugin.stats["images_unresolved"] == 1
        assert self.plugin.stats["links_unresolved"] == 0  # image failures must not bleed here

    def test_post_build_stats_suppressed_when_disabled(self, caplog):
        """Test that on_post_build logs nothing when show_stats is false."""
        import logging
        self.plugin.config["show_stats"] = False
        mock_config = MagicMock()

        with caplog.at_level(logging.INFO, logger="mkdocs.plugins.easylinks"):
            self.plugin.on_post_build(config=mock_config)

        assert len(caplog.messages) == 0

    def test_post_build_stats_logged_when_enabled(self, caplog):
        """Test that on_post_build logs all stat categories when show_stats is true."""
        import logging
        self.plugin.config["show_stats"] = True
        self.plugin.stats.update({
            "total_files_scanned": 10,
            "files_indexed": 8,
            "files_ignored": 2,
            "links_processed": 5,
            "links_resolved": 4,
            "links_unresolved": 1,
            "images_processed": 3,
            "images_resolved": 3,
            "images_unresolved": 0,
        })
        mock_config = MagicMock()

        with caplog.at_level(logging.INFO, logger="mkdocs.plugins.easylinks"):
            self.plugin.on_post_build(config=mock_config)

        joined = "\n".join(caplog.messages)
        assert "Files scanned: 10" in joined
        assert "Files indexed: 8" in joined
        assert "Files ignored: 2" in joined
        assert "Links processed: 5" in joined
        assert "Links resolved: 4" in joined
        assert "Links unresolved: 1" in joined
        assert "Images processed: 3" in joined
        assert "Images resolved: 3" in joined
        assert "Images unresolved: 0" in joined

    def test_post_build_most_linked_files(self, caplog):
        """Test that most frequently linked files are logged."""
        import logging
        self.plugin.config["show_stats"] = True
        self.plugin.link_counts["docs/api.md"] = 5
        self.plugin.link_counts["docs/guide.md"] = 2
        mock_config = MagicMock()

        with caplog.at_level(logging.INFO, logger="mkdocs.plugins.easylinks"):
            self.plugin.on_post_build(config=mock_config)

        joined = "\n".join(caplog.messages)
        assert "docs/api.md" in joined
        assert "docs/guide.md" in joined

    def test_post_build_orphaned_files(self, caplog):
        """Test that orphaned files are reported."""
        import logging
        self.plugin.config["show_stats"] = True
        self.plugin.file_map = {
            "api.md": "docs/api.md",
            "guide.md": "docs/guide.md",
        }
        self.plugin.link_counts["docs/api.md"] = 1  # guide.md is orphaned
        mock_config = MagicMock()

        with caplog.at_level(logging.INFO, logger="mkdocs.plugins.easylinks"):
            self.plugin.on_post_build(config=mock_config)

        joined = "\n".join(caplog.messages)
        assert "docs/guide.md" in joined
        assert "Orphaned" in joined

    def test_post_build_paths_use_forward_slashes(self, caplog):
        """Stats output must read the same regardless of the platform's separator."""
        import logging
        self.plugin.config["show_stats"] = True
        self.plugin.file_map = {"orphan.md": r"docs\sub\orphan.md"}
        self.plugin.link_counts[r"docs\sub\linked.md"] = 3
        mock_config = MagicMock()

        with caplog.at_level(logging.INFO, logger="mkdocs.plugins.easylinks"):
            self.plugin.on_post_build(config=mock_config)

        joined = "\n".join(caplog.messages)
        assert "docs/sub/linked.md" in joined
        assert "docs/sub/orphan.md" in joined
        assert "\\" not in joined

    def test_post_build_paths_are_sanitized(self, caplog):
        """Filenames are attacker-controlled, so stats output must escape them too."""
        import logging
        self.plugin.config["show_stats"] = True
        self.plugin.file_map = {"evil.md": "docs/evil\nINFO - spoofed.md"}
        mock_config = MagicMock()

        with caplog.at_level(logging.INFO, logger="mkdocs.plugins.easylinks"):
            self.plugin.on_post_build(config=mock_config)

        joined = "\n".join(caplog.messages)
        assert "docs/evil\\nINFO - spoofed.md" in joined

    def test_post_build_orphaned_files_truncated(self, caplog):
        """Test that orphaned files list is truncated after 10 entries."""
        import logging
        self.plugin.config["show_stats"] = True
        self.plugin.file_map = {f"file{i}.md": f"docs/file{i}.md" for i in range(15)}
        # link_counts is empty so all 15 are orphaned
        mock_config = MagicMock()

        with caplog.at_level(logging.INFO, logger="mkdocs.plugins.easylinks"):
            self.plugin.on_post_build(config=mock_config)

        joined = "\n".join(caplog.messages)
        assert "... and 5 more" in joined

    def test_combined_ignore_and_exclude(self):
        """Test that ignore_files and exclude_dirs work together."""
        self.plugin.config["ignore_files"] = ["draft-*.md"]
        self.plugin.config["exclude_dirs"] = ["templates/"]

        mock_config = MagicMock()
        mock_files = MagicMock(spec=Files)

        regular = self.create_mock_file("docs/regular.md")
        draft_in_docs = self.create_mock_file("docs/draft-article.md")
        file_in_templates = self.create_mock_file("templates/page.md")
        draft_in_templates = self.create_mock_file("templates/draft-test.md")

        mock_files.__iter__ = MagicMock(return_value=iter([
            regular,
            draft_in_docs,
            file_in_templates,
            draft_in_templates,
        ]))

        self.plugin.on_files(mock_files, config=mock_config)

        # Only regular file should be indexed
        assert "regular.md" in self.plugin.file_map
        assert "draft-article.md" not in self.plugin.file_map  # Ignored by pattern
        assert "page.md" not in self.plugin.file_map  # Excluded directory
        assert "draft-test.md" not in self.plugin.file_map  # Both excluded and ignored

    def test_indented_content_processed(self):
        """Test that indented content (like in admonitions) is processed for links."""
        self.plugin.file_map = {"guide.md": "reference/guide.md"}

        page = self.create_mock_page("docs/index.md")
        markdown = """
# Documentation

!!! note "Important"
    See the [guide](guide.md) for details.

    This is indented content in an admonition.
    The [guide link](guide.md) should be processed.

!!! warning
    Another [guide reference](guide.md) here.
"""

        result = self.plugin._process_links(markdown, page)

        # All links should be processed (indented content is NOT protected)
        assert result.count("../reference/guide.md") == 3

    def test_indented_list_links_processed(self):
        """Test that links in indented lists are processed."""
        self.plugin.file_map = {"api.md": "docs/reference/api.md"}

        page = self.create_mock_page("docs/index.md")
        markdown = """
Some text:

- First level
    - Nested level with [API link](api.md)
    - Another nested [link to API](api.md)
        - Even more nested [API](api.md)
"""

        result = self.plugin._process_links(markdown, page)

        # All indented links should be processed
        assert result.count("reference/api.md") == 3

    def test_fenced_vs_indented_code(self):
        """Test that fenced code is protected but indented content is not."""
        self.plugin.file_map = {"example.md": "reference/example.md"}

        page = self.create_mock_page("docs/index.md")
        markdown = """
Fenced code (should NOT be processed):

```python
# [example](example.md)
```

Indented content in admonition (SHOULD be processed):

!!! tip
    Check the [example](example.md) page.

Regular paragraph with [example link](example.md).
"""

        result = self.plugin._process_links(markdown, page)

        # Fenced code link should NOT be processed
        assert "# [example](example.md)" in result

        # Indented admonition link SHOULD be processed
        # Count should be 2 (one in admonition, one in regular paragraph)
        assert result.count("../reference/example.md") == 2

    def test_mkdocs_admonition_with_images(self):
        """Test that images in MkDocs admonitions are processed."""
        self.plugin.file_map = {"diagram.png": "images/diagram.png"}

        page = self.create_mock_page("docs/index.md")
        markdown = """
!!! note "See diagram"
    ![Architecture](diagram.png)

    The diagram above shows the architecture.
"""

        result = self.plugin._process_links(markdown, page)

        # Image in admonition should be processed
        assert "../images/diagram.png" in result

    # ------------------------------------------------------------------
    # Security fix: log injection (_sanitize_log)
    # ------------------------------------------------------------------

    def test_sanitize_log_escapes_newlines(self):
        """_sanitize_log must escape newlines so they cannot inject fake log lines."""
        from mkdocs_easylinks.plugin import _sanitize_log
        assert _sanitize_log("file\nINJECTED WARNING.md") == "file\\nINJECTED WARNING.md"

    def test_sanitize_log_escapes_carriage_returns(self):
        """_sanitize_log must escape carriage returns."""
        from mkdocs_easylinks.plugin import _sanitize_log
        assert _sanitize_log("file\r.md") == "file\\r.md"

    def test_sanitize_log_escapes_tabs(self):
        """_sanitize_log must escape tab characters."""
        from mkdocs_easylinks.plugin import _sanitize_log
        assert _sanitize_log("file\t.md") == "file\\t.md"

    def test_sanitize_log_normal_string_unchanged(self):
        """_sanitize_log must leave strings without control characters unchanged."""
        from mkdocs_easylinks.plugin import _sanitize_log
        assert _sanitize_log("subdir/normal-file.md") == "subdir/normal-file.md"

    def test_sanitize_log_multiple_control_chars(self):
        """_sanitize_log must escape all control character types in one pass."""
        from mkdocs_easylinks.plugin import _sanitize_log
        assert _sanitize_log("a\nb\rc\td") == "a\\nb\\rc\\td"

    def test_sanitize_log_escapes_ansi_escape(self):
        """_sanitize_log must escape ESC so terminals tailing logs cannot be hijacked."""
        from mkdocs_easylinks.plugin import _sanitize_log
        assert _sanitize_log("file\x1b[31mRED.md") == "file\\x1b[31mRED.md"

    def test_sanitize_log_escapes_null_byte(self):
        """_sanitize_log must escape NUL bytes."""
        from mkdocs_easylinks.plugin import _sanitize_log
        assert _sanitize_log("file\x00.md") == "file\\x00.md"

    def test_sanitize_log_escapes_vertical_tab_and_form_feed(self):
        """_sanitize_log must escape \\v and \\f, which can move the cursor in some terminals."""
        from mkdocs_easylinks.plugin import _sanitize_log
        assert _sanitize_log("a\vb\fc") == "a\\x0bb\\x0cc"

    def test_sanitize_log_escapes_unicode_line_separator(self):
        """_sanitize_log must escape U+2028 and U+2029, which act as line breaks in some viewers."""
        from mkdocs_easylinks.plugin import _sanitize_log
        assert _sanitize_log("a b c") == "a\\u2028b\\u2029c"

    def test_sanitize_log_preserves_printable_unicode(self):
        """_sanitize_log must leave printable Unicode (accents, emoji, CJK) alone."""
        from mkdocs_easylinks.plugin import _sanitize_log
        assert _sanitize_log("café-日本語-🚀.md") == "café-日本語-🚀.md"

    # ------------------------------------------------------------------
    # Security fix: path traversal (_is_safe_path / on_files)
    # ------------------------------------------------------------------

    def test_is_safe_path_normal_path(self):
        """A normal relative path should be considered safe."""
        assert self.plugin._is_safe_path("subdir/file.md") is True

    def test_is_safe_path_root_level_file(self):
        """A filename at the root level should be safe."""
        assert self.plugin._is_safe_path("file.md") is True

    def test_is_safe_path_traversal_escape(self):
        """A path that escapes the docs root must be rejected."""
        assert self.plugin._is_safe_path("../../etc/passwd") is False

    def test_is_safe_path_single_parent_traversal(self):
        """A path starting with .. must be rejected."""
        assert self.plugin._is_safe_path("../outside.md") is False

    def test_is_safe_path_embedded_traversal_that_escapes(self):
        """An embedded .. sequence that resolves outside the root must be rejected."""
        assert self.plugin._is_safe_path("subdir/../../../escape.md") is False

    def test_is_safe_path_embedded_traversal_that_stays_inside(self):
        """An embedded .. that stays within the root should be accepted."""
        assert self.plugin._is_safe_path("subdir/../other/file.md") is True

    def test_is_safe_path_rejects_posix_absolute(self):
        """An absolute POSIX path must be rejected even though it has no '..'."""
        assert self.plugin._is_safe_path("/etc/passwd") is False

    def test_is_safe_path_rejects_windows_absolute(self):
        """An absolute Windows path must be rejected when running on Windows."""
        import os
        import pytest
        if os.name != "nt":
            pytest.skip("Windows-specific path semantics")
        assert self.plugin._is_safe_path(r"C:\Windows\System32\config\SAM") is False
        assert self.plugin._is_safe_path(r"\\server\share\file.md") is False

    def test_traversal_path_ignored_in_on_files(self):
        """Files whose src_path escapes the docs root must be excluded from the index."""
        mock_config = MagicMock()
        mock_files = MagicMock(spec=Files)

        safe_file = self.create_mock_file("docs/safe.md")
        traversal_file = self.create_mock_file("../../secret.md")

        mock_files.__iter__ = MagicMock(return_value=iter([safe_file, traversal_file]))

        self.plugin.on_files(mock_files, config=mock_config)

        assert "safe.md" in self.plugin.file_map
        assert "secret.md" not in self.plugin.file_map
        assert self.plugin.stats["files_ignored"] == 1

    # ------------------------------------------------------------------
    # Security fix: URL scheme allowlist
    # ------------------------------------------------------------------

    def test_dangerous_url_schemes_unchanged(self):
        """Links with dangerous URL schemes must be returned untouched."""
        page = self.create_mock_page("docs/index.md")

        dangerous = [
            "[XSS](javascript:alert(1))",
            "[Data](data:text/html,<h1>test</h1>)",
            "[VB](vbscript:msgbox('xss'))",
            "[Blob](blob:https://example.com/some-uuid)",
        ]

        for markdown in dangerous:
            result = self.plugin._process_links(markdown, page)
            assert result == markdown, f"Expected unchanged: {markdown}"

    def test_file_url_unchanged(self):
        """file: URLs must be passed through unchanged, not treated as filenames."""
        # Even if a matching basename happened to be indexed, the scheme must win.
        self.plugin.file_map = {"passwd": "/etc/passwd"}
        page = self.create_mock_page("docs/index.md")
        markdown = "[Secret](file:///etc/passwd)"

        result = self.plugin._process_links(markdown, page)
        assert result == markdown

    # ------------------------------------------------------------------
    # Security fix: empty string in exclude_dirs
    # ------------------------------------------------------------------

    def test_exclude_dirs_empty_string_does_not_exclude_all(self):
        """An empty string entry in exclude_dirs must not silently exclude every file."""
        self.plugin.config["exclude_dirs"] = [""]

        mock_config = MagicMock()
        mock_files = MagicMock(spec=Files)

        file1 = self.create_mock_file("docs/page.md")
        file2 = self.create_mock_file("docs/another.md")

        mock_files.__iter__ = MagicMock(return_value=iter([file1, file2]))

        self.plugin.on_files(mock_files, config=mock_config)

        assert "page.md" in self.plugin.file_map
        assert "another.md" in self.plugin.file_map
        assert self.plugin.stats["files_indexed"] == 2
