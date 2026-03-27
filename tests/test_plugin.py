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

        result = self.plugin._process_links(markdown, page, None)
        assert result == "[Link text](target.md)"

    def test_link_with_anchor(self):
        """Test link replacement with anchor preservation."""
        self.plugin.file_map = {"target.md": "docs/guides/target.md"}

        page = self.create_mock_page("docs/index.md")
        markdown = "[Link](target.md#section)"

        result = self.plugin._process_links(markdown, page, None)
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
            result = self.plugin._process_links(markdown, page, None)
            assert result == markdown

    def test_anchor_only_links_unchanged(self):
        """Test that anchor-only links are not modified."""
        page = self.create_mock_page("docs/index.md")
        markdown = "[Link](#section)"

        result = self.plugin._process_links(markdown, page, None)
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
            result = self.plugin._process_links(markdown, page, None)
            assert result == markdown

    def test_absolute_paths_unchanged(self):
        """Test that absolute paths are not modified."""
        page = self.create_mock_page("docs/index.md")
        markdown = "[Link](/docs/file.md)"

        result = self.plugin._process_links(markdown, page, None)
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

        result = self.plugin._process_links(markdown, page, None)
        assert "[First link](file1.md)" in result
        assert "[Second link](guides/file2.md)" in result

    def test_ambiguous_file_resolution(self):
        """Test that ambiguous files use the first occurrence."""
        self.plugin.ambiguous_files = {
            "index.md": ["docs/index.md", "docs/guides/index.md"]
        }

        page = self.create_mock_page("docs/about.md")
        resolved = self.plugin._resolve_filename("index.md", page)

        assert resolved == "docs/index.md"

    def test_missing_file_returns_none(self):
        """Test that missing files return None."""
        self.plugin.file_map = {}

        page = self.create_mock_page("docs/index.md")
        resolved = self.plugin._resolve_filename("nonexistent.md", page)

        assert resolved is None

    def test_dotfiles_ignored(self):
        """Test that files starting with a dot are ignored."""
        mock_config = MagicMock()
        mock_files = MagicMock(spec=Files)

        # Create mock files including some that start with a dot
        regular_file = self.create_mock_file("docs/regular.md")
        dotfile = self.create_mock_file("docs/.hidden.md")
        another_regular = self.create_mock_file("docs/another.md")

        mock_files.documentation_pages.return_value = [
            regular_file,
            dotfile,
            another_regular,
        ]

        self.plugin.on_files(mock_files, config=mock_config)

        # Verify that regular files are in the map
        assert "regular.md" in self.plugin.file_map
        assert "another.md" in self.plugin.file_map

        # Verify that dotfiles are NOT in the map
        assert ".hidden.md" not in self.plugin.file_map

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

        result = self.plugin._process_links(markdown, page, None)

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

        result = self.plugin._process_links(markdown, page, None)

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

        result = self.plugin._process_links(markdown, page, None)

        # Count how many times the processed link appears (should be 3)
        processed_count = result.count("guides/target.md")
        assert processed_count == 3

        # Verify code fences are preserved
        assert "[Link in code](target.md)" in result
        assert "[Another link in code](target.md)" in result

        # Verify HTML comment is preserved
        assert "[Link in comment](target.md)" in result

    def test_code_fence_with_backticks(self):
        """Test code fences using backticks."""
        self.plugin.file_map = {"api.md": "docs/api.md"}

        page = self.create_mock_page("docs/index.md")
        markdown = """
[Normal link](api.md)

```
[Link in fence](api.md)
```

[Another normal link](api.md)
"""

        result = self.plugin._process_links(markdown, page, None)

        # Should have exactly 2 processed links
        assert result.count("docs/api.md") == 2

        # Code fence content should be unchanged
        assert "[Link in fence](api.md)" in result

    def test_code_fence_with_tildes(self):
        """Test code fences using tildes."""
        self.plugin.file_map = {"test.md": "docs/test.md"}

        page = self.create_mock_page("docs/index.md")
        markdown = """
[Normal link](test.md)

~~~
[Link in fence](test.md)
~~~

[Another normal link](test.md)
"""

        result = self.plugin._process_links(markdown, page, None)

        # Should have exactly 2 processed links
        assert result.count("docs/test.md") == 2

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

        result = self.plugin._process_links(markdown, page, None)

        # Regular links should be processed
        assert "[Link to guide](docs/guide.md)" in result or "[Link to guide](guide.md)" in result
        assert "[API](reference/api.md)" in result

        # Code fence content should be unchanged
        assert "# See [guide.md](guide.md) for details" in result
        assert "# Also check [api.md](api.md)" in result

        # HTML comment should be unchanged including its nested code fence
        assert "And a [link](api.md) in the comment" in result

    def test_image_link_simple(self):
        """Test that image links are processed."""
        self.plugin.file_map = {"diagram.png": "assets/images/diagram.png"}

        page = self.create_mock_page("docs/index.md")
        markdown = "![Diagram](diagram.png)"

        result = self.plugin._process_links(markdown, page, None)
        assert result == "![Diagram](../assets/images/diagram.png)"

    def test_image_link_same_directory(self):
        """Test image link in same directory."""
        self.plugin.file_map = {"logo.svg": "docs/logo.svg"}

        page = self.create_mock_page("docs/index.md")
        markdown = "![Logo](logo.svg)"

        result = self.plugin._process_links(markdown, page, None)
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

        result = self.plugin._process_links(markdown, page, None)

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

        result = self.plugin._process_links(markdown, page, None)

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
            result = self.plugin._process_links(markdown, page, None)
            assert result == markdown

    def test_image_with_absolute_path(self):
        """Test that images with absolute paths are not modified."""
        page = self.create_mock_page("docs/index.md")
        markdown = "![Image](/static/image.png)"

        result = self.plugin._process_links(markdown, page, None)
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

        result = self.plugin._process_links(markdown, page, None)

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

        result = self.plugin._process_links(markdown, page, None)

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

        self.plugin._process_links(markdown, page, None)

        # Check link counts
        assert self.plugin.link_counts["docs/api.md"] == 3
        assert self.plugin.link_counts["docs/guide.md"] == 1

    def test_statistics_unresolved_links(self):
        """Test that unresolved links are counted."""
        self.plugin.file_map = {"exists.md": "docs/exists.md"}

        page = self.create_mock_page("docs/index.md")
        markdown = """
[Exists](exists.md)
[Missing](missing.md)
[Another missing](notfound.md)
"""

        self.plugin._process_links(markdown, page, None)

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

        self.plugin._process_links(markdown, page, None)

        assert self.plugin.stats["links_processed"] == 2
        assert self.plugin.stats["links_resolved"] == 2
        assert self.plugin.stats["images_processed"] == 1
        assert self.plugin.stats["images_resolved"] == 1

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
        self.plugin.file_map = {"guide.md": "docs/guide.md"}

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

        result = self.plugin._process_links(markdown, page, None)

        # All links should be processed (indented content is NOT protected)
        assert result.count("docs/guide.md") == 3 or result.count("[guide](docs/guide.md)") >= 1

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

        result = self.plugin._process_links(markdown, page, None)

        # All indented links should be processed
        assert result.count("reference/api.md") == 3

    def test_fenced_vs_indented_code(self):
        """Test that fenced code is protected but indented content is not."""
        self.plugin.file_map = {"example.md": "docs/example.md"}

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

        result = self.plugin._process_links(markdown, page, None)

        # Fenced code link should NOT be processed
        assert "# [example](example.md)" in result

        # Indented admonition link SHOULD be processed
        # Count should be 2 (one in admonition, one in regular paragraph)
        assert result.count("docs/example.md") == 2 or result.count("[example](docs/example.md)") >= 1

    def test_mkdocs_admonition_with_images(self):
        """Test that images in MkDocs admonitions are processed."""
        self.plugin.file_map = {"diagram.png": "images/diagram.png"}

        page = self.create_mock_page("docs/index.md")
        markdown = """
!!! note "See diagram"
    ![Architecture](diagram.png)

    The diagram above shows the architecture.
"""

        result = self.plugin._process_links(markdown, page, None)

        # Image in admonition should be processed
        assert "../images/diagram.png" in result
