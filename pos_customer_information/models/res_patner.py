# -*- coding: utf-8 -*-
from odoo import api, models
import json
import base64
import time
import logging


_logger = logging.getLogger(__name__)


def dump_to_json(values):
    return json.dumps(values).encode('utf8')


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def create_from_ui(self, partner):
        province_id = self.env.ref(partner['province_id'])
        amphur_id = self.env.ref(partner['amphur_id'])
        tambon_id = self.env.ref(partner['tambon_id'])
        zip_id = self.env.ref(partner['zip_id'])

        partner.update({
            'province_id': province_id.id,
            'amphur_id': amphur_id.id,
            'tambon_id': tambon_id.id,
            'zip_id': zip_id.id,
        })

        return super(ResPartner, self).create_from_ui(partner)

    def load_address_data(self):
        province_ids = self.env['province'].search([])
        provinces = province_ids.read(['id', 'name', 'name_eng', 'code'])
        provinces_external = province_ids._get_external_ids()

        amphur_ids = self.env['amphur'].search([])
        amphurs = amphur_ids.read(['id', 'name', 'name_eng', 'code', 'province_id'])
        amphurs_external = amphur_ids._get_external_ids()

        tambon_ids = self.env['tambon'].search([])
        tambons = tambon_ids.read(['id', 'name', 'name_eng', 'amphur_id'])
        tambons_external = tambon_ids._get_external_ids()

        postcode_ids = self.env['zip'].search([])
        postcodes = postcode_ids.read(['id', 'name', 'tambon_id'])
        postcodes_external = postcode_ids._get_external_ids()

        return provinces, provinces_external, amphurs, amphurs_external, tambons, tambons_external, postcodes, postcodes_external

    # province = {
    #     code: 81,
    #     id: 1,
    #     name: "กระบี่",
    #     name_eng: "Krabi"
    # }
    #
    # amphur = {
    #     code: "3",
    #     id: 1,
    #     province_id: 1,
    #     name: "เกาะลันตา",
    #     name_eng: "Kolanta"
    # }
    #
    # tambon = {
    #     amphur_id: 232,
    #     id: 7441,
    #     province_id: 14,
    #     name: "ฮอด",
    #     name_eng: "Hot"
    # }
    #
    # postcode = {
    #     amphur_id: 37,
    #     tambon_ids: [3190, 3191, 3192, 3193, 3194, 6530, 6531, 6532],
    #     name: "10100",
    #     province_id: 2,
    #     ids: [3231, 3232, 3233, 3234, 3235, 6605, 6606, 6607],
    #     tambon_ids_ids: {"6530": 6605, "6531": 6606, "6532": 6607, "3190": 3231, "3191": 3232, "3192": 3233,
    #                      "3193": 3234, "3194": 3235}
    # }

    @api.model
    def refresh_address_cache(self):
        start = time.time()
        provinces, provinces_external, amphurs, amphurs_external, tambons, tambons_external, \
        postcodes, postcodes_external = self.load_address_data()

        province_dict = dict()
        amphur_dict = dict()
        tambon_dict = dict()
        postcode_dict = dict()

        for province in provinces:
            province.update({
                'internal_id': province.get('id'),
                'id': int(provinces_external[province.get('id')][0].replace('base.province_', '')),
            })
            province_dict[province.get('id')] = province

        for amphur in amphurs:
            amphur.update({
                'internal_id': amphur.get('id'),
                'id': int(amphurs_external[amphur.get('id')][0].replace('base.amphur_', '')),
                'province_id': int(provinces_external[amphur.get('province_id')[0]][0].replace('base.province_', ''))
            })
            amphur_dict[amphur.get('id')] = amphur

        for tambon in tambons:
            tambon.update({
                'internal_id': tambon.get('id'),
                'id': int(tambons_external[tambon.get('id')][0].replace('base.tambon_', '')),
                'amphur_id': int(amphurs_external[tambon.get('amphur_id')[0]][0].replace('base.amphur_', '')),
            })
            tambon['province_id'] = amphur_dict[tambon.get('amphur_id')].get('province_id')
            tambon_dict[tambon.get('id')] = tambon

        for postcode in postcodes:
            postcode.update({
                'internal_id': postcode.get('id'),
                'id': int(postcodes_external[postcode.get('id')][0].replace('base.postcode_', '')),
                'tambon_id': int(tambons_external[postcode.get('tambon_id')[0]][0].replace('base.tambon_', '')),
            })
            post_name = int(postcode.get('name'))
            tambon_id = postcode.get('tambon_id')
            if post_name not in postcode_dict:
                tambon = tambon_dict[tambon_id]
                tambon_ids_ids = dict()
                tambon_ids_ids[tambon_id] = postcode.get('id')

                obj = {
                    'ids': [int(postcode.get('id'))],
                    'name': postcode.get('name'),
                    'tambon_ids': [tambon_id],
                    'tambon_ids_ids': tambon_ids_ids,
                    'province_id': tambon.get('province_id'),
                    'amphur_id': tambon.get('amphur_id'),
                }
                postcode_dict[post_name] = obj
            else:
                postcode_dict[post_name]['ids'].append(postcode.get('id'))
                postcode_dict[post_name]['tambon_ids'].append(tambon_id)
                postcode_dict[post_name]['tambon_ids_ids'][tambon_id] = int(postcode.get('id'))

        province_list = list()
        for item in sorted(province_dict.keys()):
            province_list.append(province_dict[item])

        amphur_list = list()
        for item in sorted(amphur_dict.keys()):
            amphur_list.append(amphur_dict[item])

        tambon_list = list()
        for item in sorted(tambon_dict.keys()):
            tambon_list.append(tambon_dict[item])

        postcode_list = list()
        for item in sorted(postcode_dict.keys()):
            postcode_list.append(postcode_dict[item])

        self.env.ref('base.province_json').write({
            'datas': base64.encodestring(dump_to_json(province_list)),
        })
        self.env.ref('base.amphur_json').write({
            'datas': base64.encodestring(dump_to_json(amphur_list)),
        })
        self.env.ref('base.tambon_json').write({
            'datas': base64.encodestring(dump_to_json(tambon_list)),
        })
        self.env.ref('base.postcode_json').write({
            'datas': base64.encodestring(dump_to_json(postcode_list)),
        })

        del province_dict, amphur_dict, tambon_dict, postcode_dict
        del province_list, amphur_list, tambon_list, postcode_list

        _logger.info("finish generate address cache %s", time.time() - start)

    @api.model
    def get_address_cache(self):
        datas = []
        list_name = [
            ('province','base.province_json'),
            ('amphur','base.amphur_json'),
            ('tambon','base.tambon_json'),
            ('postcode','base.postcode_json'),
        ]
        has_datas = True
        for name, name_json in list_name:
            if not self.env.ref(name_json).datas:
                has_datas = False

        if not has_datas:
            self.refresh_address_cache()

        for name, name_json in list_name:
            datas.append({
                'name': name,
                'datas': json.loads(base64.decodestring(self.env.ref(name_json).datas))
            })
        return datas
