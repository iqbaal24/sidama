"""Form helpers: consistent widget styling across the internal app."""
from __future__ import annotations

from django import forms


class StyledFormMixin:
    """Attach the right CSS class to every widget of a form."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                css = "checkbox"
            elif isinstance(widget, forms.Select):
                css = "select"
            elif isinstance(widget, forms.Textarea):
                css = "textarea"
                widget.attrs.setdefault("rows", 3)
            elif isinstance(widget, forms.FileInput):
                css = "file"
            elif isinstance(widget, (forms.DateInput, forms.DateTimeInput)):
                css = "input"
                widget.attrs.setdefault("type", "date")
            else:
                css = "input"
            existing = widget.attrs.get("class", "")
            widget.attrs["class"] = f"{existing} {css}".strip()
            if field.required and not isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("required", "required")


class StyledModelForm(StyledFormMixin, forms.ModelForm):
    pass


class StyledForm(StyledFormMixin, forms.Form):
    pass
