# -*- coding: utf-8 -*-
import json


def uninstall_hook(env):
    """Give the Accounting > Loans menu/action back to what it was before."""
    ICP = env['ir.config_parameter'].sudo()

    # menu fallback
    prefix = 'lds.legacy_menu_action.'
    for param in ICP.search([('key', 'like', prefix + '%')]):
        menu = env['ir.ui.menu'].browse(int(param.key[len(prefix):])).exists()
        if menu and param.value:
            menu.action = param.value
        param.unlink()

    # action (path 'loans')
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
