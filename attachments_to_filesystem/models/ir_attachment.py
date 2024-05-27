# -*- coding: utf-8 -*-
# Copyright 2015-2024 - Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import logging
import pytz
from datetime import datetime
from dateutil.relativedelta import relativedelta

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
        ir_attachment = self.pool["ir.attachment"]
        try:
            # Put everything in try, except finally block, to cetainly close cursor.
            new_cr = pooler.get_db(cr.dbname).cursor()
            # attachments can be big, so we read every attachment on its own
            for counter, attachment_id in enumerate(attachment_ids, start=1):
                attachment_data = ir_attachment.read(
                    new_cr, uid, [attachment_id], ["datas"], context=context
                )[0]
                try:
                    ir_attachment.write(
                        new_cr,
                        uid,
                        [attachment_id],
                        {"datas": attachment_data["datas"], "db_datas": False},
                        context=context,
                    )
                    new_cr.commit()
                except Exception as exc:
                    _logger.exception(
                        "Unexpected error moving attachment with id %d",
                        attachment_id,
                    )
                    new_cr.rollback()
                if counter == len(attachment_ids) or (not counter % 64):
                    _logger.info("moving attachments: %d done", counter)
        except Exception as exc:
            _logger.exception(
                "Unexpected error in moving attachments"
            )
        finally:
            new_cr.close()

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
