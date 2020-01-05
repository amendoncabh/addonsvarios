# -*- coding: utf-8 -*-

from odoo import models, fields, api

class PromotionWeekMixin(models.AbstractModel):

    _name = 'promotion.week.mixin'

    is_custom_day = fields.Boolean(
        string="Set Valid Days",
        default=False,
    )

    all_sunday = fields.Boolean(
        string="All Sunday",
        dafault=False,
    )

    all_monday = fields.Boolean(
        string="All Monday",
        dafault=False,
    )

    all_tuesday = fields.Boolean(
        string="All tuesday",
        dafault=False,
    )

    all_wednesday = fields.Boolean(
        string="All Wednesday",
        dafault=False,
    )

    all_thursday = fields.Boolean(
        string="All Thursday",
        dafault=False,
    )

    all_friday = fields.Boolean(
        string="All Friday",
        dafault=False,
    )

    all_saturday = fields.Boolean(
        string="All Saturday",
        dafault=False,
    )

    first_sunday = fields.Boolean(
        string="1st Sunday",
        dafault=False,
    )

    first_monday = fields.Boolean(
        string="1st Monday",
        dafault=False,
    )

    first_tuesday = fields.Boolean(
        string="1st Tuesday",
        dafault=False,
    )

    first_wednesday = fields.Boolean(
        string="1st Wednesday",
        dafault=False,
    )

    first_thursday = fields.Boolean(
        string="1st Thursday",
        dafault=False,
    )

    first_friday = fields.Boolean(
        string="1st Friday",
        dafault=False,
    )

    first_saturday = fields.Boolean(
        string="1st Saturday",
        dafault=False,
    )

    second_sunday = fields.Boolean(
        string="2nd Sunday",
        dafault=False,
    )

    second_monday = fields.Boolean(
        string="2nd Monday",
        dafault=False,
    )

    second_tuesday = fields.Boolean(
        string="2nd Tuesday",
        dafault=False,
    )

    second_wednesday = fields.Boolean(
        string="2nd Wednesday",
        dafault=False,
    )

    second_thursday = fields.Boolean(
        string="2nd Thursday",
        dafault=False,
    )

    second_friday = fields.Boolean(
        string="2nd Friday",
        dafault=False,
    )

    second_saturday = fields.Boolean(
        string="2nd Saturday",
        dafault=False,
    )

    third_sunday = fields.Boolean(
        string="3rd Sunday",
        dafault=False,
    )

    third_monday = fields.Boolean(
        string="3rd Monday",
        dafault=False,
    )

    third_tuesday = fields.Boolean(
        string="3rd Tuesday",
        dafault=False,
    )

    third_wednesday = fields.Boolean(
        string="3rd Wednesday",
        dafault=False,
    )

    third_thursday = fields.Boolean(
        string="3rd Thursday",
        dafault=False,
    )

    third_friday = fields.Boolean(
        string="3rd Friday",
        dafault=False,
    )

    third_saturday = fields.Boolean(
        string="3rd Saturday",
        dafault=False,
    )

    fourth_sunday = fields.Boolean(
        string="4th Sunday",
        dafault=False,
    )

    fourth_monday = fields.Boolean(
        string="4th Monday",
        dafault=False,
    )

    fourth_tuesday = fields.Boolean(
        string="4th Tuesday",
        dafault=False,
    )

    fourth_wednesday = fields.Boolean(
        string="4th Wednesday",
        dafault=False,
    )

    fourth_thursday = fields.Boolean(
        string="4th Thursday",
        dafault=False,
    )

    fourth_friday = fields.Boolean(
        string="4th Friday",
        dafault=False,
    )

    fourth_saturday = fields.Boolean(
        string="4th Saturday",
        dafault=False,
    )

    last_sunday = fields.Boolean(
        string="Last Sunday",
        dafault=False,
    )

    last_monday = fields.Boolean(
        string="Last Monday",
        dafault=False,
    )

    last_tuesday = fields.Boolean(
        string="Last Tuesday",
        dafault=False,
    )

    last_wednesday = fields.Boolean(
        string="Last Wednesday",
        dafault=False,
    )

    last_thursday = fields.Boolean(
        string="Last Thursday",
        dafault=False,
    )

    last_friday = fields.Boolean(
        string="Last Friday",
        dafault=False,
    )

    last_saturday = fields.Boolean(
        string="Last Saturday",
        dafault=False,
    )

    @api.onchange('is_custom_day')
    def onchange_is_custom_day(self):
        self.all_sunday = False
        self.all_monday = False
        self.all_tuesday = False
        self.all_wednesday = False
        self.all_thursday = False
        self.all_friday = False
        self.all_saturday = False

    @api.onchange('all_sunday')
    def onchange_all_sunday(self):
        self.first_sunday = self.all_sunday
        self.second_sunday = self.all_sunday
        self.third_sunday = self.all_sunday
        self.fourth_sunday = self.all_sunday
        self.last_sunday = self.all_sunday

    @api.onchange('all_monday')
    def onchange_all_monday(self):
        self.first_monday = self.all_monday
        self.second_monday = self.all_monday
        self.third_monday = self.all_monday
        self.fourth_monday = self.all_monday
        self.last_monday = self.all_monday

    @api.onchange('all_tuesday')
    def onchange_all_tuesday(self):
        self.first_tuesday = self.all_tuesday
        self.second_tuesday = self.all_tuesday
        self.third_tuesday = self.all_tuesday
        self.fourth_tuesday = self.all_tuesday
        self.last_tuesday = self.all_tuesday

    @api.onchange('all_wednesday')
    def onchange_all_wednesday(self):
        self.first_wednesday = self.all_wednesday
        self.second_wednesday = self.all_wednesday
        self.third_wednesday = self.all_wednesday
        self.fourth_wednesday = self.all_wednesday
        self.last_wednesday = self.all_wednesday

    @api.onchange('all_thursday')
    def onchange_all_thursday(self):
        self.first_thursday = self.all_thursday
        self.second_thursday = self.all_thursday
        self.third_thursday = self.all_thursday
        self.fourth_thursday = self.all_thursday
        self.last_thursday = self.all_thursday

    @api.onchange('all_friday')
    def onchange_all_friday(self):
        self.first_friday = self.all_friday
        self.second_friday = self.all_friday
        self.third_friday = self.all_friday
        self.fourth_friday = self.all_friday
        self.last_friday = self.all_friday

    @api.onchange('all_saturday')
    def onchange_all_saturday(self):
        self.first_saturday = self.all_saturday
        self.second_saturday = self.all_saturday
        self.third_saturday = self.all_saturday
        self.fourth_saturday = self.all_saturday
        self.last_saturday = self.all_saturday

    @api.onchange('first_sunday', 'second_sunday', 'third_sunday', 'fourth_sunday', 'last_sunday')
    def onchange_nth_sunday(self):
        if not self.first_sunday or not self.second_sunday or not self.third_sunday \
                or not self.fourth_sunday or not self.last_sunday:
            self.all_sunday = False

    @api.onchange('first_monday', 'second_monday', 'third_monday', 'fourth_monday', 'last_monday')
    def onchange_nth_monday(self):
        if not self.first_monday or not self.second_monday or not self.third_monday \
                or not self.fourth_monday or not self.last_monday:
            self.all_monday = False

    @api.onchange('first_tuesday', 'second_tuesday', 'third_tuesday', 'fourth_tuesday', 'last_tuesday')
    def onchange_nth_tuesday(self):
        if not self.first_tuesday or not self.second_tuesday or not self.third_tuesday \
                or not self.fourth_tuesday or not self.last_tuesday:
            self.all_tuesday = False

    @api.onchange('first_wednesday', 'second_wednesday', 'third_wednesday', 'fourth_wednesday', 'last_wednesday')
    def onchange_nth_wednesday(self):
        if not self.first_wednesday or not self.second_wednesday or not self.third_wednesday \
                or not self.fourth_wednesday or not self.last_wednesday:
            self.all_wednesday = False

    @api.onchange('first_thursday', 'second_thursday', 'third_thursday', 'fourth_thursday', 'last_thursday')
    def onchange_nth_thursday(self):
        if not self.first_thursday or not self.second_thursday or not self.third_thursday \
                or not self.fourth_thursday or not self.last_thursday:
            self.all_thursday = False

    @api.onchange('first_friday', 'second_friday', 'third_friday', 'fourth_friday', 'last_friday')
    def onchange_nth_friday(self):
        if not self.first_friday or not self.second_friday or not self.third_friday \
                or not self.fourth_friday or not self.last_friday:
            self.all_friday = False

    @api.onchange('first_saturday', 'second_saturday', 'third_saturday', 'fourth_saturday', 'last_saturday')
    def onchange_nth_saturday(self):
        if not self.first_saturday or not self.second_saturday or not self.third_saturday \
                or not self.fourth_saturday or not self.last_saturday:
            self.all_saturday = False
