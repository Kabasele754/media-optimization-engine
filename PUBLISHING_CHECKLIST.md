# First publication checklist

1. Create the source repository and push the package source.
2. Create accounts on PyPI and TestPyPI and enable 2FA.
3. In TestPyPI, configure a Trusted Publisher for the repository, workflow `.github/workflows/publish-testpypi.yml`, environment `testpypi`.
4. In PyPI, configure a Trusted Publisher for workflow `.github/workflows/publish-pypi.yml`, environment `pypi`.
5. Push a release-candidate tag such as `v1.4.0-rc1` and verify TestPyPI installation in a fresh virtual environment.
6. Run the Django smoke test: install package, add `media_engine`, migrate, doctor, upload one normal image and one panorama.
7. Create GitHub Release `v1.4.0`; the PyPI workflow publishes the immutable release.
8. Test `pip install media-optimization-engine==1.4.0` on a clean machine.

Do not reuse a version number already uploaded to PyPI/TestPyPI. Publish a new patch release instead.
