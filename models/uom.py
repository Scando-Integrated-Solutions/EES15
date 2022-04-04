# -*- coding: utf-8 -*-

from odoo import models, fields


class UoM(models.Model):
    _inherit = "uom.uom"

    eta_code = fields.Char(string="Code", copy=False)
