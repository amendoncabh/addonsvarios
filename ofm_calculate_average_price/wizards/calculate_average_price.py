# -*- coding: utf-8 -*-

from odoo import api, fields, models
import datetime


class CalculateAveragePrice(models.TransientModel):
    _name = 'calculate.average.price.wizard'
    _description = "Calculate Average Price"

    branch_id = fields.Many2one(
        comodel_name="pos.branch",
        string="Branch",
        required=True,
        index=True,
        default=lambda self: self.env.user.branch_id,
    )

    month = fields.Selection(
        string="Month",
        selection=[
           ('1', 'มกราคม'),
           ('2', 'กุมภาพันธ์'),
           ('3', 'มีนาคม'),
           ('4', 'เมษายน'),
           ('5', 'พฤษภาคม'),
           ('6', 'มิถุนายน'),
           ('7', 'กรกฎาคม'),
           ('8', 'สิงหาคม'),
           ('9', 'กันยายน'),
           ('10', 'ตุลาคม'),
           ('11', 'พฤษจิกายน'),
           ('12', 'ธันวาคม'),
        ],
        required=True,
    )

    year = fields.Selection(
        string="Year",
        selection=[
            ('2014', '2014'),
            ('2015', '2015'),
            ('2016', '2016'),
            ('2017', '2017'),
            ('2018', '2018'),
            ('2019', '2019'),
            ('2020', '2020'),
            ('2021', '2021'),
            ('2022', '2022'),
            ('2023', '2023'),
            ('2024', '2024'),
            ('2025', '2025'),
            ('2026', '2026'),
            ('2027', '2027'),
            ('2028', '2028'),
            ('2029', '2029'),
            ('2030', '2030'),
            ('2031', '2031'),
            ('2032', '2032'),
            ('2033', '2033'),
            ('2034', '2034'),
            ('2035', '2035'),
            ('2036', '2036'),
            ('2037', '2037'),
            ('2038', '2038'),
        ],
        required=True,
    )

    product_id = fields.Many2one(
        comodel_name="product.product",
        string="",
        required=False,
    )

    def get_last_average_price_obj(self, product_id, branch_id, stock_location_id):
        return self.env['average.price'].search([('product_id', '=', product_id),
                                                 ('branch_id', '=', branch_id),
                                                 ('stock_location_id', '=', stock_location_id),
                                                 ], order="id desc", limit=1)

    def get_cost_product_supplierinfo(self, product_id, branch_id):
        parameter = (
            int(branch_id),
            int(product_id),
        )
        self._cr.execute("""
                    select distinct on (pd_supinfo.product_tmpl_id, branch_id)
                        pd_supinfo.id, company_id, branch_id, name, pd_supinfo.product_tmpl_id, price
                    from (
                        select id, company_id, branch_id, name, product_tmpl_id, price
                        from product_supplierinfo 
                        where branch_id = %s
                    )pd_supinfo
                    inner join (
                        select id, product_tmpl_id
                        from product_product
                        where id = %s
                    )pp on pp.product_tmpl_id = pd_supinfo.product_tmpl_id
                    order by pd_supinfo.product_tmpl_id, branch_id, pd_supinfo.id desc 
                    limit 1
                """, parameter)
        product_supplierinfo = self._cr.dictfetchall()
        price = 0
        for item in product_supplierinfo:
            price = item['price'] or 0
        return price

    def calculate_average_price(self, new_stock_move):
        move_date = '/'.join([
            str(self.year),
            str(self.month),
            '01',
        ])

        parameter_delete = (
            move_date,
            self.branch_id.id,
            int(self.product_id.id),
            int(self.product_id.id),
        )

        query_str = """
            select pbw.id as branch_id,
                   result.*
            from (
                  select pos_move.pos_id,
                     coalesce(po_move.po_id, return_po_move.po_id) as po_id,
                     so_move.so_id,
                     sa_move.sa_id,
                     coalesce(in_int_move.int_id, out_int_move.int_id) as int_id,
                     case when sa_move.move_type in ('SA', 'RT_SA')
                          then sa_move.stock_location_id 
                          when pos_move.move_type = 'POS' 
                           or return_po_move.move_type = 'RT_PO' 
                           or so_move.move_type = 'SO'
                           or out_int_move.move_type = 'OUT_INT'
                          then stm.location_id
                          else stm.location_dest_id
                     end as stock_location_id,
                     stm.picking_id,
                     stm.id as move_id,
                     stm.product_id,
                     COALESCE(pos_move.move_type, 
                          po_move.move_type, 
                          so_move.move_type,
                          return_po_move.move_type, 
                          sa_move.move_type,
                          in_int_move.move_type,
                          out_int_move.move_type
                         ) as move_type,
                     stm.date as move_date,
                     stm.product_uom as product_uom_id,
                     case when pos_move.move_type = 'POS' 
                               or return_po_move.move_type = 'RT_PO' 
                               or so_move.move_type = 'SO'
                               or sa_move.move_type =  'RT_SA'
                               or out_int_move.move_type = 'OUT_INT'
                          then product_uom_qty*-1
                          else product_uom_qty
                     end as product_uom_qty,
                     COALESCE(pos_move.price, 
                          po_move.price, 
                          so_move.price, 
                          return_po_move.price, 
                          sa_move.price,
                          in_int_move.price,
                          out_int_move.price) as price,
                     COALESCE(pos_move.priority, 
                          po_move.priority, 
                          so_move.priority, 
                          return_po_move.priority, 
                          sa_move.priority,
                          in_int_move.priority,
                          out_int_move.priority) as priority
                  from (
                    select *
                    from stock_move
                    where state = 'done'
                              and date_part('month', date + interval '7 hour') = {month}
                      and date_part('year', date + interval '7 hour') = {year}
                      and (product_id = {product_id} or coalesce({product_id}, 0) = 0)
                   ) stm
                  left join (
                         select distinct pod.id as pos_id,
                                COALESCE(aci.number, pod.inv_no) as doc_no,
                                pod.picking_id,
                                case when pod.is_return_order is true 
                                      or pod.is_void_order is true
                                 then cast('RT_POS' as varchar)
                                 else cast('POS' as varchar)
                            end as move_type,
                                pol.product_id,
                                abs(pol.qty) as join_qty,
                                pol.price_unit as price,
                                case when pod.is_return_order is true 
                                      or pod.is_void_order is true
                                 then cast(2 as int)
                                 else cast(12 as int)
                            end as priority
                         from pos_order pod
                         inner join pos_order_line pol on pod.id = pol.order_id
                         left join (
                            select * 
                                    from account_invoice
                                    where state <> 'draft'
                                   ) aci on pod.id = aci.pos_id
                        ) pos_move on stm.picking_id = pos_move.picking_id
                                  and stm.product_id = pos_move.product_id
                                  and stm.product_uom_qty = pos_move.join_qty
                  left join (
                         select puo.id as po_id,
                                puo.name as doc_no,
                                cast('PO' as varchar) as move_type,
                                pul.id as po_line_id,
                                pul.price_unit as price,
                                cast(1 as int) as priority
                         from purchase_order puo
                         inner join purchase_order_line pul on puo.id = pul.order_id
                        ) po_move on stm.purchase_line_id = po_move.po_line_id
                  left join (
                             select puo.id as po_id,
                                puo.name as doc_no,
                                cast('RT_PO' as varchar) as move_type,
                                pul.product_id,
                                pul.price_unit as price,
                                spk.id as picking_id,
                                cast(11 as int) as priority
                         from purchase_order puo
                             inner join purchase_order_line pul on puo.id = pul.order_id
                         inner join stock_picking spk on puo.group_id = spk.group_id
                         inner join (
                                     select id
                                     from stock_picking_type
                                     where code = 'outgoing'
                                    ) spt on spk.picking_type_id = spt.id
                        ) return_po_move on stm.picking_id = return_po_move.picking_id
                                        and stm.product_id = return_po_move.product_id
                  left join (
                         select sod.id as so_id,
                                sod.name as doc_no,
                                case when pmo2.code = 'incoming'
                                 then cast('RT_SO' as varchar)
                                 else cast('SO' as varchar)
                                end as move_type,
                                pmo2.procurement_order_id,
                                sol.id as po_line_id,
                                sol.price_unit as price,
                                pmo2.picking_id,
                                case when pmo2.code = 'incoming'
                                 then 3
                                 else 13
                                end as priority
                        from sale_order sod
                        inner join sale_order_line sol on sod.id = sol.order_id
                        inner join (
                                    select pmo1.id as procurement_order_id,
                                       pmo1.sale_line_id,
                                       pmo1.group_id,
                                       spt.code,
                                       spk.id as picking_id
                                    from procurement_order pmo1
                                    inner join stock_picking spk on pmo1.group_id = spk.group_id
                                    inner join stock_picking_type spt on spk.picking_type_id = spt.id
                                    where pmo1.state = 'done'
                                   ) pmo2 on sol.id = pmo2.sale_line_id
                      ) so_move on stm.procurement_id = so_move.procurement_order_id 
                                   and stm.picking_id = so_move.picking_id
                  left join (
                        select sa.*,
                            coalesce(in_lpr.product_average_price, 0) as price
                        from (
                            select in_sa.id as sa_id,
                                in_sa.branch_id,
                                in_sa_stm.id as move_id,
                                in_sa_stm.product_id,
                                case when in_sa_std.usage = 'inventory'
                                    then cast('RT_SA' as varchar)
                                    else cast('SA' as varchar)
                                end as move_type,
                                case when in_sa_std.usage = 'inventory'
                                    then 15
                                    else 5
                                end as priority,
                                case when in_sa_std.usage = 'inventory'
                                    then in_sa_stm.location_id
                                    else in_sa_stm.location_dest_id
                                end as stock_location_id
                            from (
                                select *
                                from stock_inventory
                                where state = 'done'
                                ) in_sa
                            inner join (
                                select * 
                                from stock_move
                                where state = 'done'
                                ) in_sa_stm on in_sa.id = in_sa_stm.inventory_id
                            inner join stock_location in_sa_stl on in_sa_stm.location_id = in_sa_stl.id
                            inner join stock_location in_sa_std on in_sa_stm.location_dest_id = in_sa_std.id
                            ) sa
                        left join (
                            select avp.branch_id, 
                                stock_location_id, 
                                product_id, 
                                product_average_price
                            from (
                                select max(id) as id
                                from average_price
                                group by branch_id, 
                                stock_location_id, 
                                product_id
                                ) m_avp
                            inner join average_price avp on m_avp.id = avp.id
                            ) in_lpr on sa.branch_id = in_lpr.branch_id
                        and sa.stock_location_id = in_lpr.stock_location_id
                        and sa.product_id = in_lpr.product_id
                        ) sa_move on stm.inventory_id = sa_move.sa_id and stm.id = sa_move.move_id 
                  left join (
                             select in_sim.id as int_id,
                                in_int_stm.id as stock_move_id,
                                cast('IN_INT' as varchar) as move_type,
                                in_int_stm.product_id,
                                coalesce(in_lpr.product_average_price, 0) as price,
                                4 as priority
                             from ofm_stock_internal_move in_sim
                             inner join (
                             select *
                                     from stock_picking
                                     where state = 'done'
                                    ) origin_int_spk on in_sim.picking_id = origin_int_spk.id
                             inner join (
                             select * 
                                     from stock_picking
                                     where state = 'done'
                                    ) in_int_spk on in_sim.picking_dest_id = in_int_spk.id
                             inner join (
                             select * 
                                     from stock_move
                                     where state = 'done'
                                    ) in_int_stm on in_int_spk.id = in_int_stm.picking_id
                             left join (
                            select avp.branch_id, 
                                   stock_location_id, 
                                   product_id, 
                                   product_average_price
                            from (
                                              select max(id) as id
                                  from average_price
                              group by branch_id, 
                                       stock_location_id, 
                                       product_id
                             ) m_avp
                                inner join average_price avp on m_avp.id = avp.id
                               ) in_lpr on in_sim.branch_id = in_lpr.branch_id
                                           and origin_int_spk.location_id = in_lpr.stock_location_id
                                           and in_int_stm.product_id = in_lpr.product_id
                            ) in_int_move on stm.id = in_int_move.stock_move_id
                  left join (
                             select in_sim.id as int_id,
                                in_int_stm.id as stock_move_id,
                                cast('OUT_INT' as varchar) as move_type,
                                in_int_stm.product_id,
                                0 as price,
                                14 as priority
                             from ofm_stock_internal_move in_sim
                             inner join (
                             select * 
                                     from stock_picking
                                     where state = 'done'
                                    ) in_int_spk on in_sim.picking_id = in_int_spk.id
                             inner join (
                             select * 
                                     from stock_move
                             where state = 'done'
                            ) in_int_stm on in_int_spk.id = in_int_stm.picking_id
                            ) out_int_move on stm.id = out_int_move.stock_move_id
                  left join stock_location stl on stm.location_dest_id = stl.id
                  left join stock_picking spk on stm.picking_id = spk.id
                 ) result
            inner join stock_location slw on result.stock_location_id = slw.id
            inner join stock_warehouse stw on slw.complete_name like ('%/' || stw.code || '/%')
            inner join (
                        select * 
                        from pos_branch
                        where id = {branch_id}
                       ) pbw on pbw.warehouse_id = stw.id
            order by product_id, 
                 stock_location_id, 
                 move_date, priority, 
                 product_uom_qty DESC, 
                 move_id
        """.format(
            month=self.month,
            year=self.year,
            product_id=int(self.product_id.id),
            branch_id=self.branch_id.id
        )
        # print query_str
        self._cr.execute(query_str)

        stock_move_obj = self._cr.dictfetchall()

        if len(new_stock_move) == 1:
            stock_move_obj = stock_move_obj + new_stock_move

        dict_last_average_price = {
            'stock_location_id': '',
            'product_id': '',
        }

        self._cr.execute("""
            delete from average_price
            where (move_date + interval '7 hour')::date >= %s::date
                  and branch_id = %s
                  and (product_id = %s or coalesce(%s, 0) = 0)
        """, parameter_delete)

        average_price_obj = self.env['average.price']

        last_po_price = 0
        last_remain_qty = 0

        for item in stock_move_obj:

            price = item['price']

            if dict_last_average_price['product_id'] == item['product_id'] \
                    and dict_last_average_price['branch_id'] == item['branch_id'] \
                    and dict_last_average_price['stock_location_id'] == item['stock_location_id']:

                if item['move_type'] in ('OUT_INT', 'RT_POS', 'RT_SO'):
                    price = self.get_last_average_price_obj(item['product_id'],
                                                            item['branch_id'],
                                                            item['stock_location_id']).product_average_price

                if item['product_uom_qty'] > 0:
                    # Fix Me Please check some value is False on under
                    dict_last_average_price['product_average_price'] = dict_last_average_price['product_average_price'] or 0
                    dict_last_average_price['remain_product_qty'] = dict_last_average_price['remain_product_qty'] or 0
                    item['product_uom_qty'] = item['product_uom_qty'] or 0
                    price = price or 0

                    upper = ((dict_last_average_price['remain_product_qty']
                              * dict_last_average_price['product_average_price']) + (item['product_uom_qty'] * price))
                    lower = (dict_last_average_price['remain_product_qty'] + item['product_uom_qty'])

                    if upper == 0 or lower == 0 \
                            or (lower > 0 > dict_last_average_price['remain_product_qty']):
                        product_average_price = price
                    else:
                        product_average_price = upper / lower
                else:
                    price = dict_last_average_price['product_average_price']
                    product_average_price = dict_last_average_price['product_average_price']

                remain_product_qty = dict_last_average_price['remain_product_qty'] + item['product_uom_qty']

                if item['move_type'] == 'PO':
                    last_po_price = price

                last_remain_qty = dict_last_average_price['remain_product_qty']

            else:
                last_po_price = 0
                last_remain_qty = 0

                last_average_price = self.get_last_average_price_obj(item['product_id'],
                                                                     item['branch_id'],
                                                                     item['stock_location_id'])

                if item['product_uom_qty'] > 0:
                    upper = ((last_average_price.remain_product_qty
                             * last_average_price.product_average_price) + (item['product_uom_qty'] * price))
                    lower = (last_average_price.remain_product_qty + item['product_uom_qty'])

                    if upper == 0 or lower == 0 \
                            or (lower > 0 > last_average_price.remain_product_qty):
                        product_average_price = price
                    else:
                        product_average_price = upper / lower
                else:
                    price = last_average_price.product_average_price
                    product_average_price = last_average_price.product_average_price

                remain_product_qty = last_average_price.remain_product_qty + item['product_uom_qty']

                last_remain_qty = last_average_price.remain_product_qty

            if product_average_price < 0 or (remain_product_qty < 0 > last_remain_qty):

                if last_po_price == 0:
                    last_po_average_price_obj = self.env['average.price'].search([('product_id', '=', item['product_id']),
                                                  ('branch_id', '=', item['branch_id']),
                                                  ('stock_location_id', '=', item['stock_location_id']),
                                                  ('move_type', '=', 'PO'),
                                                  ], order="id desc", limit=1)
                    if last_po_average_price_obj:
                        product_average_price = last_po_average_price_obj.product_average_price
                    else:
                        product_average_price = 0
                else:
                    product_average_price = last_po_price

            if product_average_price == 0:
                cost_price = self.get_cost_product_supplierinfo(item['product_id'], item['branch_id'])
            else:
                cost_price = product_average_price

            dict_last_average_price = {
                'branch_id': item['branch_id'],
                'pos_id': item['pos_id'],
                'po_id': item['po_id'],
                'so_id': item['so_id'],
                'sa_id': item['sa_id'],
                'int_id': item['int_id'],
                'stock_location_id': item['stock_location_id'],
                'picking_id': item['picking_id'],
                'move_id': item['move_id'],
                'move_type': item['move_type'],
                'move_date': item['move_date'],
                'product_id': item['product_id'],
                'product_uom_id': item['product_uom_id'],
                'product_uom_qty': item['product_uom_qty'],
                'move_amount': (item['product_uom_qty'] * price),
                'price': price,
                'remain_product_qty': remain_product_qty,
                'remain_product_amount': remain_product_qty * product_average_price,
                'product_average_price': product_average_price,
                'cost': cost_price,
            }

            average_price_obj.create(dict_last_average_price)

        if self.product_id:
            new_avg_price = dict_last_average_price['price'] if item['move_type'] in ('IN_INT', 'OUT_INT', 'RT_PO') \
                else dict_last_average_price['product_average_price']

            return new_avg_price
        else:
            return {
                'view_type': 'form',
                'view_mode': 'tree',
                'name': 'Average Price',
                'res_model': 'average.price',
                'type': 'ir.actions.act_window',
                'target': 'current',
            }

    def check_recalculate_average_price(self, branch_id):
        query_str = """
            select distinct on (result.product_id, pbw.branch_id)
                   pbw.id as branch_id,
                   result.product_id,
                   result.month,
                   result.year
            from (
                  select stm.product_id as product_id, 
                     cast(date_part('month', stm.date + interval '7 hour') as int) as month,
                     cast(date_part('year', stm.date + interval '7 hour') as int) as year,
                     case when sa_move.move_type in ('SA', 'RT_SA')
                          then sa_move.stock_location_id 
                          when pos_move.move_type = 'POS' 
                               or return_po_move.move_type = 'RT_PO' 
                           or so_move.move_type = 'SO'
                           or out_int_move.move_type = 'OUT_INT'
                          then stm.location_id
                          else stm.location_dest_id
                         end as stock_location_id
                  from (
                    select *
                    from stock_move
                    where state = 'done'
                   ) stm
                  left join (
                     select distinct pod.id as pos_id,
                            COALESCE(aci.number, pod.inv_no) as doc_no,
                        pod.picking_id,
                            case when pod.is_return_order is true 
                                  or pod.is_void_order is true
                                 then cast('RT_POS' as varchar)
                                 else cast('POS' as varchar)
                            end as move_type,
                            pol.product_id,
                            abs(pol.qty) as join_qty,
                            pol.price_unit as price,
                            case when pod.is_return_order is true 
                                  or pod.is_void_order is true
                                 then cast(2 as int)
                                 else cast(12 as int)
                            end as priority
                         from pos_order pod
                         inner join pos_order_line pol on pod.id = pol.order_id
                         left join (
                                    select * 
                                from account_invoice
                                where state <> 'draft'
                               ) aci on pod.id = aci.pos_id
                        ) pos_move on stm.picking_id = pos_move.picking_id
                                  and stm.product_id = pos_move.product_id
                                  and stm.product_uom_qty = pos_move.join_qty
                  left join (
                         select puo.id as po_id,
                            puo.name as doc_no,
                            cast('PO' as varchar) as move_type,
                            pul.id as po_line_id,
                            pul.price_unit as price,
                            cast(1 as int) as priority
                         from purchase_order puo
                         inner join purchase_order_line pul on puo.id = pul.order_id
                        ) po_move on stm.purchase_line_id = po_move.po_line_id
                  left join (
                         select puo.id as po_id,
                            puo.name as doc_no,
                            cast('RT_PO' as varchar) as move_type,
                            pul.product_id,
                            pul.price_unit as price,
                            spk.id as picking_id,
                            cast(11 as int) as priority
                        from purchase_order puo
                        inner join purchase_order_line pul on puo.id = pul.order_id
                        inner join stock_picking spk on puo.group_id = spk.group_id
                        inner join (
                                select id
                                from stock_picking_type
                                where code = 'outgoing'
                               ) spt on spk.picking_type_id = spt.id
                       ) return_po_move on stm.picking_id = return_po_move.picking_id
                                   and stm.product_id = return_po_move.product_id
                  left join (
                         select sod.id as so_id,
                            sod.name as doc_no,
                            case when pmo2.code = 'incoming'
                                 then cast('RT_SO' as varchar)
                                 else cast('SO' as varchar)
                            end as move_type,
                            pmo2.procurement_order_id,
                            sol.id as po_line_id,
                            sol.price_unit as price,
                            pmo2.picking_id,
                            case when pmo2.code = 'incoming'
                                 then 3
                                 else 13
                            end as priority
                        from sale_order sod
                        inner join sale_order_line sol on sod.id = sol.order_id
                        inner join (
                                select pmo1.id as procurement_order_id,
                                       pmo1.sale_line_id,
                                       pmo1.group_id,
                                       spt.code,
                                       spk.id as picking_id
                                from procurement_order pmo1
                                inner join stock_picking spk on pmo1.group_id = spk.group_id
                                inner join stock_picking_type spt on spk.picking_type_id = spt.id
                                where pmo1.state = 'done'
                               ) pmo2 on sol.id = pmo2.sale_line_id
                          ) so_move on stm.procurement_id = so_move.procurement_order_id 
                               and stm.picking_id = so_move.picking_id
                  left join (
                        select sa.*,
                            coalesce(in_lpr.product_average_price, 0) as price
                        from (
                            select in_sa.id as sa_id,
                                in_sa.branch_id,
                                in_sa_stm.product_id,
                                case when in_sa_std.usage = 'inventory'
                                    then cast('RT_SA' as varchar)
                                    else cast('SA' as varchar)
                                end as move_type,
                                case when in_sa_std.usage = 'inventory'
                                    then 15
                                    else 5
                                end as priority,
                                case when in_sa_std.usage = 'inventory'
                                    then in_sa_stm.location_id
                                    else in_sa_stm.location_dest_id
                                end as stock_location_id
                            from (
                                select *
                                from stock_inventory
                                where state = 'done'
                                ) in_sa
                            inner join (
                                select * 
                                from stock_move
                                where state = 'done'
                                ) in_sa_stm on in_sa.id = in_sa_stm.inventory_id
                            inner join stock_location in_sa_stl on in_sa_stm.location_id = in_sa_stl.id
                            inner join stock_location in_sa_std on in_sa_stm.location_dest_id = in_sa_std.id
                            ) sa
                        left join (
                            select avp.branch_id, 
                                stock_location_id, 
                                product_id, 
                                product_average_price
                            from (
                                select max(id) as id
                                from average_price
                                group by branch_id, 
                                stock_location_id, 
                                product_id
                                ) m_avp
                            inner join average_price avp on m_avp.id = avp.id
                            ) in_lpr on sa.branch_id = in_lpr.branch_id
                        and sa.stock_location_id = in_lpr.stock_location_id
                        and sa.product_id = in_lpr.product_id
                        ) sa_move on stm.inventory_id = sa_id
                  left join (
                         select in_sim.id as int_id,
                            in_int_stm.id as stock_move_id,
                            cast('IN_INT' as varchar) as move_type,
                            in_int_stm.product_id,
                            coalesce(in_lpr.product_average_price, 0) as price,
                            4 as priority
                         from ofm_stock_internal_move in_sim
                         inner join (
                                     select *
                                 from stock_picking
                                 where state = 'done'
                                ) origin_int_spk on in_sim.picking_id = origin_int_spk.id
                         inner join (
                                     select * 
                                 from stock_picking
                                 where state = 'done'
                                ) in_int_spk on in_sim.picking_dest_id = in_int_spk.id
                         inner join (
                                     select * 
                                 from stock_move
                                 where state = 'done'
                                ) in_int_stm on in_int_spk.id = in_int_stm.picking_id
                         left join (
                                    select avp.branch_id, 
                                       stock_location_id, 
                                       product_id, 
                                       product_average_price
                                    from (
                                  select max(id) as id
                                      from average_price
                                          group by branch_id, 
                                               stock_location_id, 
                                               product_id
                                         ) m_avp
                                inner join average_price avp on m_avp.id = avp.id
                                   ) in_lpr on in_sim.branch_id = in_lpr.branch_id
                                       and origin_int_spk.location_id = in_lpr.stock_location_id
                                       and in_int_stm.product_id = in_lpr.product_id
                        ) in_int_move on stm.id = in_int_move.stock_move_id
                  left join (
                         select in_sim.id as int_id,
                            in_int_stm.id as stock_move_id,
                            cast('OUT_INT' as varchar) as move_type,
                            in_int_stm.product_id,
                            0 as price,
                            14 as priority
                         from ofm_stock_internal_move in_sim
                         inner join (
                                     select * 
                                 from stock_picking
                                 where state = 'done'
                                ) in_int_spk on in_sim.picking_id = in_int_spk.id
                         inner join (
                                     select * 
                                 from stock_move
                                     where state = 'done'
                                    ) in_int_stm on in_int_spk.id = in_int_stm.picking_id
                       ) out_int_move on stm.id = out_int_move.stock_move_id
                  left join stock_location stl on stm.location_dest_id = stl.id
                  left join stock_picking spk on stm.picking_id = spk.id
                  left join average_price avp on avp.move_id = stm.id
                  where avp.move_id is null
                 ) result
            inner join stock_location slw on result.stock_location_id = slw.id
            inner join stock_warehouse stw on slw.complete_name like ('%/' || stw.code || '/%')
            inner join (
                        select * 
                        from pos_branch
                        where id = {branch_id} or coalesce({branch_id}, 0) = 0
                       ) pbw on pbw.warehouse_id = stw.id
            order by result.product_id,
                     pbw.branch_id
        """.format(
            branch_id=branch_id
        )
        # print query_str
        self._cr.execute(query_str)

        avp_product_obj = self._cr.dictfetchall()

        if not avp_product_obj:
            return False
        else:
            for item in avp_product_obj:
                new_calculate_average_price_obj = self.create({
                    'branch_id': item['branch_id'],
                    'month': str(item['month']),
                    'year': str(item['year']),
                    'product_id': item['product_id'],
                })

                new_calculate_average_price_obj.calculate_average_price([])
