from odoo import models


class ProcurementComputeAll(models.TransientModel):
    _inherit = 'procurement.order.compute.all'


    def ofm_procure_calculation(self):
        context = dict(self._context)
        context.update({
            'company_id': self.env.user.company_id,
            'branch_id': self.env.user.branch_id,
            'type_purchase_ofm': True,
            'action_return': {}
        })

        res = self.env['procurement.order'].with_context(context).ofm_suggest_fulfillment()

        # Search all confirmed stock_moves and try to assign them
        confirmed_moves = self.env['stock.move'].search([('state', '=', 'confirmed'), ('product_uom_qty', '!=', 0.0)],
                                                        limit=None, order='priority desc, date_expected asc')
        for x in xrange(0, len(confirmed_moves.ids), 100):
            # TDE CLEANME: muf muf
            self.env['stock.move'].browse(confirmed_moves.ids[x:x + 100]).action_assign()

        return res