# Contributing

Contributions are welcome.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[all]"
```

Run the project checks before opening a pull request:

```bash
python -m compileall media_engine
python -m build
```

For Django integration testing:

```bash
python manage.py migrate
python manage.py media_engine_doctor
```

## Pull requests

- Keep changes focused.
- Add or update tests for behavior changes.
- Preserve original uploaded media; generate derivatives from originals.
- Do not introduce project-specific dependencies into the reusable engine.
- Document new settings, processors, storage backends, or public API changes.

## Versioning

The project follows semantic versioning. Published package versions are immutable.
