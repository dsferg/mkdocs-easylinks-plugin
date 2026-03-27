# Welcome to EasyLinks Example

This is an example site demonstrating the EasyLinks plugin for MkDocs.

## Easy Cross-References

With the EasyLinks plugin, you can reference other pages using just their filename:

- Check out the [getting started guide](getting-started.md)
- See the [API reference](api.md)
- Read about [configuration](configuration.md#options)

Without this plugin, you would need to write the full paths:

```markdown
- [getting started guide](guides/getting-started.md)
- [API reference](reference/api.md)
- [configuration](reference/configuration.md#options)
```

## How It Works

The plugin automatically:

1. Scans all your documentation files
2. Creates a filename-to-path mapping
3. Resolves simple filename links to their correct relative paths

## Next Steps

- [Get started](getting-started.md) with your first project
- Explore [advanced features](advanced.md)
