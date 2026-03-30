# MkDocs EasyLinks Plugin

An MkDocs plugin that allows you to create cross-references and embed images by specifying only the filename, without needing to know the full path.

## Features

- **Simple linking**: Reference any file in your docs with just its filename
- **Image support**: Embed images using simple filenames like `![alt](image.png)`
- **Automatic resolution**: The plugin finds the file and generates the correct relative path
- **Glob patterns**: Use wildcards to ignore multiple files (e.g., `draft-*.md`, `*.tmp`)
- **Directory exclusion**: Exclude entire directories from being indexed
- **Link statistics**: See which files are most linked and find orphaned content
- **Ambiguity warnings**: Get notified if multiple files share the same name
- **Material for MkDocs compatible**: Works seamlessly with Material theme
- **Smart protection**: Code fences and HTML comments are preserved unchanged

## Installation

```bash
pip install mkdocs-easylinks-plugin
```

## Usage

Add the plugin to your `mkdocs.yml`:

```yaml
plugins:
  - search
  - easylinks
```

### Configuration Options

```yaml
plugins:
  - easylinks:
      warn_on_missing: true      # Warn when a file can't be found (default: true)
      warn_on_ambiguous: true    # Warn when multiple files have the same name (default: true)
      ignore_files: []           # List of filenames/patterns to ignore (default: [])
      exclude_dirs: []           # List of directories to exclude (default: [])
      show_stats: false          # Show link statistics after build (default: false)
      protect_code_fences: true  # Leave links inside fenced code blocks unchanged (default: true)
      protect_html_comments: true  # Leave links inside HTML comments unchanged (default: true)
```

#### Available Options

- **`warn_on_missing`** (bool, default: `true`): Show warnings when a linked file cannot be found
- **`warn_on_ambiguous`** (bool, default: `true`): Show warnings when multiple files share the same name
- **`ignore_files`** (list, default: `[]`): List of filenames/patterns to exclude from link resolution (supports glob patterns)
- **`exclude_dirs`** (list, default: `[]`): List of directories to exclude completely
- **`show_stats`** (bool, default: `false`): Display link statistics after the build completes
- **`protect_code_fences`** (bool, default: `true`): When enabled, links inside fenced code blocks (` ``` ` or `~~~`) are left unchanged. Set to `false` to process them like normal content.
- **`protect_html_comments`** (bool, default: `true`): When enabled, links inside HTML comments (`<!-- -->`) are left unchanged. Set to `false` to process them like normal content.

#### Ignoring Specific Files

Use `ignore_files` to exclude certain files. Supports both exact matches and glob patterns:

```yaml
plugins:
  - easylinks:
      ignore_files:
        - draft.md           # Exact match
        - template.md        # Exact match
        - "draft-*.md"       # Glob pattern - all files starting with "draft-"
        - "*.tmp"            # Glob pattern - all .tmp files
        - "test_*"           # Glob pattern - all files starting with "test_"
```

#### Excluding Directories

Use `exclude_dirs` to exclude entire directories:

```yaml
plugins:
  - easylinks:
      exclude_dirs:
        - drafts/
        - templates/
        - .archive/
```

All files in these directories (and subdirectories) will be excluded from indexing.

> **Note:** Directory paths are matched as prefixes against each file's path within the docs directory. This means `exclude_dirs: ["api"]` excludes `api/page.md` but **not** `docs/api/page.md`. To exclude a nested directory, specify the full path from the docs root: `exclude_dirs: ["docs/api"]`.

#### Link Statistics

Enable `show_stats` to see detailed statistics after your build:

```yaml
plugins:
  - easylinks:
      show_stats: true
```

This will display:
- Files scanned and indexed
- Links processed, resolved, and unresolved
- Images processed, resolved, and unresolved
- Most frequently linked files
- Orphaned files (indexed but never linked)

## Examples

### Documentation Links

Instead of writing:

```markdown
[See the guide](../../advanced/guides/configuration.md)
```

You can now write:

```markdown
[See the guide](configuration.md)
```

The plugin will automatically resolve `configuration.md` to its full path and generate the correct relative link.

### Images

Works with images too! Instead of:

```markdown
![Diagram](../../assets/images/architecture.png)
```

Just write:

```markdown
![Diagram](architecture.png)
```

### With Anchors

Anchors work for document links:

```markdown
[See section](somefile.md#advanced-features)
```

### What Links Are Processed

**Processed** (converted to full paths):
- `[text](filename.md)` - Simple document filenames
- `[text](file.md#anchor)` - Document filenames with anchors
- `![alt](image.png)` - Simple image filenames (png, jpg, svg, gif, etc.)

**Not processed** (left as-is):
- `[text](https://example.com)` - External URLs
- `![alt](https://example.com/image.png)` - External images
- `[text](/absolute/path.md)` - Absolute paths
- `[text](../relative/path.md)` - Explicit relative paths with directories
- `[text](#anchor)` - Fragment-only links
- Links/images inside code fences (` ``` ` or `~~~`)
- Links/images inside HTML comments (`<!-- -->`)

### Protected Content

The plugin intelligently ignores links in:

**Code fences:**
````markdown
```python
# This [link](example.md) won't be processed
```
````

**HTML comments:**
```markdown
<!-- This [link](example.md) won't be processed -->
```

This ensures that example code and commented-out content remain unchanged.

**Important: Indented Content**

Only explicit code fences (``` or ~~~) are protected. Indented content, such as in MkDocs admonitions, **is processed normally**:

```markdown
!!! note
    This [link](guide.md) WILL be processed.
    The plugin works inside admonitions!
```

This design choice ensures the plugin works seamlessly with MkDocs features like admonitions, which rely heavily on indentation.

## How It Works

1. During the build, the plugin scans all files (documentation, images, assets, etc.)
2. It creates a mapping of filenames to their full paths
3. When processing each page, it finds markdown links and images with simple filenames
4. It replaces them with the correct relative path from the current page to the target

**Files that are excluded from mapping:**
- Files starting with `.` (dotfiles) - always ignored
- Files listed in `ignore_files` configuration - useful for drafts and templates

## Using with mkdocs-macros-plugin (Snippets)

If you use [mkdocs-macros-plugin](https://mkdocs-macros-plugin.readthedocs.io/) to include snippet files via `{% include '...' %}`, easylinks works correctly with no extra configuration — as long as the plugin order in `mkdocs.yml` is correct:

```yaml
plugins:
  - macros:
      include_dir: docs/.snippets
  - easylinks        # must come after macros
```

Because macros runs first, snippet content is inlined into the page before easylinks processes it. Links in snippets are resolved relative to the **including page**, not the snippet file itself — which is exactly the right behaviour when a snippet may be included from pages at different directory levels.

**Best practices:**

- Always list `easylinks` after `macros` in your `plugins` configuration.
- Use simple filename links (e.g. `[text](target.md)`) in your snippets rather than relative paths, since relative paths would break when the same snippet is included from different locations.
- If your snippets directory could contain files whose names clash with published docs files, add it to `exclude_dirs` to prevent false ambiguity warnings:

```yaml
plugins:
  - easylinks:
      exclude_dirs: ['.snippets']
```

## Handling Ambiguous Filenames

If you have multiple files with the same name (e.g., `index.md` in different folders), the plugin will:

1. Warn you about the ambiguity
2. Use the first occurrence found
3. Recommend using full paths for those specific files

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/dsferg/mkdocs-easylinks-plugin.git
cd mkdocs-easylinks-plugin

# Install in development mode
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
```

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
