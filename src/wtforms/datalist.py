import inspect
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
        a callable invoked at render time. The callable may take:

        - no argument (``fn()``) — static list;
        - two arguments (``fn(form, field)``) — compute suggestions
          from the current field value (``field.data``) and other
          fields of the form (e.g. a cascade ``country → region``).

        Arity is detected via :mod:`inspect`. The callable form enables
        server-side filtering and works well with dynamic re-rendering
        (e.g. htmx).
    :param render_kw:
        An optional dict of HTML attributes to apply to the rendered
        ``<datalist>`` element.
    :param widget:
        An optional callable replacing the default ``<datalist>``
        rendering. When set, it is invoked as
        ``widget(datalist, form=form, field=field, **kwargs)`` and its
        return value becomes the rendered output. ``render_kw`` is
        ignored on this path — the widget is responsible for the full
        markup. Useful when the choices need to render as something
        other than a native ``<datalist>`` (e.g. a clickable
        ``<ul role="listbox">``).

    Usage::

        class MyForm(Form):
            countries = DataList(choices=[Choice("FR", "France")])
            country = StringField("Country", datalist=countries)

    The same form-level :class:`DataList` can be referenced by
    multiple fields and is rendered only once. A 0-argument callable
    (``fn()``) is allowed at form level — it behaves as a lazy
    constant. A ``fn(form, field)`` callable is **not** allowed at
    form level (``TypeError`` is raised), because its output depends
    on the calling field and a shared ``<datalist>`` has no single
    field context: pass the :class:`DataList` inline to a field
    instead, which gives each field — including each
    :class:`~wtforms.FieldList` entry — its own bound clone with a
    unique id.

    Unlike :class:`~wtforms.fields.choices.SelectField`, the input is
    not constrained to the suggestions — the user may type any value.
    Combine with :class:`~wtforms.validators.AnyOf` if you need a
    closed set.
    """

    _formdatalist = True
    _creation_counter = count()

    def __init__(self, choices=None, *, render_kw=None, widget=None):
        self._raw_choices = choices
        self.render_kw = render_kw or {}
        self.widget = widget
        self.creation_counter = next(DataList._creation_counter)

        # Set at bind time:
        self.id = None
        self.short_name = None
        self._form = None

    def bind(self, form, name, prefix="", id=None):
        """Return a new :class:`DataList` bound to ``form`` with an id.

        The returned instance shares ``_raw_choices`` and ``render_kw``
        with ``self`` but carries a unique ``id`` / ``short_name`` and
        keeps a reference to ``form`` (used as a fallback when the
        callable ``choices`` needs form state but no ``form`` is
        passed explicitly to :meth:`iter_choices` — e.g. form-level
        rendering via ``form.my_list()``).
        """
        bound = DataList.__new__(DataList)
        bound._raw_choices = self._raw_choices
        bound.render_kw = self.render_kw
        bound.widget = self.widget
        bound.creation_counter = self.creation_counter
        bound.short_name = name
        bound.id = id if id is not None else prefix + name
        bound._form = form
        return bound

    def iter_choices(self, form=None, field=None):
        """Resolve the ``choices`` parameter to a list of :class:`Choice`.

        If ``choices`` is a callable, it is invoked according to its
        arity (detected via :mod:`inspect`):

        - ``fn()`` — static, lazy constant.
        - ``fn(form)`` — form-aware. Allowed at form level for
          standalone DataLists that depend on form state.
        - ``fn(form, field)`` — form + field. Inline only (rejected at
          form level): a shared form-level DataList has no single field
          context.

        Choices whose :attr:`~Choice.value` equals ``field.data`` are
        flagged with ``_selected=True`` — callers can use this to
        locate the Choice matching the field's current value.
        """
        raw = self._raw_choices
        if callable(raw):
            n = len(inspect.signature(raw).parameters)
            ctx = form if form is not None else self._form
            if n >= 2:
                raw = raw(ctx, field)
            elif n == 1:
                raw = raw(ctx)
            else:
                raw = raw()
        if raw is None:
            return []
        choices = [_to_choice(item) for item in raw]
        value = field.data if field is not None else None
        if value is not None:
            for choice in choices:
                if choice.value == value:
                    choice._selected = True
        return choices

    def __call__(self, form=None, field=None, **kwargs):
        """Render the ``<datalist>`` element with its ``<option>`` children.

        If a ``widget`` was provided to :meth:`__init__`, delegates to
        it and returns its output unchanged.
        """
        if form is None:
            form = self._form
        if self.widget is not None:
            return self.widget(self, form=form, field=field, **kwargs)
        attrs = {**self.render_kw, "id": self.id, **kwargs}
        options = []
        for choice in self.iter_choices(form, field):
            option_attrs = {"value": choice.value}
            if choice.label is not None and choice.label != choice.value:
                option_attrs["label"] = choice.label
            if choice.render_kw:
                option_attrs = {**choice.render_kw, **option_attrs}
            options.append(f"<option {html_params(**option_attrs)}>")
        return Markup(f"<datalist {html_params(**attrs)}>{''.join(options)}</datalist>")

    def __html__(self):
        return self()
