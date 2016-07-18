from openerp import models, fields, api, _
from openerp.osv import osv
from openerp.exceptions import except_orm, ValidationError
from StringIO import StringIO
import urllib2, httplib, urlparse, gzip, requests, json
import openerp.addons.decimal_precision as dp
import logging
import datetime
from openerp.fields import Date as newdate

class sale_order_line(models.Model):
        _inherit = 'sale.order.line'

	second_discount = fields.Float(string='2do descuento')

	@api.one
	@api.constrains('second_discount')
	def _check_second_discount(self):
		if self.second_discount > 99.9 or self.second_discount < 0:
			raise ValidationError('El valor a ingresar debe ser menor a 100 y mayor a 0')

class account_invoice_line(models.Model):
        _inherit = 'account.invoice.line'

	second_discount = fields.Float(string='2do descuento',digits= dp.get_precision('Discount'),default=0.0)

	@api.one
	@api.constrains('second_discount')
	def _check_second_discount(self):
		if self.second_discount > 99.9 or self.second_discount < 0:
			raise ValidationError('El valor a ingresar debe ser menor a 100 y mayor a 0')

	@api.one
	@api.depends('price_unit', 'discount','second_discount','invoice_line_tax_id', 'quantity','product_id', 'invoice_id.partner_id', 'invoice_id.currency_id')
	def _compute_price(self):
	        price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
	        price = price * (1 - (self.second_discount or 0.0) / 100.0)
        	taxes = self.invoice_line_tax_id.compute_all(price, self.quantity, product=self.product_id, partner=self.invoice_id.partner_id)
	        self.price_subtotal = taxes['total']
        	if self.invoice_id:
			self.price_subtotal = self.invoice_id.currency_id.round(self.price_subtotal)

	@api.model
	def move_line_get(self, invoice_id):
		inv = self.env['account.invoice'].browse(invoice_id)
		currency = inv.currency_id.with_context(date=inv.date_invoice)
		company_currency = inv.company_id.currency_id

		res = []
		for line in inv.invoice_line:
			mres = self.move_line_get_item(line)
			mres['invl_id'] = line.id
			res.append(mres)
			tax_code_found = False
			taxes = line.invoice_line_tax_id.compute_all(
				(line.price_unit * (1.0 - (line.discount or 0.0) / 100.0) * (1.0 - (line.second_discount or 0.0) / 100.0)),
		                line.quantity, line.product_id, inv.partner_id)['taxes']
			for tax in taxes:
				if inv.type in ('out_invoice', 'in_invoice'):
					tax_code_id = tax['base_code_id']
					tax_amount = tax['price_unit'] * line.quantity * tax['base_sign']
				else:
					tax_code_id = tax['ref_base_code_id']
					tax_amount = tax['price_unit'] * line.quantity * tax['ref_base_sign']
				if tax_code_found:
					if not tax_code_id:
						continue
					res.append(dict(mres))
					res[-1]['price'] = 0.0
					res[-1]['account_analytic_id'] = False
                		elif not tax_code_id:
					continue
				tax_code_found = True

				res[-1]['tax_code_id'] = tax_code_id
				res[-1]['tax_amount'] = currency.compute(tax_amount, company_currency)

	        return res


	@api.v8
	def compute(self, invoice):
		tax_grouped = {}
		currency = invoice.currency_id.with_context(date=invoice.date_invoice or fields.Date.context_today(invoice))
		company_currency = invoice.company_id.currency_id
		for line in invoice.invoice_line:
			taxes = line.invoice_line_tax_id.compute_all(
				(line.price_unit * (1 - (line.discount or 0.0) / 100.0) * (1-(line.second_discount or 0.0)/100.0)  ),
				line.quantity, line.product_id, invoice.partner_id)['taxes']
			for tax in taxes:
				val = {
					'invoice_id': invoice.id,
					'name': tax['name'],
					'amount': tax['amount'],
					'manual': False,
					'sequence': tax['sequence'],
					'base': currency.round(tax['price_unit'] * line['quantity']),
			                }
		                if invoice.type in ('out_invoice','in_invoice'):
					val['base_code_id'] = tax['base_code_id']
					val['tax_code_id'] = tax['tax_code_id']
					val['base_amount'] = currency.compute(val['base'] * tax['base_sign'], company_currency, round=False)
					val['tax_amount'] = currency.compute(val['amount'] * tax['tax_sign'], company_currency, round=False)
					val['account_id'] = tax['account_collected_id'] or line.account_id.id
					val['account_analytic_id'] = tax['account_analytic_collected_id']
				else:
					val['base_code_id'] = tax['ref_base_code_id']
					val['tax_code_id'] = tax['ref_tax_code_id']
					val['base_amount'] = currency.compute(val['base'] * tax['ref_base_sign'], company_currency, round=False)
					val['tax_amount'] = currency.compute(val['amount'] * tax['ref_tax_sign'], company_currency, round=False)
					val['account_id'] = tax['account_paid_id'] or line.account_id.id
					val['account_analytic_id'] = tax['account_analytic_paid_id']

		                # If the taxes generate moves on the same financial account as the invoice line
                		# and no default analytic account is defined at the tax level, propagate the
		                # analytic account from the invoice line to the tax line. This is necessary
                		# in situations were (part of) the taxes cannot be reclaimed,
		                # to ensure the tax move is allocated to the proper analytic account.
				if not val.get('account_analytic_id') and line.account_analytic_id and val['account_id'] == line.account_id.id:
					val['account_analytic_id'] = line.account_analytic_id.id

				key = (val['tax_code_id'], val['base_code_id'], val['account_id'])
				if not key in tax_grouped:
					tax_grouped[key] = val
				else:
					tax_grouped[key]['base'] += val['base']
					tax_grouped[key]['amount'] += val['amount']
					tax_grouped[key]['base_amount'] += val['base_amount']
					tax_grouped[key]['tax_amount'] += val['tax_amount']

		for t in tax_grouped.values():
			t['base'] = currency.round(t['base'])
			t['amount'] = currency.round(t['amount'])
			t['base_amount'] = currency.round(t['base_amount'])
			t['tax_amount'] = currency.round(t['tax_amount'])

		return tax_grouped

