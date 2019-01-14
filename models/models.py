# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools
import logging

_logger = logging.getLogger(__name__)


class TechnicalServiceDeviceCategory(models.Model):
	_name = 'technical.service.device.category'
	_description = 'Categories for Devices'

	name = fields.Char(string="Category", required=True)
	description = fields.Text(string="Description")
	device_ids = fields.One2many('technical.service.device', 'category_id', string="Devices")


class TechnicalServiceDevice(models.Model):
	_name = 'technical.service.device'
	_description = 'Representation of an optional device to by fixed'

	photo = fields.Binary(string="Image", attachment=True,
	    help="This field holds the image used as avatar for this contact, limited to 1024x1024px")
	image_small = fields.Binary(string="Small-sized image", compute="_get_images", store=True)
	image_medium = fields.Binary(string="Medium-sized image", compute="_get_images", store=True)
	name = fields.Char(string="Model", required=True)
	serial_code = fields.Char(string="Serial Code")
	company_id = fields.Many2one('res.partner', string="Company", domain="[('is_company','=',True)]")
	category_id = fields.Many2one('technical.service.device.category', string="Category")
	notes = fields.Text(string="Notes")

	@api.one
	@api.depends('photo')
	def _get_images(self):
		resized_images = tools.image_get_resized_images(self.photo, avoid_resize_medium=True)
		self.image_small = resized_images['image_small']
		self.image_medium = resized_images['image_medium']


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

	def _get_our_companies(self):
		records = self.env['technical.service.request'].search([])
		companies_ids = [rec.related_company_id.id for rec in records]

		return [(6, 0, companies_ids)]
		


	customer = fields.Many2one('res.partner', string="Customer", required=True)
	our_companies = fields.Many2many('res.partner', store=True, default=_get_our_companies)
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

