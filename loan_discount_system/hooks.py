# -*- coding: utf-8 -*-
import json


def restore_legacy(env):
    """Give Accounting > Loans back exactly as it was (undo any earlier redirect of this module)."""
    ICP = env['ir.config_parameter'].sudo()

    prefix = 'lds.legacy_menu_action.'
    for param in ICP.search([('key', 'like', prefix + '%')]):
        menu = env['ir.ui.menu'].browse(int(param.key[len(prefix):])).exists()
        if menu and param.value:
            menu.action = param.value
        param.unlink()

    prefix = 'lds.legacy_action_backup.'
    for param in ICP.search([('key', 'like', prefix + '%')]):
        action = env['ir.actions.act_window'].sudo().browse(int(param.key[len(prefix):])).exists()
        if action and param.value:
            data = json.loads(param.value)
            action.view_ids.unlink()
            action.write({
                'res_model': data['res_model'],
                'view_mode': data['view_mode'],
                'view_id': data['view_id'],
                'search_view_id': data['search_view_id'],
                'domain': data['domain'],
                'context': data['context'] or '{}',
                'res_id': data['res_id'],
            })
            for seq, mode, view_id in data.get('views', []):
                env['ir.actions.act_window.view'].sudo().create({
                    'act_window_id': action.id, 'sequence': seq,
                    'view_mode': mode, 'view_id': view_id,
                })
        param.unlink()


def uninstall_hook(env):
    xmlid = env['ir.model.data'].sudo().search([
        ('module', '=', 'loan_discount_system'),
        ('name', '=', 'view_bank_loan_form_lds_distributors'),
    ], limit=1)
    if xmlid:
        view = env['ir.ui.view'].sudo().browse(xmlid.res_id).exists()
        if view:
            view.unlink()
        xmlid.unlink()

    restore_legacy(env)
