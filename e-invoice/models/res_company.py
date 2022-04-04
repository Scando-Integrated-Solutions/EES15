# -*- coding: utf-8 -*-

import json
import logging

import requests
from odoo import models, fields, service, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    e_invoice_environment = fields.Selection([
        ("sit", "SIT"),
        ("uat_preprod", "UAT/PreProd"),
        ("prod", "Production")], default="sit", string="Environment", copy=False)
    e_invoice_api_url = fields.Char(string="API URL", copy=False)
    e_invoice_api_id = fields.Char(string="API ID", copy=False)
    e_invoice_api_secret = fields.Char(string="API Secret", copy=False)
    e_invoice_version = fields.Selection([("0.9", "0.9"), ("1.0", "1.0")], default="0.9", string="Version", copy=False)
    limit_person_invoice = fields.Float(string="Limit Person Invoice",
                                        help="limit person invoice for national id is required")

    def check_data_api_required(self):
        # check information api that is required

        if not self.e_invoice_environment:
            raise UserError(_("Environment is required"))

        if not self.e_invoice_api_url:
            raise UserError(_("API URL is required"))

        if not self.e_invoice_api_id:
            raise UserError(_("API ID is required"))

        if not self.e_invoice_api_secret:
            raise UserError(_("API Secret is required"))

        return True

    def test_e_invoice_connection(self):
        # test information of api eta gov egypt is correct or not

        # check information api that is required
        self.check_data_api_required()

        # convert data to json
        data = json.dumps({"params": {
            "environment": self.e_invoice_environment,
            "api_url": self.e_invoice_api_url,
            "api_id": self.e_invoice_api_id,
            "api_secret": self.e_invoice_api_secret,
            "database_id": self.sudo().env['ir.config_parameter'].get_param("database.uuid"),
            "company_vat": self.vat,
            "odoo_version": service.common.exp_version()['server_serie']
        }})
        headers = {"Content-type": "application/json", "cache-control": "no-cache"}

        response = requests.request("Post", self.e_invoice_api_url + "/connect/token", data=data, headers=headers)

        response_content = json.loads(response.json()["result"])

        # response is successfully if 200 otherwise failed
        if response_content["code"] != 200:
            if response.reason == "NOT FOUND":
                raise UserError(_("URL is not found"))

            raise UserError("%s - %s" % (response_content["code"], response_content["error"]))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': response_content["message"],
                'type': 'success',
                'sticky': False,
            }
        }
