# -*- coding: utf-8 -*-

from odoo import models, fields, api


class EtaTaxTypeCode(models.Model):
    _name = "eta.tax.type.code"
    _description = "E-Invoice Tax Type Codes"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _parent_store = True
    _rec_name = "complete_name"

    code = fields.Char(string="code", copy=False, required=True, tracking=True)
    name = fields.Char("Name", index=True, translate=True, copy=False)
    complete_name = fields.Char("Complete Name", compute="_compute_complete_name", store=True)
    parent_id = fields.Many2one("eta.tax.type.code", "Parent Type", index=True, ondelete="cascade", tracking=True)
    child_id = fields.One2many("eta.tax.type.code", "parent_id", "Child Types")
    parent_path = fields.Char(index=True)
    taxable_fees = fields.Boolean(string="Taxable Fees", copy=False)

    @api.depends("code", "parent_id.complete_name")
    def _compute_complete_name(self):
        for tax_type_code in self:
            if tax_type_code.parent_id:
                tax_type_code.complete_name = "%s / %s" % (tax_type_code.parent_id.complete_name, tax_type_code.code)
            else:
                tax_type_code.complete_name = tax_type_code.code
