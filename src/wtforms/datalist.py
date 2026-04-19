from itertools import count

from markupsafe import Markup

from wtforms.fields.choices import Choice
from wtforms.widgets.core import html_params

__all__ = ("DataList",)


def _to_choice(item):
    """Coerce a str or :class:`Choice` to a :class:`Choice`."""
    if isinstance(item, Choice):
        return item
    if isinstance(item, str):
        return Choice(value=item)
    raise TypeError(
        f"DataList choices must be str or Choice instances, got {type(item).__name__}"
    )


class DataList:
    """A ``<datalist>`` of suggestions, declared at form level.

    A :class:`DataList` is referenced by :class:`~wtforms.Field` instances
    via their ``datalist=`` parameter. At render time, the field's
    input emits a ``list="<datalist-id>"`` attribute, and the datalist
    renders ``<datalist id="...">`` with ``<option>`` children.

    :param choices:
        A list of :class:`~wtforms.fields.choices.Choice`, a list of
        strings (where each string is both the value and the label), or
        a callable ``(value) -> list`` invoked at render time with the
        current field value. The callable form enables server-side
        filtering and works well with dynamic re-rendering (e.g. htmx).
    :param render_kw:
        An optional dict of HTML attributes to apply to the rendered
        ``<datalist>`` element.

    Usage::

        class MyForm(Form):
            countries = DataList(choices=[Choice("FR", "France")])
            country = StringField("Country", datalist=countries)

    The same form-level :class:`DataList` can be referenced by
    multiple fields and is rendered only once. Callable ``choices``
    are forbidden at form level (``TypeError`` is raised): pass the
    :class:`DataList` inline to a field instead, which gives each
    field — including each :class:`~wtforms.FieldList` entry — its
    own bound clone with a unique id.

    Unlike :class:`~wtforms.fields.choices.SelectField`, the input is
    not constrained to the suggestions — the user may type any value.
    Combine with :class:`~wtforms.validators.AnyOf` if you need a
    closed set.
    """

    _formdatalist = True
    _creation_counter = count()

    def __init__(self, choices=None, *, render_kw=None):
        self._raw_choices = choices
        self.render_kw = render_kw or {}
        self.creation_counter = next(DataList._creation_counter)

        # Set at bind time:
        self.id = None
        self.short_name = None

    def bind(self, form, name, prefix="", id=None):
        """Return a new :class:`DataList` bound to ``form`` with an id.

        The returned instance shares ``_raw_choices`` and ``render_kw``
        with ``self`` but carries a unique ``id`` / ``short_name``. This
        lets the same :class:`DataList` be reused across multiple form
        instances — or, when passed inline to a field, cloned per
        field bind — without mutation.

        ``id`` overrides the default ``prefix + name`` id, used when a
        field owns an inline (anonymous) :class:`DataList` and wants a
        field-derived id.
        """
        bound = DataList.__new__(DataList)
        bound._raw_choices = self._raw_choices
        bound.render_kw = self.render_kw
        bound.creation_counter = self.creation_counter
        bound.short_name = name
        bound.id = id if id is not None else prefix + name
        return bound

    def iter_choices(self, value=None):
        """Resolve the ``choices`` parameter to a list of :class:`Choice`.

        If ``choices`` is a callable, it is invoked with ``value`` so
        that the returned list can depend on the current field value.
        Choices whose :attr:`~Choice.value` equals ``value`` are
        flagged with ``_selected=True`` — callers can use this to
        locate the Choice matching the field's current value.
        """
        raw = self._raw_choices
        if callable(raw):
            raw = raw(value)
        if raw is None:
            return []
        choices = [_to_choice(item) for item in raw]
        if value is not None:
            for choice in choices:
                if choice.value == value:
                    choice._selected = True
        return choices

    def __call__(self, value=None, **kwargs):
        """Render the ``<datalist>`` element with its ``<option>`` children."""
        attrs = {**self.render_kw, "id": self.id, **kwargs}
        options = []
        for choice in self.iter_choices(value):
            option_attrs = {"value": choice.value}
            if choice.label is not None and choice.label != choice.value:
                option_attrs["label"] = choice.label
            if choice.render_kw:
                option_attrs = {**choice.render_kw, **option_attrs}
            options.append(f"<option {html_params(**option_attrs)}>")
        return Markup(f"<datalist {html_params(**attrs)}>{''.join(options)}</datalist>")

    def __html__(self):
        return self()
