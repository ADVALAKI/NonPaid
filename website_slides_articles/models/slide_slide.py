# -*- coding: utf-8 -*-
from openerp import api, fields, models

class SlideSlideCategory(models.Model):

    _inherit = "slide.slide"
    
    blog_tag_id = fields.Many2one('blog.blog', string="Blog Categories")
    slide_blog_url = fields.Char(string="Blog URL", compute="_compute_bu_url")
    
    @api.one
    @api.depends('name')
    def _compute_bu_url(self):
        if self.blog_tag_id:
            self.slide_blog_url = self.blog_tag_id.name.replace(" ","-").lower()
            self.slide_blog_url += "-" + str(self.blog_tag_id.id)
        else:
            slide_blog_url = "blog"