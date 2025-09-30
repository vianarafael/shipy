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

Tutorial (Todo w/ Auth): https://shipy.rafaelviana.com/docs/tutorials/todo

Deploy (VPS in 15 min): https://shipy.rafaelviana.com/docs/deploy/vps-15min

Stripe stub → live: https://shipy.rafaelviana.com/docs/payments/stripe-stub

## Contributing

Good First Issues: https://github.com/rafaelviana/shipy/issues?q=is%3Aissue+is%3Aopen+label%3A"good%20first%20issue"

Guide: https://shipy.rafaelviana.com/docs/contribute

## License

MIT
