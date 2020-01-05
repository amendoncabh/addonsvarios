odoo.define('ofm_the_one_card.the_one_card', function (require) {
    "use strict";

    var PosBaseWidget = require('point_of_sale.BaseWidget');
    var models = require('point_of_sale.models');
    var PosDB = require('point_of_sale.DB');

    var gui = require('point_of_sale.gui');
    var screens = require('point_of_sale.screens');
    var core = require('web.core');
    var popups = require('point_of_sale.popups');
    var QWeb = core.qweb;
    var _t = core._t;
    var Model = require('web.DataModel');


    var OrdersScreenWidget = require('pos_orders.pos_orders');
    var OrderReturnPopup = require('pos_order_return.pos_order_return').OrderReturnPopup;


    OrderReturnPopup.include({
        create_return_order: function(return_dict, return_reason_id, amount_tender){
            var self = this;
            var refund_order = self._super(return_dict, return_reason_id, amount_tender);

			var order = self.options.order;
            var old_order = self.pos.db.order_by_id[order.id];

            refund_order.pos_offline = old_order.pos_offline;
            refund_order.t1c_set = old_order.t1c_set;
            refund_order.membercard = {
                the_one_card_no: old_order.the_one_card_no,
                phone: old_order.phone_number,
            };
            if(refund_order.pos_offline === false){
                refund_order.membercard.expire_this_year = old_order.points_expiry_this_year;
                refund_order.membercard.balance_points = old_order.points_balance;
                refund_order.membercard.member_name = old_order.member_name;
            }

            return refund_order;
        },
    });

    var CardOfflinePopupWidget = popups.extend({
        template: 'CardOfflinePopupWidget',

        init: function(parent, options) {
			this._super(parent, options);
		},
        renderElement: function(){
            var self = this;
            this._super();
            var t1c_content = this.$el;
            var t1c_no = this.$('#t1c_no_offline_input');


            if(t1c_no.val() == ''){
                this.$('.button.t1c_offline.confirm').prop('disabled', true);
                this.$('.button.t1c_offline.confirm').css('opacity', '0.4')
            }

            t1c_no.on('keydown keyup keypress', function(event){
                //console.log('test')
                if(this.value === ''){
                    $('.button.t1c_offline.confirm').prop('disabled', true);
                    $('.button.t1c_offline.confirm').css('opacity', '0.4')
                } else {
                    $('.button.t1c_offline.confirm').prop('disabled', false);
                    $('.button.t1c_offline.confirm').css('opacity', '1.0')
                }
            })

            t1c_content.off('keypress', '.only_number');
            t1c_content.on('keypress', '.only_number',function(event){
                if( !(event.key == '0' || event.key == '1' || event.key == '2' || event.key == '3'
                    || event.key == '4' || event.key == '5' || event.key == '6' || event.key == '7'
                    || event.key == '8' || event.key == '9') ){
                    event.preventDefault();
                }
            });

        },
//        show: function(){
//
//            var self = this;
//            this._super();
//            var t1c_content = this.$el;
//            var t1c_no = this.$('#t1c_no_offline_input');
//
//
//            if(t1c_no.val() == ''){
//                this.$('.button.t1c_offline.confirm').prop('disabled', true);
//                this.$('.button.t1c_offline.confirm').css('opacity', '0.4')
//            }
//
//            t1c_no.on('keydown keyup keypress', function(event){
//                console.log('test')
//                if(this.value === ''){
//                    $('.button.t1c_offline.confirm').prop('disabled', true);
//                    $('.button.t1c_offline.confirm').css('opacity', '0.4')
//                } else {
//                    $('.button.t1c_offline.confirm').prop('disabled', false);
//                    $('.button.t1c_offline.confirm').css('opacity', '1.0')
//                }
//            })
//        },
    });
    gui.define_popup({name: 'card_offline', widget: CardOfflinePopupWidget});

    models.Order = models.Order.extend({
        add_t1c_line: function(cashregister, options) {
            this.assert_editable();
            var redeem_type = cashregister.journal.redeem_type_id;
            // console.log(redeem_type);
            var is_t1cc = redeem_type.code === "T1CC" ? (redeem_type && redeem_type.active) : false;
            var is_t1cp = redeem_type.code === "T1CP" ? (redeem_type && redeem_type.active) : false;
            let conditions = [
                is_t1cc, 
                is_t1cp,
            ];
            if(conditions.indexOf(true) !== -1){
                var newPaymentline = new models.Paymentline({},{order: this, cashregister:cashregister, pos: this.pos});
                newPaymentline.set_amount( options.amount || 0);
                if (is_t1cc) {
                    newPaymentline.t1cc_barcode = options.code;
                } else {
                    newPaymentline.t1cp_receipt_no = options.code;
                    newPaymentline.transactions = options.transactions;
                    newPaymentline.api_to_be_cancelled = options.api_to_be_cancelled;
                    newPaymentline.api_cancel_success = options.api_cancel_success;
                }
                this.paymentlines.unshift(newPaymentline);
                this.select_paymentline(newPaymentline);
            }
        },
    });

    var paymentline_proto = models.Paymentline.prototype;
    models.Paymentline = models.Paymentline.extend({
        initialize: function(attributes, options) {
            var self = this;
            self.t1cc_barcode = "";
            self.t1cp_receipt_no = "";
            self.transactions = [];
            self.api_to_be_cancelled = 0;
            self.api_cancel_success = 0;
            paymentline_proto.initialize.call(this, attributes, options);
        },        
        init_from_JSON: function(json){
            var self = this;
            paymentline_proto.init_from_JSON.call(this, json);
            self.t1cc_barcode = json.t1cc_barcode;
            self.t1cp_receipt_no = json.t1cp_receipt_no;
            self.transactions = JSON.parse(json.transactions);
            self.api_to_be_cancelled = json.api_to_be_cancelled;
            self.api_cancel_success = json.api_cancel_success;
        },
        // returns the associated cashregister
        //exports as JSON for server communication
        export_as_JSON: function(){
            var self = this;
            var loaded = paymentline_proto.export_as_JSON.call(this);
            loaded.t1cc_barcode = self.t1cc_barcode;
            loaded.t1cp_receipt_no = self.t1cp_receipt_no;
            loaded.transactions = JSON.stringify(self.transactions);
            loaded.api_to_be_cancelled = self.api_to_be_cancelled;
            loaded.api_cancel_success = self.api_cancel_success;
            return loaded;
        },
    });

    var _super_order = models.Order;
    models.Order = models.Order.extend({
        initialize: function (attributes, options){
//            this.the_one_card_no = '';
//            this.member_name = '';
//            this.company = '';
//            this.status = '';
//            this.tier = '';
//            this.cg_staff = '';
//            this.balance_points = '';
//            this.redeem_rights = '';
//            this.segment = '';
//            this.staff = '';
//            this.expire_this_year = '';
            this.pos_offline = false;
            this.t1c_set = false;
            this.membercard = {
                'the_one_card_no': 'N/A',
                'member_name': 'N/A',
                'card_type': 'N/A',
                'customer_group_segment': 'N/A',
                'phone': 'N/A',
                'company': 'N/A',
                'status': 'N/A',
                'tier': 'N/A',
                'cg_staff': 'N/A',
                'balance_points': 'N/A',
                'redeem_rights': 'N/A',
                'segment': 'N/A',
                'staff': 'N/A',
                'expire_this_year': 'N/A',
            };
            _super_order.prototype.initialize.call(this, attributes, options);
        },
        init_from_JSON: function (json) {
//            this.the_one_card_no = json.the_one_card_no;
//            this.member_name = json.member_name;
//            this.company = json.company;
//            this.status = json.status;
//            this.tier = json.tier;
//            this.cg_staff = json.cg_staff;
//            this.balance_points = json.balance_points;
//            this.redeem_rights = json.redeem_rights;
//            this.segment = json.segment;
//            this.staff = json.staff;
//            this.expire_this_year = json.expire_this_year;
            this.pos_offline = json.pos_offline;
            this.t1c_set = json.t1c_set;
            this.membercard = json.membercard;
            _super_order.prototype.init_from_JSON.call(this, json);
        },
        export_as_JSON: function () {
            var data = _super_order.prototype.export_as_JSON.call(this);
//            data.the_one_card_no = this.the_one_card_no;
//            data.member_name = this.member_name;
//            data.company = this.company;
//            data.status = this.status;
//            data.tier = this.tier;
//            data.cg_staff = this.cg_staff;
//            data.balance_points = this.balance_points;
//            data.redeem_rights = this.redeem_rights;
//            data.segment = this.segment;
//            data.staff = this.staff;
//            data.expire_this_year = this.expire_this_year;
            data.pos_offline = this.pos_offline;
            data.t1c_set = this.t1c_set;
            data.membercard = this.membercard;
            return data;
        },
        increase_payment_no: function(){
            _super_order.prototype.increase_payment_no.call(this);
            this.pos.request_the_one_card_no = 0;
        },
    });

    var TheOneCardWidget = screens.ScreenWidget.extend({
        template: 'TheOneCardPaymentScreenInput',
        init: function(parent, options) {
			this._super(parent, options);
//			if(options.the_one_card_no){
//			    this.the_one_card_no = options.the_one_card_no;
//			}
		},
        sync_t1c_from_order: function(){
            var order = this.pos.get_order();

            this.$('.member-name').text(order.membercard.member_name);
            this.$('.member-the_one_card_no').text(order.membercard.the_one_card_no);
            this.$('.member-phone').text(order.membercard.phone);

        },
        renderElement: function(){
            var self = this;
            this._super();
            var t1c_content = this.$el;
            t1c_content.off('keypress', '.only_number');
            t1c_content.on('keypress', '.only_number',function(event){
                self.allow_number(event);
            });

//            t1c_content.on('change paste keyup', '.t1c_in_product_class',function(event){
//                if(event.target && event.target.tagName.toUpperCase() == 'INPUT'){
//                    var order = self.pos.get_order();
//                    order.the_one_card_no = $(this).val();
//                    order.save_to_db();
//                }
//
//            });
        },
    });

    screens.ActionpadWidget.include({
        check_t1c: function(){
            var order = this.pos.get_order();
//            if(order.the_one_card_no.length == 0 ||  order.the_one_card_no.length == 10 || order.the_one_card_no.length == 16){
//                return true;
//            }
//            else{
//                this.pos.gui.show_popup('alert', {
//                    'title': 'Alert',
//                    'body': 'The One Card allows 10 digits and 16 digits.',
//                });
//                return false;
//            }
        },
        click_pay: function(self){
//            if(!this.check_t1c()){
//                return;
//            }
            this._super(self);
        },
        validate_t1c: function(val){
            if(val.length == 0 ||  val.length == 10 || val.length == 16){
                return true;
            }
            else{
                this.pos.gui.show_popup('alert', {
                    'title': 'Alert',
                    'body': 'The One Card allows 10 digits and 16 digits.',
                });
                return false;
            }
        },
        renderElement: function() {
            var self = this;
            this._super();

            var order = this.pos.get_order();
            this.the_one_card = new TheOneCardWidget(this);
            this.the_one_card.replace(this.$('.theonecardproductscreen-container'));

            this.member = new MemberCardDetailsWidget(this);
            this.member.replace(this.$('.placeholder-MemberCardDetailsWidget'));

            this.$('.set_the_one_card').click(function(){
                self.click_set_card();
            });
        },
        click_set_card: function(){
            var order = this.pos.get_order();
            /* Condition for Check Online state */
            var condition = navigator.onLine ? "online" : "offline";
            if (condition === 'online'){
                this.gui.show_screen('cardlist');
            } else {
                /* if pos status is offline show popup! */
                this.gui.show_popup('card_offline',{
                    title: "Alert! No internet connection",
                    confirm: function() {
                         var value = this.$('input').val();
                         order.membercard.the_one_card_no = value;
                         order.t1c_set = true;
                         order.pos_offline = true;
                         $('.member_search').text(value);
                         $('.member-the_one_card_no').text(value);
                         order.save_to_db();
                    },
                });

            }

        },
    });

    screens.ProductScreenWidget.include({
        show: function () {
            var self = this;
            this._super();
            this.actionpad.the_one_card.sync_t1c_from_order();
            this.actionpad.member.sync_the_one_card();
        },
    });

    var MemberCardDetailsWidget = PosBaseWidget.extend({
        template:'MemberCardDetailsWidget',

        sync_the_one_card: function(){
            var order = this.pos.get_order();
            if (order.t1c_set && !order.pos_offline){
                $('.member_detail').removeClass('empty');
                $('.member_search').addClass('empty');
                this.$('.member-status').text(order.membercard.status);
                this.$('.member-company').text(order.membercard.company);
                this.$('.member-card_type').text(order.membercard.card_type);
                this.$('.member-customer_group_segment').text(order.membercard.customer_group_segment);
                this.$('.member-tier').text(order.membercard.tier);
                this.$('.member-cg_staff').text(order.membercard.cg_staff);
                this.$('.member-redeem_rights').text(order.membercard.redeem_rights);
                this.$('.member-staff').text(order.membercard.staff);
                this.$('.member-balance_points').text(order.membercard.balance_points);
                this.$('.member-expire_this_year').text(order.membercard.expire_this_year);
                this.$('.member-segment').text(order.membercard.segment);
            } else {
                $('.member_detail').addClass('empty');
                $('.member_search').text('Search T1C');
                $('.member_search').removeClass('empty');
            }
        },
        renderElement: function(){
            var self = this;
            this._super();

        },
    });


    var CardListScreenWidget = screens.ScreenWidget.extend({
    template: 'CardListScreenWidget',

    init: function(parent, options){
        this._super(parent, options);
    },

    auto_back: true,
    zero_pad: function(num,size){
        var s = ""+num;
        while (s.length < size) {
            s = "0" + s;
        }
        return s;
    },
    get_request_header: function(date){
        var self = this;
        var now = moment(date);
        /*<PartnerCode>_<storecode>_<Receipt-no>_#request_DD_HHMMSSMMM*/
        var SourceTransID = [
            'OFM',
            self.pos.branch.branch_code,
            self.pos.get_order().get_inv_no(),
            self.zero_pad(++self.pos.request_the_one_card_no, 3),
            now.format('DD_HH:mm:ss:SSS')
        ].join('_');
        var i;
        return {
            'SourceTransID': SourceTransID,
            'RequestTime': now.format('DDMMYYYY_HH:mm:ss:SSS'),
            'LanguagePreference': 'TH',
            'client_id': self.pos.the_1_config.client_id,
            'client_secret': self.pos.the_1_config.client_secret,
            'PartnerCode': self.pos.the_1_config.partnerCode,
            'TransactionChannel': self.pos.the_1_config.transactionChannel,
            'Content-Type': 'application/json',
        }
    },
    show: function(){
        var self = this;
        this._super();

        this.renderElement();
        this.membercard_list = {};
        this.old_card = null;
        this.new_card = null;


        this.$('.back').click(function(){
            self.gui.back();
        });

        this.$('.next').click(function(){
            self.save_changes();
            self.gui.back();
        });

        if(this.pos.get_order().t1c_set){
            this.old_card = this.pos.get_order().membercard;
            self.display_card_details('show', this.old_card);
        } else {
            $('input.the_one_card_input').val('');
            $('.card-list-contents').empty();
        }

        this.$('.card-list-contents').delegate('.card-list','click',function(event){
            self.line_select(event,$(this),parseInt(this.id));
        });

        this.$('input.the_one_card_no.the_one_card_input').focus();

        this.$('input.the_one_card_input').off('focus');
        this.$('input.the_one_card_input').on('focus', function(e){
            var t1c_no = $('.the_one_card_no');
            var tel = $('.telephone');
            var taxid = $('.tax_id');

            if(t1c_no.val() !== '' || tel.val() !== '' || taxid.val() !== ''){
                t1c_no.val('');
                tel.val('');
                taxid.val('');
            }
        });

        this.$('.button-search').off('click');
        this.$('.button-search').on('click', function(e){
            var kp = jQuery.Event("keypress");
            kp.which = 13;
            if($('input.the_one_card_no.the_one_card_input').val() != ""){
                $('input.the_one_card_no.the_one_card_input').trigger(kp);
            } else if ($('input.telephone.the_one_card_input').val() != ""){
                $('input.telephone.the_one_card_input').trigger(kp);
            } else if ($('input.tax_id.the_one_card_input').val() != ""){
                $('input.tax_id.the_one_card_input').trigger(kp);
            }
        })
        this.$('input.the_one_card_input').off('keypress');
        this.$('input.the_one_card_input').on('keypress', function(e){
            var keycode = (e.keyCode ? e.keyCode : e.which);
            if (keycode == '13') {

                self.display_card_details('hide');

                var classList = e.target.classList[0];
                var t1c_val, tel_val, tax_val = undefined;


                if(classList == 'the_one_card_no'){
                    t1c_val = e.target.value;
                    if(t1c_val.length != 10 && t1c_val.length != 16){
                        self.pos.gui.show_popup('alert', {
                            'title': 'Alert',
                            'body': 'The One Card allows 10 digits and 16 digits.',
                        });
                        return false;
                    }
                } else if(classList == 'telephone'){
                    tel_val = e.target.value;
                    if(tel_val.length != 10){
                        self.pos.gui.show_popup('alert', {
                            'title': 'Alert',
                            'body': 'Tel allows 10 digits.',
                        });
                        return false;
                    }
                } else if(classList == 'tax_id'){
                    tax_val = e.target.value;
                    if(tax_val.length != 13){
                        self.pos.gui.show_popup('alert', {
                            'title': 'Alert',
                            'body': 'Tax ID allows 13 digits.',
                        });
                        return false;
                    }
                }


                var order = self.pos.get_order();

                var header = self.get_request_header(new Date());
                var body = {
                    "phoneNo": tel_val || '',
                    "cardNo": t1c_val || '',
                    "nationalID": tax_val || '',
                }

                self.chrome.loading_show();
                self.chrome.loading_message('กำลังประมวลผล', 0.8);
                $.ajax({
                      url: self.pos.the_1_config.T1CQryMemInSrv.url,
                      type: self.pos.the_1_config.T1CQryMemInSrv.method,
                      data: JSON.stringify(body),
//                      async: false,
                      dataType: 'json',
                      contentType:'application/json',
                      secure: true,
                      headers: header,
                      success: function(data){
                          self.chrome.loading_hide();
                          $('.member-not-found').empty();
                          $('.card-list-contents').empty();

                          if((data.responseBody.members).length === 1 ){
                            if((data.responseBody.members[0].cards).length === 1){
                                var member_name;

                                if(header.LanguagePreference == 'TH'){
                                    member_name = data.responseBody.members[0].memberFirstNameThai + ' ' + data.responseBody.members[0].memberLastNameThai
                                } else if (header.LanguagePreference == 'EN'){
                                    member_name = data.responseBody.members[0].memberFirstNameEng + ' ' + data.responseBody.members[0].memberLastNameEng
                                }

                                var card_type, company = 'N/A';
                                if(data.responseBody.members[0].cards[0].cardType == 'I'){
                                    card_type = 'Individual'
                                } else if(data.responseBody.members[0].cards[0].cardType == 'C'){
                                    card_type = 'Corporate'
                                    company = data.responseBody.members[0].cards[0].parentMemberName;
                                }
                                self.pos.get_order().membercard = {
                                    'the_one_card_no': data.responseBody.members[0].cards[0].cardNo || 'N/A',
                                    'member_name': member_name || 'N/A',
                                    'card_type': card_type || 'N/A',
                                    'customer_group_segment': data.segmentLevel || 'N/A',
                                    'phone': (data.phone || tel_val || 'N/A'),
                                    'company': company || 'N/A',
                                    'status': data.status || 'N/A',
                                    'tier': data.memberTier || 'N/A',
                                    'cg_staff': data.employeeFlag || 'N/A',
                                    'balance_points': data.responseBody.members[0].cards[0].pointsBalance,
                                    'redeem_rights': data.responseBody.members[0].cards[0].authorityType,
                                    'segment': 'N/A',
                                    'staff': 'N/A',
                                    'expire_this_year': data.responseBody.members[0].cards[0].expiringPointsThisYear || 'N/A',
                                }
                                self.pos.get_order().t1c_set = true;
                                self.pos.get_order().pos_offline = false;
                                self.gui.back();
                                return;
                            }
                          }


                          (data.responseBody.members).forEach(function(data){
                            var member_name;

                            if(header.LanguagePreference == 'TH'){
                                member_name = data.memberFirstNameThai + ' ' + data.memberLastNameThai
                            } else if (header.LanguagePreference == 'EN'){
                                member_name = data.memberFirstNameEng + ' ' + data.memberLastNameEng
                            }

                            (data.cards).forEach(function(card){
                                var card_type, company = 'N/A';
                                if(card.cardType == 'I'){
                                    card_type = 'Individual'
                                } else if(card.cardType == 'C'){
                                    card_type = 'Corporate'
                                    company = card.parentMemberName;
                                }
                                //console.log((data.cards).length);
                                $('.card-list-contents').append(
                                    '<tr class="card-list" id=' + card.cardNo + '>' +
                                        '<td>' +
                                            card.cardNo +
                                        '</td>' +
                                        '<td>' +
                                            member_name +
                                        '</td>' +
                                        '<td>' +
                                            card_type +
                                        '</td>' +
                                        '<td>' +
                                            (data.phone || tel_val || '') +
                                        '</td>' +
                                        '<td>' +
                                            card.pointsBalance +
                                        '</td>' +
                                        '<td>' +
                                            card.expiringPointsThisYear +
                                        '</td>' +
                                    '</tr>'
                                )
                                self.membercard_list[card.cardNo] = {
                                    'the_one_card_no': card.cardNo,
                                    'member_name': member_name,
                                    'card_type': card_type,
                                    'customer_group_segment': data.segmentLevel || '',
                                    'phone': (data.phone || tel_val || ''),
                                    'company': company,
                                    'status': data.status,
                                    'tier': data.memberTier,
                                    'cg_staff': data.employeeFlag,
                                    'balance_points': card.pointsBalance,
                                    'redeem_rights': card.authorityType,
                                    'segment': 'N/A',
                                    'staff': 'N/A',
                                    'expire_this_year': card.expiringPointsThisYear,
                                }
                            });
                          });

                      },
                      error: function(){
                            self.chrome.loading_hide();
                            $('.member-not-found').empty();
                            self.display_card_details('hide');
                            $('.cardlist-screen .button.next').addClass('oe_hidden');
                            $('input.the_one_card_input').val('');
                            $('.card-details-contents').empty();
                            $('.card-list-contents').empty();
                            $('.card-list').after(
                                '<div class="member-not-found"">' +
                                '--- Member not found ---' +
                                '</div>'
                            )
                      }
                });

            }
        });

    },
    hide: function () {
        this._super();
        this.new_card = null;
    },
    get_card_by_id: function(id){
        var self = this;
        var order = this.pos.get_order();
        //console.log(this.membercard_list);
        var membercard = null;
        if (jQuery.isEmptyObject(this.old_card) && !jQuery.isEmptyObject(this.new_card) && this.membercard_list == ''){
            membercard = this.old_card;
        } else {
            membercard = this.membercard_list[id]
        }
        return membercard
    },
    save_changes: function(){
        var self = this;
        var order = this.pos.get_order();
        if(this.new_card){
            order.membercard = this.new_card;
            order.t1c_set = true;
            order.pos_offline = false;
        } else {
            if(this.old_card){
                order.membercard = {
                    'the_one_card_no': 'N/A',
                    'member_name': 'N/A',
                    'card_type': 'N/A',
                    'customer_group_segment': 'N/A',
                    'phone': 'N/A',
                    'company': 'N/A',
                    'status': 'N/A',
                    'tier': 'N/A',
                    'cg_staff': 'N/A',
                    'balance_points': 'N/A',
                    'redeem_rights': 'N/A',
                    'segment': 'N/A',
                    'staff': 'N/A',
                    'expire_this_year': 'N/A',
                };
                order.t1c_set = false;
            } else {
                order.membercard = this.old_card;
                order.t1c_set = true;
                order.pos_offline = false;
            }
        }
        order.save_to_db();
    },
    set_card: function(id){
//        var membercard = this.get_card_by_id(id);
        var order = this.pos.get_order();
        order.membercard = this.get_card_by_id(id);
        order.save_to_db();
    },
    renderElement: function(){
            var self = this;
            this._super();
            var t1c_content = this.$el;
            t1c_content.off('keypress', '.only_number');
            t1c_content.on('keypress', '.only_number',function(event){
                self.allow_number(event);
            });
    },
    toggle_save_button: function(){
        var $button = this.$('.button.next');
        $button.addClass('oe_hidden');
        if( this.new_card ){
            $button.text(_t('Set Customer'));
            $button.removeClass('oe_hidden');
        } else if (this.old_card) {
            $button.text(_t('Deselect Customer'));
            $button.removeClass('oe_hidden');
        }
    },
    line_select: function(event,$line,id){
        var membercard = this.get_card_by_id(id);

        this.$('.card-list .lowlight').removeClass('lowlight');
        if ( $line.hasClass('highlight') ){
            $line.removeClass('highlight');
            $line.addClass('lowlight');
            this.new_card = null;
            this.display_card_details('hide');
        }else{
            //console.log(membercard);
            this.$('.card-list .highlight').removeClass('highlight');
            $line.addClass('highlight');
            this.new_card = membercard;
            this.display_card_details('show',membercard);
        }

    },
    display_card_details: function(visibility,membercard){
        var self = this;
        var contents = this.$('.card-details-contents');
        var order = self.pos.get_order();



        if(visibility === 'show'){
            contents.empty();
            contents.append($(QWeb.render('CardDetails',{widget:this,membercard:membercard})));
            this.toggle_save_button()
        } else if (visibility === 'hide') {
            contents.empty();
            this.toggle_save_button()
        }

    },
    close: function(){
        this._super();
        if (this.pos.config.iface_vkeyboard && this.chrome.widget.keyboard) {
            this.chrome.widget.keyboard.hide();
        }
    },
    });
    gui.define_screen({name:'cardlist', widget: CardListScreenWidget});

    return {
        CardListScreenWidget: CardListScreenWidget,
        MemberCardDetailsWidget: MemberCardDetailsWidget,
    };


});
