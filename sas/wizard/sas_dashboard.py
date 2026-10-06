# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date, timedelta


class ShippingOrderDashboard(models.Model):
    """Extends shipping.order with a single RPC-friendly method that feeds
    the OWL dashboard. All queries go through the normal ORM (search_read /
    read_group) so existing ir.rule record rules are respected automatically
    -- an Officer only sees their own KPIs, a Manager sees everything.
    """
    _inherit = 'shipping.order'

    @api.model
    def get_dashboard_data(self):
        Order = self.env['shipping.order']
        Clearance = self.env['clearance.record']
        Transport = self.env['transport.assignment']

        today = date.today()
        month_start = today.replace(day=1)

        active_domain = [('state', 'not in', ('done', 'cancelled'))]

        # ---- KPI tiles ----
        total_active = Order.search_count(active_domain)
        overdue_count = Order.search_count(active_domain + [('is_overdue', '=', True)])
        in_clearing = Order.search_count([('state', '=', 'clearing')])
        cleared_this_month = Order.search_count([
            ('state', 'in', ('cleared', 'received', 'transported', 'delivered', 'done')),
            ('assessed_date', '>=', month_start),
        ])

        duty_group = Order.read_group(
            [('order_date', '>=', month_start)], ['duty_amount:sum'], []
        )
        duty_this_month = duty_group[0]['duty_amount'] if duty_group else 0.0

        cost_group = Clearance.read_group(
            [('clearance_date', '>=', month_start)], ['total_clearance_cost:sum'], []
        )
        clearance_cost_this_month = cost_group[0]['total_clearance_cost'] if cost_group else 0.0

        pending_trips = Transport.search_count([('state', 'in', ('draft', 'confirmed', 'in_progress'))])

        # ---- Charts ----
        # 1) Orders by state
        state_groups = Order.read_group(active_domain, ['id'], ['state'])
        state_labels = dict(Order._fields['state'].selection)
        by_state = [
            {'label': state_labels.get(g['state'], g['state']), 'value': g['state_count']}
            for g in state_groups
        ]

        # 2) Orders by transport mode (last 6 months)
        six_months_ago = today - timedelta(days=180)
        mode_groups = Order.read_group(
            [('order_date', '>=', six_months_ago)], ['id'], ['transport_mode']
        )
        mode_labels = dict(Order._fields['transport_mode'].selection)
        by_mode = [
            {'label': mode_labels.get(g['transport_mode'], g['transport_mode'] or 'Unknown'),
             'value': g['transport_mode_count']}
            for g in mode_groups
        ]

        # 3) Duty amount trend, last 6 months
        duty_trend = []
        for i in range(5, -1, -1):
            m_start = (month_start - timedelta(days=30 * i)).replace(day=1)
            m_end = (m_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            grp = Order.read_group(
                [('order_date', '>=', m_start), ('order_date', '<=', m_end)],
                ['duty_amount:sum'], []
            )
            duty_trend.append({
                'label': m_start.strftime('%b %Y'),
                'value': grp[0]['duty_amount'] if grp else 0.0,
            })

        # 4) Top consignees by shipment count (active orders)
        consignee_groups = Order.read_group(active_domain, ['id'], ['consignee_id'])
        consignee_groups.sort(key=lambda g: g['consignee_id_count'], reverse=True)
        top_consignees = [
            {'label': g['consignee_id'][1] if g['consignee_id'] else 'Unknown',
             'value': g['consignee_id_count']}
            for g in consignee_groups[:8]
        ]

        return {
            'kpis': {
                'total_active': total_active,
                'overdue_count': overdue_count,
                'in_clearing': in_clearing,
                'cleared_this_month': cleared_this_month,
                'duty_this_month': duty_this_month,
                'clearance_cost_this_month': clearance_cost_this_month,
                'pending_trips': pending_trips,
                'currency_symbol': self.env.company.currency_id.symbol,
            },
            'charts': {
                'by_state': by_state,
                'by_mode': by_mode,
                'duty_trend': duty_trend,
                'top_consignees': top_consignees,
            },
        }
