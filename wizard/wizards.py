# -*- coding: utf-8 -*-

import logging
from datetime import timedelta

from odoo import models, fields, api
from odoo.exceptions import ValidationError


_logger = logging.getLogger(__name__)


# I need to update the wizard to the new duration and schedule system
class TechnicalServiceRequestDuration(models.TransientModel):
	_name = 'ts.request.duration'
	_description = "Confirm the duration of the Technical Request\
					in the case it's still 0"

	first_schedule_date = fields.Datetime(string="Scheduled Date", help="Date the maintenance team plans the maintenance.  It should not differ much from the Request Date.")
	b_first_schedule_date = fields.Boolean(default=True)
	schedule_date_ids = fields.Many2many('ts.calendar', string="New Scheduled Date")
	b_schedule_date_ids = fields.Boolean(default=True)

	@api.multi
	def confirm_duration(self):
		request = self.env['ts.request'].browse(self.env.context.get('active_id'))

		if self.b_first_schedule_date == False and self.first_schedule_date:
			values = {
					'name': self.env.context.get('name'),
					'start': self.first_schedule_date,
					'stop': self.first_schedule_date + timedelta(hours=1),
					'duration': 1,
					'technical_request_id': request.id,
					'technical_team_id': request.technical_team.id,
					}

			request.update({'first_schedule_date': self.first_schedule_date, 'schedule_date_ids': [(0, False, values)]})
			self.b_first_schedule_date = True

		if self.b_schedule_date_ids == False and self.schedule_date_ids:
			self.b_schedule_date_ids = True

		if all([self.b_first_schedule_date, self.b_schedule_date_ids]):
			request.requirements = True
		return request._check_requirements()

		
		
