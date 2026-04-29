# Changelog

All notable changes to this project will be documented in this file.

## [0.2.3] - 2026-04-29

### Security
- Expanded log sanitizer to escape ANSI escape sequences, NUL bytes, vertical tab, form feed, and Unicode line separators (U+2028/U+2029) in addition to `\n`, `\r`, and `\t`
- Path safety check now rejects absolute and drive-relative paths (e.g. `/etc/passwd`, `C:\…`, `\\server\share\…`) in addition to `..` traversal

### Fixed
- `mkdocs_easylinks.__version__` is now read from installed package metadata, eliminating drift between `pyproject.toml` and the module attribute

## [0.2.2] - 2026-04-13

### Security
- Fixed log injection via user-controlled filenames
- Fixed path traversal via malformed file paths
- Fixed URL scheme bypass allowing dangerous link types
- Fixed misconfigured `exclude_dirs` empty-string entry

### Performance
- `_restore_protected_blocks` now uses a single compiled regex substitution instead of N sequential `str.replace` calls, making restoration O(n) in document length
- `_is_safe_path` short-circuits immediately for paths containing no `..` component (the common case), avoiding the `os.path.normpath` call entirely
- Config flags and the stats dict are captured as locals before the per-link closure is entered, removing repeated attribute and dict lookups on every link match
- Relative path results are cached per page so repeated links to the same target file call `_get_relative_path` only once

## [0.2.1] - 2026-04-02

### Fixed
- Replaced deprecated `license = {text = "MIT"}` with SPDX expression `license = "MIT"`
- Removed deprecated `License :: OSI Approved :: MIT License` classifier
- Bumped setuptools build requirement to `>=77.0.0` to support SPDX license format

## [0.2.0] - 2026-04-02

### Removed
- Dropped support for Python 3.8 and 3.9 (both EOL)

## [0.1.4] - 2026-03-30

### Changed
- Pre-compiled code fence and HTML comment regex patterns as class-level constants for consistency and minor performance improvement
- Excluded directories are now normalized once per build rather than on every file check
- `_should_ignore_file` simplified to a single `any()` expression
- `files_ambiguous` stat now tracked separately from `files_indexed`, making both counts accurate and meaningful
- Development status classifier updated from Alpha to Beta
- README stats section updated to reflect `files_ambiguous` and `files_ignored` counters

### Fixed
- `files_indexed` no longer counts ambiguous duplicate filenames — those are now counted in the new `files_ambiguous` stat

### Dev
- Added mypy type checking to CI (`typecheck` job in GitHub Actions)

## [0.1.3] - 2026-03-30

### Added
- `protect_code_fences` config option (default: `true`) — set to `false` to process links inside fenced code blocks rather than leaving them unchanged
- `protect_html_comments` config option (default: `true`) — set to `false` to process links inside HTML comments rather than leaving them unchanged

## [0.1.2] - 2026-03-26

### Fixed
- Protected block placeholders now use a UUID-based prefix, preventing a collision where a literal `___PROTECTED_BLOCK_N___` string in markdown would be incorrectly replaced with code fence content during processing

## [0.1.1] - 2026-03-26

### Fixed
- Relative path calculation replaced with `os.path.relpath` — the previous custom algorithm could miscalculate paths for certain directory structures, producing silently broken links
- `exclude_dirs` no longer incorrectly excludes directories whose names contain the excluded name as a substring (e.g. excluding `"api"` no longer excluded `"apidocs/"`)
- Unresolved images now increment `images_unresolved` instead of `links_unresolved`, preventing misleading statistics
- Duplicate filenames are now correctly counted in `files_indexed` statistics
- `stats` and `link_counts` now reset on each build, preventing accumulation across rebuilds during `mkdocs serve` live reload
- Restored `files` parameter to `on_page_markdown` signature for compatibility with MkDocs versions that pass all keyword arguments directly

### Added
- Per-page warning when a link resolves to an ambiguous filename, including the referring page path and all candidate locations
- All plugin warnings now prefixed with `easylinks:` for easier identification in build output
- `images_unresolved` statistic counter

### Changed
- Migrated plugin configuration from deprecated `config_scheme` tuple to typed `PluginConfig` class (MkDocs 1.5+ style)
- Regex pattern for link matching compiled once at class level rather than per page
- Removed unused `page` parameter from `_resolve_filename`
- Merged duplicate closures in `_extract_protected_blocks` into a single function

## [0.1.0] - Initial release

- Simple filename-based link and image resolution
- Automatic relative path calculation
- Glob pattern support for `ignore_files`
- Directory exclusion via `exclude_dirs`
- Ambiguity detection and warnings
- Code fence and HTML comment protection
- Post-build link statistics via `show_stats`
