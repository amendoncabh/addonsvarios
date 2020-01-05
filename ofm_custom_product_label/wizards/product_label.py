# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import except_orm


class ProductLabel(models.TransientModel):
    _name = 'product.label.wizard'
    _description = "Product label"

    price_type = fields.Selection(
        [
            ('retail', 'Retail'),
            ('promotion', 'Promotion'),
            ('pricelists', 'Price-lists'),
        ],
        string='Price Type',
        default='retail',
        required=True,
    )

    branch_id = fields.Many2one(
        'pos.branch',
        string='Branch',
        default=lambda self: self.env.user.branch_id,
        required=True,
    )

    def check_print_label(self):
        if self.price_type == 'pricelists':
            parameter = (
                str(self.branch_id.id),
                str(self.branch_id.id),
                str(self.branch_id.id),
                str(self.branch_id.id),
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

                select pricelists.* 
                from (
                      select distinct on (pll.product_id)
                             pll.product_id,
                             coalesce(pll.price_inc_vat, 0) as price,
                             prl.pricelists_start_date,
                             prl.pricelists_end_date
                      from (
                            select tpl.pricelists_id,
                                   tpl.pricelists_sequence,
                                   tpl.pricelists_start_date,
                                   tpl.pricelists_end_date
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
                                   tpl.pricelists_sequence,
                                   tpl.pricelists_start_date,
                                   tpl.pricelists_end_date
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
                      inner join (
                                  select s_prp.*
                                  from product_product s_prp
                                  inner join (
                                              select distinct on (product_id)
                                                     product_id,
                                                     remain_product_qty
                                              from average_price
                                              -- parameter --
                                              where branch_id = %s
                                              order by product_id,
                                                       id desc
                                             ) avp on s_prp.id = avp.product_id 
                                                      and avp.remain_product_qty > 0
                                  where active is true
                                 ) prp on pll.product_id = prp.id
                      inner join (
                                  select *
                                  from product_template
                                  where type = 'product'
                                 ) ptp on prp.product_tmpl_id = ptp.id
                      order by pll.product_id,
                               prl.pricelists_sequence,
                               pll.id DESC
                     ) pricelists
                left join (                    
                           select product_id as product_id,
                                  printed_price
                           from printed_product
                           -- parameter --
                           where branch_id = %s
                                 and pricelists_start_date is not null
                                 and pricelists_end_date is not null
                          ) mpp on pricelists.product_id = mpp.product_id
                                   and pricelists.price = mpp.printed_price
                where mpp.product_id is null
                limit 2700
                            """, parameter)
        elif self.price_type in ('promotion', 'retail'):
            parameter = (
                self.price_type,
                str(self.branch_id.id),
                str(self.branch_id.id),
                str(self.branch_id.id),
                self.price_type,
                str(self.branch_id.id),
                str(self.branch_id.id),
            )

            self._cr.execute("""
                WITH temp_product_template (
                    product_id, 
                    price,
                    is_promotion,
                    product_type
                ) AS
                (
                 select prp.id as product_id,
                        -- parameter --
                        case when 'promotion' = %s
                             then price_promotion::float
                             else price_normal::float
                        end as price,
                        is_promotion as is_promotion,
                        type as product_type
                 from (
                       select *
                       from pos_config
                       -- parameter --
                       where branch_id = %s
                             and active is true
                      ) pcf
                 inner join (
                            select *
                            from pos_product_template
                            where check_active is true
                           ) ppt on pcf.pos_product_template_id = ppt.id
                 inner join pos_product_template_line ptl on ppt.id = ptl.template_id
                 inner join (
                             select s_prp.*
                             from product_product s_prp
                             inner join (
                                         select distinct on (product_id)
                                                product_id,
                                                remain_product_qty
                                         from average_price
                                         -- parameter --
                                         where branch_id = %s
                                         order by product_id,
                                                  id desc
                                        ) avp on s_prp.id = avp.product_id 
                                                 and avp.remain_product_qty > 0
                             where active is true
                            ) prp on ptl.product_id = prp.id
                 inner join product_template ptp on prp.product_tmpl_id = ptp.id
                 group by prp.id,
                          ptp.price_promotion,
                          ptp.price_normal,
                          ptp.is_promotion,
                          ptp.type
                ),
                
                temp_pricelists (
                    pricelists_id,
                    is_except_branch,
                    pricelists_sequence
                ) AS
                (
                 select id as pricelists_id,
                        is_except_branch as is_except_branch,
                        sequence as pricelists_sequence
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
                
                select mpp.product_id,
                       coalesce(mpp.price, 0) as price,
                       null as pricelists_start_date,
                       null as pricelists_end_date
                from (
                      select tpt.product_id,
                             tpt.price
                      from temp_product_template tpt
                      left join (
                                 select product_id as product_id,
                                        printed_price
                                  from printed_product
                                  -- parameter --
                                  where branch_id = %s
                                ) ptp on tpt.product_id = ptp.product_id 
                                         and tpt.price = ptp.printed_price
                      where tpt.product_type = 'product'
                            and (
                                 -- parameter --
                                 case when 'promotion' = %s
                                      then tpt.is_promotion is true
                                      else tpt.is_promotion is false
                                 end
                                )
                            and ptp.product_id is null
                     ) mpp
                left join (
                           select distinct on (pll.product_id)
                                  pll.product_id
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
                                   prl.pricelists_sequence
                         ) pricelist on mpp.product_id = pricelist.product_id
                where pricelist.product_id is null
                limit 2700
                                        """, parameter)

        product_obj = self._cr.dictfetchall()

        if not product_obj:
            raise except_orm(_('No Data.'))

        result = ", ".join(str(x['product_id']) for x in product_obj)

        printed_product_obj = self.env['printed.product']

        for product in product_obj:

            parameter_delete_product = (
                self.branch_id.id,
                product['product_id'],
            )

            self._cr.execute("""
                delete from printed_product
                where branch_id = %s
                      and product_id = %s
                            """, parameter_delete_product)

            printed_product_obj.create({
                'branch_id': self.branch_id.id,
                'product_id': product['product_id'],
                'pricelists_start_date': product['pricelists_start_date'],
                'pricelists_end_date': product['pricelists_end_date'],
                'printed_price': product['price'],
            })

        return result

    @api.multi
    def action_print_label(self, data):
        records = []
        report_name = "product.label.jasper"

        wizard = self

        # Send parameter to print
        params = {
            'product_ids': wizard.check_print_label(),
            'price_type': wizard.price_type,
            'branch_id': wizard.branch_id.id
        }
        data.update({'records': records, 'parameters': params})
        res = {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data,
        }

        return res
