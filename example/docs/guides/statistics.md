# Link Statistics

The EasyLinks plugin can display detailed statistics about your documentation's link structure.

## Enabling Statistics

Add `show_stats: true` to your configuration:

```yaml
plugins:
  - easylinks:
      show_stats: true
```

## What You'll See

After your build completes, you'll see a statistics report in your build log:

```
INFO - ============================================================
INFO - EasyLinks Plugin Statistics
INFO - ============================================================
INFO - Files scanned: 150
INFO - Files indexed: 145
INFO - Files ignored: 5
INFO -
INFO - Links processed: 324
INFO - Links resolved: 320
INFO - Links unresolved: 4
INFO -
INFO - Images processed: 45
INFO - Images resolved: 45
INFO -
INFO - Most frequently linked files (top 10):
INFO -    15x  docs/reference/api.md
INFO -    12x  docs/guides/getting-started.md
INFO -     8x  docs/index.md
INFO -     7x  docs/reference/configuration.md
INFO -     6x  docs/guides/advanced.md
INFO -     5x  docs/reference/images-guide.md
INFO -     4x  docs/guides/examples.md
INFO -     3x  docs/guides/ignore-files-example.md
INFO -     2x  docs/reference/api.md
INFO -     1x  docs/guides/statistics.md
INFO -
INFO - Orphaned files (indexed but never linked): 3
INFO -   - docs/old-guide.md
INFO -   - docs/unused-page.md
INFO -   - images/unused-diagram.png
INFO - ============================================================
```

## Understanding the Statistics

### File Statistics

- **Files scanned**: Total number of files found in your project
- **Files indexed**: Files that can be linked using simple filenames
- **Files ignored**: Files excluded (dotfiles, `ignore_files`, `exclude_dirs`)

### Link Statistics

- **Links processed**: Total number of simple filename links found (e.g., `[text](file.md)`)
- **Links resolved**: How many were successfully converted to full paths
- **Links unresolved**: Links that couldn't be resolved (file not found)

### Image Statistics

- **Images processed**: Simple filename image references (e.g., `![alt](image.png)`)
- **Images resolved**: Successfully converted to full paths

### Most Frequently Linked Files

This shows which files are referenced most often across your documentation. Useful for:

- Identifying your most important documentation pages
- Finding hub pages that connect your docs together
- Understanding your documentation's structure

### Orphaned Files

Files that are indexed but never linked to. These might be:

- **Pages you forgot to link**: Add navigation links to make them discoverable
- **Old content**: Consider archiving or removing
- **Images not yet used**: Clean up unused assets

## Use Cases

### Documentation Health Check

Run your build with statistics enabled periodically to:

1. **Find broken links**: Check the "unresolved" count
2. **Identify orphaned content**: Review files that are never linked
3. **Understand usage patterns**: See which pages are central to your docs

### Refactoring Validation

When reorganizing documentation:

```yaml
plugins:
  - easylinks:
      show_stats: true
      warn_on_missing: true
```

The statistics help verify that all your links were properly updated.

### Content Audit

Use statistics to find:

- Unused images taking up space
- Documentation pages that need better integration
- Key pages that should be highlighted in navigation

## Example Workflow

```bash
# Build with statistics
mkdocs build

# Review the output
# - Are there unresolved links? Fix them!
# - Are there orphaned files? Link to them or remove them
# - Which pages are most linked? Make sure they're high quality!

# Disable stats for regular development
# (Edit mkdocs.yml: show_stats: false)
mkdocs serve
```

## Performance Impact

Statistics collection has minimal performance impact:

- No extra file scans (tracking is done during normal processing)
- Report generation only happens at the end of the build
- Can be disabled for faster development builds

## See Also

- [Configuration Reference](configuration.md) - All configuration options
- [Ignoring Files](ignore-files-example.md) - How ignored files affect statistics
- [Getting Started](getting-started.md) - Basic plugin usage
