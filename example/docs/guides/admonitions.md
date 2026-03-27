# Using Links in Admonitions

This guide explains how the EasyLinks plugin handles links in MkDocs admonitions and other indented content.

## Key Principle

**Only explicit code fences are protected. Indented content is processed normally.**

This means:

- Code fences (``` or ~~~): Links are NOT processed
- Indented content (admonitions, lists, etc.): Links ARE processed

## Working with Admonitions

Admonitions in MkDocs use indentation to define their content. The EasyLinks plugin processes links inside admonitions normally.

### Basic Example

```markdown
!!! note
    See the [configuration guide](configuration.md) for details.
```

Result:

!!! note
    See the [configuration guide](configuration.md) for details.

The link to `configuration.md` is processed and resolved to the correct path!

### Different Admonition Types

All admonition types work:

!!! tip "Pro Tip"
    Check out the [examples page](examples.md) for more ideas.

!!! warning "Important"
    Read the [API documentation](api.md) before making changes.

!!! info
    For advanced usage, see [advanced guide](advanced.md).

### Images in Admonitions

Images work too:

!!! note "Architecture Overview"
    ![Sample Diagram](sample.svg)

    The diagram above shows our architecture.

## Nested Indentation

Links work at any indentation level:

!!! note "Multi-level Content"
    First level content with a [link](getting-started.md).

    - Bullet point with [another link](api.md)
        - Nested bullet with [more links](configuration.md)

    Back to first level with [final link](examples.md).

All four links above are processed correctly!

## Code Examples in Admonitions

When you want to show code examples inside admonitions, use code fences:

!!! example "Example Usage"
    Here's how to create a link:

    ```markdown
    [See the guide](configuration.md)
    ```

    The link in the code fence above is NOT processed (as expected).
    But this [actual link](configuration.md) outside the fence IS processed.

## Comparison: Fenced vs Indented

Here's a side-by-side comparison:

### Fenced Code (NOT Processed)

```markdown
[This link](guide.md) stays as-is
![This image](diagram.png) stays as-is
```

The links above in the code fence are NOT processed.

### Indented Content (Processed)

!!! note
    [This link](guide.md) is converted to the full path
    ![This image](sample.svg) is also converted

The links in the admonition above ARE processed.

## Why This Design?

This design choice was intentional:

1. **MkDocs admonitions rely on indentation**: Processing indented content ensures the plugin works with standard MkDocs features

2. **Code examples use explicit fences**: When you want to show example code, you use ``` fences, which are protected

3. **Best of both worlds**: Real links work everywhere, including admonitions, while example code remains unchanged

## Lists and Quotes

Other indented structures also have their links processed:

### Lists

- Top level [link](api.md)
    - Nested [link](guide.md)
        - Deeply nested [link](configuration.md)

### Block Quotes

> This is a quote with a [link](getting-started.md).
>
> > Nested quote with [another link](examples.md).

All links above are processed!

## Best Practices

1. **For real links**: Use them anywhere, including in admonitions
   ```markdown
   !!! tip
       See [this guide](guide.md)
   ```

2. **For example code**: Always use code fences
   ````markdown
   !!! example
       ```markdown
       [Example link](guide.md)
       ```
   ````

3. **Mixed content**: Combine both freely
   ```markdown
   !!! note
       Click [this link](guide.md).

       Example code:
       ```
       [example](guide.md)
       ```
   ```

## See Also

- [Examples](examples.md) - More examples of link processing
- [Configuration](configuration.md) - Plugin configuration options
- [Getting Started](getting-started.md) - Basic usage
