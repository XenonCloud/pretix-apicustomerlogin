API Customer Login
==========================

This is a plugin for `pretix`_. 

Short description

API endpoints
-------------

In addition to customer login and payment helpers, the plugin provides an endpoint for
refunding an order to a **newly issued gift card**. This is the API equivalent of the
backend workflow "Refund to new gift card". Since pretix 2026.10 the core refund API
rejects ``provider: "giftcard"`` (CVE-2026-101273), so this plugin endpoint is the
supported way to trigger this workflow from an API client.

``POST /api/v1/organizers/{organizer}/events/{event}/giftcard_refunds/create/``

Requires the ``event.orders:write`` event permission. Parameters:

* ``order_code`` (required): code of an order of the given event.
* ``amount`` (optional): amount to refund. Must be positive and must not exceed the
  still refundable amount of the order. If omitted, the full refundable amount is used.
* ``comment`` (optional): refund reason, also stored on the gift card transaction.
* ``expires`` (optional): expiry date in ``YYYY-MM-DD`` format. If omitted, the
  organizer's default gift card expiry is used. Pass ``null`` for no expiry.
* ``conditions`` (optional): special terms and conditions for the new gift card.

The response contains the created ``refund`` (already in state ``done``) and the
``giftcard`` including its secret code. The order row is locked while the refund is
processed, so concurrent refunds cannot over-refund the order.

Development setup
-----------------

1. Make sure that you have a working `pretix development setup`_.

2. Clone this repository.

3. Activate the virtual environment you use for pretix development.

4. Execute ``python setup.py develop`` within this directory to register this application with pretix's plugin registry.

5. Execute ``make`` within this directory to compile translations.

6. Restart your local pretix server. You can now use the plugin from this repository for your events by enabling it in
   the 'plugins' tab in the settings.

This plugin has CI set up to enforce a few code style rules. To check locally, you need these packages installed::

    pip install flake8 isort black

To check your plugin for rule violations, run::

    black --check .
    isort -c .
    flake8 .

You can auto-fix some of these issues by running::

    isort .
    black .

To automatically check for these issues before you commit, you can run ``.install-hooks``.


License
-------


Copyright 2026 XenonCloud

Released under the terms of the Apache License 2.0



.. _pretix: https://github.com/pretix/pretix
.. _pretix development setup: https://docs.pretix.eu/en/latest/development/setup.html
