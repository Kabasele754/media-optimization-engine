# 360 Panorama Pipeline

MOE preserves the uploaded equirectangular panorama as the immutable source of truth. It does not crop panorama originals into normal card/hero aspect ratios.

## Explicit panorama ingestion

When the application knows the upload is 360, prefer explicit configuration:

```text
media_kind=panorama
projection=equirectangular
profile=panorama.multires
```

For Marzipano use:

```text
profile=panorama.marzipano
```

## Multiresolution strategy

A large equirectangular source is converted into progressive levels and tiles. Viewers should display a preview/low level first and request only tiles relevant to the current field of view.

Typical equirectangular pyramid for 8192×4096:

```text
L0 1024×512
L1 2048×1024
L2 4096×2048
L3 8192×4096
```

The Marzipano profile converts the source into six cubemap faces per level and tiles each face.

## Quality rule

All derivatives are generated from the untouched original. Never use an already compressed derivative as the input for another derivative generation pass.
