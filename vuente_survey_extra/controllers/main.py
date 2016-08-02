# -*- coding: utf-8 -*-
import werkzeug
import json
import base64

import openerp.http as http
from openerp.http import request

from openerp.addons.website.models.website import slug

class SurveyLeadController(http.Controller):

    @http.route('/survey/lead/<survey_id>', type="http", auth="public", website=True)
    def survey_lead(self, survey_id, **kw):
        """Create lead and link to survey anwser"""
 
        values = {}
 	for field_name, field_value in kw.items():
            values[field_name] = field_value

        my_lead = request.env['crm.lead'].create({'name': values['name'] + " (Survey Lead)", 'contact_name': values['name'], 'email_from': values['email'] })
            
        survey_answer = request.env['survey.user_input'].search([('token','=',values['token'] )])
        survey_answer.lead_id = my_lead.id
        
        return werkzeug.utils.redirect("/")