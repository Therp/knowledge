# -*- coding: utf-8 -*-
# Copyright 2024 - Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import logging
import os

import pooler
from openerp.osv.orm import AbstractModel
from openerp.addons.document.content_index import cntIndex

SUPERUSER_ID = 1

_logger = logging.getLogger(__name__)


class Base64RepairBatch(AbstractModel):
    """Batch to periodically repair all attachments that still got stored in base64."""
    _name = "b64repair.batch"
    _description = __doc__

    def _b64repair_batch_cron(self, cr, uid, context=None):
        """Repair all attachments that are still in base64 format."""
        attachment_rows = self._get_attachment_rows(cr)
        attachment_model = self.pool["ir.attachment"]
        location = attachment_model._get_location(cr)
        _logger.info("b64repairing %d attachments", len(attachment_rows))
        errors = 0
        repaired = 0
        try:
            # Put everything in try, except finally block, to certainly close cursor.
            new_cr = pooler.get_db(cr.dbname).cursor()
            for counter, row in enumerate(attachment_rows, start=1):
                attachment_id = row[0]
                filename = row[1]
                store_fname = row[2]
                try:
                    full_path = os.path.join(location, store_fname.strip("/\\"))
                    data_bytes = ""  # Default empty byte array (is python2 string).
                    with open(full_path, "rb") as os_file:
                        data_bytes = os_file.read()
                    if attachment_model._is_base64(data_bytes):
                        bin_value = attachment_model._get_bin_value(data_bytes)
                        store_fname = attachment_model._file_write(
                            new_cr, SUPERUSER_ID, data_bytes
                        )
                        repaired += 1
                    # Always rewrite store_fname, as it may have changed.
                    new_cr.execute(
                        "UPDATE ir_attachment"
                        " SET store_fname = %s, certified_binary = true"
                        "  WHERE id = %s",
                        (store_fname, attachment_id)
                    )
                    new_cr.commit()
                except Exception as exc:
                    _logger.exception(
                        "Unexpected error checking attachment"
                        " for base64 with name %s and id %d",
                        filename,
                        attachment_id,
                    )
                    new_cr.rollback()
                    errors += 1
                if counter == len(attachment_rows) or (not counter % 64):
                    _logger.info(
                        "b64repairing attachments: %d read, %d repaired",
                        counter,
                        repaired
                    )
        except Exception as exc:
            _logger.exception(
                "Unexpected error in checking attachments for base64"
            )
        finally:
            new_cr.close()
        if errors:
            _logger.error(
                "There where %d errors when checking attachments for base64",
                errors
            )

    def _get_attachment_rows(self, cr):
        """Get attachments to b64repair through SQL.

        The document module has an error in the search function, making
        it return only a limited subset of attachments that are available,
        """
        limit = 512  # If b64repairing is fast enough, increase cron frequency...
        cr.execute(
            "SELECT id, name, store_fname FROM ir_attachment"
            " WHERE NOT store_fname IS NULL"
            "   AND (certified_binary IS NULL OR NOT certified_binary)"
            " ORDER BY id DESC"
            " LIMIT %d" % limit
        )
        rows = cr.fetchall()
        return rows
