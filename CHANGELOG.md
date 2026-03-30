# Changelog

All notable changes to this project will be documented in this file.

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
