# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountTax(models.Model):
    _inherit = "account.tax"

    eta_tax_type_code_id = fields.Many2one("eta.tax.type.code", string="Code", copy=False,
                                           domain=[("parent_id", "=", False)])
    eta_tax_sub_type_code_id = fields.Many2one("eta.tax.type.code", string="SubType Code", copy=False,
                                               domain="[('parent_id','!=',False),('parent_id','=',eta_tax_type_code_id)]")

    @api.onchange('eta_tax_type_code_id')
    def onchange_eta_tax_type_code(self):
        self.eta_tax_sub_type_code_id = False
