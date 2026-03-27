# Ignoring Files Example

This guide demonstrates how to use the `ignore_files` configuration option.

## Why Ignore Files?

Sometimes you have files in your docs directory that you don't want to be linkable by simple filenames:

- **Draft documents** - Work in progress that isn't ready for linking
- **Template files** - Skeleton files you copy from
- **Scratch notes** - Temporary documentation
- **Internal files** - Files meant only for reference

## Configuration

In your `mkdocs.yml`:

```yaml
plugins:
  - easylinks:
      ignore_files:
        - draft.md
        - template.md
        - notes.md
        - scratch.png
```

## How It Works

Files in the `ignore_files` list will:

- Still exist in your docs directory
- Still be rendered if they're in your `nav`
- **NOT** be indexed for simple filename linking
- **NOT** be resolvable via `[text](filename.md)`

## Example Scenario

Let's say you have:

```
docs/
  ├── index.md
  ├── guide.md
  ├── draft.md      # In ignore_files list
  └── template.md   # In ignore_files list
```

With this configuration:

```yaml
plugins:
  - easylinks:
      ignore_files:
        - draft.md
        - template.md
```

### What Works

```markdown
# In any page:
[See the guide](guide.md)  # This works!
```

The plugin resolves `guide.md` to its full path.

### What Doesn't Work

```markdown
# In any page:
[Check draft](draft.md)  # This won't be resolved
```

The link stays as `[Check draft](draft.md)` and may be broken. This is intentional - you don't want links to draft content!

## Glob Patterns

The `ignore_files` option supports glob patterns for flexible matching:

```yaml
plugins:
  - easylinks:
      ignore_files:
        - draft.md           # Exact match
        - "draft-*.md"       # Pattern: all files starting with "draft-"
        - "*.tmp"            # Pattern: all .tmp files
        - "*-backup.md"      # Pattern: all files ending with "-backup.md"
        - "test_*"           # Pattern: all files starting with "test_"
```

### Common Patterns

**Drafts:**
```yaml
ignore_files:
  - "draft-*.md"      # draft-article.md, draft-notes.md, etc.
  - "*-draft.md"      # article-draft.md, notes-draft.md, etc.
```

**Temporary files:**
```yaml
ignore_files:
  - "*.tmp"           # Any .tmp file
  - "*.bak"           # Any .bak file
  - "~*"              # Files starting with ~
```

**Test files:**
```yaml
ignore_files:
  - "test_*.md"       # test_example.md, test_data.md, etc.
  - "*_test.md"       # example_test.md, data_test.md, etc.
```

## Combined with Dotfiles

Note that files starting with `.` are **always** ignored automatically. You don't need to add them to `ignore_files`:

```yaml
plugins:
  - easylinks:
      ignore_files:
        - "draft-*.md"
        # No need to add .hidden.md - dotfiles are auto-ignored
```

## Use Cases

### Draft Workflow

Keep all drafts organized with a naming convention:

```yaml
ignore_files:
  - "draft-*.md"      # All files starting with "draft-"
  - "wip-*.md"        # All work-in-progress files
```

### Template Files

Prevent accidentally linking to templates:

```yaml
ignore_files:
  - page-template.md
  - section-template.md
```

### Temporary Files

Ignore scratch files:

```yaml
ignore_files:
  - scratch.md
  - temp.md
  - notes.md
```

## See Also

- [Configuration Reference](configuration.md) - All configuration options
- [API Documentation](api.md) - Technical details
- [Getting Started](getting-started.md) - Basic usage
