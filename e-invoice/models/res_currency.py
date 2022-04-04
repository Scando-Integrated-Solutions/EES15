# -*- coding: utf-8 -*-

from odoo import models, fields


class ResCurrency(models.Model):
    _inherit = "res.currency"

    iso_code = fields.Char(string="ISO Code", copy=False)
