# Shipy

**One-box web framework** to ship indie apps fast: Python backend, HTMX front, SQLite storage. Zero build chain. Deploy on a $12 VPS.

- 🚢 **Ship daily**: scaffold → auth → CRUD → deploy in under 30 minutes
- 🧰 **Batteries included**: signed-cookie sessions, CSRF, forms, HTMX helpers
- 🧠 **Fits in your head**: one repo, raw SQL first, no tool sprawl

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install shipy-web
shipy new demo && cd demo
shipy db init
shipy dev  # http://localhost:8000
```

## Docs

Get Started: https://shipy.rafaelviana.com/docs/get-started

## Contributing

Good First Issues: https://github.com/vianarafael/shipy/issues

## License

MIT
