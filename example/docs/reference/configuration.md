# Configuration

Complete configuration reference for the EasyLinks plugin.

## Basic Configuration

```yaml
plugins:
  - easylinks
```

## Options

### warn_on_missing

Controls whether warnings are shown when a file cannot be found.

```yaml
plugins:
  - easylinks:
      warn_on_missing: true
```

### warn_on_ambiguous

Controls whether warnings are shown when multiple files have the same name.

```yaml
plugins:
  - easylinks:
      warn_on_ambiguous: true
```

### ignore_files

Specify a list of filenames or patterns to exclude from link resolution. Supports glob patterns for flexible matching.

**Type:** List of strings (supports glob patterns)
**Default:** `[]`

```yaml
plugins:
  - easylinks:
      ignore_files:
        - draft.md           # Exact filename match
        - template.md        # Exact filename match
        - "draft-*.md"       # Glob: all files starting with "draft-"
        - "*.tmp"            # Glob: all .tmp files
        - "test_*"           # Glob: all files starting with "test_"
```

**Glob pattern examples:**
- `*.tmp` - Matches any file ending with `.tmp`
- `draft-*` - Matches any file starting with `draft-`
- `*-backup.md` - Matches files ending with `-backup.md`
- `temp_*.png` - Matches image files starting with `temp_`

**Use cases:**
- Draft documents that aren't ready to be linked
- Template files
- Temporary or scratch files
- Test files or data

**Note:** Files starting with `.` (dotfiles) are always ignored automatically, so you don't need to add them to this list.

### exclude_dirs

Exclude entire directories from being indexed. All files within these directories (and their subdirectories) will be ignored.

**Type:** List of strings
**Default:** `[]`

```yaml
plugins:
  - easylinks:
      exclude_dirs:
        - drafts/
        - templates/
        - .archive/
        - docs/internal/
```

**Features:**
- Works with or without trailing slash (`drafts/` or `drafts`)
- Excludes all files in subdirectories too
- More efficient than listing individual files

**Use cases:**
- Draft folders
- Template directories
- Internal documentation
- Archive folders

### show_stats

Display detailed link statistics after the build completes.

**Type:** Boolean
**Default:** `false`

```yaml
plugins:
  - easylinks:
      show_stats: true
```

**When enabled, shows:**
- Total files scanned and indexed
- Number of files ignored/excluded
- Links and images processed and resolved
- Most frequently linked files (top 10)
- Orphaned files (indexed but never linked)

**Example output:**
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
INFO - ...
```

## Complete Example

```yaml
site_name: My Documentation
theme:
  name: material

plugins:
  - search
  - easylinks:
      warn_on_missing: true
      warn_on_ambiguous: true
      ignore_files:
        - draft.md
        - template.md
        - "draft-*.md"      # Pattern matching
        - "*.tmp"
      exclude_dirs:
        - drafts/
        - templates/
        - .archive/
      show_stats: true      # Display statistics after build
```

## Protected Content Behavior

The plugin processes links differently depending on where they appear:

### Processed (Links are converted)

- Regular markdown content
- **Indented content** (MkDocs admonitions, lists, block quotes)
- Nested structures at any indentation level

### Not Processed (Links are preserved as-is)

- Fenced code blocks (``` or ~~~)
- HTML comments (`<!-- -->`)

**Important:** Only explicit code fences are protected. Indented content, such as in MkDocs admonitions, IS processed normally. This ensures the plugin works seamlessly with MkDocs features that rely on indentation.

Example:

```markdown
!!! note
    This [link](guide.md) WILL be processed.

```python
# This [link](guide.md) will NOT be processed.
```
```

For detailed examples, see [Admonitions Guide](admonitions.md).

## See Also

- [API Reference](api.md) for technical details
- [Advanced usage guide](advanced.md)
- [Getting started](getting-started.md)
