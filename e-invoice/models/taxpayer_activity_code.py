# -*- coding: utf-8 -*-

from odoo import models, fields


class EtaTaxpayerActivityCode(models.Model):
    _name = "eta.taxpayer.activity.code"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "E-Invoice taxpayer Activity Code"
    _rec_name = "code"
    
    code = fields.Char(string="code", copy=False, required=True, tracking=True)
    description = fields.Char(string="Description", copy=False, tracking=True)
