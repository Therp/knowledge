# -*- coding: utf-8 -*-
# Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
# Copyright 2024 - Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from datetime import datetime
from dateutil.relativedelta import relativedelta
import hashlib
import logging
import os
import pytz
import re

from openerp.osv import  fields, osv
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT

SUPERUSER_ID = 1

class IrAttachment(osv.osv):
    _inherit = "ir.attachment"

    def _attachments_to_filesystem_init(self, cr, uid, context=None):
        """Set up config parameter and cron job"""
        module_name = __name__.split(".")[-3]
        ir_model_data = self.pool["ir.model.data"]
        ir_cron = self.pool["ir.cron"]
        location = self.pool["ir.config_parameter"].get_param(
            cr, uid, "ir_attachment.location"
        )
        if location:
            # we assume the user knows what she's doing. Might be file:, but
            # also whatever other scheme shouldn't matter. We want to bring
            # data from the database to there
            pass
        else:
            ir_model_data._update(
                cr,
                uid,
                "ir.config_parameter",
                module_name,
                {"key": "ir_attachment.location", "value": "file:///filestore"},
                xml_id="config_parameter_ir_attachment_location",
                noupdate=True,
                context=context,
            )

    # 'data' field implementation
    def _full_path(self, cr, uid, location, path):
        # Unlike in OpenERP 7.0 we will use the document file store,
        assert location.startswith('file:'), "Unhandled filestore location %s" % location
        location = super(IrAttachment, self)._get_filestore(cr)
        path = re.sub('[.]','',path)
        path = path.strip('/\\')
        return os.path.join(location, path)

    def _file_read(self, cr, uid, location, fname, bin_size=False):
        full_path = self._full_path(cr, uid, location, fname)
        r = ''
        try:
            if bin_size:
                r = os.path.getsize(full_path)
            else:
                r = open(full_path,'rb').read().encode('base64')
        except IOError:
            _logger.error("_read_file reading %s",full_path)
        return r

    def _file_write(self, cr, uid, location, value):
        bin_value = value.decode('base64')
        fname = hashlib.sha1(bin_value).hexdigest()
        # scatter files across 1024 dirs
        # we use '/' in the db (even on windows)
        fname = fname[:3] + '/' + fname
        full_path = self._full_path(cr, uid, location, fname)
        try:
            dirname = os.path.dirname(full_path)
            if not os.path.isdir(dirname):
                os.makedirs(dirname)
            open(full_path,'wb').write(bin_value)
        except IOError:
            _logger.error("_file_write writing %s",full_path)
        return fname

    def _file_delete(self, cr, uid, location, fname):
        # using SQL to include files hidden through unlink or due to record rules
        cr.execute("SELECT COUNT(*) FROM ir_attachment WHERE store_fname = %s", (fname,))
        count = cr.fetchone()[0]
        if count <= 1:
            full_path = self._full_path(cr, uid, location, fname)
            try:
                os.unlink(full_path)
            except OSError:
                _logger.error("_file_delete could not unlink %s",full_path)
            except IOError:
                # Harmless and needed for race conditions
                _logger.error("_file_delete could not unlink %s",full_path)

    def _data_get(self, cr, uid, ids, name, arg, context=None):
        if context is None:
            context = {}
        result = {}
        location = self.pool.get('ir.config_parameter').get_param(cr, SUPERUSER_ID, 'ir_attachment.location')
        bin_size = context.get('bin_size')
        for attach in self.browse(cr, uid, ids, context=context):
            if location and attach.store_fname:
                result[attach.id] = self._file_read(cr, uid, location, attach.store_fname, bin_size)
            else:
                result[attach.id] = attach.db_datas
                if bin_size:
                    result[attach.id] = int(result[attach.id] or 0)
        return result


    def _data_set(self, cr, uid, id, name, value, arg, context=None):
        # We dont handle setting data to null
        if not value:
            return True
        if context is None:
            context = {}
        location = self.pool.get('ir.config_parameter').get_param(cr, SUPERUSER_ID, 'ir_attachment.location')
        file_size = len(value.decode('base64'))
        if location:
            attach = self.browse(cr, uid, id, context=context)
            if attach.store_fname:
                self._file_delete(cr, uid, location, attach.store_fname)
            fname = self._file_write(cr, uid, location, value)
            # SUPERUSER_ID as probably don't have write access, trigger during create
            super(IrAttachment, self).write(
                cr, SUPERUSER_ID, [id], {'store_fname': fname, 'file_size': file_size}, context=context
            )
        else:
            super(IrAttachment, self).write(
                cr, SUPERUSER_ID, [id], {'db_datas': value, 'file_size': file_size}, context=context
            )
        return True

    _columns = {
        'datas': fields.function(
            _data_get, fnct_inv=_data_set,
            string='File Content',
            type="binary", nodrop=True,
        ),
        'db_datas': fields.binary('Database Data'),
        'file_size': fields.integer('File Size'),
    }

    def read(self, cr, uid, ids, fields_to_read=None, context=None, load='_classic_read'):
        if isinstance(ids, (int, long)):
            ids = [ids]
        self.check(cr, uid, ids, 'read', context=context)
        return super(IrAttachment, self).read(cr, uid, ids, fields_to_read, context, load)

    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        self.check(cr, uid, ids, 'write', context=context, values=vals)
        if 'file_size' in vals:
            del vals['file_size']
        return super(IrAttachment, self).write(cr, uid, ids, vals, context)

    def unlink(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        self.check(cr, uid, ids, 'unlink', context=context)
        location = self.pool.get('ir.config_parameter').get_param(cr, SUPERUSER_ID, 'ir_attachment.location')
        if location:
            for attach in self.browse(cr, uid, ids, context=context):
                if attach.store_fname:
                    self._file_delete(cr, uid, location, attach.store_fname)
        return super(IrAttachment, self).unlink(cr, uid, ids, context)

    def create(self, cr, uid, values, context=None):
        self.check(cr, uid, [], mode='write', context=context, values=values)
        if 'file_size' in values:
            del values['file_size']
        return super(IrAttachment, self).create(cr, uid, values, context)
