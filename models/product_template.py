# -*- coding: utf-8 -*-

from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = "product.template"

    eta_code = fields.Char(string="Code", tracking=True, copy=False)
    eta_code_type = fields.Selection([("GS1", "GS1"), ("EGS", "EGS")], default="GS1", string="Code Type", copy=False,
                                     tracking=True)
