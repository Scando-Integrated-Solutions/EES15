# -*- coding: utf-8 -*-

from odoo import models


class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"

    def _prepare_default_reversal(self, move):
        vals = super(AccountMoveReversal, self)._prepare_default_reversal(move)

        vals.update({
            "taxpayer_activity_code_id": move.taxpayer_activity_code_id and move.taxpayer_activity_code_id.id or False})
        return vals
