/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class EstateOwlDashboard extends Component {
    static template = "ad_estate_base.EstateOwlDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            data: {
                total_projects: 0,
                active_projects: 0,
                total_buildings: 0,
                total_units: 0,
                available_units: 0,
                reserved_units: 0,
                sold_units: 0,
                leased_units: 0,
                sales_revenue: 0.0,
                active_contracts: 0,
                total_offers: 0,
                monthly_rent_roll: 0.0,
                pending_maintenance: 0,
                recent_projects: [],
                recent_transactions: [],
                project_stage_data: {},
                unit_type_breakdown: [],
            }
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        const result = await this.orm.call(
            "estate.dashboard",
            "get_owl_dashboard_data",
            []
        );
        this.state.data = result;
    }

    formatCurrency(val) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            maximumFractionDigits: 0
        }).format(val || 0);
    }

    openProjects() {
        this.action.doAction({
            name: "Projects",
            type: "ir.actions.act_window",
            res_model: "estate.project",
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
        });
    }

    openUnits() {
        this.action.doAction({
            name: "Properties & Units",
            type: "ir.actions.act_window",
            res_model: "estate.unit",
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
        });
    }

    openSales() {
        this.action.doAction({
            name: "Sales Contracts",
            type: "ir.actions.act_window",
            res_model: "estate.sale.contract",
            views: [[false, "list"], [false, "pivot"], [false, "form"]],
        });
    }

    openTenancy() {
        this.action.doAction({
            name: "Lease Contracts",
            type: "ir.actions.act_window",
            res_model: "estate.lease.contract",
            views: [[false, "list"], [false, "pivot"], [false, "form"]],
        });
    }

    openProjectRecord(projectId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "estate.project",
            res_id: projectId,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("estate_owl_dashboard_action", EstateOwlDashboard);
