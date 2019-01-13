# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class TechnicalServiceDevice(models.Model):
	_name = 'technical.service.device'
	_description = 'Representation of an optional device to by fixed'

	photo = fields.Binary(string="Image", attachment=True,
	    help="This field holds the image used as avatar for this contact, limited to 1024x1024px")
	name = fields.Char(string="Model", required=True)
	serial_code = fields.Char(string="Serial Code")
	company_id = fields.Many2one('res.partner', string="Company", domain="[('is_company','=',True)]")


class TechnicalServiceTeam(models.Model):
	_name = 'technical.service.team'
	_description = 'Technical Service Teams'

	name = fields.Char(string='Name', required=True)
	member_ids = fields.One2many('res.users', 'name', string="Members")
	color = fields.Integer(string="Color Index", default=0)
	request_ids = fields.One2many('technical.service.request', 'name', string="Request")


class TechnicalServiceRequest(models.Model):
	_name = 'technical.service.request'
	_description = 'Main body of a Tecnical Service Request, also used in the Kanban view.'
	_inherit = 'maintenance.request'

	customer = fields.Many2one('res.partner', string="Customer", required=True)
	address = fields.Char(string="Address", compute="_get_customer_address", store=True)
	device = fields.Many2one('technical.service.device')
	related_company_id = fields.Many2one('res.partner', string="Related Company", required=True, domain="[('is_company','=',True)]")
	custom_field1 = fields.Char(string="Custom Field - 1")
	custom_field2 = fields.Char(string="Custom Field - 2")
	technical_team = fields.Many2one('technical.service.team', string="Technical Team", required=True)


	@api.onchange('related_company_id')
	def _get_device_domain(self):
		res = {'domain': {'device': [('company_id.id', '=', self.related_company_id.id)]}}
		return res

	@api.depends('customer')
	def _get_customer_address(self):
		
		for request in self:
			if request.customer:
				customer = request.customer
				address = ''
				for elem in [customer.street, customer.zip, customer.city]:
					if elem:
						address += elem + ' '
				if customer.state_id:
					address += customer.state_id.name + ' '
				if customer.country_id:
					address += customer.country_id.name
				request.address = address

