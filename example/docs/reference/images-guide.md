# Image Reference Guide

This guide shows how to use images with the EasyLinks plugin.

## Basic Image Usage

Just reference images by their filename, regardless of where they're stored:

```markdown
![Sample](sample.svg)
```

Result:

![Sample](sample.svg)

## How It Works

The plugin automatically:

1. Scans all image files in your project (PNG, JPG, SVG, GIF, etc.)
2. Creates a filename-to-path mapping
3. Resolves simple filenames to their full relative paths

## Supported Image Formats

All standard image formats work:

- PNG: `![Logo](logo.png)`
- JPG/JPEG: `![Photo](photo.jpg)`
- SVG: `![Icon](icon.svg)`
- GIF: `![Animation](animation.gif)`
- WebP: `![Modern](modern.webp)`

## Images in Different Locations

No matter where the image is stored in your project, you can reference it by filename:

```markdown
![Sample](sample.svg)
```

This works whether `sample.svg` is in:
- `images/sample.svg`
- `assets/sample.svg`
- `static/images/sample.svg`
- Or any other location!

## External Images

External images (with URLs) work normally and are not modified:

```markdown
![External](https://example.com/image.png)
```

## Best Practices

1. **Unique filenames**: Give your images unique names to avoid ambiguity
2. **Descriptive alt text**: Always provide meaningful alt text for accessibility
3. **Organize logically**: While you can reference images by filename alone, organizing them in folders (like `images/`) keeps your project tidy

## Back to Documentation

- [Getting Started](getting-started.md)
- [API Reference](api.md)
- [Examples](examples.md)
