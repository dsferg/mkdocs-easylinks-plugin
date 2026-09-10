"""MkDocs plugin for easy cross-references using only filenames."""

import os
import re
import logging
import fnmatch
from uuid import uuid4
from typing import DefaultDict, Dict, List, Optional, Tuple
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


def _display_path(path: str) -> str:
    """Format a source path for log output.

    MkDocs supplies ``src_path`` with the platform's separator, so the same
    build logs ``guides/setup.md`` on Linux and ``guides\\setup.md`` on Windows.
    Reporting one form everywhere keeps the statistics output comparable.
    Filenames are attacker-controlled, so they are sanitized as anywhere else.
    """
    return _sanitize_log(path.replace("\\", "/"))


class EasyLinksConfig(Config):
    warn_on_missing = config_options.Type(bool, default=True)
    warn_on_ambiguous = config_options.Type(bool, default=True)
    ignore_files = config_options.Type(list, default=[])
    exclude_dirs = config_options.Type(list, default=[])
    show_stats = config_options.Type(bool, default=False)
    protect_code_fences = config_options.Type(bool, default=True)
    protect_html_comments = config_options.Type(bool, default=True)
    protect_inline_code = config_options.Type(bool, default=True)


class EasyLinksPlugin(BasePlugin[EasyLinksConfig]):
    """Plugin to resolve markdown links by filename only."""

    # Link text may be empty (an image with no alt text is the recommended form
    # for decorative images) and may contain one level of bracket nesting, so
    # that a linked badge or thumbnail — [![alt](icon.png)](target.md) — is read
    # as one link rather than cut short at the inner image's closing bracket.
    # The two text alternatives cannot match the same first character, so the
    # repetition cannot backtrack exponentially.
    _link_pattern = re.compile(r'(!)?\[((?:[^\[\]]|\[[^\]]*\])*)\]\(([^)]*)\)')

    # Protected blocks are located by finding *openers* and then scanning for
    # each opener's own closer, rather than by one regex matching whole blocks.
    # A single expression cannot state "a closing fence must be at least as long
    # as the fence that opened it", which is what makes ````-fences containing
    # ```-fences parse correctly.
    #
    # Openers for every construct are found in one left-to-right pass, so
    # whichever opens first owns its entire region: a fence inside a comment, or
    # a comment inside a fence, belongs wholly to the outer block. Scanning for
    # them separately would embed the inner block's placeholder in the outer
    # block's stored text, and since the restore pass does not rescan its own
    # replacements, that placeholder would reach the page verbatim.
    #
    # Fence openers are matched at any indentation. CommonMark only allows three
    # spaces at the top level, but a fence nested in a list item is indented to
    # its content column, and failing to protect one silently rewrites links in
    # a code sample. Over-protecting merely leaves a link unresolved, which is
    # visible; under-protecting corrupts code, which is not.
    #
    # The fence alternative is listed before the code-span one so that a line
    # opening with three or more backticks is read as a fence rather than as an
    # inline span.
    _FENCE_OPENER = r'(?P<fence>^[ \t]*(?:`{3,}|~{3,}))'
    _COMMENT_OPENER = r'(?P<comment><!--)'
    _CODE_SPAN_OPENER = r'(?P<span>(?<!`)`+(?!`))'
    _COMMENT_CLOSER = '-->'
    _BLANK_LINE = re.compile(r'\n[ \t]*\n')
    _opener_patterns: Dict[
        Tuple[bool, bool, bool], Optional["re.Pattern[str]"]
    ] = {}

    @classmethod
    def _opener_pattern(
        cls, fences: bool, comments: bool, inline: bool
    ) -> Optional["re.Pattern[str]"]:
        """Return the opener pattern for a combination of protection flags."""
        key = (fences, comments, inline)
        if key not in cls._opener_patterns:
            alternatives = [
                alternative
                for enabled, alternative in (
                    (fences, cls._FENCE_OPENER),
                    (comments, cls._COMMENT_OPENER),
                    (inline, cls._CODE_SPAN_OPENER),
                )
                if enabled
            ]
            cls._opener_patterns[key] = (
                re.compile('|'.join(alternatives), re.MULTILINE)
                if alternatives
                else None
            )
        return cls._opener_patterns[key]
    # Matches the placeholders written by _extract_protected_blocks. Restoring
    # by pattern rather than by alternating over the placeholder keys avoids a
    # prefix collision: 'EASYLINKS_<hex>_1' is a textual prefix of
    # 'EASYLINKS_<hex>_10', so an alternation would match the shorter key first
    # and splice the wrong block into the page.
    _placeholder_pattern = re.compile(r'EASYLINKS_[0-9a-f]{32}_\d+_')

    def __init__(self) -> None:
        super().__init__()
        self.file_map: Dict[str, str] = {}
        self.ambiguous_files: Dict[str, List[str]] = {}
        self._normalized_exclude_dirs: List[str] = []
        # Statistics tracking
        self.stats: Dict[str, int] = {
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
        # Track how many times each file is referenced
        self.link_counts: DefaultDict[str, int] = defaultdict(int)

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
            raw_destination = match.group(3)
            prefix = "!" if is_image else ""

            # A link's text can itself hold an image or link — a badge or
            # thumbnail wrapped in a link. Resolve those first, so a nested
            # image still resolves even when the outer target is left alone.
            processed_text = (
                self._link_pattern.sub(replace_link, link_text)
                if "](" in link_text
                else link_text
            )
            unchanged = (
                match.group(0)
                if processed_text == link_text
                else f"{prefix}[{processed_text}]({raw_destination})"
            )

            parsed = self._split_destination(raw_destination)
            if parsed is None:
                return unchanged
            leading, destination, trailing, angled = parsed

            # Separate the anchor before inspecting the target, so that a
            # fragment containing a colon does not read as a URL scheme.
            target, separator, fragment = destination.partition("#")
            anchor = separator + fragment

            # Skip anything that is not a bare filename. A colon is the scheme
            # sentinel: bare filenames never contain one, so every schemed URL
            # (http:, https:, javascript:, data:, file:, mailto:, blob:,
            # vbscript:, …) is left untouched rather than resolved. A slash
            # means the author wrote an explicit path — absolute, protocol
            # relative, or relative — and meant it. An empty target is either a
            # fragment-only link or an empty destination.
            if not target or ":" in target or "/" in target or "\\" in target:
                return unchanged

            if is_image:
                stats["images_processed"] += 1
            else:
                stats["links_processed"] += 1

            resolved_path = self._resolve_filename(target)
            if not resolved_path:
                # Track unresolved links/images separately
                if is_image:
                    stats["images_unresolved"] += 1
                else:
                    stats["links_unresolved"] += 1

                if warn_on_missing:
                    file_type = "image" if is_image else "file"
                    logger.warning(
                        f"easylinks: Could not resolve {file_type} link to '{_sanitize_log(target)}' on page '{_sanitize_log(page_src_path)}'"
                    )
                return unchanged

            # Warn if this filename is ambiguous
            if warn_on_ambiguous and target in self.ambiguous_files:
                all_paths = self.ambiguous_files[target]
                logger.warning(
                    f"easylinks: Ambiguous filename '{_sanitize_log(target)}' referred to in "
                    f"'{_sanitize_log(page_src_path)}': exists at "
                    f"{[_sanitize_log(p) for p in all_paths]}. "
                    f"Using '{_sanitize_log(resolved_path)}'."
                )

            # Track successful resolution
            if is_image:
                stats["images_resolved"] += 1
            else:
                stats["links_resolved"] += 1

            # Count every reference, image embeds included, so that an
            # embedded image is not reported as an orphaned file.
            self.link_counts[resolved_path] += 1

            # Calculate relative path from current page to target; cache
            # the result since from_path is constant for this page.
            if resolved_path not in relative_path_cache:
                relative_path_cache[resolved_path] = self._get_relative_path(
                    page_src_path, resolved_path
                )
            relative_path = relative_path_cache[resolved_path]

            # Rebuild, preserving how the author wrote the destination: angle
            # brackets, spacing, and any link title all survive untouched.
            rewritten = f"{relative_path}{anchor}"
            if angled:
                rewritten = f"<{rewritten}>"
            return f"{prefix}[{processed_text}]({leading}{rewritten}{trailing})"

        markdown = self._link_pattern.sub(replace_link, markdown)

        # Restore code fences and HTML comments
        markdown = self._restore_protected_blocks(markdown, protected_blocks)

        return markdown

    def _block_end(self, markdown: str, opener: "re.Match[str]") -> Optional[int]:
        """Return the offset just past the block opened by *opener*.

        Returns None when the opener does not in fact open anything, which the
        caller treats as ordinary text.

        An unterminated fence or comment extends to the end of the document,
        matching how CommonMark treats an unclosed fence; leaving the remainder
        unprotected would process links in what the renderer still shows as
        code. An unterminated backtick run is different: CommonMark leaves it as
        literal text, so it protects nothing.
        """
        kind = opener.lastgroup
        text = opener.group(0)

        if kind == 'fence':
            # A closer uses the same character, is at least as long as the
            # opener, and carries nothing else on its line. Requiring the length
            # to match is what stops a ```-fence from closing a ````-fence.
            fence = text.strip()
            closer = re.compile(
                rf'^[ \t]*{fence[0]}{{{len(fence)},}}[ \t]*$', re.MULTILINE
            ).search(markdown, opener.end())
            return closer.end() if closer else len(markdown)

        if kind == 'comment':
            end = markdown.find(self._COMMENT_CLOSER, opener.end())
            return end + len(self._COMMENT_CLOSER) if end != -1 else len(markdown)

        # A run of three or more backticks alone at the start of a line is a
        # fence delimiter, never a code span opener. When fence protection is
        # enabled the fence alternative claims it first; when it is disabled the
        # user has asked for those lines to be inert, so pairing them here would
        # protect the fence body by the back door.
        line_start = markdown.rfind('\n', 0, opener.start()) + 1
        if len(text) >= 3 and not markdown[line_start:opener.start()].strip():
            return None

        # A code span closes on a backtick run of exactly the same length. The
        # search stops at the next blank line: inline parsing cannot cross a
        # block boundary, and without that limit a single stray backtick would
        # pair with another one paragraphs away and suppress every link between.
        blank_line = self._BLANK_LINE.search(markdown, opener.end())
        limit = blank_line.start() if blank_line else len(markdown)
        closer = re.compile(rf'(?<!`)`{{{len(text)}}}(?!`)').search(
            markdown, opener.end(), limit
        )
        return closer.end() if closer else None

    def _extract_protected_blocks(self, markdown: str) -> Tuple[str, Dict[str, str]]:
        """Extract code fences, HTML comments and code spans as placeholders.

        Openers for every construct are found in one pass and each block is
        closed on its own terms — see ``_opener_pattern``.

        Note: only explicit fenced code blocks (``` or ~~~) are protected.
        Merely indented content, as in MkDocs admonitions, is NOT protected and
        is processed normally. This is intentional to support MkDocs features.
        """
        pattern = self._opener_pattern(
            self.config["protect_code_fences"],
            self.config["protect_html_comments"],
            self.config["protect_inline_code"],
        )
        if pattern is None:
            return markdown, {}

        protected_blocks: Dict[str, str] = {}
        prefix = uuid4().hex
        chunks = []
        pos = 0

        for opener in pattern.finditer(markdown):
            # Openers inside a block already claimed by an earlier opener are
            # part of that block's content, not blocks of their own.
            if opener.start() < pos:
                continue

            end = self._block_end(markdown, opener)
            if end is None:  # opener that closes nothing: ordinary text
                continue

            # The trailing underscore terminates the counter so that no
            # placeholder can be a textual prefix of another.
            placeholder = f"EASYLINKS_{prefix}_{len(protected_blocks)}_"
            protected_blocks[placeholder] = markdown[opener.start():end]

            chunks.append(markdown[pos:opener.start()])
            chunks.append(placeholder)
            pos = end

        if not protected_blocks:
            return markdown, {}

        chunks.append(markdown[pos:])
        return "".join(chunks), protected_blocks

    def _restore_protected_blocks(
        self, markdown: str, protected_blocks: Dict[str, str]
    ) -> str:
        """Restore protected blocks from placeholders.

        Placeholder-shaped text that this page did not produce is left alone
        rather than raising, so authored content cannot be swallowed.
        """
        if not protected_blocks:
            return markdown
        return self._placeholder_pattern.sub(
            lambda m: protected_blocks.get(m.group(0), m.group(0)), markdown
        )

    @staticmethod
    def _split_destination(raw: str) -> Optional[Tuple[str, str, str, bool]]:
        """Split the inside of a link's parentheses into destination and title.

        Markdown allows ``[text](file.md "Title")`` and ``[text](<file name.md>)``,
        and tolerates surrounding whitespace. Returns
        ``(leading, destination, trailing, angled)`` where *leading* and
        *trailing* are re-emitted verbatim so the author's spacing and title
        survive. Returns None when the text cannot be parsed — an unterminated
        angle bracket or an empty destination — leaving the link untouched.
        """
        stripped = raw.lstrip()
        leading = raw[: len(raw) - len(stripped)]

        if stripped.startswith("<"):
            end = stripped.find(">")
            if end == -1:
                return None
            return leading, stripped[1:end], stripped[end + 1:], True

        # A bare destination ends at the first whitespace; anything after it is
        # a title, which is preserved rather than interpreted.
        parts = stripped.split(maxsplit=1)
        if not parts:
            return None
        return leading, parts[0], stripped[len(parts[0]):], False

    def _resolve_filename(self, filename: str) -> Optional[str]:
        """Resolve a filename to its full path within the docs.

        Ambiguous filenames need no special case: ``on_files`` only starts an
        ``ambiguous_files`` entry for a name already in ``file_map``, and never
        rewrites that first entry, so ``file_map`` already holds the first
        occurrence — which is the one an ambiguous name resolves to.
        """
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

        # Most referenced files (links and image embeds alike)
        if self.link_counts:
            logger.info("\nMost frequently referenced files (top 10):")
            sorted_links = sorted(self.link_counts.items(), key=lambda x: x[1], reverse=True)
            for path, count in sorted_links[:10]:
                logger.info(f"  {count:3d}x  {_display_path(path)}")

        # Orphaned files (indexed but never referenced by a bare-filename link
        # or image embed; references written as explicit paths are not counted)
        orphaned = set(self.file_map.values()) - set(self.link_counts.keys())
        if orphaned:
            logger.info(
                f"\nOrphaned files (indexed but never referenced): {len(orphaned)}"
            )
            # Show first 10
            for path in sorted(orphaned)[:10]:
                logger.info(f"  - {_display_path(path)}")
            if len(orphaned) > 10:
                logger.info(f"  ... and {len(orphaned) - 10} more")

        logger.info("=" * 60)
