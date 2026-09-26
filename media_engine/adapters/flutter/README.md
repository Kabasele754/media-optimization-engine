# Flutter adapter

Media Optimization Engineer can be consumed by Flutter through the same immutable manifest API used by other native clients.

The Python package ships Dart reference models under this directory. They are framework-neutral examples that consuming Flutter applications can copy or wrap in their own networking/cache layer.

## Standard images

\`standard_images.dart\` parses a standard MOE manifest and selects a derivative from:

~~~text
target physical width = rendered logical width × devicePixelRatio
~~~

Recommended policy:

1. fetch the asset manifest once;
2. cache the manifest in memory;
3. measure the actual widget width with \`LayoutBuilder\`;
4. multiply by \`MediaQuery.devicePixelRatioOf(context)\`;
5. select the first WebP derivative at or above that physical width;
6. if none is large enough, use the largest available derivative;
7. cache the selected immutable URL with the application's normal image cache;
8. fall back to the manifest fallback/original URL if needed.

Example:

~~~dart
final targetLogicalWidth = constraints.maxWidth;
final dpr = MediaQuery.devicePixelRatioOf(context);

final variant = manifest.select(
  logicalWidth: targetLogicalWidth,
  devicePixelRatio: dpr,
  preferredFormat: 'webp',
);
~~~

WebP is a conservative default for broad Android/iOS compatibility. Applications may prefer AVIF on platforms where their Flutter image stack reliably supports it.

## Panorama 360

\`models.dart\` parses the generic panorama manifest.

Recommended panorama policy:

- show \`preview\` immediately;
- select a level from viewport width × DPR;
- request only tiles intersecting the current field of view;
- keep adjacent tiles warm for smooth panning;
- use AVIF where supported, otherwise WebP.

## API

A standard image manifest is available from the REST viewset:

~~~text
GET /api/v1/images/<asset-id>/manifest/?profile=<profile>
~~~

When MOE is mounted under another prefix in a Django project, keep the same route relative to that prefix.

The native client should never upload or process an image merely to render it. Processing stays server-side; Flutter only chooses among READY immutable derivatives.
