# -*- coding: utf-8 -*-

import logging
from datetime import timedelta

from odoo import models, fields, api, tools, _ , SUPERUSER_ID
from odoo.exceptions import ValidationError, RedirectWarning



_logger = logging.getLogger(__name__)


class InvoiceLineInherited(models.Model):
	_inherit = 'account.invoice.line'

	technical_request = fields.Many2one('ts.request', string="Technical Request", readonly=True)

class TechnicalResUsersInherited(models.Model):
	_inherit = 'res.users'

	technical_team_id = fields.Many2one('ts.team', string="Technical Team")

class TechnicalServiceCalendar(models.Model):
	_name = 'ts.calendar'
	_description = 'Calendar dedicated exclusively to technical requests'

	name = fields.Char('Request')
	start = fields.Datetime('Start Date')
	stop = fields.Datetime('End Date', compute="_get_stop_date", readonly=True, store=True)
	duration = fields.Float('Duration')
	technical_team_id = fields.Many2one('ts.team', string="Technical Team", ondelete="cascade")
	technical_request_id = fields.Many2one('ts.request', string="Technical Request", ondelete="cascade")

	@api.depends('stop', 'duration', 'start')
	def _get_stop_date(self):
		for visit in self:
			if visit.start and visit.duration:
				visit.stop = visit.start + timedelta(hours=visit.duration)

class TechnicalServiceDeviceCategory(models.Model):
	_name = 'ts.device.category'
	_description = 'Categories for Devices'

	name = fields.Char(string="Category", required=True)
	description = fields.Text(string="Description")
	device_ids = fields.One2many('ts.device', 'category_id', string="Devices")

class TechnicalServiceDevice(models.Model):
	_name = 'ts.device'
	_description = 'Representation of an optional device to by fixed'

	photo = fields.Binary(string="Image", attachment=True,
	    help="This field holds the image used as avatar for this contact, limited to 1024x1024px")
	image_small = fields.Binary(string="Small-sized image", compute="_get_images", store=True)
	image_medium = fields.Binary(string="Medium-sized image", compute="_get_images", store=True)
	name = fields.Char(string="Model", required=True)
	serial_code = fields.Char(string="Serial Code")
	company_id = fields.Many2one('res.partner', string="Company", domain="[('is_company','=',True)]", ondelete="cascade")
	category_id = fields.Many2one('ts.device.category', string="Category")
	notes = fields.Text(string="Notes")

	@api.one
	@api.depends('photo')
	def _get_images(self):
		resized_images = tools.image_get_resized_images(self.photo, avoid_resize_medium=True)
		self.image_small = resized_images['image_small']
		self.image_medium = resized_images['image_medium']


class TechnicalServiceTeam(models.Model):
	_name = 'ts.team'
	_description = 'Technical Service Teams'

	name = fields.Char(string='Name', required=True)
	member_ids = fields.One2many('res.users', 'technical_team_id', string="Members")
	color = fields.Selection([(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'), (8, '8'), (9, '9'), (10, '10'), (11, '11'), (12, '12')], string="Color Index", readonly=True)
	request_ids = fields.One2many('ts.request', 'technical_team', string="Request")
	events_ids = fields.One2many('ts.calendar', 'technical_team_id', string="Interventions")
	rate = fields.Float(string="Rate", help="Service rate per hour", required=True)

	@api.model
	def create(self, vals):
		if not self.color:
			res = super(TechnicalServiceTeam, self).create(vals)
			res['color'] = res['id']
			return res
		else:
			return super(TechnicalServiceTeam, self).create(vals)

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

class TechnicalServiceState(models.Model):
    _name = 'ts.request.state'
    _description = 'Technical Service States'

    name = fields.Char('Name', required=True, translate=True)
    sequence = fields.Integer('Sequence', default=20)
    fold = fields.Boolean('Folded in Technical Service Pipe')
    done = fields.Boolean('Request Done')

class TechnicalServiceRequest(models.Model):
	_name = 'ts.request'
	_inherit = ['mail.thread']
	_description = 'Main body of a Tecnical Service Request, also used in the Kanban view.'

	def _get_comp_clients(self):
		records = self.env['ts.request'].search([])
		companies_ids = [rec.company_id.id for rec in records]

		return [(6, 0, companies_ids)]

	@api.multi
	def _track_subtype(self, init_values):
	    self.ensure_one()
	    if 'state' in init_values and self.state.sequence == 0:
	        return 'technical_service.ts_req_created'
	    elif 'state' in init_values and self.state.sequence > 1:
	        return 'technical_service.ts_req_status'
	    return super(TechnicalServiceRequest, self)._track_subtype(init_values)

	name = fields.Char('Subject', required=True)
	archive = fields.Boolean(default=False,  help="Set archive to true to hide the technical request without deleting it.")
	color = fields.Integer('Color')
	state = fields.Many2one('ts.request.state', ondelete="restrict", string="Stage", copy=False, default=lambda r: r.env['ts.request.state'].search([('sequence','=', 0)])[0], track_visibility="onchange", group_expand='_read_group_stage_ids')
	state_sequence = fields.Integer(related="state.sequence", string="State Sequence", store=True)
	requested_by = fields.Many2one('res.users', 'Created by User', default=lambda r: r.env.uid)
	request_date = fields.Date('Request Date', default=fields.Date.context_today)
	close_date = fields.Datetime('Close Date', help="The intervention has finished")
	priority = fields.Selection([('0', 'Very Low'), ('1', 'Low'), ('2', 'Normal'), ('3', 'High')], string="Priority")
	kanban_state = fields.Selection([('normal', 'In Progress'), ('blocked', 'Blocked'), ('done', 'Ready for next stage')], string='Kanban State', required=True, default='normal')
	partner_id = fields.Many2one('res.partner', string="Customer", required=True)
	companies_clients = fields.Many2many('res.partner', store=True, default=_get_comp_clients)
	address = fields.Char(string="Address", compute="_get_customer_address", store=True, help="Customer address")
	device = fields.Many2one('ts.device', string="Device", help="The device to be checked")
	company_id = fields.Many2one('res.partner', string="Company", required=True, domain="[('is_company','=',True)]")
	custom_field1 = fields.Char(string="Custom Field - 1")
	custom_field2 = fields.Char(string="Custom Field - 2")
	user_id = fields.Many2one('res.partner', string="Responsible")
	technical_team = fields.Many2one('ts.team', string="Technical Team", required=True)
	first_schedule_date = fields.Datetime('Scheduled Date', help="The day you plan to visit the customer for the first time")
	schedule_date_ids = fields.One2many('ts.calendar', 'technical_request_id', string="Intervention Time", help="Every line is a technical intervention made in a day. Hours must be filled accordingly")
	invoice_line_ids = fields.One2many('account.invoice.line', inverse_name="technical_request", string="Replacements & Resources", readonly=False, help="Here you can indicate the resources you spent in the intervention. It'll be invoiced automatically.")
	invoice_id = fields.Many2one('account.invoice', string="Invoice", ondelete="cascade")
	requirements = fields.Boolean(default=True)
	description = fields.Text('Description')

	@api.multi
	def archive_equipment_request(self):
	    self.write({'archive': True})

	@api.multi
	def reset_equipment_request(self):
	    self.write({'archive': False, 'state': 0})

	@api.multi
	def write(self, vals):
	    if vals and 'kanban_state' not in vals and 'state' in vals:
	        vals['kanban_state'] = 'normal'
	    res = super(TechnicalServiceRequest, self).write(vals)
	    if 'state' in vals:
	        self.filtered(lambda m: m.state.sequence == 3).write({'close_date': fields.Date.today()})
	    return res


	@api.onchange('first_schedule_date')
	def _set_first_schedule_date(self):
		if self.first_schedule_date:
			values = {
					'name': self.name,
					'start': self.first_schedule_date,
					'stop': self.first_schedule_date + timedelta(hours=1),
					'duration': 1,
					'technical_team_id': self.technical_team.id,
					'technical_request_id': self.id,
					}

			if len(self.schedule_date_ids) == 0 and self.state.sequence in (0, 1,):
				self.update({'schedule_date_ids': [(0, False, values)]})

			elif self.state.sequence in (0, 1,):
				self.update({'schedule_date_ids': [(1, self.schedule_date_ids[0].id, values)]})

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

	@api.onchange('company_id')
	def _get_device_domain(self):
		res = {'domain': {'device': [('company_id.id', '=', self.company_id.id)]}}
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
				'res_model': 'ts.request.duration',
				'type': 'ir.actions.act_window',
				'target': 'new',
				'context': {'name': self.name, 'technical_team_id': self.technical_team.id},
				}			

		if self.state.sequence == 1:
			if not self.first_schedule_date:
				res_id = self.env['ts.request.duration'].create({'b_first_schedule_date': False})
				action.update({'res_id': res_id.id})
				return action

		if self.state.sequence in (2, 3, 4, 5,):
			if not self.schedule_date_ids:
				res_id = self.env['ts.request.duration'].create({'b_schedule_date_ids': False})
				action.update({'res_id': res_id.id})
				return action

	@api.onchange('state', 'first_schedule_date', 'schedule_date_ids')
	def _check_requirements(self):
		self.requirements = True

		if self.state.sequence in (1,):
			if not self.first_schedule_date and not self.schedule_date_ids:
				self.requirements = False
				return {'warning': {'title': _("Have you scheduled your visit?"),
									'message': _("Please, click the 'Requirements' button to fill this detail.")}}

		if self.state.sequence in (2, 3,):
			if not self.invoice_id:
				draft = {'partner_id': self.partner_id.id,
						 'state': 'draft',
						 'type': 'out_invoice',
						 'account_id': 193,
						 'currency_id': 1,
						 'company_id': self.env['res.company']._company_default_get('ts.request').id,
						 'journal_id': 1,
						 }
				invoice = self.env['account.invoice'].create(draft).id
				self.invoice_id = invoice

			if not self.schedule_date_ids:
				self.requirements = False
				return {'warning': {'title': _("How much time have you spent in this intervention?"),
									'message': _("Please, click the 'Requirements' button to fill all the details.")}}

		if self.state.sequence == 5:
			if not self.schedule_date_ids:
				self.requirements = False
				return {'warning': {'title': _("How much time have you spent in this intervention?"),
									'message': _("Please, click the 'Requirements' button to fill all the details.")}}

			if self.invoice_id.state not in ('open', 'paid',):
				raise ValidationError(_('Sorry, to mark this service as Inoiced you must before create the Invoice.'))
	
	@api.multi
	def generate_invoice(self):
		duration = 0

		for line in self.schedule_date_ids:
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
		self.state = self.env['ts.request.state'].search([('sequence', '=', 5)])[0].id

	@api.model
	def _read_group_stage_ids(self, stages, domain, order):
	    """ Read group customization in order to display all the stages in the
	        kanban view, even if they are empty
	    """
	    stage_ids = stages._search([], order=order, access_rights_uid=SUPERUSER_ID)
	    return stages.browse(stage_ids)
