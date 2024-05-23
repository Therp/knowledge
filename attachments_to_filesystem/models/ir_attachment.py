# -*- coding: utf-8 -*-
# Copyright 2015-2024 - Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import logging
import pytz
from datetime import datetime
from dateutil.relativedelta import relativedelta

import pooler
from openerp.osv.orm import Model

_logger = logging.getLogger(__name__)


class IrAttachment(Model):
    _inherit = "ir.attachment"

    def _attachments_to_filesystem_cron(self, cr, uid, context=None, limit=512):
        """Do the actual moving. Commit each move through a separate cursor."""
        limit = (
            int(
                self.pool["ir.config_parameter"].get_param(
                    cr, uid, "attachments_to_filesystem.limit", "0"
                )
            )
            or limit
        )
        ir_attachment = self.pool["ir.attachment"]
        domain = [("db_datas", "!=", False)]
        attachment_ids = ir_attachment.search(
            cr, uid, domain, limit=limit, order="id asc", context=context
        )
        _logger.info("moving %d attachments to filestore", len(attachment_ids))
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
                if counter == limit or (not counter % 64):
                    _logger.info("moving attachments: %d done", counter)
        except Exception as exc:
            _logger.exception(
                "Unexpected error in moving attachments"
            )
        finally:
            new_cr.close()
