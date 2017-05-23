# -*- coding: utf-8 -*-
import logging
_logger = logging.getLogger(__name__)
import werkzeug
import json
import urllib2
import requests
from openerp.http import request
from datetime import datetime, timedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, exception_to_unicode
from openerp.exceptions import UserError
from openerp.addons.google_account import TIMEOUT
from lxml import etree

from openerp import api, fields, models

class GoogleContacts(models.Model):

    _name = "google.contacts"
    _description = "Google Contacts"
    
    fake_field = fields.Char(string="Fake Field")
    
    
    def need_authorize(self):
        return self.env.user.google_contacts_rtoken is False

    def authorize_google_uri(self, from_url='http://www.openerp.com'):
        url = self.env['google.service']._get_authorize_uri(from_url, 'contacts', scope=self.get_google_scope())
        return url

    @api.model
    def set_all_tokens(self, authorization_code):
        _logger.error("token set")
        gs_pool = self.env['google.service']
        all_token = gs_pool._get_google_token_json(authorization_code, 'contacts')
        
        vals = {}
        vals['google_contacts_rtoken'] = all_token.get('refresh_token')
        vals['google_contacts_token_validity'] = datetime.now() + timedelta(seconds=all_token.get('expires_in'))
        vals['google_contacts_token'] = all_token.get('access_token')
        self.env.user.write(vals)
        
    @api.multi
    def g_contact_download(self):
        self.ensure_one()
        
        if self.need_authorize():
            my_from_url = request.httprequest.host_url + "google/contacts/auth"
            url = self.authorize_google_uri(from_url=my_from_url)
            return {'type': 'ir.actions.act_url', 'url': url, 'target': 'self'}


    @api.model
    def cron_sync(self):
        gs_pool = self.env['google.service']

        #Get a new access token
        all_token = self.env['google.service']._refresh_google_token_json(self.env.user.google_contacts_rtoken, 'contacts')
        
        access_token = self.env.user.google_contacts_token

        headers = {'Authorization': 'Bearer ' + access_token, 'GData-Version': '3.0'}
        response_string = requests.get("https://www.google.com/m8/feeds/contacts/default/full?alt=json", headers=headers)
        _logger.error(response_string.text.encode('utf-8'))
        google_contacts_json = json.loads(response_string.text.encode('utf-8'))
            
        account_email = google_contacts_json['feed']['id']['$t'] 
        
        for contact in google_contacts_json['feed']['entry']:
            
            if 'gd$name' not in contact:
                continue
            
            contact_id = contact['id']['$t']
            
            g_contact_dict = {'google_contacts_id': contact_id, 'customer': False, 'google_contacts_account': account_email}

            g_contact_dict['name'] = contact['gd$name']['gd$fullName']['$t']
            
            if 'gd$email' in contact:
                g_contact_dict['email'] = contact['gd$email'][0]['address']

            if 'gd$phoneNumber' in contact:
                g_contact_dict['phone'] = contact['gd$phoneNumber'][0]['$t']
            
            if 'gd$structuredPostalAddress' in contact:
                if 'gd$street' in contact['gd$structuredPostalAddress'][0]:
                    g_contact_dict['street'] = contact['gd$structuredPostalAddress'][0]['gd$street']['$t']

                if 'gd$city' in contact['gd$structuredPostalAddress'][0]:
                    g_contact_dict['city'] = contact['gd$structuredPostalAddress'][0]['gd$city']['$t']

                if 'gd$region' in contact['gd$structuredPostalAddress'][0]:
                    state = contact['gd$structuredPostalAddress'][0]['gd$region']['$t']
                    
                    #Find the corresponding state in out database
                    state_search = self.env['res.country.state'].search([('name','=', state)])
                    if state_search:
                        g_contact_dict['state_id'] = state_search[0].id

                if 'gd$country' in contact['gd$structuredPostalAddress'][0]:
                    country = contact['gd$structuredPostalAddress'][0]['gd$country']['$t']

                    #Find the corresponding country in out database
                    country_search = self.env['res.country'].search([('name','=', country)])
                    if country_search:
                        g_contact_dict['country_id'] = country_search[0].id
    
            existing_contact = self.env['res.partner'].search([('google_contacts_id', '=', contact_id)])
            if existing_contact:
                #Update existing partner
                existing_contact.write(g_contact_dict)
            else:
                #Create new partner
                self.env['res.partner'].create(g_contact_dict)

        
    def get_google_scope(self):
        return 'https://www.googleapis.com/auth/contacts.readonly'

    def get_access_token(self, scope=None):
        ir_config = self.env['ir.config_parameter']
        google_contacts_refresh_token = ir_config.get_param('google_contacts_refresh_token')
        if not google_contacts_refresh_token:
            if self.env['res.users']._is_admin([self.env.uid]):
                model, action_id = self.env['ir.model.data'].get_object_reference('base_setup', 'action_general_configuration')
                msg = _("You haven't configured 'Authorization Code' generated from google, Please generate and configure it .")
                raise openerp.exceptions.RedirectWarning(msg, action_id, _('Go to the configuration panel'))
            else:
                raise UserError(_("Google Contacts is not yet configured. Please contact your administrator."))
        google_contacts_client_id = ir_config.get_param('google_contacts_client_id')
        google_contacts_client_secret = ir_config.get_param('google_contacts_client_secret')
        #For Getting New Access Token With help of old Refresh Token

        data = werkzeug.url_encode(dict(client_id=google_contacts_client_id,
                                     refresh_token=google_contacts_refresh_token,
                                     client_secret=google_contacts_client_secret,
                                     grant_type="refresh_token",
                                     scope=scope or 'https://www.googleapis.com/auth/contacts.readonly'))
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        try:
            req = urllib2.Request('https://accounts.google.com/o/oauth2/token', data, headers)
            content = urllib2.urlopen(req, timeout=TIMEOUT).read()
        except urllib2.HTTPError:
            if user_is_admin:
                model, action_id = self.env['ir.model.data'].get_object_reference('base_setup', 'action_general_configuration')
                msg = _("Something went wrong during the token generation. Please request again an authorization code .")
                raise openerp.exceptions.RedirectWarning(msg, action_id, _('Go to the configuration panel'))
            else:
                raise UserError(_("Google Drive is not yet configured. Please contact your administrator."))
        content = json.loads(content)
        return content.get('access_token')
