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
from datetime import timedelta


class ReservationOrder(models.Model):
    _name = 'reservation.order'
    _rec_name = 'name'
    _description = 'Reservation Order'
    _order = "id desc"

    # region Fields
    name = fields.Char('Name', readonly=True)
    customer_id = fields.Many2one('res.partner', string='Customer')
    product_id = fields.Many2one('product.product', string='Product')
    location_id = fields.Many2one('stock.location', string='Location')
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')
    product_uom = fields.Many2one('uom.uom', string='UoM')
    reservation_qty = fields.Float(string='Reservation Quantity')
    expiration_duration = fields.Integer(string='Expiration Duration')
    expiry_date = fields.Date(string='Expiry Date')
    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled'),
    ], string='Status', required=True, readonly=True, copy=False, tracking=True,
        default='draft')
    # endregion

    # region Core Methods
    @api.model
    def create(self, vals):
        """
        This method is create for sequence wise name.
        :param vals: values
        :return:super
        """
        # res = super(ReservationOrder, self).create(vals)
        seq = self.env['ir.sequence'].next_by_code('reservation.order.sequence')
        vals['name'] = seq
        return super(ReservationOrder, self).create(vals)
    # endregion

    # region Onchange Methods
    @api.onchange('expiration_duration')
    def onchange_expiration_duration(self):
        self.ensure_one()
        if self.expiration_duration:
            delta = self.expiration_duration
            self.expiry_date = fields.Date.today() + timedelta(days=delta)
    # endregion
