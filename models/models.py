# -*- coding: utf-8 -*-

import logging
from datetime import timedelta

from odoo import models, fields, api, tools, _ 
from odoo.exceptions import ValidationError, RedirectWarning



_logger = logging.getLogger(__name__)


class InvoiceLineInherited(models.Model):
	_inherit = 'account.invoice.line'

	technical_request = fields.Many2one('technical.service.request', string="Technical Request", readonly=True)

class TechnicalResUsersInherited(models.Model):
	_inherit = 'res.users'

	technical_team_id = fields.Many2one('technical.service.team', string="Technical Team")

class MeetingInherited(models.Model):
	_inherit = 'calendar.event'

	technical_request_id = fields.Many2one('technical.service.request', string="Technical Request")

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
	member_ids = fields.One2many('res.users', 'technical_team_id', string="Members")
	color = fields.Integer(string="Color Index", readonly=True)
	request_ids = fields.One2many('technical.service.request', 'technical_team', string="Request")
	rate = fields.Float(string="Rate", help="Service rate per hour", required=True)

	@api.model
	def create(self, vals):
		res = super(TechnicalServiceTeam, self).create(vals)
		res['color'] = res['id']
		return res

	@api.one
	@api.constrains('rate')
	def _check_rate(self):
	    if self.rate < 1:
	        return ValidationError(_("The 'rate' for this team is too low. Consider increase it, at least at a minimum of 1."))

	@api.onchange('rate')
	def _check_rate_onchange(self):
		if self.rate >= 1 and self.rate < 6:
			return {'warning': {'title': _("The rate is still quite low"),
								'message': _("You can leave it in {} if you want. But remember this is the rate this team will invoice per hour at work.").format(str(self.rate))}}

class TechnicalServiceRequest(models.Model):
	_name = 'technical.service.request'
	_description = 'Main body of a Tecnical Service Request, also used in the Kanban view.'
	_inherit = 'maintenance.request'

	def _get_our_companies(self):
		records = self.env['technical.service.request'].search([])
		companies_ids = [rec.related_company_id.id for rec in records]

		return [(6, 0, companies_ids)]

	stage_sequence = fields.Integer(related="stage_id.sequence", readonly=True, store=True)
	partner_id = fields.Many2one('res.partner', string="Customer", required=True)
	our_companies = fields.Many2many('res.partner', store=True, default=_get_our_companies)
	address = fields.Char(string="Address", compute="_get_customer_address", store=True, help="Customer address")
	device = fields.Many2one('technical.service.device', string="Device", help="The device to be checked")
	related_company_id = fields.Many2one('res.partner', string="Related Company", required=True, domain="[('is_company','=',True)]")
	custom_field1 = fields.Char(string="Custom Field - 1")
	custom_field2 = fields.Char(string="Custom Field - 2")
	technical_team = fields.Many2one('technical.service.team', string="Technical Team", required=True)
	requirements = fields.Boolean(default=True)
	invoice_line_ids = fields.One2many('account.invoice.line', inverse_name="technical_request", string="Replacements & Resources", readonly=False, help="Here you can indicate the resources you spent in the intervention. It'll be invoiced automatically.")
	invoice_id = fields.Many2one('account.invoice', string="Invoice")
	new_schedule_date = fields.One2many('calendar.event', 'technical_request_id', string="Intervention Time", help="Every line is a technical intervention made in a day. Hours must be filled accordingly")
	first_schedule_date = fields.Datetime('Scheduled Date', help="The day you plan to visit the customer for the first time")

	@api.onchange('first_schedule_date')
	def _set_first_schedule_date(self):
		if self.first_schedule_date:
			values = {
					'name': self.name,
					'user_id': self.env.user.id,
					'start_datetime': self.first_schedule_date,
					'start': self.first_schedule_date,
					'stop_datetime': self.first_schedule_date + timedelta(hours=1),
					'stop': self.first_schedule_date + timedelta(hours=1),
					'duration': 1,
					'technical_request_id': self.id,
					}

			if len(self.new_schedule_date) == 0 and self.stage_id.sequence in (0, 1,):
				self.update({'new_schedule_date': [(0, False, values)]})

			elif self.stage_id.sequence in (0, 1,):
				self.update({'new_schedule_date': [(1, self.new_schedule_date[0].id, values)]})

	@api.onchange('technical_team')
	def _get_team_color(self):
		if self.technical_team and self.technical_team.color:
			self.color = self.technical_team.color

	@api.multi
	def invoice_see(self):
		self.ensure_one
		action = self.env.ref('technical_service.invoice_see_action').read()[0]
		action['domain'] = [('id', '=', self.invoice_id.id)]
		action['res_id'] = self.invoice_id.id
		return action

	@api.onchange('related_company_id')
	def _get_device_domain(self):
		res = {'domain': {'device': [('company_id.id', '=', self.related_company_id.id)]}}
		return res

	@api.depends('partner_id')
	def _get_customer_address(self):	
		for request in self:
			if request.partner_id:
				partner_id = request.partner_id
				address = ''
				for elem in [partner_id.street, partner_id.zip, partner_id.city]:
					if elem:
						address += elem + ' '
				if partner_id.state_id:
					address += partner_id.state_id.name + ' '
				if partner_id.country_id:
					address += partner_id.country_id.name
				request.address = address


	def check_requirements(self):
		requirements = {}
		action = {
				'name': _("Fill Requirements"),
				'view_mode': 'form',
				'view_type': 'form',
				'res_model': 'technical.service.request.duration',
				'type': 'ir.actions.act_window',
				'target': 'new',
				'context': {'name': self.name},
				}

		if self.stage_id.sequence == 1:
			if not self.first_schedule_date:
				res_id = self.env['technical.service.request.duration'].create({'b_first_schedule_date': False})
				action.update({'res_id': res_id.id})
				return action

		if self.stage_id.sequence in (2, 3, 4, 5,):
			if not self.new_schedule_date:
				res_id = self.env['technical.service.request.duration'].create({'b_new_schedule_date': False})
				action.update({'res_id': res_id.id})
				return action

	@api.onchange('stage_id', 'first_schedule_date', 'new_schedule_date')
	def _check_requirements(self):
		self.requirements = True
		message = []

		if self.stage_id.sequence in (1, 2,):
			if not self.invoice_id:
				draft = {'partner_id': self.partner_id.id,
						 'state': 'draft',
						 'type': 'out_invoice',
						 'account_id': 193,
						 'currency_id': 1,
						 'company_id': self.env['res.company']._company_default_get('technical.service.request').id,
						 'journal_id': 1,
						 }
				invoice = self.env['account.invoice'].create(draft).id
				self.invoice_id = invoice

			if not self.first_schedule_date and not self.new_schedule_date:
				self.requirements = False
				return {'warning': {'title': _("Have you scheduled your visit?"),
									'message': _("Please, click the 'Requirements' button to fill this detail.")}}

		if self.stage_id.sequence in (3, 4,):
			if not self.new_schedule_date:
				self.requirements = False
				return {'warning': {'title': _("How much time have you spent in this intervention?"),
									'message': _("Please, click the 'Requirements' button to fill all the details.")}}

		if self.stage_id.sequence == 5:
			if not self.new_schedule_date:
				self.requirements = False
				return {'warning': {'title': _("How much time have you spent in this intervention?"),
									'message': _("Please, click the 'Requirements' button to fill all the details.")}}

			if self.invoice_id.state not in ('open', 'paid',):
				raise ValidationError(_('Sorry, to mark this sertvice as Inoiced you must before create the Invoice.'))
	
	@api.multi
	def generate_invoice(self):
		duration = 0

		for line in self.new_schedule_date:
			duration += line.duration

		service =  {
					'invoice_id': self.invoice_id.id,
					'account_id': 495,
					'currency_id': 1,
					'technical_request': self.id,
					'name': _('Service Hours'),
					'quantity': duration,
					'price_unit': self.technical_team.rate,
					'invoice_line_tax_ids': [(4, 2, False)],
					}

		old_service = self.invoice_line_ids.search([('account_id', '=', 495), ('invoice_id', '=', self.invoice_id.id)])
		if len(old_service) == 0:
			self.invoice_line_ids.create(service)
		else:
			old_service.write(service)

		self.invoice_id.compute_taxes()
		self.invoice_id.action_invoice_open()
		self.stage_id = self.env['maintenance.stage'].search([('sequence','=',5)]).id
