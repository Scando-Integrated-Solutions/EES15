# -*- coding: utf-8 -*-

from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    branch_id = fields.Char(string="Branch ID", copy=False, tracking=True)
    building_number = fields.Char(string="Building Number", copy=False, tracking=True)
    floor = fields.Char(string="Floor", copy=False, tracking=True)
    room = fields.Char(string="Room", copy=False, tracking=True)
    landmark = fields.Char(string="Landmark", copy=False, tracking=True)
    additional_information = fields.Char(string="Additional Information", copy=False, tracking=True)
    national_id = fields.Char(string="National ID", copy=False, tracking=True)
