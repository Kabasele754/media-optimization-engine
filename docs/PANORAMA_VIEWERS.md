# Panorama viewer adapters

MOE exposes a canonical panorama manifest and adapters for:

- generic clients;
- Pannellum;
- Marzipano;
- Three.js;
- Flutter consumers.

Endpoint:

```text
GET /api/v1/images/<uuid>/panorama/?profile=panorama.multires&adapter=generic
```

Marzipano:

```text
GET /api/v1/images/<uuid>/panorama/?profile=panorama.marzipano&adapter=marzipano
```

A viewer should not download every high-resolution tile. It should display the preview/lowest level, select a level from viewport and DPR, fetch visible tiles, and prefetch nearby tiles as the camera moves.
