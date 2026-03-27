# API Reference

This page documents the plugin's API.

## Plugin Configuration

The EasyLinks plugin accepts the following configuration options:

### `warn_on_missing`

**Type:** `bool`
**Default:** `true`

Whether to warn when a linked file cannot be found.

### `warn_on_ambiguous`

**Type:** `bool`
**Default:** `true`

Whether to warn when multiple files share the same filename.

### `ignore_files`

**Type:** `list`
**Default:** `[]`

List of filenames or glob patterns to exclude from link resolution. Files matching these patterns will not be indexed and cannot be referenced using simple filenames.

Supports glob patterns like `*.tmp`, `draft-*`, etc.

### `exclude_dirs`

**Type:** `list`
**Default:** `[]`

List of directories to completely exclude from indexing. All files within these directories (and subdirectories) will be ignored.

### `show_stats`

**Type:** `bool`
**Default:** `false`

When enabled, displays detailed statistics about links and files after the build completes, including most frequently linked files and orphaned files.

For configuration examples, see the [configuration page](configuration.md).

## How Links Are Resolved

The plugin resolves links in this order:

1. Check if the filename exists in the file map
2. If ambiguous, use the first occurrence
3. Calculate the relative path from the current page
4. Replace the link with the full relative path

## Related Pages

- [Configuration details](configuration.md)
- [Getting started guide](getting-started.md)
- [Home](index.md)
