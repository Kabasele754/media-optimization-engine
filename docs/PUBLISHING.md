# Publishing Media Optimization Engine

The canonical source repository is:

```text
Kabasele754/media-optimization-engine
```

The Python distribution name is:

```text
media-optimization-engine
```

The import name is:

```python
import media_engine
```

## Trusted Publishing

Publishing uses GitHub Actions OIDC Trusted Publishing. Do not store long-lived PyPI API tokens in GitHub.

### TestPyPI

Configure a TestPyPI Trusted Publisher with:

- owner: `Kabasele754`
- repository: `media-optimization-engine`
- workflow: `publish-testpypi.yml`
- environment: `testpypi`

The workflow can be started manually or by an RC tag such as:

```text
v1.4.0-rc1
```

### PyPI

Configure the PyPI Trusted Publisher with:

- owner: `Kabasele754`
- repository: `media-optimization-engine`
- workflow: `publish-pypi.yml`
- environment: `pypi`

The production workflow publishes when a GitHub Release is published.

## First-publication sequence

1. Validate GitHub Actions on `master`.
2. Configure TestPyPI Trusted Publishing.
3. Publish a release candidate to TestPyPI.
4. Install it into a clean virtual environment and a second Django project.
5. Validate normal image + panorama upload.
6. Configure PyPI Trusted Publishing.
7. Publish GitHub Release `v1.4.0`.
8. Verify `pip install media-optimization-engine==1.4.0`.

PyPI versions are immutable. If a release is wrong, publish a new version rather than trying to overwrite it.

## Optional container publication

Docker/GHCR remains a supported deployment path for standalone nodes. Always deploy pinned versions rather than `latest`.
