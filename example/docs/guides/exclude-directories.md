# Excluding Directories

The `exclude_dirs` option allows you to exclude entire directories from being indexed, making it more efficient than listing individual files.

## Basic Usage

```yaml
plugins:
  - easylinks:
      exclude_dirs:
        - drafts/
        - templates/
        - .archive/
```

## How It Works

When you exclude a directory:

- All files in the directory are excluded
- All files in subdirectories are also excluded
- More efficient than listing files individually
- Files in excluded directories **cannot** be linked using simple filenames

## Example Scenario

```
docs/
  ├── index.md
  ├── guides/
  │   ├── getting-started.md
  │   └── advanced.md
  ├── drafts/              # Excluded directory
  │   ├── article.md
  │   └── notes/
  │       └── ideas.md
  └── templates/           # Excluded directory
      └── page-template.md
```

### Configuration

```yaml
plugins:
  - easylinks:
      exclude_dirs:
        - drafts/
        - templates/
```

### What Gets Indexed

- `index.md`
- `guides/getting-started.md`
- `guides/advanced.md`

### What Gets Excluded

- `drafts/article.md`
- `drafts/notes/ideas.md` (subdirectories too!)
- `templates/page-template.md`

## Path Formats

The plugin is flexible with path formats:

```yaml
exclude_dirs:
  - drafts/         # With trailing slash
  - templates       # Without trailing slash
  - docs/internal/  # Nested path
  - .archive        # Hidden directory
```

All formats work correctly!

## Common Use Cases

### Draft Workflow

Keep all drafts in a dedicated directory:

```yaml
exclude_dirs:
  - drafts/
  - wip/            # work-in-progress
```

### Templates

Exclude template directories:

```yaml
exclude_dirs:
  - templates/
  - _templates/
  - docs/templates/
```

### Internal Documentation

Exclude internal-only docs from public builds:

```yaml
exclude_dirs:
  - docs/internal/
  - docs/private/
  - .internal/
```

### Archive Content

Keep old content around without indexing it:

```yaml
exclude_dirs:
  - .archive/
  - old/
  - deprecated/
```

### Multi-version Docs

When managing multiple versions:

```yaml
exclude_dirs:
  - versions/v1/
  - versions/v2/
  # Only index current version
```

## Combine with ignore_files

Use both for maximum control:

```yaml
plugins:
  - easylinks:
      exclude_dirs:
        - drafts/        # Exclude entire directory
        - templates/
      ignore_files:
        - "*.tmp"        # Also ignore temp files anywhere
        - "scratch.md"   # And specific files
```

### When to Use Which

**Use `exclude_dirs` when:**
- You have an entire directory of content to exclude
- All files in a folder serve the same purpose (drafts, templates, etc.)
- You want better performance (more efficient than listing files)

**Use `ignore_files` when:**
- You need to exclude specific files scattered across directories
- You want to use glob patterns for filenames
- The exclusion is based on naming convention, not location

## Nested Paths

You can exclude nested directories:

```yaml
exclude_dirs:
  - docs/internal/drafts/
  - docs/guides/wip/
```

## Performance Benefits

Excluding directories is more efficient than individual file patterns:

```yaml
# Less efficient
ignore_files:
  - "drafts/*.md"           # Requires checking every file

# More efficient
exclude_dirs:
  - drafts/                 # Skips entire directory
```

## Verification

Enable statistics to see what's excluded:

```yaml
plugins:
  - easylinks:
      exclude_dirs:
        - drafts/
        - templates/
      show_stats: true      # Shows "files ignored" count
```

Output:
```
INFO - Files scanned: 150
INFO - Files indexed: 140
INFO - Files ignored: 10    # From excluded directories
```

## Example: Publishing Workflow

```yaml
# Development (index everything)
plugins:
  - easylinks:
      exclude_dirs: []

# Production (exclude drafts and internal)
plugins:
  - easylinks:
      exclude_dirs:
        - drafts/
        - internal/
        - .archive/
```

Tip: Use different config files (`mkdocs.yml` vs `mkdocs-prod.yml`) for different environments.

## See Also

- [Ignoring Files](ignore-files-example.md) - File-level exclusions with glob patterns
- [Configuration Reference](configuration.md) - All configuration options
- [Statistics](statistics.md) - See what's being excluded
