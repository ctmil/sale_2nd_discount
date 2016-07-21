
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

	def _calc_line_base_price(self, cr, uid, line, context=None):
		if line.second_discount == 0:
			return line.price_unit * (1 - (line.discount or 0.0) / 100.0)
		else:
			temp_value = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
			return temp_value * (1 - (line.second_discount or 0.0) / 100.0)

	def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
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


sale_order_line()

class stock_move(osv.osv):
	_inherit = "stock.move"


	def _get_invoice_line_vals(self, cr, uid, move, partner, inv_type, context=None):
        	res = super(stock_move, self)._get_invoice_line_vals(cr, uid, move, partner, inv_type, context=context)
	        if inv_type in ('out_invoice', 'out_refund') and move.procurement_id and move.procurement_id.sale_line_id:
        	    sale_line = move.procurement_id.sale_line_id
	            res['invoice_line_tax_id'] = [(6, 0, [x.id for x in sale_line.tax_id])]
        	    res['account_analytic_id'] = sale_line.order_id.project_id and sale_line.order_id.project_id.id or False
	            res['discount'] = sale_line.discount
	            res['second_discount'] = sale_line.second_discount
        	    if move.product_id.id != sale_line.product_id.id:
                	res['price_unit'] = self.pool['product.pricelist'].price_get(
	                    cr, uid, [sale_line.order_id.pricelist_id.id],
        	            move.product_id.id, move.product_uom_qty or 1.0,
                	    sale_line.order_id.partner_id, context=context)[sale_line.order_id.pricelist_id.id]
	            else:
        	        res['price_unit'] = sale_line.price_unit
	            uos_coeff = move.product_uom_qty and move.product_uos_qty / move.product_uom_qty or 1.0
        	    res['price_unit'] = res['price_unit'] / uos_coeff
	        return res

