# -*- coding: utf-8 -*-
# Copyright 2015-2024 - Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
{
    "name": "Move existing attachments to filesystem",
    "version": "6.1.1.0.0",
    "author": "Therp BV,Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "complexity": "normal",
    "description": """
Introduction
============
This addon allows to automatically move existing attachments to the file
system.

Configuration
=============
The module will use the first (=lowest id) document.storage record that points
to the external file system. To be effective such a record should be created
if it does not exist already.

You have to configure and activate the defined cron job to get everything running.
The cronjob will do a maximum of 10000 conversions per run.
The limit is configurable with the parameter `attachments_to_filesystem.limit`.

After all attachments are migrated (the log will show then `moving 0
attachments to filestore`), you can disable or delete the cronjob.

Credits
=======

Contributors
------------

* Holger Brunn <hbrunn@therp.nl>
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
    "depends": ["attachment_v7_compatible"],
    "data": ["data/ir_cron.xml"],
    "test": [],
    "auto_install": False,
    "installable": True,
    "application": False,
    "external_dependencies": {"python": ["dateutil", "pytz"]},
}
