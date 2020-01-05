odoo.define('pos_customer_information.customer', function (require) {
    "use strict";
    var PosDB = require('point_of_sale.DB');
    var screens = require('point_of_sale.screens');
    var models = require('point_of_sale.models');
    var core = require('web.core');
    var Model = require('web.DataModel');
    var _t = core._t;
    var QWeb = core.qweb;

    models.load_fields('res.partner', [
        'alley', 
        'street2', 
        'moo', 
        'province_id', 
        'amphur_id', 
        'tambon_id', 
        'zip_id', 
        'ignore_repeat', 
        'main_contact_person',
        'company_id',
    ]);

    PosDB.include({
        trust_level: {
            'good': 'Good Debtor',
            'normal': 'Normal Debtor',
            'bad': 'Bad Debtor'
        },
        address_index: ['street', 'alley', 'street2', 'moo'],
        gen_partner_full_address: function(partner){
            if(!partner)
                return false

            var tambon = partner.tambon_id ? partner.tambon_id[1]:'';
            var amphur = partner.amphur_id ? partner.amphur_id[1]:'';
            var province = partner.province_id ? partner.province_id[1]:'';
            var postcode = partner.zip_id ? partner.zip_id[1]:'';

            if('กรุงเทพมหานคร'.toString().localeCompare(province.toString(), 'th') == 0){
                tambon = 'แขวง ' + tambon;
                amphur = 'เขต ' + amphur;
            }
            else{
                tambon = 'ตำบล ' + tambon;
                amphur = 'อำเภอ ' + amphur;
                province = 'จังหวัด ' + province;
            }

            var arr_address = [];
            this.address_index.forEach(function(address){
                if(partner[address])
                    arr_address.push(partner[address]);
            });
            return arr_address.join(' ') + [tambon, amphur, province, postcode].join(' ');
        },
        add_partners: function (partners) {
            var self = this;
            var updated_count = this._super(partners);
            var partner;
            if (updated_count) {
                for (var id in this.partner_by_id) {
                    partner = this.partner_by_id[id];

                    if (partner.barcode) {
                        this.partner_by_barcode[partner.barcode] = partner;
                    }

                    partner.full_address = this.gen_partner_full_address(partner);
                    if(partner.child_res_partner_ids && partner.child_res_partner_ids.length){
                        partner.child_res_partner_ids.sort((a,b)=>b.id-a.id).forEach(function(customer){
                            if(customer.type && customer.type != 'contact'){
                                customer.full_address = self.gen_partner_full_address(customer);
                                partner['full_'+ customer.type+'_address'] = customer.full_address;
                            }
                            partner[customer.type+'_address_id'] = customer.id;
                        });
                    }


                    partner.address =
                            (partner.street || '') + ', ' +
                            (partner.alley || '') + ', ' +
                            (partner.street2 || '') + ', ' +
                            (partner.moo || '') + ', ' +
                            (partner.tambon_id[1] || '') + ', ' +
                            (partner.amphur_id[1] || '') + ', ' +
                            (partner.province_id[1] || '') + ', ' +
                            (partner.zip_id[1] || '') + ' ' +
                            (partner.country_id[1] || '');
                    this.partner_search_string += this._partner_search_string(partner);
                }
            }
            return updated_count;

        }
    });

    screens.ClientListScreenWidget.include({
        province_value: '',
        amphur_value: '',
        tambon_value: '',
        postcode_value: '',
        main_contact_person_value: '',
        str_to_array(str, delimiter=','){
            str += "";
            var arr = [];
            str.split(delimiter).map(function(n){
                arr.push(Number(n));
            })
            return arr
        },
        filter_amphur: function () {
            var self = this;
            var options = "<option value=''>None</option>";
            var $select = self.$('select[name="amphur_id"]');
            var select_val = $select.val();
            $select.html(options);
            var filtered_states = _.filter(self.amphur, function (item) {
                if (self.province_value == '' || self.province_value == item.province_id) {
                    $select.append("<option value=" + item.id + ">" + item.name + "</option>");
                    return true;
                }
                return false;
            });
            $select.val(select_val);
        },
        filter_tambon: function () {
            var self = this;
            var options = "<option value=''>None</option>";
            var $select = self.$('select[name="tambon_id"]');
            var select_val = $select.val();
            $select.html(options);
            var filtered_states = _.filter(self.tambon, function (item) {
                if (self.amphur_value == '' || self.amphur_value == item.amphur_id) {
                    $select.append("<option value=" + item.id + ">" + item.name + "</option>");
                    return true;
                }
                return false;
            });
            $select.val(select_val);
        },
        filter_postcode: function () {
            var self = this;
            var options = "<option value=''>None</option>";
            var $select = self.$('select[name="zip_id"]');
            var select_val = $select.val();
            $select.html(options);
            var filtered_states = _.filter(self.postcode, function (item) {
                if (self.tambon_value == '' || item.tambon_ids.includes(parseInt(self.tambon_value))) {
                    $select.append("<option value=" + item.name + ">" + item.name + "</option>");
                    return true;
                }
                return false;
            });
            $select.val(select_val);
        },
        display_client_details: function (visibility, partner, clickpos) {
            var self = this;
            var contents = this.$('.client-details-contents');

            this._super(visibility, partner, clickpos);

            if (visibility === 'edit') {

                contents.off('change', 'select[name="province_id"]');
                contents.off('change', 'select[name="amphur_id"]');
                contents.off('change', 'select[name="tambon_id"]');
                contents.off('change', 'select[name="postcode_id"]');

                //event allow number
                contents.off('keypress', '.only_number');
                contents.on('keypress', '.only_number',function(event){
                    self.allow_number(event);
                });

                if(_.isObject(partner.province_id)){
                    var province = self.get_province_by_name([partner.province_id[1]]).id;
                    if(province){
                        self.province_value = province;
                        contents.find('select[name="[province_id"]').val(province);
                        this.filter_amphur();
                    }
                }
                if(_.isObject(partner.amphur_id)){
                    var amphur = self.get_amphur_by_name([partner.amphur_id[1]]).id;
                    if(amphur){
                        self.amphur_value = amphur;
                        contents.find('select[name="amphur_id"]').val(amphur);
                        this.filter_tambon();
                    }
                }
                if(_.isObject(partner.tambon_id)){
                    var tambon = self.get_tambon_by_name([partner.tambon_id[1]]).id;
                    if(tambon){
                        self.tambon_value = tambon;
                        contents.find('select[name="tambon_id"]').val(tambon);
                        this.filter_postcode();
                        if(_.isString(partner.zip) && partner.zip != ''){
                            self.postcode_value = partner.zip;
                            contents.find('select[name="zip_id"]').val(partner.zip);
                        }
                    }
                }

                contents.on('change', 'select[name="province_id"]', function (event) {
                    self.province_value = $(this).val();
                    if(self.province_value != ''){
                        self.filter_amphur();
                    }
                    contents.find('select[name="amphur_id"]').val('');
                    contents.find('select[name="tambon_id"]').val('');
                    contents.find('select[name="zip_id"]').val('');
                });
                contents.on('change', 'select[name="amphur_id"]', function (event) {
                    self.amphur_value = $(this).val();
                    if(self.amphur_value != ''){
                        self.filter_tambon();
                    }
                    contents.find('select[name="tambon_id"]').val('');
                    contents.find('select[name="zip_id"]').val('');
                });
                contents.on('change', 'select[name="tambon_id"]', function (event) {
                    self.tambon_value = $(this).val();
                    if(self.tambon_value != ''){
                        self.filter_postcode();
                    }
                     contents.find('select[name="zip_id"]').val('');
                });
                contents.on('change', 'select[name="zip_id"]', function(event) {
                    self.postcode_value = $(this).val();
                });
                
                contents.on('change', 'select[name="main_contact_person"]', function(event) {
                    self.main_contact_person_value = $(this).val();
                });

            }
        },

        save_client_details: function (partner) {
            var self = this;

            var fields = {};
            this.$('.client-details-contents .detail').each(function (idx, el) {
                fields[el.name] = el.value;
            });

            if (!fields.name) {
                this.gui.show_popup('alert',{
                    'title': 'Alert',
                    'body':  _t('A Customer Name Is Required')
                });
                return;
            }

            if(!fields.vat){
                this.gui.show_popup('alert',{
                    'title': 'Alert',
                    'body':  _t('A Tax ID Is Required')
                });
                return;
            }

            if(fields.vat.length != 13){
                this.gui.show_popup('alert',{
                    'title': 'Alert',
                    'body':  _t('A Tax ID Is Required 13 digits')
                });
                return;
            }

            if(fields.company_type == 'company' && !fields.shop_id){
                this.gui.show_popup('alert',{
                    'title': 'Alert',
                    'body':  _t('A Shop ID Is Required')
                });
                return;
            }

            if(fields['province_id'] == ''){
                this.gui.show_popup('alert',{
                    'title': 'Alert',
                    'body':  _t('A Province Is Required')
                });
                return;
            }
            else{
               fields['province_id'] = 'base.province_' + fields['province_id'];
            }


            if(fields['amphur_id'] == ''){
                this.gui.show_popup('alert',{
                    'title': 'Alert',
                    'body':  _t('A Amphur Is Required')
                });
                return;
            }
            else{
               fields['amphur_id'] = 'base.amphur_' + fields['amphur_id'];
            }


            if(fields['tambon_id'] == ''){
                this.gui.show_popup('alert',{
                    'title': 'Alert',
                    'body':  _t('A Tambon Is Required')
                });
                return;
            }
            else{

                if(fields['zip_id'] == ''){
                    this.gui.show_popup('alert',{
                        'title': 'Alert',
                        'body':  _t('A Post Code Is Required')
                    });
                    return;
                }
                else{
                    fields['zip_id'] = 'base.postcode_' + this.postcode_by_name[fields['zip_id']].tambon_ids_ids[fields['tambon_id']];
                }
                fields['tambon_id'] = 'base.tambon_' + fields['tambon_id'];
            }

            if(fields.company_type == 'person' && this.check_vat_repeat(partner, fields.vat)){
                this.gui.show_popup('alert',{
                    'title': 'Alert',
                    'body':  _t('Individual Tax ID Can\'t Repeat')
                });
                return;
            }

            if(fields['main_contact_person'] == ''){
                this.gui.show_popup('alert',{
                    'title': 'Alert',
                    'body':  _t('A Main Contact Person Is Required')
                });
                return;
            }

            if (this.uploaded_picture) {
                fields.image = this.uploaded_picture;
            }

            fields.id = partner.id || false;
            fields.country_id = fields.country_id || false;
            fields.barcode = fields.barcode || '';
            fields.company_id = self.pos.company.id;
            fields.ignore_repeat = partner.ignore_repeat || true;

            if(fields.id == false){
                fields.branch_id = self.pos.config.branch_id[0];
            }

            function nl2br(str, is_xhtml) {
                var breakTag = (is_xhtml || typeof is_xhtml === 'undefined') ? '<br />' : '<br>';
                return (str + '').replace(/([^>\r\n]?)(\r\n|\n\r|\r|\n)/g, '$1' + breakTag + '$2');
            }

            self.chrome.loading_show();
            self.chrome.loading_message('กรุณารอสักครู่ ระบบกำลังบันทึกข้อมูล', 0.5);
            new Model('res.partner').call('create_from_ui', [fields]).then(function (partner_id) {
                self.saved_client_details(partner_id);
                self.chrome.loading_hide();
            }, function (err, event) {
                event.preventDefault();
                self.chrome.loading_hide();
                if (err.code == 200) {
                    self.gui.show_popup('error', {
                        'title': _t('Error: Could not Save Changes'),
                        'body': nl2br(_t(err.data.message)),
                    });
                } else {
                    self.gui.show_popup('error', {
                        'title': _t('Error: Could not Save Changes'),
                        'body': _t('Your Internet connection is probably down.'),
                    });
                }
            });
        },

        check_vat_repeat: function (partner, vat){
            return !!_.find(this.pos.db.partner_by_id, function(data){
                if (_.isEqual(data.vat, vat) ) {
                    return !_.isEqual(data.id, partner.id)
                }
            });
        },

        render_list: function(partners){
            var filtered_partners = _.filter(partners, function(partner){
                if (partner.company_id[0] === posmodel.company.id){
                    return true;
                }
            });
            this._super(filtered_partners);
        },

    });
});