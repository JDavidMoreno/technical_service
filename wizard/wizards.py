# -*- coding: utf-8 -*-

import logging

from odoo import models, fields, api
from odoo.exceptions import ValidationError


_logger = logging.getLogger(__name__)


class TechnicalServiceRequestDuration(models.TransientModel):
	_name = 'technical.service.request.duration'
	_description = "Confirm the duration of the Technical Request\
					in the case it's still 0"

	duration = fields.Float(string="Duration", help="Duration in minutes and seconds.")
	b_duration = fields.Boolean(default=True)
	schedule_date = fields.Datetime(string="Scheduled Date", help="Date the maintenance team plans the maintenance.  It should not differ much from the Request Date.")
	b_schedule_date = fields.Boolean(default=True)

	@api.multi
	def confirm_duration(self):
		request = self.env['technical.service.request'].browse(self.env.context.get('active_id'))

		if not self.b_duration and self.duration != 0:
			request.duration = self.duration
			self.b_duration = True

		if not self.b_schedule_date and self.schedule_date:
			request.schedule_date = self.schedule_date
			self.b_schedule_date = True

		if all([self.b_duration, self.schedule_date]):
			request.requirements = True
			
		else:
			return request._check_requirements()

		
		
