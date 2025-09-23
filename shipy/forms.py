# shipy/forms.py
from __future__ import annotations
import re

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

class Form:
    """
    Tiny helper for classic HTML forms.
    - Build from request.form (urlencoded)
    - Chain simple validators
    - Refill fields in templates: {{ form['email'] }}
    - Show errors: {% for e in form.errors_for('email') %}...{% endfor %}
    """
    def __init__(self, data: dict[str, str | list[str]] | None = None):
        data = data or {}
        # normalize multi-values to a single string (first)
        self.data: dict[str, str] = {
            k: (v if isinstance(v, str) else (v[0] if v else ""))
            for k, v in data.items()
        }
        self.errors: dict[str, list[str]] = {}

    # ----- API -----
    @property
    def ok(self) -> bool:
        return not self.errors

    def require(self, *fields: str) -> "Form":
        for f in fields:
            v = self.data.get(f, "").strip()
            if v == "":
                self._err(f, "required")
        return self

    def min(self, field: str, n: int) -> "Form":
        if len(self.data.get(field, "")) < n:
            self._err(field, f"min {n} chars")
        return self

    def email(self, field: str = "email") -> "Form":
        v = self.data.get(field, "").strip()
        if v and not _EMAIL_RE.match(v):
            self._err(field, "invalid email")
        return self

    # templating sugar
    def __getitem__(self, key: str) -> str:
        return self.data.get(key, "")

    def errors_for(self, field: str) -> list[str]:
        return self.errors.get(field, [])

    def to_dict(self) -> dict[str, str]:
        return dict(self.data)

    # ----- internals -----
    def _err(self, field: str, msg: str):
        self.errors.setdefault(field, []).append(msg)
