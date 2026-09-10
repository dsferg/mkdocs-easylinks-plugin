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
- **Smart protection**: Code fences and HTML comments are preserved unchanged by default (configurable)

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
      protect_inline_code: true  # Leave links inside `code spans` unchanged (default: true)
```

#### Available Options

- **`warn_on_missing`** (bool, default: `true`): Show warnings when a linked file cannot be found
- **`warn_on_ambiguous`** (bool, default: `true`): Show warnings when multiple files share the same name
- **`ignore_files`** (list, default: `[]`): List of filenames/patterns to exclude from link resolution (supports glob patterns)
- **`exclude_dirs`** (list, default: `[]`): List of directories to exclude completely
- **`show_stats`** (bool, default: `false`): Display link statistics after the build completes
- **`protect_code_fences`** (bool, default: `true`): When enabled, links inside fenced code blocks (` ``` ` or `~~~`) are left unchanged. Set to `false` to process them like normal content.
- **`protect_html_comments`** (bool, default: `true`): When enabled, links inside HTML comments (`<!-- -->`) are left unchanged. Set to `false` to process them like normal content.
- **`protect_inline_code`** (bool, default: `true`): When enabled, links inside inline code spans (`` `like this` ``) are left unchanged. Set to `false` to process them like normal content.

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
- Files scanned, indexed, ambiguous, and ignored
- Links processed, resolved, and unresolved
- Images processed, resolved, and unresolved
- Most frequently referenced files
- Orphaned files (indexed but never referenced)

> **Note:** Reference counts include both links and image embeds, but only those written as bare filenames — the form this plugin resolves. A file reached solely through an explicit relative path (`../images/logo.png`) is invisible to the plugin and will be listed as orphaned.
>
> The orphan list also covers every file MkDocs supplies, which includes your theme's own CSS, JavaScript and icons. Those are never referenced from your Markdown, so they will always be listed. Add them to `exclude_dirs` if the noise bothers you.

Statistics are written at `INFO` level, which MkDocs shows by default; `mkdocs build --quiet` suppresses them.

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
- `![](image.png)` - Images with no alt text
- `[text](file.md "Title")` - Destinations with a link title, which is preserved
- `[text](<file name.md>)` - Angle-bracketed destinations, which keep their brackets
- `[![alt](icon.png)](file.md)` - A linked image; both the image and the link resolve

**Not processed** (left as-is):
- `[text](https://example.com)` - External URLs
- `![alt](https://example.com/image.png)` - External images
- `[text](/absolute/path.md)` - Absolute paths
- `[text](../relative/path.md)` - Explicit relative paths with directories
- `[text](#anchor)` - Fragment-only links
- `[text](javascript:...)`, `[text](data:...)`, `[text](mailto:...)`, etc. — any destination containing a colon (treated as a scheme). The destination is checked with any `#fragment` removed, so a colon inside an anchor is not mistaken for a scheme.
- `[text][ref]` with a `[ref]: file.md` definition — reference-style links are not resolved
- `[text](file.md?query=1)` - Destinations carrying a query string
- Links/images inside code fences (` ``` ` or `~~~`) — unless `protect_code_fences: false`
- Links/images inside HTML comments (`<!-- -->`) — unless `protect_html_comments: false`
- Links/images inside inline code spans (`` `like this` ``) — unless `protect_inline_code: false`

> **Security note:** easylinks does not sanitize link targets. Schemed URLs (including `javascript:` and `data:`) are passed through unchanged for the Markdown renderer to handle. XSS protection in your rendered site is the responsibility of MkDocs and the Markdown extensions you have configured — not this plugin.

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

**Inline code spans:**
````markdown
Write `[link](example.md)` to reference a file.
````

A code span is closed by a backtick run of the same length, and never spans a
blank line — so a stray backtick in your prose is harmless.

This ensures that example code and commented-out content remain unchanged. All three behaviours are configurable via `protect_code_fences`, `protect_html_comments` and `protect_inline_code`.

Fences are matched the way a Markdown renderer matches them:

- A fence is closed only by the same character, repeated at least as many times, alone on its line. So a ` ```` ` block can contain ` ``` ` blocks — useful for documenting fenced syntax itself.
- A fence with no closing fence extends to the end of the document.
- Fences are recognised at any indentation, so a code block nested inside a list item or an admonition is protected.

**Important: Indented Content**

Only explicit code fences (``` or ~~~) are protected. Indented *prose*, such as the body of a MkDocs admonition, **is processed normally**:

````markdown
!!! note
    This [link](guide.md) WILL be processed.
    The plugin works inside admonitions!

    ```
    But this [link](guide.md) will NOT be — it is a fence.
    ```
````

This design choice ensures the plugin works seamlessly with MkDocs features like admonitions, which rely heavily on indentation, while still leaving genuine code samples alone.

## How It Works

1. During the build, the plugin scans all files (documentation, images, assets, etc.)
2. It creates a mapping of filenames to their full paths
3. When processing each page, it finds markdown links and images with simple filenames
4. It replaces them with the correct relative path from the current page to the target

**Files that are excluded from mapping:**
- Files starting with `.` (dotfiles) - always ignored
- Files listed in `ignore_files` configuration - useful for drafts and templates
- Files in directories listed in `exclude_dirs`

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
