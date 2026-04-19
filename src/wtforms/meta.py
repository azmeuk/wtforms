from markupsafe import Markup

from wtforms import i18n
from wtforms.utils import WebobInputWrapper
from wtforms.widgets.core import clean_key


class DefaultMeta:
    """
    This is the default Meta class which defines all the default values and
    therefore also the 'API' of the class Meta interface.
    """

    # -- Basic form primitives

    def bind_field(self, form, unbound_field, options):
        """
        bind_field allows potential customization of how fields are bound.

        The default implementation simply passes the options to
        :meth:`UnboundField.bind`.

        :param form: The form.
        :param unbound_field: The unbound field.
        :param options:
            A dictionary of options which are typically passed to the field.

        :return: A bound field
        """
        return unbound_field.bind(form=form, **options)

    def bind_datalist(self, form, datalist, options):
        """
        bind_datalist allows potential customization of how form-level
        :class:`~wtforms.DataList` instances are bound to a form,
        symmetrically to :meth:`bind_field`.

        The default implementation passes the options to
        :meth:`DataList.bind`. Subclasses may override to copy
        framework-specific state from the unbound declaration onto the
        bound clone (e.g. an htmx config dict).

        :param form: The form.
        :param datalist: The unbound :class:`~wtforms.DataList`.
        :param options:
            A dictionary of options which are typically passed to the
            datalist (``name``, ``prefix``).

        :return: A bound :class:`~wtforms.DataList`.
        """
        return datalist.bind(form=form, **options)

    def wrap_formdata(self, form, formdata):
        """
        wrap_formdata allows doing custom wrappers of WTForms formdata.

        The default implementation detects webob-style multidicts and wraps
        them, otherwise passes formdata back un-changed.

        :param form: The form.
        :param formdata: Form data.
        :return: A form-input wrapper compatible with WTForms.
        """
        if formdata is not None and not hasattr(formdata, "getlist"):
            if hasattr(formdata, "getall"):
                return WebobInputWrapper(formdata)
            else:
                raise TypeError(
                    "formdata should be a multidict-type wrapper that"
                    " supports the 'getlist' method"
                )
        return formdata

    def render_field(self, field, render_kw):
        """
        render_field allows customization of how widget rendering is done.

        The default implementation calls ``field.widget(field, **render_kw)``
        and, when the field owns an inline :class:`~wtforms.DataList`
        (passed directly via ``datalist=DataList(...)``), appends the
        rendered ``<datalist>`` after the widget output so that
        ``<input list="X">`` and ``<datalist id="X">`` are always
        emitted together as a functional pair. Form-level datalists
        (declared as class attributes and referenced by name or
        instance) are not auto-emitted — they may be shared by several
        fields and are rendered once via ``form.<name>()``.

        Meta subclasses that route the rendering to a custom renderer
        (e.g. a wrapping callable) bypass this behavior by not
        delegating to ``super().render_field`` — they take full
        control of the emitted HTML, including whether a
        ``<datalist>`` is appended.
        """

        render_kw = {clean_key(k): v for k, v in render_kw.items()}

        other_kw = getattr(field, "render_kw", None)
        if other_kw is not None:
            other_kw = {clean_key(k): v for k, v in other_kw.items()}
            render_kw = dict(other_kw, **render_kw)
        html = field.widget(field, **render_kw)
        dl = field._datalist
        if dl is not None and not isinstance(dl, str):
            form_dls = getattr(dl._form, "_datalists", None) or {}
            if dl not in form_dls.values():
                html = Markup(html) + field.datalist()
        return html

    # -- CSRF

    csrf = False
    csrf_field_name = "csrf_token"
    csrf_secret = None
    csrf_context = None
    csrf_class = None

    def build_csrf(self, form):
        """
        Build a CSRF implementation. This is called once per form instance.

        The default implementation builds the class referenced to by
        :attr:`csrf_class` with zero arguments. If `csrf_class` is ``None``,
        will instead use the default implementation
        :class:`wtforms.csrf.session.SessionCSRF`.

        :param form: The form.
        :return: A CSRF implementation.
        """
        if self.csrf_class is not None:
            return self.csrf_class()

        from wtforms.csrf.session import SessionCSRF

        return SessionCSRF()

    # -- i18n

    locales = False
    cache_translations = True
    translations_cache = {}

    def get_translations(self, form):
        """
        Override in subclasses to provide alternate translations factory.
        See the i18n documentation for more.

        :param form: The form.
        :return: An object that provides gettext() and ngettext() methods.
        """
        locales = self.locales
        if locales is False:
            return None

        if self.cache_translations:
            # Make locales be a hashable value
            locales = tuple(locales) if locales else None

            translations = self.translations_cache.get(locales)
            if translations is None:
                translations = self.translations_cache[locales] = i18n.get_translations(
                    locales
                )

            return translations

        return i18n.get_translations(locales)

    # -- General

    def update_values(self, values):
        """
        Given a dictionary of values, update values on this `Meta` instance.
        """
        for key, value in values.items():
            setattr(self, key, value)
