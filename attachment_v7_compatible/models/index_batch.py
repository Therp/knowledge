# -*- coding: utf-8 -*-
# Copyright 2024 - Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import logging
import os

import pooler
from openerp.osv.orm import AbstractModel
from openerp.addons.document.content_index import cntIndex

_logger = logging.getLogger(__name__)


class IndexBatch(AbstractModel):
    """Batch to periodically index all not as yet indexed attachments."""
    _name = "index.batch"
    _description = __doc__

    def _index_batch_cron(self, cr, uid, context=None):
        """Index all not indexed attachments that can be indexed."""
        attachment_rows = self._get_attachment_rows(cr)
        attachment_model = self.pool["ir.attachment"]
        location = attachment_model._get_location(cr)
        _logger.info("indexing %d attachments", len(attachment_rows))
        errors = 0
        try:
            # Put everything in try, except finally block, to certainly close cursor.
            new_cr = pooler.get_db(cr.dbname).cursor()
            # attachments can be big, so we read every attachment on its own
            for counter, row in enumerate(attachment_rows, start=1):
                attachment_id = row[0]
                filename = row[1]
                store_fname = row[2]
                full_path = os.path.join(location, store_fname.strip("/\\"))
                try:
                    file_type, index_content = cntIndex.doIndex(
                        None, filename=filename, content_type=None, realfname=full_path
                    )
                    # We need to put something in index_content, even is there is
                    # nothing applicable, otherwise the row will be selected every time
                    # the cronjob runs.
                    index_content = index_content or "--n/a--"  # Not applicable.
                    new_cr.execute(
                        "UPDATE ir_attachment"
                        " SET index_content = %s, file_type = %s"
                        "  WHERE id = %s",
                        (index_content, file_type, attachment_id)
                    )
                    new_cr.commit()
                except Exception as exc:
                    _logger.exception(
                        "Unexpected error indexing attachment with name %s and id %d",
                        filename,
                        attachment_id,
                    )
                    new_cr.rollback()
                    errors += 1
                if counter == len(attachment_rows) or (not counter % 64):
                    _logger.info("indexing attachments: %d done", counter)
        except Exception as exc:
            _logger.exception(
                "Unexpected error in indexing attachments"
            )
        finally:
            new_cr.close()
        if errors:
            _logger.error("There where %d errors when indexing attachments" % errors)

    def _get_attachment_rows(self, cr):
        """Get attachments to index through SQL.

        The document module has an error in the search function, making
        it return only a limited subset of attachments that are available,
        """
        limit = 512  # If indexing is fast enough, increase cron frequency...
        cr.execute(
            "SELECT id, name, store_fname FROM ir_attachment"
            " WHERE NOT store_fname IS NULL"
            "   AND (index_content IS NULL OR index_content = '')"
            " ORDER BY id DESC"
            " LIMIT %d" % limit
        )
        rows = cr.fetchall()
        return rows

