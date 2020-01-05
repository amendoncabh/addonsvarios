from odoo import models


class Pricelist(models.Model):
    _inherit = "product.pricelist"

    def _compute_price_rule(self, products_qty_partner, date=False, uom_id=False):
        results = super(Pricelist, self)._compute_price_rule(products_qty_partner, date=False, uom_id=False)

        parameter = (
            str(self._context.get('pricelist_branch_id')),
            str(self._context.get('pricelist_branch_id')),
        )

        self._cr.execute("""
            WITH temp_pricelists (
                pricelists_id,
                is_except_branch,
                pricelists_sequence,
                pricelists_start_date,
                pricelists_end_date
            ) AS
            (
             select id as pricelists_id,
                    is_except_branch as is_except_branch,
                    sequence as pricelists_sequence,
                    start_date as pricelists_start_date,
                    end_date as pricelists_start_date
             from pricelists
             where Now() BETWEEN start_date AND end_date
                   and active is true
            ),
                
            temp_pricelists_branch_rel (
                pricelists_id,
                pos_branch_id
            ) AS
            (
             select pbpr.pricelists_id as pricelists_id,
                    pbpr.pos_branch_id as pos_branch_id
             from pos_branch_pricelists_rel pbpr
             inner join temp_pricelists tpl on pbpr.pricelists_id = tpl.pricelists_id
            )
                
            -------------------------------------------------------------------------
            -------------------------------------------------------------------------

            select distinct on (pll.product_id)
                   pll.product_id,
                   pll.price_inc_vat
            from (
                  select tpl.pricelists_id,
                         tpl.pricelists_sequence
                  from temp_pricelists tpl
                  left join temp_pricelists_branch_rel bpr on tpl.pricelists_id = bpr.pricelists_id
                  where (
                         case when bpr.pos_branch_id is not null
                              -- parameter --
                              then pos_branch_id = %s
                              else bpr.pricelists_id is null 
                         end
                        )
                        and is_except_branch is false 
                       
                  union all 
                 
                  select tpl.pricelists_id,
                         tpl.pricelists_sequence
                  from temp_pricelists tpl
                  left join (
                             select *
                             from temp_pricelists_branch_rel
                             -- parameter --
                             where pos_branch_id = %s
                            ) bpr on tpl.pricelists_id = bpr.pricelists_id
                  where (
                         case when bpr.pricelists_id is not null 
                              then false
                              else true
                         end
                        )
                        and is_except_branch is true
                 ) prl
            inner join pricelists_line pll on prl.pricelists_id = pll.pricelists_id
            order by pll.product_id,
                     prl.pricelists_sequence,
                     pll.id DESC
                """, parameter)

        pricelists_obj = self._cr.fetchall()

        for pricelist in pricelists_obj:

            try:
                product_result = results[pricelist[0]]
            except Exception:
                product_result = False

            if product_result:
                results[pricelist[0]] = (pricelist[1], results[pricelist[0]][1])

        return results
