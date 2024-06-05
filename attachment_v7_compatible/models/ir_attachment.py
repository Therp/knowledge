# -*- coding: utf-8 -*-
# Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
# Copyright 2024 - Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import hashlib
import logging
import os
import re

from openerp.osv import  fields, osv

SUPERUSER_ID = 1

check64 = re.compile("^(?=(.{4})*$)[A-Za-z0-9+/]*={0,2}$")

_logger = logging.getLogger(__name__)


class IrAttachment(osv.osv):
    _inherit = "ir.attachment"

    def _full_path(self, cr, path):
        # Unlike in OpenERP 7.0 we will use the document file store,
        location = self._get_location(cr)
        path = path.strip('/\\')
        return os.path.join(location, path)

    def _file_read(self, cr, uid, fname, bin_size=False):
        full_path = self._full_path(cr, fname)
        r = ''
        try:
            if bin_size:
                r = os.path.getsize(full_path)
            else:
                with open(full_path,'rb') as os_file:
                    r = os_file.read().encode('base64')
        except IOError:
            _logger.error("_read_file reading %s",full_path)
        return r

    def _file_write(self, cr, uid, bin_value):
        try:
            fname = hashlib.sha1(bin_value).hexdigest()
        except UnicodeEncodeError:
            return self._file_write(cr, uid, bin_value.encode("utf-8"))
        # scatter files across 1024 dirs
        # we use '/' in the db (even on windows)
        fname = fname[:3] + '/' + fname
        full_path = self._full_path(cr, fname)
        try:
            dirname = os.path.dirname(full_path)
            if not os.path.isdir(dirname):
                os.makedirs(dirname)
            with open(full_path,'wb') as os_file:
                os_file.write(bin_value)
        except IOError:
            _logger.error("_file_write writing %s", full_path)
        return fname

    def _file_delete(self, cr, uid, fname):
        # using SQL to include files hidden through unlink or due to record rules
        cr.execute("SELECT COUNT(*) FROM ir_attachment WHERE store_fname = %s", (fname,))
        count = cr.fetchone()[0]
        if count <= 1:
            full_path = self._full_path(cr, fname)
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
        location = self._get_location(cr)
        bin_size = context.get('bin_size')
        for attach in self.browse(cr, uid, ids, context=context):
            if location and attach.store_fname:
                result[attach.id] = self._file_read(cr, uid, attach.store_fname, bin_size)
            else:
                result[attach.id] = attach.db_datas
                if bin_size:
                    result[attach.id] = int(result[attach.id] or 0)
        return result

    def _data_set(self, cr, uid, id, name, value, arg, context=None):
        # We dont handle setting data to null
        if not value:
            return True
        context = context or {}
        context["__from_node"] = True
        location = self._get_location(cr)
        bin_value = self._get_bin_value(value)
        vals = {
            "file_size": len(bin_value),
        }
        if location:
            attach = self.browse(cr, uid, id, context=context)
            if attach.store_fname:
                self._file_delete(cr, uid, attach.store_fname)
            fname = self._file_write(cr, uid, bin_value)
            vals["store_fname"] = fname
        else:
            vals["db_datas"] = value
        # SUPERUSER_ID as probably don't have write access, trigger during create
        return super(IrAttachment, self).write(cr, SUPERUSER_ID, [id], vals, context=context)

    def _get_bin_value(self, value):
        """If value is base64 encoded, decode it, else return as is."""
        # base64 encoded strings can contain newlines (used in the past for
        # sending them in lines through email), but they are NOT part of
        # the encoded data.
        if self._is_base64(value):
            # Convert base64 values to binary
            bin_value = value.decode('base64')
        else:
            # Value already is in binary format
            bin_value = value
        return bin_value

    def _is_base64(self, value):
        # Only check the (max) 64 first positions.
        if check64.match(value.replace("\n", "")[:64]):
            return True
        return False

    _columns = {
        # Need to re-add this as functions not specified as string or with lambda.
        "datas": fields.function(
            _data_get, fnct_inv=_data_set,
            string="File Content",
            type="binary", nodrop=True,
        ),
        "certified_binary": fields.boolean(
            string="File has been certified to contain binary (not base64) content",
            default=False,
        ),
    }

    def read(self, cr, uid, ids, fields, context=None, load='_classic_read'):
        if isinstance(ids, (int, long)):
            ids = [ids]
        self.check(cr, uid, ids, 'read', context=context)
        return super(IrAttachment, self).read(
                cr, uid, ids, fields, context=context, load=load
        )

    def write(self, cr, uid, ids, vals, context=None):
        context = context or {}
        context["__from_node"] = True
        return super(IrAttachment, self).write(cr, uid, ids, vals, context=context)

    def unlink(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        self.check(cr, uid, ids, 'unlink', context=context)
        location = self._get_location(cr)
        if location:
            for attach in self.browse(cr, uid, ids, context=context):
                if attach.store_fname:
                    self._file_delete(cr, uid, attach.store_fname)
        return super(IrAttachment, self).unlink(cr, uid, ids, context)

    def create(self, cr, uid, values, context=None):
        self.check(cr, uid, [], mode='write', context=context, values=values)
        if 'file_size' in values:
            del values['file_size']
        return super(IrAttachment, self).create(cr, uid, values, context)

    def _get_location(self, cr, context=None):
        """Location will be the first document.storage for filesystem."""
        storage_model = self.pool["document.storage"]
        domain = [("type", "=", "realstore")]
        storage_ids = storage_model.search(
            cr, SUPERUSER_ID, domain, limit=1, order="id desc", context=context
        )
        if not storage_ids:
            return False
        storage_info = storage_model.read(cr, SUPERUSER_ID, storage_ids, ["path"])
        if not storage_info:
            return False
        return storage_info[0]["path"]
