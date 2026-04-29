"""MkDocs plugin for easy cross-references using only filenames."""

import os
import re
import logging
import fnmatch
from uuid import uuid4
from typing import Dict, Optional, Tuple
from collections import defaultdict
from mkdocs.config import config_options
from mkdocs.config.base import Config
from mkdocs.plugins import BasePlugin
from mkdocs.structure.files import Files
from mkdocs.structure.pages import Page
from mkdocs.config.defaults import MkDocsConfig

logger = logging.getLogger("mkdocs.plugins.easylinks")


_LOG_ESCAPES = {"\n": "\\n", "\r": "\\r", "\t": "\\t"}


def _sanitize_log(value: str) -> str:
    """Escape control characters and other non-printable codepoints before logging.

    Filenames can legally contain ANSI escape sequences, NULs, vertical tabs,
    form feeds, or Unicode line separators on POSIX systems. Logging them
    verbatim would let an attacker spoof log lines, recolor output, or
    manipulate a terminal that tails the build log.
    """
    out = []
    for c in value:
        if c in _LOG_ESCAPES:
            out.append(_LOG_ESCAPES[c])
        elif c.isprintable():
            out.append(c)
        elif ord(c) <= 0xff:
            out.append(f"\\x{ord(c):02x}")
        else:
            out.append(f"\\u{ord(c):04x}")
    return "".join(out)


class EasyLinksConfig(Config):
    warn_on_missing = config_options.Type(bool, default=True)
    warn_on_ambiguous = config_options.Type(bool, default=True)
    ignore_files = config_options.Type(list, default=[])
    exclude_dirs = config_options.Type(list, default=[])
    show_stats = config_options.Type(bool, default=False)
    protect_code_fences = config_options.Type(bool, default=True)
    protect_html_comments = config_options.Type(bool, default=True)


class EasyLinksPlugin(BasePlugin[EasyLinksConfig]):
    """Plugin to resolve markdown links by filename only."""

    _link_pattern = re.compile(r'(!)?\[([^\]]+)\]\(([^)]+)\)')
    _code_fence_pattern = re.compile(r'^```[\s\S]*?^```|^~~~[\s\S]*?^~~~', re.MULTILINE)
    _html_comment_pattern = re.compile(r'<!--[\s\S]*?-->')

    def __init__(self):
        super().__init__()
        self.file_map: Dict[str, str] = {}
        self.ambiguous_files: Dict[str, list] = {}
        self._normalized_exclude_dirs: list = []
        # Statistics tracking
        self.stats = {
            "total_files_scanned": 0,
            "files_indexed": 0,
            "files_ambiguous": 0,
            "files_ignored": 0,
            "links_processed": 0,
            "links_resolved": 0,
            "links_unresolved": 0,
            "images_processed": 0,
            "images_resolved": 0,
            "images_unresolved": 0,
        }
        self.link_counts = defaultdict(int)  # Track how many times each file is linked

    def on_files(self, files: Files, *, config: MkDocsConfig) -> Files:
        """Build a mapping of filenames to their full paths."""
        self.file_map = {}
        self.ambiguous_files = {}
        self.stats = {key: 0 for key in self.stats}
        self.link_counts = defaultdict(int)
        self._normalized_exclude_dirs = [
            d.replace("\\", "/").rstrip("/") + "/"
            for d in self.config["exclude_dirs"]
            if d  # skip empty strings — they would normalize to "/" and exclude everything
        ]

        # Process all files (documentation pages, images, etc.)
        for file in files:
            self.stats["total_files_scanned"] += 1

            # Reject paths that escape the docs root (e.g. via symlink traversal)
            if not self._is_safe_path(file.src_path):
                logger.warning(
                    f"easylinks: Skipping file with path outside docs root: "
                    f"'{_sanitize_log(file.src_path)}'"
                )
                self.stats["files_ignored"] += 1
                continue

            filename = os.path.basename(file.src_path)

            # Ignore files starting with a dot (hidden files)
            if filename.startswith('.'):
                self.stats["files_ignored"] += 1
                continue

            # Check if file is in an excluded directory
            if self._is_excluded_dir(file.src_path):
                self.stats["files_ignored"] += 1
                continue

            # Ignore files matching patterns in ignore_files
            if self._should_ignore_file(filename):
                self.stats["files_ignored"] += 1
                continue

            if filename in self.file_map:
                if filename not in self.ambiguous_files:
                    self.ambiguous_files[filename] = [self.file_map[filename]]
                self.ambiguous_files[filename].append(file.src_path)
                self.stats["files_ambiguous"] += 1
            else:
                self.file_map[filename] = file.src_path
                self.stats["files_indexed"] += 1

        # Warn about ambiguous files
        if self.config["warn_on_ambiguous"] and self.ambiguous_files:
            for filename, paths in self.ambiguous_files.items():
                safe_filename = _sanitize_log(filename)
                safe_paths = [_sanitize_log(p) for p in paths]
                logger.warning(
                    f"easylinks: Ambiguous filename '{safe_filename}' found in multiple locations:\n"
                    + "\n".join(f"  - {p}" for p in safe_paths)
                    + "\nLinks to this file will use the first occurrence. "
                    "Consider using full paths for disambiguation."
                )

        return files

    def _is_safe_path(self, src_path: str) -> bool:
        """Return True if src_path stays within the docs root.

        MkDocs supplies src_path as a relative path (e.g. ``subdir/page.md``).
        Absolute paths (``/etc/passwd``, ``C:\\Windows\\...``, UNC paths) and
        relative paths that escape the docs root after normalization (e.g.
        ``../../etc/passwd``) would both produce traversal links in the
        output and must be rejected.
        """
        # os.path.isabs alone is not enough: on Python 3.13+ Windows it returns
        # False for drive-relative paths like ``/etc/passwd`` or ``\foo``, which
        # would still escape the docs root once a drive is resolved.
        if os.path.isabs(src_path) or src_path.startswith(("/", "\\")):
            return False
        if ".." not in src_path:
            return True
        return not os.path.normpath(src_path).startswith("..")

    def _is_excluded_dir(self, file_path: str) -> bool:
        """Check if a file is in an excluded directory."""
        if not self._normalized_exclude_dirs:
            return False

        normalized_path = file_path.replace("\\", "/")
        return any(normalized_path.startswith(d) for d in self._normalized_exclude_dirs)

    def _should_ignore_file(self, filename: str) -> bool:
        """Check if a filename matches any ignore pattern (supports glob patterns)."""
        return any(fnmatch.fnmatch(filename, p) for p in self.config["ignore_files"])

    def on_page_markdown(
        self, markdown: str, *, page: Page, config: MkDocsConfig, files: Files
    ) -> str:
        """Replace simple filename links with full path links."""
        return self._process_links(markdown, page)

    def _process_links(self, markdown: str, page: Page) -> str:
        """Process markdown links and image links, replacing simple filenames with full paths."""
        # Extract code fences and HTML comments before processing
        markdown, protected_blocks = self._extract_protected_blocks(markdown)

        # Capture config flags and stats dict as locals to avoid repeated
        # attribute + dict lookups inside the closure on every link match.
        warn_on_ambiguous = self.config["warn_on_ambiguous"]
        warn_on_missing = self.config["warn_on_missing"]
        stats = self.stats
        page_src_path = page.file.src_path
        # Cache relative-path results within this page: from_path is constant,
        # so keying on to_path alone is sufficient.
        relative_path_cache: Dict[str, str] = {}

        def replace_link(match):
            is_image = match.group(1)  # Will be '!' for images, None for regular links
            link_text = match.group(2)
            link_url = match.group(3)

            # Skip external links, anchors, absolute paths, and any URL with a
            # scheme (colon present). Using a colon as the scheme sentinel is an
            # intentional allowlist: bare filenames never contain colons, so any
            # URL that does (http:, https:, javascript:, data:, file:, mailto:,
            # blob:, vbscript:, etc.) is left untouched rather than resolved.
            if (link_url.startswith(('http://', 'https://', '//', '#', '/'))
                    or ':' in link_url):
                return match.group(0)

            # Extract anchor if present (only relevant for links, not images)
            anchor = ""
            if "#" in link_url:
                link_url, anchor = link_url.split("#", 1)
                anchor = "#" + anchor

            # Check if this is just a filename (no path separators)
            if "/" not in link_url and "\\" not in link_url:
                # Track statistics
                if is_image:
                    stats["images_processed"] += 1
                else:
                    stats["links_processed"] += 1

                resolved_path = self._resolve_filename(link_url)
                if resolved_path:
                    # Warn if this filename is ambiguous
                    if warn_on_ambiguous and link_url in self.ambiguous_files:
                        all_paths = self.ambiguous_files[link_url]
                        logger.warning(
                            f"easylinks: Ambiguous filename '{_sanitize_log(link_url)}' referred to in "
                            f"'{_sanitize_log(page_src_path)}': exists at "
                            f"{[_sanitize_log(p) for p in all_paths]}. "
                            f"Using '{_sanitize_log(resolved_path)}'."
                        )

                    # Track successful resolution
                    if is_image:
                        stats["images_resolved"] += 1
                    else:
                        stats["links_resolved"] += 1
                        # Count how many times each file is linked
                        self.link_counts[resolved_path] += 1

                    # Calculate relative path from current page to target; cache
                    # the result since from_path is constant for this page.
                    if resolved_path not in relative_path_cache:
                        relative_path_cache[resolved_path] = self._get_relative_path(
                            page_src_path, resolved_path
                        )
                    relative_path = relative_path_cache[resolved_path]
                    # Reconstruct with or without the ! prefix
                    prefix = "!" if is_image else ""
                    return f"{prefix}[{link_text}]({relative_path}{anchor})"
                else:
                    # Track unresolved links/images separately
                    if is_image:
                        stats["images_unresolved"] += 1
                    else:
                        stats["links_unresolved"] += 1

                    if warn_on_missing:
                        file_type = "image" if is_image else "file"
                        logger.warning(
                            f"easylinks: Could not resolve {file_type} link to '{_sanitize_log(link_url)}' on page '{_sanitize_log(page_src_path)}'"
                        )

            return match.group(0)

        markdown = self._link_pattern.sub(replace_link, markdown)

        # Restore code fences and HTML comments
        markdown = self._restore_protected_blocks(markdown, protected_blocks)

        return markdown

    def _extract_protected_blocks(self, markdown: str) -> Tuple[str, dict]:
        """Extract code fences and HTML comments, replacing them with placeholders.

        Note: Only explicit fenced code blocks (``` or ~~~) are protected.
        Indented content (like in MkDocs admonitions) is NOT protected and will
        be processed normally. This is intentional to support MkDocs features.
        """
        protected_blocks = {}
        counter = 0
        prefix = uuid4().hex

        def make_placeholder(match):
            nonlocal counter
            placeholder = f"EASYLINKS_{prefix}_{counter}"
            protected_blocks[placeholder] = match.group(0)
            counter += 1
            return placeholder

        # Match fenced code blocks (both ``` and ~~~)
        # Indented code blocks are NOT protected to support MkDocs admonitions
        if self.config["protect_code_fences"]:
            markdown = self._code_fence_pattern.sub(make_placeholder, markdown)

        # Extract HTML comments
        if self.config["protect_html_comments"]:
            markdown = self._html_comment_pattern.sub(make_placeholder, markdown)

        return markdown, protected_blocks

    def _restore_protected_blocks(self, markdown: str, protected_blocks: dict) -> str:
        """Restore protected blocks from placeholders."""
        if not protected_blocks:
            return markdown
        pattern = re.compile('|'.join(re.escape(k) for k in protected_blocks))
        return pattern.sub(lambda m: protected_blocks[m.group(0)], markdown)

    def _resolve_filename(self, filename: str) -> Optional[str]:
        """Resolve a filename to its full path within the docs."""
        # Check if file exists in our mapping
        if filename in self.ambiguous_files:
            # Return the first occurrence for ambiguous files
            return self.ambiguous_files[filename][0]

        return self.file_map.get(filename)

    def _get_relative_path(self, from_path: str, to_path: str) -> str:
        """Calculate relative path from one file to another."""
        from_dir = os.path.dirname(from_path)
        rel = os.path.relpath(to_path, from_dir) if from_dir else to_path
        return rel.replace("\\", "/")

    def on_post_build(self, *, config: MkDocsConfig) -> None:
        """Display statistics after the build completes."""
        if not self.config["show_stats"]:
            return

        logger.info("=" * 60)
        logger.info("EasyLinks Plugin Statistics")
        logger.info("=" * 60)

        # File statistics
        logger.info(f"Files scanned: {self.stats['total_files_scanned']}")
        logger.info(f"Files indexed: {self.stats['files_indexed']}")
        logger.info(f"Files ambiguous: {self.stats['files_ambiguous']}")
        logger.info(f"Files ignored: {self.stats['files_ignored']}")

        # Link statistics
        logger.info(f"\nLinks processed: {self.stats['links_processed']}")
        logger.info(f"Links resolved: {self.stats['links_resolved']}")
        logger.info(f"Links unresolved: {self.stats['links_unresolved']}")

        # Image statistics
        logger.info(f"\nImages processed: {self.stats['images_processed']}")
        logger.info(f"Images resolved: {self.stats['images_resolved']}")
        logger.info(f"Images unresolved: {self.stats['images_unresolved']}")

        # Most linked files
        if self.link_counts:
            logger.info(f"\nMost frequently linked files (top 10):")
            sorted_links = sorted(self.link_counts.items(), key=lambda x: x[1], reverse=True)
            for path, count in sorted_links[:10]:
                logger.info(f"  {count:3d}x  {path}")

        # Orphaned files (files that are indexed but never linked)
        orphaned = set(self.file_map.values()) - set(self.link_counts.keys())
        if orphaned:
            logger.info(f"\nOrphaned files (indexed but never linked): {len(orphaned)}")
            # Show first 10
            for path in sorted(orphaned)[:10]:
                logger.info(f"  - {path}")
            if len(orphaned) > 10:
                logger.info(f"  ... and {len(orphaned) - 10} more")

        logger.info("=" * 60)
