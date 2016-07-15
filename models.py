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
