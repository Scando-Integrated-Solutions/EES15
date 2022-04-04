# -*- coding: utf-8 -*-

##############################################################################
#
#
#    Copyright (C) 2019-TODAY .
#    Author: Scando Integrated Solutions (<www.scando.solutions>)
#
#    It is forbidden to publish, distribute, sublicense, or sell copies
#    of the Software or modified copies of the Software.
#
##############################################################################

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, date


class StockLocation(models.Model):
    _inherit = 'stock.location'

    # region Fields
    is_reservation_location = fields.Boolean(default=False, string='Is Reservation Location')
    # endregion

