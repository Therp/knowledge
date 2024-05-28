# -*- coding: utf-8 -*-
# Copyright 2015-2024 - Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import logging

import pooler
from openerp.osv.orm import Model

SUPERUSER_ID = 1

_logger = logging.getLogger(__name__)


class IrAttachment(Model):
    _inherit = "ir.attachment"

    def _attachments_to_filesystem_cron(self, cr, uid, context=None):
        """Do the actual moving. Commit each move through a separate cursor."""
        attachment_ids = self._get_attachment_ids(cr)
        _logger.info("moving %d attachments to filestore", len(attachment_ids))
        errors = 0
        try:
            # Put everything in try, except finally block, to certainly close cursor.
            new_cr = pooler.get_db(cr.dbname).cursor()
            # attachments can be big, so we read every attachment on its own
            for counter, attachment_id in enumerate(attachment_ids, start=1):
                try:
                    new_cr.execute(
                        "SELECT db_datas, name FROM ir_attachment WHERE id = %d"
                        % attachment_id
                    )
                    row = new_cr.fetchone()
                    bin_value = row[0]  # We assume value is already raw binary.
                    attachment_name = row[1]
                    file_size = len(bin_value)
                    fname = self._file_write(new_cr, SUPERUSER_ID, bin_value)
                    if not fname:
                        _logger.error(
                            "No fname generated for attachment with name %s and id %d",
                            attachment_name,
                            attachment_id
                        )
                        errors += 1
                    new_cr.execute(
                        "UPDATE ir_attachment"
                        " SET db_datas = NULL, store_fname = '%s', file_size = %d"
                        " WHERE id = %d"
                        % (fname, file_size, attachment_id)
                    )
                    new_cr.commit()
                except Exception as exc:
                    _logger.exception(
                        "Unexpected error moving attachment with name %s and id %d",
                        attachment_name,
                        attachment_id,
                    )
                    new_cr.rollback()
                    errors += 1
                if counter == len(attachment_ids) or (not counter % 64):
                    _logger.info("moving attachments: %d done", counter)
        except Exception as exc:
            _logger.exception(
                "Unexpected error in moving attachments"
            )
        finally:
            new_cr.close()
        if errors:
            _logger.error("There where %d errors when moving attachments" % errors)

    def _get_attachment_ids(self, cr):
        """Get attachments to move through SQL.

        The document module has an error in the search function, making
        it return only a limited subset of attachments that are available,
        """
        limit = int(
            self.pool["ir.config_parameter"].get_param(
                cr, SUPERUSER_ID, "attachments_to_filesystem.limit", "512"
            )
        )
        cr.execute(
            "SELECT id FROM ir_attachment"
            " WHERE NOT db_datas IS NULL AND store_fname IS NULL"
            " ORDER BY id ASC"
            " LIMIT %d" % limit
        )
        rows = cr.fetchall()
        return [row[0] for row in rows]
