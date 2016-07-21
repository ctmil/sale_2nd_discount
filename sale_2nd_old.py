# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from datetime import datetime, timedelta
import time
from openerp import SUPERUSER_ID
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import openerp.addons.decimal_precision as dp
from openerp import workflow


class sale_order_line(osv.osv):
	_inherit = 'sale.order.line'

	def _amount_line_v2(self, cr, uid, ids, field_name, arg, context=None):
		tax_obj = self.pool.get('account.tax')
		cur_obj = self.pool.get('res.currency')
		res = {}
		if context is None:
			context = {}
		for line in self.browse(cr, uid, ids, context=context):
			price = line.price_unit * (1 - (line.discount or 0.0) / 100.0) * (1 - (line.second_discount or 0.0) / 100)
	            	taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, line.product_uom_qty, line.product_id, line.order_id.partner_id)
	                cur = line.order_id.pricelist_id.currency_id
		        res[line.id] = cur_obj.round(cr, uid, cur, taxes['total'])
        	return res


	_columns = {
		'price_subtotal': fields.function(_amount_line_v2, string='Subtotal', digits_compute= dp.get_precision('Account')),
		}

sale_order_line()

class sale_order(osv.osv):
	_inherit = 'sale.order'

	def _amount_line_tax(self, cr, uid, line, context=None):
        	val = 0.0
	        for c in self.pool.get('account.tax').compute_all(cr, uid, line.tax_id, \
			line.price_unit * (1-(line.discount or 0.0)/100.0) * (1-(line.second_discount or 0.0)/100.0),\
			 line.product_uom_qty, line.product_id, line.order_id.partner_id)['taxes']:
        		val += c.get('amount', 0.0)
	        return val


sale_order()
