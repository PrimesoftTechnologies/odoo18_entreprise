# -*- coding: utf-8 -*-
from odoo import fields, models, tools


class ShippingOrderReport(models.Model):
    """
    Read-only reporting model backing the Onshore / Shipment Report.

    It flattens one row per Shipping Order (joining its cargo lines and its
    latest Clearance Record) so the fields the client's Excel template
    tracks (Antrak/PO ref, mode, ports, ETA/ATA, duties, clearance dates,
    container info, invoicing, etc.) can be sliced with Odoo's Pivot / List
    / Graph views instead of a fixed spreadsheet layout.

    Being a SQL VIEW (_auto = False) it is always in sync with live data,
    read-only, and fast to aggregate over — exactly what a pivot needs.

    NOTE: A few template columns (Truck No., Driver's Name, ETD/ATD
    Truck-Border-Site, Demurrage days/amount) live on models not included
    in what you shared (e.g. `transport.assignment`, a demurrage tracker).
    They are left as TODO placeholders below — add them the same way once
    those models/fields are confirmed.
    """
    _name = 'shipping.order.report'
    _description = 'Onshore / Shipment Report (Pivot Analysis)'
    _auto = False
    _order = 'eta desc, id desc'

    # ── Identification ────────────────────────────────────────────
    shipping_order_id = fields.Many2one('shipping.order', string='Shipping Order', readonly=True)
    name = fields.Char(string='SAS Logistics Ref', readonly=True)
    client_po_number = fields.Char(string='PO No.', readonly=True)
    supplier_invoice_no = fields.Char(string='Invoice Number', readonly=True)

    # ── Parties ────────────────────────────────────────────────────
    shipper_id = fields.Many2one('res.partner', string='Supplier / Shipper', readonly=True)
    consignee_id = fields.Many2one('res.partner', string='Consignee (Antrak/Client)', readonly=True)
    agent_id = fields.Many2one('res.partner', string='Forwarding Agent', readonly=True)
    customer_relation_user_id = fields.Many2one('res.users', string='Customer Relations Officer', readonly=True)

    # ── Routing / Mode ────────────────────────────────────────────
    order_type = fields.Selection([
        ('import', 'Import'), ('export', 'Export'), ('transit', 'Transit'),
        ('domestic', 'Domestic'), ('local delivery', 'Local Delivery'), ('other', 'Others'),
    ], string='Order Type', readonly=True)
    transport_mode = fields.Selection([
        ('sea', 'Sea'), ('air', 'Air'), ('land', 'Road'),
    ], string='Mode', readonly=True)
    loading_port_id = fields.Many2one('freight.port', string='Origin (POL)', readonly=True)
    discharging_port_id = fields.Many2one('freight.port', string='Destination (POD)', readonly=True)
    vessel_flight_name = fields.Char(string='Vessel / Flight Name', readonly=True)
    voyage_flight_number = fields.Char(string='Voyage / Flight No.', readonly=True)
    bl_awb_number = fields.Char(string='Bill No. / AWB No.', readonly=True)
    bl_awb_date = fields.Date(string='B/L / AWB Date', readonly=True)

    # ── Dates ─────────────────────────────────────────────────────
    order_date = fields.Date(string='Order / Pre-Alert Date', readonly=True)
    etd = fields.Datetime(string='ETD', readonly=True)
    atd = fields.Datetime(string='ATD', readonly=True)
    eta = fields.Datetime(string='ETA', readonly=True)
    ata = fields.Datetime(string='ATA', readonly=True)

    # ── Status ────────────────────────────────────────────────────
    state = fields.Selection([
        ('draft', 'Draft'), ('submitted', 'Submitted'), ('confirmed', 'Confirmed'),
        ('arrived', 'Arrived'), ('clearing', 'Clearing'), ('cleared', 'Cleared'),
        ('received', 'Stock Received'), ('transported', 'Transported'),
        ('delivered', 'Delivered'), ('done', 'Done'), ('cancelled', 'Cancelled'),
    ], string='Equipment / Shipment Status', readonly=True)
    is_overdue = fields.Boolean(string='Overdue', readonly=True)
    remarks = fields.Text(string='Comments', readonly=True)

    # ── Cargo (aggregated from shipping.order.line) ─────────────────
    container_numbers = fields.Char(string='Container No.(s)', readonly=True)
    container_types = fields.Char(string='Equipment Type(s)', readonly=True)
    cargo_descriptions = fields.Char(string='Description', readonly=True)
    total_quantity = fields.Float(string='Total Qty', readonly=True)
    total_weight = fields.Float(string='Cargo Gross Weight (kg)', readonly=True)
    total_volume = fields.Float(string='Total Volume (cbm)', readonly=True)
    total_packages = fields.Integer(string='Total Packages', readonly=True)

    # ── Duties / Customs (from shipping.order) ──────────────────────
    assessed_date = fields.Date(string='Duties Assessed (Due) Date', readonly=True)
    duty_amount = fields.Monetary(string='Duty Amount', readonly=True, currency_field='currency_id')
    duty_paid_date = fields.Date(string='Duties Paid - Actual', readonly=True)
    rfd_date = fields.Date(string='RFD Date', readonly=True)

    # ── Delivery Order ──────────────────────────────────────────────
    do_number = fields.Char(string='Delivery Order (DO) No.', readonly=True)
    do_date = fields.Date(string='DO Date', readonly=True)
    do_expiry_date = fields.Date(string='DO Expiry Date', readonly=True)

    # ── Clearance Record (latest one linked to the order) ───────────
    clearance_id = fields.Many2one('clearance.record', string='Clearance Record', readonly=True)
    clearance_name = fields.Char(string='Clearance Ref', readonly=True)
    clearance_handler = fields.Selection([
        ('our', 'SAS Logistics (In-House)'), ('other', 'Third-Party Agent'),
    ], string='Clearing Handler', readonly=True)
    clearance_state = fields.Selection([
        ('draft', 'Draft'), ('in_progress', 'In Progress'),
        ('done', 'Completed'), ('cancelled', 'Cancelled'),
    ], string='Clearance Status', readonly=True)
    clearance_deadline = fields.Date(string='Import Clearance Due', readonly=True)
    clearance_completed_date = fields.Date(string='Import Clearance Actual', readonly=True)
    gate_pass_number = fields.Char(string='Gate Pass No.', readonly=True)
    gate_pass_date = fields.Date(string='Gate Pass Date', readonly=True)
    cargo_released = fields.Boolean(string='Cargo Released', readonly=True)
    cargo_release_date = fields.Date(string='Cargo Release Date', readonly=True)
    container_deposit_amount = fields.Monetary(string='Container Deposit Amount', readonly=True, currency_field='currency_id')
    container_deposit_refunded = fields.Boolean(string='Deposit Refunded', readonly=True)
    clearance_duty_tax = fields.Monetary(string='Total Duty & Tax (Clearance)', readonly=True, currency_field='currency_id')
    clearance_total_cost = fields.Monetary(string='Total Clearance Cost', readonly=True, currency_field='currency_id')

    # ── Financials (shipping.order) ─────────────────────────────────
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    freight_charges = fields.Monetary(string='Freight Charges', readonly=True, currency_field='currency_id')
    insurance_amount = fields.Monetary(string='Insurance Amount', readonly=True, currency_field='currency_id')
    other_charges = fields.Monetary(string='Other Charges', readonly=True, currency_field='currency_id')
    total_amount = fields.Monetary(string='Total Amount', readonly=True, currency_field='currency_id')

    # ── TODO placeholders (need transport.assignment / demurrage models) ─
    # truck_number, driver_name, etd_truck, atd_truck, eta_border, ata_border,
    # etd_border, atd_border, eta_site, ata_site, etd_site, atd_site,
    # container_returned, dem_free_days, dem_start_date, total_dem_days,
    # total_dem_amount, services_invoice_id, det_dem_invoice_id, other_invoice_id

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    so.id                           AS id,
                    so.id                           AS shipping_order_id,
                    so.name                         AS name,
                    so.client_po_number             AS client_po_number,
                    so.supplier_invoice_no          AS supplier_invoice_no,
                    so.shipper_id                   AS shipper_id,
                    so.consignee_id                 AS consignee_id,
                    so.agent_id                     AS agent_id,
                    so.customer_relation_user_id    AS customer_relation_user_id,
                    so.order_type                   AS order_type,
                    so.transport_mode               AS transport_mode,
                    so.loading_port_id              AS loading_port_id,
                    so.discharging_port_id          AS discharging_port_id,
                    so.vessel_flight_name           AS vessel_flight_name,
                    so.voyage_flight_number         AS voyage_flight_number,
                    so.bl_awb_number                AS bl_awb_number,
                    so.bl_awb_date                  AS bl_awb_date,
                    so.order_date                   AS order_date,
                    so.etd                          AS etd,
                    so.atd                          AS atd,
                    so.eta                          AS eta,
                    so.ata                          AS ata,
                    so.state                        AS state,
                    so.remarks                      AS remarks,
                    cl.container_numbers            AS container_numbers,
                    cl.container_types              AS container_types,
                    cl.cargo_descriptions           AS cargo_descriptions,
                    so.total_quantity               AS total_quantity,
                    so.total_weight                 AS total_weight,
                    so.total_volume                 AS total_volume,
                    so.total_packages               AS total_packages,
                    so.assessed_date                AS assessed_date,
                    so.duty_amount                  AS duty_amount,
                    so.duty_paid_date               AS duty_paid_date,
                    so.rfd_date                      AS rfd_date,
                    so.do_number                    AS do_number,
                    so.do_date                       AS do_date,
                    so.do_expiry_date               AS do_expiry_date,
                    cr.id                            AS clearance_id,
                    cr.name                          AS clearance_name,
                    cr.handler                       AS clearance_handler,
                    cr.state                         AS clearance_state,
                    cr.deadline                      AS clearance_deadline,
                    cr.final_assessment_date         AS clearance_completed_date,
                    cr.gate_pass_number              AS gate_pass_number,
                    cr.gate_pass_date                AS gate_pass_date,
                    cr.cargo_released                AS cargo_released,
                    cr.cargo_release_date            AS cargo_release_date,
                    cr.deposit_amount                AS container_deposit_amount,
                    cr.deposit_refunded              AS container_deposit_refunded,
                    cr.total_duty_tax                AS clearance_duty_tax,
                    cr.total_clearance_cost          AS clearance_total_cost,
                    so.currency_id                   AS currency_id,
                    so.freight_charges               AS freight_charges,
                    so.insurance_amount              AS insurance_amount,
                    so.other_charges                 AS other_charges,
                    so.total_amount                  AS total_amount
                FROM shipping_order so
                LEFT JOIN (
                    SELECT
                        order_id,
                        string_agg(DISTINCT NULLIF(container_number, ''), ', ') AS container_numbers,
                        string_agg(DISTINCT NULLIF(container_type, ''), ', ')   AS container_types,
                        string_agg(DISTINCT NULLIF(cargo_description, ''), ', ') AS cargo_descriptions
                    FROM shipping_order_line
                    GROUP BY order_id
                ) cl ON cl.order_id = so.id
                LEFT JOIN LATERAL (
                    SELECT *
                    FROM clearance_record c
                    WHERE c.shipping_order_id = so.id
                    ORDER BY c.id DESC
                    LIMIT 1
                ) cr ON true
            )
        """ % self._table)
