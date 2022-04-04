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


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # region Fields
    is_allowed_product_reservation_limit = fields.Boolean(default=False, string='Product Reservation Limit')
    product_reservation_limit = fields.Integer('Reservation Limit')
    # endregion

