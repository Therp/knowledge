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
If it doesn't exist, the module creates a parameter `ir_attachment.location`
with value `file:///filestore`. This will make new attachments end up in your
root path (the odoo configuration value `root_path`) in a subdirectory called
`filestore`.

Then it will create a cron job that does the actual transfer and schedule it
for 01:42 at night in the installing user's time zone. The cronjob will do a
maximum of 10000 conversions per run and is run every night.
The limit is configurable with the parameter `attachments_to_filesystem.limit`.

After all attachments are migrated (the log will show then `moving 0
attachments to filestore`), you can disable or delete the cronjob.

If you need to run the migration synchronously during install, set the
parameter `attachments_to_filesystem.move_during_init` *before* installing this
addon.

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
    "depends": ["attachements_v7_compatible"],
    "data": ["data/ir_cron.xml", "data/init.xml"],
    "test": [],
    "auto_install": False,
    "installable": True,
    "application": False,
    "external_dependencies": {"python": ["dateutil", "pytz"]},
}
