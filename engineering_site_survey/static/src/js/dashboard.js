/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";

export class EngineeringDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");

        this.state = useState({
            draft_count: 0,
            pending_count: 0,
            completed_count: 0,
            total_count: 0,
            total_amount: 0,
            currency_code: "",
            currency_symbol: "",
            from_date: "",
            to_date: "",
            stage: "all",
        });

        onWillStart(async () => {
            await this.fetchData();
        });
    }

    async fetchData() {
        try {
            const result = await this.orm.call(
                "engineering.site.survey",
                "get_engineering_dashboard_data",
                [],
                {
                    from_date: this.state.from_date || false,
                    to_date: this.state.to_date || false,
                    stage: this.state.stage || "all",
                }
            );

            if (result) {
                this.state.draft_count = result.draft_count;
                this.state.pending_count = result.pending_count;
                this.state.completed_count = result.completed_count;
                this.state.total_count = result.total_count;
                this.state.total_amount = result.total_amount;
                this.state.currency_code = result.currency_code;
                this.state.currency_symbol = result.currency_symbol;
            }
        } catch (error) {
            console.error(
                "Error fetching dashboard data:",
                error
            );
        }
    }

    formatAmount(amount) {
        return Number(amount || 0).toLocaleString("en-US", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    onSearchClick(ev) {
        ev.preventDefault();
        this.fetchData();
    }

    onViewDetails(stage) {
        const domain = [];

        if (this.state.from_date) {
            domain.push([
                "create_date",
                ">=",
                this.state.from_date,
            ]);
        }

        if (this.state.to_date) {
            domain.push([
                "create_date",
                "<=",
                this.state.to_date,
            ]);
        }

        if (stage === "draft") {
            domain.push([
                "state",
                "=",
                "draft",
            ]);
        } else if (stage === "pending") {
            domain.push([
                "state",
                "in",
                [
                    "submitted",
                    "approved",
                    "survey_done",
                    "report_submitted",
                ],
            ]);
        } else if (stage === "completed") {
            domain.push([
                "state",
                "=",
                "completed",
            ]);
        }

        this.actionService.doAction({
            name: "Filtered Site Surveys",
            type: "ir.actions.act_window",
            res_model: "engineering.site.survey",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain: domain,
            target: "current",
        });
    }
}

EngineeringDashboard.template = "engineering_dashboard_template";

registry
    .category("actions")
    .add(
        "engineering_dashboard_tag",
        EngineeringDashboard
    );