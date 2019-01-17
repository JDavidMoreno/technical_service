# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools, _
from odoo.exceptions import ValidationError, RedirectWarning
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
	rate = fields.Float(string="Rate", help="Service rate per hour", required=True)


class TechnicalServiceRequest(models.Model):
	_name = 'technical.service.request'
	_description = 'Main body of a Tecnical Service Request, also used in the Kanban view.'
	_inherit = 'maintenance.request'

	def _get_our_companies(self):
		records = self.env['technical.service.request'].search([])
		companies_ids = [rec.related_company_id.id for rec in records]

		return [(6, 0, companies_ids)]

	@api.multi
	def invoice_see(self):
		_logger.info('#############')
		_logger.info(self.env.context)

		self.ensure_one

		action = self.env.ref('technical_service.invoice_see_action').read()[0]
		action['domain'] = [('id', '=', self.invoice_id.id)]
		return action


	@api.multi
	def action_view_partner_invoices(self):
	    self.ensure_one()
	    action = self.env.ref('account.action_invoice_refund_out_tree').read()[0]
	    action['domain'] = literal_eval(action['domain'])
	    action['domain'].append(('partner_id', 'child_of', self.id))
	    return action
		
	stage_name = fields.Char(related="stage_id.name", readonly=True)
	customer = fields.Many2one('res.partner', string="Customer", required=True)
	our_companies = fields.Many2many('res.partner', store=True, default=_get_our_companies)
	address = fields.Char(string="Address", compute="_get_customer_address", store=True)
	device = fields.Many2one('technical.service.device')
	related_company_id = fields.Many2one('res.partner', string="Related Company", required=True, domain="[('is_company','=',True)]")
	custom_field1 = fields.Char(string="Custom Field - 1")
	custom_field2 = fields.Char(string="Custom Field - 2")
	technical_team = fields.Many2one('technical.service.team', string="Technical Team", required=True)
	requirements = fields.Boolean(default=True)
	invoice_line_ids = fields.One2many('account.invoice.line', 'name')
	invoice_id = fields.Many2one('account.invoice', string="Invoice")
	company_id = fields.Many2one('res.company', string='Company', change_default=True,
	    required=True, readonly=True,
	    default=lambda self: self.env['res.company']._company_default_get('account.invoice'))


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


	def check_requirements(self):
		requirements = {}
		action = {
				'name': "Fill Requirements",
				'view_mode': 'form',
				'view_type': 'form',
				'res_model': 'technical.service.request.duration',
				'type': 'ir.actions.act_window',
				'target': 'new',
				}

		if self.stage_id.name == 'Time & Replacements':
			if not self.schedule_date:
				res_id = self.env['technical.service.request.duration'].create({'b_schedule_date': False})
				action.update({'res_id': res_id.id})
				return action

		if self.stage_id.name == 'Repaired':
			if not self.schedule_date:
				requirements.update({'b_schedule_date': False})
			if self.duration == 0:
				requirements.update({'b_duration': False})
			if bool(requirements):
				res_id = self.env['technical.service.request.duration'].create(requirements)
				action.update({'res_id': res_id.id})
				return action
				
		if self.stage_id.name == 'Scrap':
			if not self.schedule_date:
				requirements.update({'b_schedule_date': False})
			if self.duration == 0:
				requirements.update({'b_duration': False})
			if bool(requirements):
				res_id = self.env['technical.service.request.duration'].create(requirements)
				action.update({'res_id': res_id.id})
				return action

		if self.stage_id.name == 'Invoiced':
			if not self.schedule_date:
				requirements.update({'b_schedule_date': False})
			if self.duration == 0:
				requirements.update({'b_duration': False})
			if bool(requirements):
				res_id = self.env['technical.service.request.duration'].create(requirements)
				action.update({'res_id': res_id.id})
				return action



	@api.onchange('stage_id')
	def _check_requirements(self):

		self.requirements = True
		message = []

		if self.stage_id.name == 'Time & Replacements':
			if not self.schedule_date:
				self.requirements = False
				return {'warning': {'title': "Did you specify the Scheduled Date?",
									'message': "Please, click the 'Requirements' button to fill all the details."}}

		if self.stage_id.name == 'Repaired':
			if not self.schedule_date:
				self.requirements = False
				message.append('Scheduled Date')
				
			if self.duration == 0:
				self.requirements = False
				message.append('Duration')

			if not self.invoice_id:
				_logger.info('##########')
				_logger.info('Not Invoice')

				draft = {'partner_id': self.customer.id,
						 'state': 'draft',
						 'type': 'out_invoice',
						 'account_id': 480,
						 'currency_id': 1,
						 'company_id': self.env['res.company']._company_default_get('technical.service.request').id,
						 'journal_id': 1,
						 }
				invoice = self.env['account.invoice'].create(draft).id
				_logger.info(invoice)
				self.invoice_id = invoice

			if self.requirements == False:
				return {'warning': {'title': "Did you specify the " + (" and the ".join(message)) + "?",
									'message': "Please, click the 'Requirements' button to fill all the details."}}

		if self.stage_id.name == 'Scrap':
			if not self.schedule_date:
				self.requirements = False
				message.append('Scheduled Date')
				
			if self.duration == 0:
				self.requirements = False
				message.append('Duration')

			if self.requirements == False:
				return {'warning': {'title': "Did you specify the " + (" and the ".join(message)) + "?",
									'message': "Please, click the 'Requirements' button to fill all the details."}}

		if self.stage_id.name == 'Invoiced':
			if not self.schedule_date:
				self.requirements = False
				message.append('Scheduled Date')
				
			if self.duration == 0:
				self.requirements = False
				message.append('Duration')

			if self.requirements == False:
				return {'warning': {'title': "Did you specify the " + (" and the ".join(message)) + "?",
									'message': "Please, click the 'Requirements' button to fill all the details."}}


	# @api.multi
	# def crear_factura(self):
	# 	for linea in self.transformacion_ids:
	# 		name_group = linea.name[:linea.name.find(':')]
	# 		factura = self.env['account.invoice'].search([('partner_id', '=', 1), ('project_id', '=', self.id), ('template_create', '=', True) ,('template_name', '=', name_group)])
	# 		if not factura:
	# 			factura = self.env['account.invoice'].create({'partner_id':1, 'project_id':self.id, 'template_create':True, 'template_name':name_group})
	# 		if not self.env['account.invoice.line'].search([('name', '=', linea.name), ('template_name', '=', name_group)]):
	# 			self._crear_linea_factura(factura, linea.name, linea.id)
	
	
	# def _crear_linea_factura(self, account, name, transf_id):
	# 	vals= {
	# 		'name':name,
	# 		'price_unit':0.00,
	# 		'quantity':1,
	# 		'invoice_id':account.id,
	# 		'account_id': account.account_id.id,
	# 		'transformacion':transf_id,
	# 	}
	# 	self.env['account.invoice.line'].create(vals)
	

