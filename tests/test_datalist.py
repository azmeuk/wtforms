import pytest

from tests.common import DummyPostData
from wtforms import Choice
from wtforms import DataList
from wtforms import EmailField
from wtforms import FieldList
from wtforms import Form
from wtforms import FormField
from wtforms import SelectField
from wtforms import StringField
from wtforms import TextAreaField


class SimpleForm(Form):
    tags = DataList(choices=["python", "htmx", "wtforms"])
    tag = StringField(datalist=tags)


class ChoiceForm(Form):
    countries = DataList(
        choices=[Choice("FR", "France"), Choice("US", "United States")],
    )
    country = StringField(datalist=countries)


class CallableForm(Form):
    query = StringField(
        datalist=DataList(choices=lambda value: [f"{value}-1", f"{value}-2"])
    )


class StringReferenceForm(Form):
    my_list = DataList(choices=["a", "b"])
    field = StringField(datalist="my_list")


class SharedForm(Form):
    options = DataList(choices=["x", "y"])
    first = StringField(datalist=options)
    second = StringField(datalist=options)


def test_str_choices_render_options():
    """String choices render as ``<option value="...">`` inside ``<datalist>``."""
    form = SimpleForm()
    html = form.tags()
    assert '<datalist id="tags">' in html
    assert '<option value="python">' in html
    assert '<option value="htmx">' in html
    assert '<option value="wtforms">' in html


def test_choice_choices_render_value_and_label():
    """``Choice`` instances render both ``value=`` and ``label=`` attributes."""
    form = ChoiceForm()
    html = form.countries()
    assert 'value="FR"' in html
    assert 'label="France"' in html
    assert 'value="US"' in html
    assert 'label="United States"' in html


def test_choice_label_omitted_when_equals_value():
    """``label=`` is omitted from the option when it equals ``value``."""
    form = Form()
    dl = DataList(choices=[Choice("x", "x")])
    bound = dl.bind(form, "dl")
    html = bound()
    assert 'value="x"' in html
    assert "label=" not in html


def test_callable_choices_receives_value():
    """An anonymous callable ``DataList`` renders with the field's current value."""
    form = CallableForm(DummyPostData({"query": ["hello"]}))
    html = str(form.query.datalist())
    assert '<option value="hello-1">' in html
    assert '<option value="hello-2">' in html


def test_callable_choices_receives_none_when_no_value():
    """A callable ``choices`` receives ``None`` when no value is passed at render."""
    dl = DataList(choices=lambda v: ["default"] if v is None else ["other"])
    bound = dl.bind(Form(), "dl")
    assert "default" in bound()


def test_field_renders_list_attr():
    """A field with ``datalist=`` emits a ``list="<id>"`` attribute on its input."""
    form = SimpleForm()
    html = form.tag()
    assert 'list="tags"' in html


def test_field_without_datalist_has_no_list_attr():
    """A field with no ``datalist=`` does not emit a ``list=`` attribute."""

    class F(Form):
        x = StringField()

    form = F()
    assert "list=" not in form.x()


def test_datalist_accessible_via_attribute():
    """A declared ``DataList`` is exposed as an attribute of the form instance."""
    form = SimpleForm()
    assert form.tags is form._datalists["tags"]


def test_datalist_not_in_form_data():
    """A ``DataList`` is a render-only element and does not appear in ``form.data``."""
    form = SimpleForm()
    assert "tags" not in form.data
    assert "tag" in form.data


def test_string_reference_resolution():
    """``datalist="name"`` resolves to the DataList declared under that name."""
    form = StringReferenceForm()
    html = form.field()
    assert 'list="my_list"' in html


def test_shared_datalist_rendered_once_referenced_twice():
    """A DataList can be shared by multiple fields and renders with a single id."""
    form = SharedForm()
    assert 'list="options"' in form.first()
    assert 'list="options"' in form.second()
    # Same DataList id, can be rendered once in template:
    assert form.options.id == "options"


def test_incompatible_field_raises():
    """A widget without ``supports_datalist`` raises ``TypeError``."""
    # TextAreaField uses TextArea widget, which does not support datalist.
    dl = DataList(choices=["a"])
    with pytest.raises(TypeError, match="does not support a datalist"):

        class F(Form):
            my_list = dl
            field = TextAreaField(datalist=my_list)

        F()


def test_select_field_incompatible():
    """``SelectField`` is explicitly incompatible with ``datalist=``."""
    dl = DataList(choices=["a"])
    with pytest.raises(TypeError, match="does not support a datalist"):

        class F(Form):
            my_list = dl
            field = SelectField(choices=["a"], datalist=my_list)

        F()


def test_email_field_compatible():
    """``EmailField`` (a text-based input) accepts ``datalist=`` and emits ``list=``."""
    dl = DataList(choices=["alice@example.com"])

    class F(Form):
        my_list = dl
        email = EmailField(datalist=my_list)

    form = F()
    html = form.email()
    assert 'list="my_list"' in html


def test_render_kw_on_datalist():
    """``render_kw`` on a ``DataList`` is applied as attributes on ``<datalist>``."""
    dl = DataList(choices=["a"], render_kw={"data-foo": "bar"})
    bound = dl.bind(Form(), "dl")
    html = bound()
    assert 'data-foo="bar"' in html


def test_choice_render_kw_on_option():
    """``render_kw`` on a ``Choice`` is applied as attributes on its ``<option>``."""
    dl = DataList(choices=[Choice("x", render_kw={"disabled": True})])
    bound = dl.bind(Form(), "dl")
    html = bound()
    assert "disabled" in html


def test_form_prefix_applied_to_datalist_id():
    """The form ``prefix=`` is prepended to the DataList ``id``."""
    form = SimpleForm(prefix="foo")
    assert form.tags.id == "foo-tags"


def test_none_choices_renders_empty_datalist():
    """``choices=None`` renders an empty ``<datalist>`` with no options."""
    dl = DataList(choices=None)
    bound = dl.bind(Form(), "dl")
    html = bound()
    assert '<datalist id="dl"></datalist>' == str(html)


def test_multiple_form_instances_independent_ids():
    """Two form instances with distinct prefixes produce distinct DataList ids."""
    form_a = SimpleForm(prefix="a")
    form_b = SimpleForm(prefix="b")
    assert form_a.tags.id == "a-tags"
    assert form_b.tags.id == "b-tags"


def test_str_choice_must_be_str_or_choice():
    """Non-str non-Choice items in ``choices`` raise ``TypeError`` at render."""
    dl = DataList(choices=[42])
    bound = dl.bind(Form(), "dl")
    with pytest.raises(TypeError, match="must be str or Choice"):
        bound()


def test_datalist_in_fieldlist_entries():
    """Each entry of a ``FieldList`` emits ``list=`` pointing to the parent DataList."""

    class F(Form):
        tags = DataList(choices=["a", "b"])
        items = FieldList(StringField(datalist=tags), min_entries=2)

    form = F()
    for entry in form.items:
        assert 'list="tags"' in entry()


def test_datalist_in_formfield_subform():
    """A DataList declared on a sub-form is prefixed with the FormField name."""

    class Sub(Form):
        opts = DataList(choices=["z"])
        inner = StringField(datalist=opts)

    class F(Form):
        sub = FormField(Sub)

    form = F()
    assert form.sub.opts.id == "sub-opts"
    assert 'list="sub-opts"' in form.sub.inner()


def test_formfield_can_reference_parent_datalist_by_string():
    """A sub-form can reference a parent DataList via a string ``datalist=``.

    The string is emitted as-is; the user is responsible for matching
    it to the bound id on the enclosing form (which is affected by
    the form ``prefix=``).
    """

    class Sub(Form):
        inner = StringField(datalist="tags")

    class F(Form):
        tags = DataList(choices=["x"])
        sub = FormField(Sub)

    form = F()
    assert 'list="tags"' in form.sub.inner()
    assert form.tags.id == "tags"


def test_anonymous_datalist_inline_on_field():
    """An inline ``DataList(...)`` gets auto-bound to a field-derived id."""

    class F(Form):
        country = StringField(datalist=DataList(choices=["FR", "US"]))

    form = F()
    assert 'list="country-datalist"' in form.country()
    html = str(form.country.datalist())
    assert '<datalist id="country-datalist">' in html
    assert '<option value="FR">' in html


def test_anonymous_datalist_field_datalist_empty_for_string_ref():
    """``field.datalist()`` returns empty markup for string references."""

    class F(Form):
        x = StringField(datalist="external")

    form = F()
    assert str(form.x.datalist()) == ""


def test_anonymous_datalist_field_datalist_empty_when_absent():
    """``field.datalist()`` returns empty markup when no ``datalist=``."""

    class F(Form):
        x = StringField()

    form = F()
    assert str(form.x.datalist()) == ""


def test_anonymous_datalist_in_fieldlist_unique_ids_per_entry():
    """Each FieldList entry gets its own bound DataList with a unique id."""

    class F(Form):
        items = FieldList(
            StringField(datalist=DataList(choices=["a", "b"])),
            min_entries=3,
        )

    form = F()
    ids = [entry._datalist.id for entry in form.items]
    assert ids == ["items-0-datalist", "items-1-datalist", "items-2-datalist"]
    for entry in form.items:
        assert f'list="{entry._datalist.id}"' in entry()


def test_anonymous_callable_datalist_per_fieldlist_entry():
    """A callable inline DataList receives each entry's own data at render."""

    class F(Form):
        items = FieldList(
            StringField(datalist=DataList(choices=lambda v: [f"{v}-1", f"{v}-2"])),
            min_entries=2,
        )

    form = F(data={"items": ["foo", "bar"]})
    dl0 = str(form.items[0].datalist())
    dl1 = str(form.items[1].datalist())
    assert '<option value="foo-1">' in dl0
    assert '<option value="bar-1">' in dl1


def test_form_level_callable_datalist_raises():
    """Callable ``choices`` on a form-level DataList raises ``TypeError``."""
    with pytest.raises(TypeError, match="callable choices"):

        class F(Form):
            suggestions = DataList(choices=lambda v: [f"{v}!"])
            query = StringField(datalist=suggestions)

        F()


def test_anonymous_datalist_form_prefix_propagates():
    """Anonymous DataList id includes the form prefix via the field id."""

    class F(Form):
        country = StringField(datalist=DataList(choices=["FR"]))

    form = F(prefix="signup")
    assert form.country._datalist.id == "signup-country-datalist"
    assert 'list="signup-country-datalist"' in form.country()


def test_iter_choices_flags_selected_on_exact_match():
    """``iter_choices(value)`` sets ``_selected=True`` on the matching Choice."""
    dl = DataList(choices=[Choice("FR", "France"), Choice("US", "United States")])
    bound = dl.bind(Form(), "dl")
    choices = bound.iter_choices("FR")
    assert [c.value for c in choices if c._selected] == ["FR"]
    assert [c.value for c in choices if not c._selected] == ["US"]


def test_iter_choices_no_flag_when_value_is_none():
    """No Choice is flagged when ``value`` is ``None``."""
    dl = DataList(choices=[Choice("FR"), Choice("US")])
    bound = dl.bind(Form(), "dl")
    assert not any(c._selected for c in bound.iter_choices())


def test_iter_choices_callable_flagged_when_callable_returns_match():
    """A callable ``choices`` that returns the exact match gets flagged too."""
    dl = DataList(
        choices=lambda v: [Choice("FR", "France")] if v == "FR" else [],
    )
    bound = dl.bind(Form(), "dl")
    choices = bound.iter_choices("FR")
    assert len(choices) == 1
    assert choices[0]._selected is True
