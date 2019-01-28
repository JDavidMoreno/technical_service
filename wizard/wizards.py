# -*- coding: utf-8 -*-

import logging
from datetime import timedelta

from odoo import models, fields, api
from odoo.exceptions import ValidationError


_logger = logging.getLogger(__name__)


# I need to update the wizard to the new duration and schedule system
class TechnicalServiceRequestDuration(models.TransientModel):
	_name = 'technical.service.request.duration'
	_description = "Confirm the duration of the Technical Request\
					in the case it's still 0"

	first_schedule_date = fields.Datetime(string="Scheduled Date", help="Date the maintenance team plans the maintenance.  It should not differ much from the Request Date.")
	b_first_schedule_date = fields.Boolean(default=True)
	new_schedule_date = fields.Many2many('calendar.event', string="New Scheduled Date")
	b_new_schedule_date = fields.Boolean(default=True)

	@api.multi
	def confirm_duration(self):
		request = self.env['technical.service.request'].browse(self.env.context.get('active_id'))

		if self.b_first_schedule_date == False and self.first_schedule_date:
			values = {
					'name': self.env.context.get('name'),
					'user_id': self.env.user.id,
					'start_datetime': self.first_schedule_date,
					'start': self.first_schedule_date,
					'stop_datetime': self.first_schedule_date + timedelta(hours=1),
					'stop': self.first_schedule_date + timedelta(hours=1),
					'duration': 1,
					'technical_request_id': request.id,
					}

			request.update({'first_schedule_date': self.first_schedule_date, 'new_schedule_date': [(0, False, values)]})
			self.b_first_schedule_date = True

		if self.b_new_schedule_date == False and self.new_schedule_date:
			self.b_new_schedule_date = True

		if all([self.b_first_schedule_date, self.b_new_schedule_date]):
			request.requirements = True
		return request._check_requirements()

		
		
