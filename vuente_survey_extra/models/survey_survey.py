# -*- coding: utf-8 -*-
from openerp import api, fields, models

class SurveySurveyLeads(models.Model):

    _inherit = "survey.survey"
    
    lead_survey = fields.Boolean(string="Lead Survey")
    category_ids = fields.One2many('survey.category', 'survey_id', string="Categories")
    
class SurveySurveyCategory(models.Model):

    _name = "survey.category"
    
    survey_id = fields.Many2one('survey.survey', string="Survey")
    name = fields.Char(string="Name")