##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2018 Serpent Consulting Services Pvt. Ltd.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import tempfile
import base64
import shutil
import os

from odoo import api, fields, models, _
from odoo.exceptions import UserError, Warning

import tesserocr
from PIL import Image


class InvoiceWizardAttachment(models.TransientModel):
    _name = 'invoice.wizard.attachment'

    read_invoice_id = fields.Many2one('read.invoice.wizard',
                                      'Read Invoice')
    import_invoice_id = fields.Many2one('import.invoice.wizard',
                                        'Read Invoice')
    color = fields.Integer(string='Color Index')
    filename = fields.Char("File name")
    image_attachment = fields.Binary("Image Attachment")


class ReadInvoiceWizard(models.TransientModel):
    _name = 'read.invoice.wizard'

    attachment_type = fields.Selection(selection=[('pdf', 'Pdf'),
                                                  ('image', 'Image')],
                                       string='Attachment Type',
                                       default='pdf')
    pdf_attachment = fields.Binary("Pdf Attachment")
    filename = fields.Char("File name")
    currency_id = fields.Many2one('res.currency', 'Attached Invoice Currency',
                                  help='Select Attached Invoice Currency')
    invoice_type = fields.Selection(selection=[('customer', 'Customer'),
                                               ('supplier', 'Supplier')],
                                    string='Invoice Type', default='customer')

    attachment_ids = fields.One2many('invoice.wizard.attachment',
                                     'read_invoice_id',
                                     string='Image Attachment')
    language = fields.Many2one('res.lang', string="Language")

    def check_pdf_file(self):
        if self.pdf_attachment:
            filename = self.filename.rsplit('.')
            if filename and filename[1] != 'pdf':
                raise UserError(_('You can attach only pdf file.'))

    def get_pdf_or_image_data(self, file_data, line_list):
        supplierinfo_obj = self.env['product.supplierinfo']
        product_obj = self.env['product.product']
        tax_obj = self.env['account.tax']
        partner_obj = self.env['res.partner']
        parsing = False
        partner_list = []
        partner = False
        counter = -1
        product = False

        translation_obj = self.env['ir.translation']
        description = translation_obj.search([
            ('lang', '=', self.language.code),
            ('src', '=', "Description")], limit=1)
        if description.value:
            trans_description = description.value.encode().decode("utf-8")
        else:
            trans_description = "Description"

        subtotal = translation_obj.search([
            ('lang', '=', self.language.code),
            ('src', '=', "Subtotal")], limit=1)
        if subtotal.value:
            trans_subtotal = subtotal.value.encode().decode("utf-8")
        else:
            trans_subtotal = "Subtotal"
        for line in file_data:
            tax = []
            cnt = 0
            counter += 1
            if counter > 5 and counter < 26:
                partner_list.append(line.split('\n')[0])
            if line.startswith(trans_description):
                parsing = True
            elif line.startswith(trans_subtotal):
                parsing = False
            if parsing and trans_description not in line:
                currency_sign_pos = line.rfind(
                    self.currency_id.symbol.encode().decode('utf-8'))
                line_length = len(line)
                if currency_sign_pos >= (line_length - 15) and \
                        not currency_sign_pos < 0:
                    line_split = line.encode().decode('utf-8')
                    count = line.count(self.currency_id.symbol)
                    symbol_find = line_split.find(self.currency_id.symbol)
                    index_find = line[symbol_find + 3:]
                    split_line = line_split.split(self.currency_id.symbol)
                    invoice_split_line = split_line and split_line[0] or False
                    invoice_line = invoice_split_line.split(' ')
                    if count > 1:
                        second_symbol = index_find.find(
                            self.currency_id.symbol)
                        if len(line[second_symbol + 3:]) > 1:
                            del invoice_line[-2]
                    else:
                        if not len(index_find) > 1:
                            del invoice_line[-2]
                    inv_line_range = list(range(len(invoice_line)))
                    inv_line_range.sort(reverse=True)
                    for inv_range in inv_line_range:
                        if not invoice_line[inv_range]:
                            continue
                        try:
                            if ',' in invoice_line[inv_range] and \
                                    '%' not in invoice_line[inv_range]:
                                float(
                                    invoice_line[inv_range].replace(',', ''))
                                cnt = inv_range
                                break
                            else:
                                float(invoice_line[inv_range])
                                cnt = inv_range
                                break
                        except ValueError:
                            tax_name = invoice_line[inv_range].strip(',')
                            domain_tax = ['|',
                                          ('name', 'ilike', tax_name),
                                          ('description', 'ilike',
                                           tax_name)]
                            if self.invoice_type == 'customer':
                                domain_tax.append(
                                    ('type_tax_use', '=', 'sale'))
                            elif self.invoice_type == 'supplier':
                                domain_tax.append(
                                    ('type_tax_use', '=', 'purchase'))
                            tax_rec = tax_obj.search(domain_tax, limit=1)
                            if tax_rec:
                                tax.append(tax_rec.id)
                    product_code = invoice_line[:1][0].strip('[]')
                    product = product_obj.search(
                        [('default_code', '=', product_code)])
                    if not product:
                        supplierinfo = supplierinfo_obj.search(
                            [('product_code', '=', product_code)])
                        if supplierinfo:
                            product = product_obj.search(
                                [('product_tmpl_id', '=',
                                  supplierinfo.product_tmpl_id.id)])
                    pro_desc = ' '.join(invoice_line[:cnt - 1])
                    if product:
                        dic = {
                            'product_id': product.id or False,
                            'name': product.name or False,
                            'quantity': float(
                                invoice_line[cnt - 1].replace(',',
                                                              '')),
                            'price_unit': float(
                                invoice_line[inv_range].replace(',', '')),
                            'uom_id': product.uom_id and product.uom_id.id or
                            False,
                            'invoice_line_tax_ids': [(6, 0, tax)]
                        }
                        line_list.append((0, 0, dic))
                    else:
                        dic = {
                            'name': pro_desc or '',
                            'invoice_line_tax_ids': [(6, 0, tax)],
                            'quantity': float(
                                invoice_line[cnt - 1].replace(',', '')),
                            'price_unit': float(
                                invoice_line[inv_range].replace(',', '')),
                        }
                        line_list.append((0, 0, dic))
        partner_list_filter = partner_list
        if partner_list_filter:
            partner = partner_obj.search(
                [('display_name', 'in', partner_list)])
        return partner, line_list

    @api.multi
    def read_invoice(self):
        ir_data_obj = self.env['ir.model.data']
        directory_name = tempfile.mkdtemp(suffix='image2txt')
        ctx = dict(self._context)
        # added context in currency id and tax type
        if self.invoice_type == 'customer':
            ctx.update({
                'currency_id': self.currency_id.id, 'tax_type':
                    'sale'
            })
        else:
            ctx.update({
                'currency_id': self.currency_id.id, 'tax_type':
                    'purchase'
            })

        line_list = []
        image_list = []
        img_attach = False
        try:
            if self.attachment_type == 'image':
                img_attach = self.attachment_ids and \
                             self.attachment_ids[0].image_attachment
                for attch_rec in self.attachment_ids:
                    image_list.append((0, 0,
                                       {
                                           'image_attachment':
                                               attch_rec.image_attachment or
                                               False
                                       }))
                    data_new = base64.decodestring(attch_rec.image_attachment)
                    fobj = tempfile.NamedTemporaryFile(delete=False)
                    fname = fobj.name
                    fobj.write(data_new)
                    fobj.close()
                    image = Image.open(fname)
                    image_to_text = tesserocr.image_to_text(image)
                    file_name = directory_name + "/" + attch_rec.filename
                    image_file = open(file_name, 'wb')
                    image_file.write(image_to_text.encode('UTF-8', 'ignore'))
                    image_file.close()
                    new_image_file = open(file_name, 'r')
                    partner, line_list = self.get_pdf_or_image_data(
                        new_image_file, line_list)
                    new_image_file.close()
                    os.remove(fname)

            elif self.attachment_type == 'pdf':
                self.check_pdf_file()
                file_name = directory_name + "/temppdf"
                new_file = open(file_name, 'wb')
                directory_name_new = tempfile.mkdtemp(suffix='tempimagenew')
                directory_text = tempfile.mkdtemp(suffix='temptext')
                content = base64.b64decode(self.pdf_attachment)
                new_file.write(content)
                new_file.close()
                command_convert = 'convert -density 700 ' + file_name + \
                                  ' -depth 8 -alpha off ' + directory_text + \
                                  '/file_code.tiff'
                os.system(command_convert)
                if self.language.iso_369_3_code:
                    iso_369_3_code = self.language.iso_369_3_code
                else:
                    raise Warning(_("Selected Language not Supported."))
                con_text = 'tesseract ' + directory_text + \
                           '/file_code.tiff ' + directory_text + \
                           '/output_code' + \
                           ' -l ' + iso_369_3_code + ' '
                os.system(con_text)
                if not os.path.exists(directory_text + '/output_code.txt'):
                    shutil.rmtree(directory_text)
                    shutil.rmtree(directory_name_new)
                    raise Warning(
                        _("Selected language not matched with tesseract-ocr\
                         package."
                          "\nInstall related package!"
                          "\nFor Reference find in: invoice_import_ocr > doc\
                           > User Reference.txt"))
                text_file = open(directory_text + '/output_code.txt', 'r')
                partner, line_list = self.get_pdf_or_image_data(
                    text_file, line_list)
                import wand.image as image
                with image.Image(filename=file_name) as img:
                    img.save(filename=directory_name_new + '/page.jpg')
                dirs = os.listdir(directory_name_new)
                for pdf_to_image_file in dirs:
                    with open(directory_name_new + '/' + pdf_to_image_file,
                              "rb") as imagefile:
                        str_new = base64.b64encode(imagefile.read())
                        image_list.append((0, 0,
                                           {
                                               'image_attachment':
                                                   str_new or False
                                           }))
                        image_list.reverse()
                self.attachment_ids = image_list
                img_attach = self.attachment_ids and \
                    self.attachment_ids[0].image_attachment
                shutil.rmtree(directory_name_new)
                shutil.rmtree(directory_text)

            import_form_id = ir_data_obj.get_object_reference(
                'invoice_import_ocr', 'import_invoice_wizard_form')[1]
            company_id = self._context.get(
                'company_id', self.env.user.company_id.id)
            if self.invoice_type == 'customer':
                journal_domain = [
                    ('type', '=', 'sale'), ('company_id', '=', company_id)]
                type_invoice = 'out_invoice'
            elif self.invoice_type == 'supplier':
                journal_domain = [
                    ('type', '=', 'purchase'), ('company_id', '=', company_id)]
                type_invoice = 'in_invoice'
            journal_id = self.env['account.journal'].search(
                journal_domain, limit=1)
            if not partner:
                ctx.update({
                    'default_invoice_line_ids': line_list,
                    'default_image_attachment': img_attach,
                    'default_attachment_ids': image_list,
                    'invoice_type': self.invoice_type,
                    'default_journal_id': journal_id and journal_id.id or
                    False,
                    'default_type': type_invoice
                })
            else:
                ctx.update({
                    'default_partner_id': partner.id,
                    'default_invoice_line_ids': line_list,
                    'default_image_attachment': img_attach,
                    'default_attachment_ids': image_list,
                    'invoice_type': self.invoice_type,
                    'default_journal_id': journal_id and journal_id.id or
                    False,
                    'default_type': type_invoice
                })
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'name': _('Invoice Import'),
                'view_mode': 'form',
                'res_model': 'import.invoice.wizard',
                'views': [(import_form_id, 'form')],
                'view_id': import_form_id,
                'target': 'inline',
                'context': ctx,
            }
        finally:
            shutil.rmtree(directory_name)


class ImportInvoiceWizard(models.TransientModel):
    _name = 'import.invoice.wizard'

    partner_id = fields.Many2one('res.partner', "Partner")
    partner = fields.Char("Partner")
    image_attachment = fields.Binary("Image Attachment")
    invoice_line_ids = fields.One2many('import.invoice.line.wizard',
                                       'invoice_wizrd_id', 'Invoice Line')
    new_partner = fields.Boolean('Create New Partner')
    attachment_ids = fields.One2many('invoice.wizard.attachment',
                                     'import_invoice_id',
                                     string='Image Attachment')
    count_image = fields.Integer('Count Image')

    @api.multi
    def create_partner(self):
        if self._context.get('invoice_type') == 'customer':
            customer = True
            supplier = False
        else:
            customer = False
            supplier = True
        if not self.partner_id:
            partner_rec = self.env['res.partner'].create(
                {
                    'name': self.partner, 'type': "contact",
                    'customer': customer, 'supplier': supplier
                })
            return partner_rec

    @api.multi
    def next_image(self):
        invoice_line_list = [attachment.image_attachment for attachment in
                             self.attachment_ids]
        for rec in self:
            rec.count_image += 1
            if len(invoice_line_list) == rec.count_image:
                rec.count_image = 0
            rec.image_attachment = invoice_line_list[rec.count_image]

    @api.multi
    def previous_image(self):
        invoice_line_list = [attachment.image_attachment for attachment in
                             self.attachment_ids]
        for rec in self:
            rec.count_image -= 1
            if rec.count_image < 0:
                rec.count_image = 0
            rec.image_attachment = invoice_line_list[rec.count_image]

    @api.multi
    def import_invoice(self):
        account_invoice_obj = self.env['account.invoice']
        invoice_line_obj = self.env['account.invoice.line']
        form_view_ref = False
        ctx = dict(self._context)
        if ctx.get('invoice_type') == 'customer':
            form_view_ref = self.env.ref(
                'account.invoice_form', False).id
        elif ctx.get('invoice_type') == 'supplier':
            form_view_ref = self.env.ref(
                'account.invoice_supplier_form', False).id
        if self.new_partner:
            partner_rec = self.with_context(ctx).create_partner()
            ctx.update({'default_partner_id': partner_rec.id})
        else:
            ctx.update({'default_partner_id': self.partner_id.id})
        invoice_line_list = []
        for invoice_line in self.invoice_line_ids:
            journal = account_invoice_obj._default_journal()
            account_id = invoice_line_obj.with_context({
                'journal_id': journal.id,
                'type': ctx.get('invoice_type') == 'customer' and 'out_invoice'
            })._default_account()
            line_vals = {
                'product_id': invoice_line.product_id.id or False,
                'name': invoice_line.product_id.name or invoice_line.name,
                'quantity': invoice_line.quantity,
                'price_unit': invoice_line.price_unit,
                'account_id': account_id,
                'uom_id': invoice_line.product_id.uom_id and
                invoice_line.product_id.uom_id.id or False,
                'invoice_line_tax_ids': [
                    (6, 0, invoice_line.invoice_line_tax_ids.ids)]
            }
            invoice_line_list.append(line_vals)
            ctx.update({'default_invoice_line_ids': invoice_line_list})
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice',
            'views': [(form_view_ref, 'form')],
            'view_id': form_view_ref,
            'context': ctx,
        }

    @api.multi
    def discard_invoice(self):
        tee_view_ref = self.env.ref('account.invoice_tree', False)
        form_view_ref = self.env.ref('account.invoice_form', False)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Customer Invoices'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'target': 'main',
            'views': [(tee_view_ref.id, 'tree'),
                      (form_view_ref.id, 'form')],
        }


class ImportInvoiceLineWizard(models.TransientModel):
    _name = 'import.invoice.line.wizard'

    invoice_wizrd_id = fields.Many2one('import.invoice.wizard',
                                       "Invoice Wizard Ref")
    product_id = fields.Many2one('product.product', "Product")
    name = fields.Char('Description')
    quantity = fields.Float('Quantity')
    price_unit = fields.Float('Price Unit')
    invoice_line_tax_ids = fields.Many2many(comodel_name='account.tax',
                                            string='Taxes',
                                            )
