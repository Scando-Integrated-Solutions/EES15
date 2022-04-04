# -*- coding: utf-8 -*-

import base64
import json
import logging

import requests
from odoo import models, fields, api, service, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    amount_discount = fields.Float(string="Amount Discount", compute="_compute_amount_discount", store=True,
                                   readonly=True)
    taxpayer_activity_code_id = fields.Many2one("eta.taxpayer.activity.code", string="taxpayerActivityCode")
    submissionId = fields.Char(string="submissionId", readonly=True, copy=False)
    uuid = fields.Char(string="UUID", readonly=True, copy=False)
    longId = fields.Char(string="longId", readonly=True, copy=False)
    hash_key = fields.Char(string="hashKey", readonly=True, copy=False)
    error_rejected = fields.Text(string="Error Rejected", readonly=True, copy=False)
    e_invoice_state = fields.Selection([
        ("draft", "Draft"),
        ("ready_to_sign", "Ready to Sign"),
        ("submitted", "Submitted"),
        ("valid", "Valid"),
        ("invalid", "Invalid"),
        ("rejected", "Rejected"),
        ("cancelled", "Cancelled")], default="draft", string="Document Status", required=True, readonly=True,
        copy=False, tracking=True)
    eta_document_id = fields.Many2one("ir.attachment", string="ETA Document", copy=False)
    e_invoice_version = fields.Selection(related="company_id.e_invoice_version", string="Version", store=True,
                                         readonly=True)

    @api.depends("invoice_line_ids.amount_discount")
    def _compute_amount_discount(self):
        for move in self:
            move.amount_discount = sum(line.amount_discount for line in move.invoice_line_ids)

    def _prepare_address_issuer_receiver_document(self, partner):
        # information of address for issuer and receiver of document
        vals = {
            "branch_id": partner.branch_id,
            "building_number": partner.building_number,
            "country_code": partner.country_id and partner.country_id.code or "",
            "governate_name": partner.state_id and partner.state_id.name or "",
            "city": partner.city or "",
            "street": partner.street or "",
            "zip": partner.zip or "",
            "floor": partner.floor or "",
            "room": partner.room or "",
            "landmark": partner.landmark or "",
            "additional_information": partner.additional_information or ""
        }
        return vals

    def _prepare_issuer_receiver_document(self, partner):
        # information for issuer and receiver of document
        vals = {
            "vat": partner.vat or "",
            "national_id": partner.national_id or "",
            "partner_type": partner.company_type,
            "partner_name": partner.name,
            "address_info": self._prepare_address_issuer_receiver_document(partner)
        }
        return vals

    def _prepare_tax_document(self, invoice_lines, tax, eg_currency):
        # total tax for every type of tax for all invoice lines
        amount_total = 0
        for line in invoice_lines:
            if tax.id in line.tax_ids.ids:
                price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                taxes = tax.compute_all(price, quantity=line.quantity, currency=line.currency_id,
                                        product=line.product_id, partner=line.partner_id)

                amount_tax = sum(t.get("amount", 0.0) for t in taxes.get("taxes", []))

                # convert to currency egp if currency of invoice is not egp
                if line.currency_id.id != eg_currency.id:
                    amount_tax = line.currency_id._convert(amount_tax, eg_currency, line.company_id, self.invoice_date)

                amount_total += amount_tax

        vals = {
            "eta_code": tax.eta_tax_type_code_id and tax.eta_tax_type_code_id.code or "",
            "amount_total": amount_total
        }
        return vals

    def _prepare_invoice_document(self, eg_currency):
        # information of document
        amount_untaxed = self.amount_untaxed
        amount_total = self.amount_total
        amount_discount = self.amount_discount
        invoice_lines = self.invoice_line_ids.filtered(lambda l: not l.display_type)

        # convert to currency egp if currency of invoice is not egp
        if self.currency_id.id != eg_currency.id:
            amount_untaxed = self.currency_id._convert(amount_untaxed, eg_currency, self.company_id, self.invoice_date)
            amount_total = self.currency_id._convert(amount_total, eg_currency, self.company_id, self.invoice_date)
            amount_discount = self.currency_id._convert(amount_discount, eg_currency, self.company_id,
                                                        self.invoice_date)

        # issuer is company of invoice and receiver is partner of invoice if type is out_invoice or out_refund
        # issuer is partner of invoice and receiver is company of invoice if type is in_invoice or in_refund
        if self.move_type in ["out_invoice", "out_refund"]:
            issuer_partner = self.company_id.partner_id
            receiver_partner = self.partner_id
        else:
            issuer_partner = self.partner_id
            receiver_partner = self.company_id.partner_id

        # list of uuids if invoice is credit note of customer or vendor
        list_uuid = []
        if self.move_type in ["out_refund", "in_refund"]:
            for payment in json.loads(self.invoice_payments_widget).get("content", []):
                move = self.browse(payment["move_id"])
                if move.move_type not in ["entry", "out_receipt", "in_receipt"]:
                    if not move.uuid:
                        raise UserError(_("Must be submit e-invoice %s") % move.name)

                    if move.e_invoice_state != "valid":
                        raise UserError(_("E-invoice %s must be valid") % move.name)

                    list_uuid.append(move.uuid)

        vals = {
            "issuer_partner": self._prepare_issuer_receiver_document(issuer_partner),
            "receiver_partner": self._prepare_issuer_receiver_document(receiver_partner),
            "move_type": self.move_type,
            "invoice_date": self.invoice_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "taxpayer_activity_code": self.taxpayer_activity_code_id.code,
            "name": self.name,
            "invoice_lines": [line._prepare_invoice_line_document(eg_currency) for line in invoice_lines],
            "amount_untaxed": amount_untaxed,
            "amount_total": amount_total,
            "amount_discount": amount_discount,
            "taxes": [self._prepare_tax_document(invoice_lines, tax, eg_currency) for tax in
                      invoice_lines.mapped("tax_ids")]
        }

        if list_uuid:
            vals.update({"list_uuid": list_uuid})

        return vals

    def action_send_e_invoice_v9(self):
        # send invoices for eta gov egypt as version 0.9 to submit
        invoices = []
        invoice_ids = {}
        # get currency of egp
        eg_currency = self.env.ref("base.EGP", False)

        # information of every invoice as document
        company = False
        for invoice in self.filtered(
                lambda inv: inv.move_type not in ["entry", "out_receipt", "in_receipt"] and inv.state == "posted" and
                            inv.e_invoice_state in ["draft", "invalid"]):

            if company and company.id != invoice.company_id.id:
                raise UserError(("Must be select same companies to send eta invoices"))
            else:
                company = invoice.company_id

            invoices.append(invoice._prepare_invoice_document(eg_currency))
            invoice_ids.update({invoice.name: invoice.id})

        if not invoices:
            return

        # check information api that is required
        company.check_data_api_required()

        # convert data to json
        data = json.dumps({"params": {
            "environment": company.e_invoice_environment,
            "api_id": company.e_invoice_api_id,
            "api_secret": company.e_invoice_api_secret,
            "limit_person_invoice": company.limit_person_invoice,
            "database_id": self.sudo().env['ir.config_parameter'].get_param("database.uuid"),
            "company_vat": company.vat,
            "odoo_version": service.common.exp_version()['server_serie'],
            "invoices": invoices,
            "invoice_ids": invoice_ids
        }})
        headers = {"Content-type": "application/json", "cache-control": "no-cache"}
        response = requests.request("Post", company.e_invoice_api_url + "/api/v0.9/send_invoices", data=data,
                                    headers=headers)
        response_content = json.loads(response.json()["result"])

        # response is successfully if 202 otherwise failed
        if response_content["code"] != 202:
            if response_content["error"] == "Generate_Token":
                company.test_e_invoice_connection()
                return self.action_send_e_invoice_v9()

            raise UserError("%s - %s" % (response_content["code"], response_content["error"]))

        message = ""
        for row in response_content["data"]:
            invoice = self.browse(row["invoice_id"])

            invoice.write(row["values"])

            if len(message) != 0:
                message += "\n"

            message += row["message"]

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_sign_e_invoice(self):
        # sign invoice
        if self.move_type in ["entry", "out_receipt",
                              "in_receipt"] or self.state != "posted" or self.e_invoice_state not in ["draft",
                                                                                                      "invalid"]:
            return

        # get currency of egp
        eg_currency = self.env.ref("base.EGP", False)

        company = self.company_id
        # check information api that is required
        company.check_data_api_required()

        invoice = self._prepare_invoice_document(eg_currency)

        # convert data to json
        data = json.dumps({"params": {
            "api_id": company.e_invoice_api_id,
            "api_secret": company.e_invoice_api_secret,
            "limit_person_invoice": company.limit_person_invoice,
            "database_id": self.sudo().env['ir.config_parameter'].get_param("database.uuid"),
            "company_vat": company.vat,
            "odoo_version": service.common.exp_version()['server_serie'],
            "invoice": invoice,
            "invoice_id": self.id
        }})

        headers = {"Content-type": "application/json", "cache-control": "no-cache"}
        response = requests.request("Post", company.e_invoice_api_url + "/api/sign_invoice", data=data, headers=headers)
        response_content = json.loads(response.json()["result"])

        # response is successfully if 200 otherwise failed
        if response_content["code"] != 200:
            raise UserError("%s - %s" % (response_content["code"], response_content["error"]))

        return self.write({"e_invoice_state": "ready_to_sign"})

    def action_send_e_invoice(self):
        # send invoices for eta gov egypt as version 1.0 to submit
        invoices = self.filtered(
            lambda inv: inv.move_type not in ["entry", "out_receipt", "in_receipt"] and inv.state == "posted" and
                        inv.e_invoice_state in ["ready_to_sign", "invalid"])

        if not invoices:
            return

        data_invoices = {}

        company = False
        for invoice in invoices:
            if company and company.id != invoice.company_id.id:
                raise UserError(("Must be select same companies to send eta invoices"))
            else:
                company = invoice.company_id

            data_invoices.update({invoice.name: invoice.id})

        # check information api that is required
        company.check_data_api_required()

        # convert data to json
        data = json.dumps({"params": {
            "environment": company.e_invoice_environment,
            "api_id": company.e_invoice_api_id,
            "api_secret": company.e_invoice_api_secret,
            "database_id": self.sudo().env['ir.config_parameter'].get_param("database.uuid"),
            "company_vat": company.vat,
            "odoo_version": service.common.exp_version()['server_serie'],
            "invoices": data_invoices,
            "invoice_ids": invoices.ids
        }})
        headers = {"Content-type": "application/json", "cache-control": "no-cache"}
        response = requests.request("Post", company.e_invoice_api_url + "/api/v1/send_invoices", data=data,
                                    headers=headers)
        response_content = json.loads(response.json()["result"])

        # response is successfully if 202 otherwise failed
        if response_content["code"] != 202:
            if response_content["error"] == "Generate_Token":
                company.test_e_invoice_connection()
                return self.action_send_e_invoice()

            raise UserError("%s - %s" % (response_content["code"], response_content["error"]))

        message = ""
        for row in response_content["data"]:
            invoice = self.browse(row["invoice_id"])

            invoice.write(row["values"])

            if len(message) != 0:
                message += "\n"

            message += row["message"]

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        }

    def get_state_e_invoice_document(self):
        # get state of document by get information document by uuid
        data = self.get_e_invoice_document()
        e_invoice_state_value = data.get("status", False)

        if e_invoice_state_value:
            e_invoice_state_selection = dict(self._fields["e_invoice_state"].selection)

            for item in e_invoice_state_selection.items():
                if item[1] == e_invoice_state_value:
                    e_invoice_state = item[0]
                    break

            self.write({"e_invoice_state": e_invoice_state})
        return True

    def get_e_invoice_document(self):
        # get information of document by uuid
        if not self.uuid:
            return

        company = self.company_id
        # check information api that is required
        company.check_data_api_required()

        lang = self._context.get("lang", False)
        language = self.env['res.lang']._lang_get(lang)

        # convert data to json
        data = json.dumps({"params": {
            "environment": company.e_invoice_environment,
            "api_id": company.e_invoice_api_id,
            "api_secret": company.e_invoice_api_secret,
            "database_id": self.sudo().env['ir.config_parameter'].get_param("database.uuid"),
            "company_vat": company.vat,
            "odoo_version": service.common.exp_version()['server_serie'],
            "language_code": language.url_code,
            "invoice_id": self.id,
            "e_invoice_version": self.e_invoice_version
        }})
        headers = {"Content-type": "application/json", "cache-control": "no-cache"}
        response = requests.request("GET", company.e_invoice_api_url + "/documents/%s" % self.uuid, data=data,
                                    headers=headers)

        response_content = json.loads(response.json()["result"])

        # response is successfully if 200 otherwise failed
        if response_content["code"] != 200:
            if response_content["error"] == "Generate_Token":
                company.test_e_invoice_connection()
                return self.get_e_invoice_document()

            raise UserError("%s - %s" % (response_content["code"], response_content["error"]))

        return response_content["data"]

    def print_e_invoice_document(self):
        # print pdf of document from eta gov egypt by uuid
        if not self.uuid:
            return

        company = self.company_id
        # check information api that is required
        company.check_data_api_required()

        lang = self._context.get("lang", False)
        language = self.env['res.lang']._lang_get(lang)

        data = {
            "environment": company.e_invoice_environment,
            "api_id": company.e_invoice_api_id,
            "api_secret": company.e_invoice_api_secret,
            "database_id": self.sudo().env['ir.config_parameter'].get_param("database.uuid"),
            "company_vat": company.vat,
            "odoo_version": service.common.exp_version()['server_serie'],
            "language_code": language.url_code
        }
        headers = {"Content-type": "application/x-www-form-urlencoded", "cache-control": "no-cache"}
        response = requests.request("GET", company.e_invoice_api_url + "/print_document/%s/%s" % (self.uuid, "pdf"),
                                    data=data,
                                    headers=headers)

        # response is successfully if 200 otherwise failed
        if response.status_code != 200:
            response_content = response.json()

            if response_content["error"] == "Generate_Token":
                company.test_e_invoice_connection()
                return self.print_e_invoice_document()

            raise UserError("%s - %s" % (response_content["code"], response_content["error"]))

        # create attachment to print report
        if response.headers.get('Content-Disposition'):
            data = base64.b64encode(response.content)
            if self.eta_document_id:
                self.eta_document_id.write({"datas": data})
            else:
                eta_document = self.env["ir.attachment"].create({"datas": data,
                                                                 "name": "E-invoice Document %s.pdf" % self.name,
                                                                 "res_model": "account.move",
                                                                 "res_id": self.id})
                self.write({"eta_document_id": eta_document.id})

            return {
                "type": "ir.actions.act_url",
                "name": "E-invoice Document",
                "url": "/web/content/ir.attachment/%s/datas/?download=true&filename=%s" % (
                    self.eta_document_id.id, self.eta_document_id.name),
                "target": "self"
            }

        return True

    def button_draft(self):
        for move in self.filtered(lambda inv: inv.move_type not in ["entry", "out_receipt", "in_receipt"]):
            if move.e_invoice_state not in ["draft", "invalid"]:
                if move.e_invoice_state == "ready_to_sign":
                    raise UserError(
                        _("You cannot reset to draft because invoice %s ready to sign") % move.display_name)
                else:
                    raise UserError(_("You cannot reset to draft because invoice %s already send") % move.display_name)
        return super(AccountMove, self).button_draft()


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    amount_discount = fields.Float(string="Amount Discount", compute="_compute_amount_discount", store=True,
                                   readonly=True)
    price_unit_discount = fields.Float(string="Price Unit Discount", compute="_compute_amount_discount", store=True,
                                       readonly=True)
    amount_tax = fields.Float(string="Amount Tax", compute="_compute_amount_tax", store=True,
                              readonly=True)

    @api.depends("price_unit", "discount", "quantity")
    def _compute_amount_discount(self):
        for line in self:
            line.price_unit_discount = line.discount != 0 and (line.price_unit * line.discount / 100) or 0
            line.amount_discount = line.price_unit_discount * line.quantity

    @api.depends('price_unit', 'discount', 'tax_ids', 'quantity',
                 'product_id', 'move_id.partner_id', 'move_id.currency_id')
    def _compute_amount_tax(self):
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_ids.compute_all(price, quantity=line.quantity, currency=line.currency_id,
                                             product=line.product_id, partner=line.partner_id)

            line.amount_tax = sum(t.get("amount", 0.0) for t in taxes.get("taxes", []))

    def _prepare_unit_value_document(self, eg_currency):
        """
        information of one unit (price unit, iso code of currency) and (amount , currency rate)
        if currency of invoice is not egp
        """

        vals = {}

        price_unit_eg = self.price_unit
        # convert to currency egp if currency of invoice is not egp
        if self.currency_id.id != eg_currency.id:
            price_unit_eg = self.currency_id._convert(price_unit_eg, eg_currency, self.company_id,
                                                      self.move_id.invoice_date)
            currency_rate = self.currency_id._get_conversion_rate(self.currency_id, eg_currency, self.company_id,
                                                                  self.move_id.invoice_date)
            vals.update({
                "amount": self.price_unit,
                "currency_rate": currency_rate
            })

        vals.update({
            "iso_code_currency": self.currency_id.iso_code,
            "amount_eg": price_unit_eg,
        })

        return vals

    def _prepare_item_tax_document(self, tax, eg_currency):
        # information of every tax
        if tax.amount_type == "group":
            raise UserError(_("Tax %s must be Percentage or Fixed") % tax.name)

        price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
        taxes = tax.compute_all(price, quantity=self.quantity, currency=self.currency_id,
                                product=self.product_id, partner=self.partner_id)

        amount_tax = sum(t.get("amount", 0.0) for t in taxes.get("taxes", []))

        # convert to currency egp if currency of invoice is not egp
        if self.currency_id.id != eg_currency.id:
            amount_tax = self.currency_id._convert(amount_tax, eg_currency, self.company_id, self.move_id.invoice_date)

        vals = {
            "eta_code": tax.eta_tax_type_code_id and tax.eta_tax_type_code_id.code or "",
            "amount_tax": amount_tax,
            "tax_rate": tax.amount_type != "fixed" and tax.amount or 0,
            "eta_sub_type_code": tax.eta_tax_sub_type_code_id and tax.eta_tax_sub_type_code_id.code or "",
            "taxable_fees": tax.eta_tax_type_code_id and tax.eta_tax_type_code_id.taxable_fees or False
        }

        return vals

    def _prepare_invoice_line_document(self, eg_currency):
        # information of invoice line
        total_sales = self.price_unit * self.quantity
        total = self.price_total
        net_total = self.price_total - self.amount_tax
        amount_discount = self.amount_discount

        # convert to currency egp if currency of invoice is not egp
        if self.currency_id.id != eg_currency.id:
            total_sales = self.currency_id._convert(total_sales, eg_currency, self.company_id,
                                                    self.move_id.invoice_date)
            total = self.currency_id._convert(total, eg_currency, self.company_id, self.move_id.invoice_date)
            net_total = self.currency_id._convert(net_total, eg_currency, self.company_id, self.move_id.invoice_date)
            amount_discount = self.currency_id._convert(amount_discount, eg_currency, self.company_id,
                                                        self.move_id.invoice_date)

        vals = {
            "name": self.name,
            "eta_product_code_type": self.product_id.eta_code_type,
            "eta_product_code": self.product_id.eta_code,
            "eta_uom_code": self.product_uom_id and self.product_uom_id.eta_code or "",
            "quantity": self.quantity,
            "unit_info": self._prepare_unit_value_document(eg_currency),
            "total_sales": total_sales,
            "total": total,
            "net_total": net_total,
            "discount": self.discount,
            "amount_discount": amount_discount
        }

        if self.tax_ids:
            vals.update({"taxes": [self._prepare_item_tax_document(tax, eg_currency) for tax in self.tax_ids]})

        internal_code = self.product_id.default_code
        if internal_code:
            vals.update({"internal_code": internal_code})

        return vals
