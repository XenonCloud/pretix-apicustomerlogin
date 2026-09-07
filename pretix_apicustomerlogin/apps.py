from django.utils.translation import gettext_lazy

from . import __version__

try:
    from pretix.base.plugins import PluginConfig
except ImportError:
    raise RuntimeError("Please use pretix 2.7 or above to run this plugin!")


class PluginApp(PluginConfig):
    default = True
    name = "pretix_apicustomerlogin"
    verbose_name = "API Customer Login"

    class PretixPluginMeta:
        name = gettext_lazy("API Customer Login")
        author = "XenonCloud"
        description = gettext_lazy(
            "Provides api endpoints for customer login and password change"
        )
        visible = True
        version = __version__
        category = "API"
        compatibility = "pretix>=2.7.0"
        settings_links = []
        navigation_links = []

    def ready(self):
        from . import signals  # NOQA
