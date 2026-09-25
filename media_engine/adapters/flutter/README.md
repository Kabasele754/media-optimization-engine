# Flutter panorama adapter

`models.dart` parses the generic MOE panorama manifest. A Flutter viewer can select the lowest level that satisfies current viewport width and devicePixelRatio, then request only visible tiles.

Recommended policy:
- show `preview` immediately;
- select a level from viewport width x DPR;
- request only tiles intersecting the current field of view;
- keep adjacent tiles warm for smooth panning;
- use AVIF where the Flutter image stack supports it, otherwise WebP.
