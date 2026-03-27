# Examples

This page demonstrates how the EasyLinks plugin handles different types of content.

## Regular Links

These links are processed normally:

- [Getting Started Guide](getting-started.md)
- [API Reference](api.md)
- [Configuration](configuration.md)

## Images

Images work just as easily! Instead of writing the full path, just use the filename:

![Sample Image](sample.svg)

The above image is referenced as `![Sample Image](sample.svg)` but it's actually located at `images/sample.svg`. The plugin automatically resolves the path!

## Links in Code Examples

When you show code examples, the links inside them are preserved:

```markdown
Here's how you might write a link in your docs:
[Check the API](api.md)
```

The link `[Check the API](api.md)` in the code fence above is **not processed** - it stays exactly as written so your examples are accurate.

### Python Code Example

```python
# Example of documentation in code
def get_docs():
    """
    Read the [documentation](getting-started.md) for details.
    """
    return "https://example.com"
```

The link in the docstring above is not processed either!

### Bash Example

```bash
# Download the guide
wget https://example.com/getting-started.md
# See also: [advanced guide](advanced.md)
```

## HTML Comments

Sometimes you want to leave notes for yourself:

<!-- TODO: Add a link to [configuration.md] when it's ready -->

The link in the comment above won't be processed, so you can use it as a reminder without breaking your build.

<!--
Commented out section:
See [advanced.md](advanced.md) for more details
[api.md](api.md)
-->

## Mixed Content

You can mix processed and unprocessed content:

1. First, read the [getting started guide](getting-started.md) ← This link works!

2. Then try this example:
   ```markdown
   [Link example](getting-started.md)
   ```
   ← That link in the code is not processed

3. Finally, check the [API docs](api.md) ← This link works too!

## MkDocs Admonitions

Links inside MkDocs admonitions work perfectly because the plugin processes indented content:

!!! note "Quick Reference"
    See the [getting started guide](getting-started.md) for setup instructions.

!!! tip
    Use the [configuration reference](configuration.md) to customize the plugin.

!!! warning
    Check the [API docs](api.md) before making breaking changes.

The plugin processes links in indented content (like admonitions) while still protecting links in code fences. This is intentional to support MkDocs features.

## Why This Matters

This intelligent processing means:

- Your actual documentation links work perfectly
- Your code examples stay accurate
- Your TODO comments don't cause warnings
- You can show markdown examples without confusion

Read more about [configuration options](configuration.md).
