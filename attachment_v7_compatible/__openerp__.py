# -*- coding: utf-8 -*-
# Copyright 2024 - Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
{
    "name": "Backport 7.0 filestorage for attachments",
    "version": "6.1.1.0.0",
    "author": "Therp BV,Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "complexity": "normal",
    "description": """
Introduction
============
This module backports the OpenERP 7.0 mechanism to store attachments
in the file system, using automatic naming of the file based on a
hash of the contents, back to 6.1.

Configuration
=============
The module will use the first (=lowest id) document.storage record that points
to the external file system. To be effective such a record should be created
if it does not exist already.

Credits
=======

Contributors
------------

* Ronald Portier <ronald@therp.nl>

Icon
----

http://commons.wikimedia.org/wiki/File:Crystal_Clear_app_harddrive.png

Maintainer
----------

.. image:: http://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: http://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

To contribute to this module, please visit http://odoo-community.org.
""",
    "category": "Knowledge Management",
    # Although this module is based on document, it overrides its complicated storage
    # mechanism completely. However the document module provides the needed extra fields
    # and takes care of the conversion from the datas field to db_datas.
    "depends": ["document"],
    "data": [],
    "auto_install": False,
    "installable": True,
    "application": False,
}
