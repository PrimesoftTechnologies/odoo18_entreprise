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
            rejected_count: 0,
            survey_done_count: 0,
            report_submitted_count: 0,
            completed_count: 0,
            total_count: 0,
            total_amount: 0,
            lead_count: 0,
            ticket_count: 0,
            engineer_data: [],
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
                this.state.draft_count =
                    result.draft_count || 0;

                this.state.pending_count =
                    result.pending_count || 0;

                this.state.rejected_count =
                    result.rejected_count || 0;

                this.state.survey_done_count =
                    result.survey_done_count || 0;

                this.state.report_submitted_count =
                    result.report_submitted_count || 0;

                this.state.completed_count =
                    result.completed_count || 0;

                this.state.total_count =
                    result.total_count || 0;

                this.state.total_amount =
                    result.total_amount || 0;

                this.state.lead_count =
                    result.lead_count || 0;

                this.state.ticket_count =
                    result.ticket_count || 0;

                this.state.engineer_data =
                    result.engineer_data || [];

                this.state.currency_code =
                    result.currency_code || "";

                this.state.currency_symbol =
                    result.currency_symbol || "";
            }
        } catch (error) {
            console.error(
                "Error fetching dashboard data:",
                error
            );
        }
    }

    get maxActivityCount() {
        return Math.max(
            this.state.lead_count,
            this.state.ticket_count,
            1
        );
    }

    get leadBarHeight() {
        if (!this.state.lead_count) {
            return 0;
        }

        return (
            this.state.lead_count /
            this.maxActivityCount
        ) * 170;
    }

    get ticketBarHeight() {
        if (!this.state.ticket_count) {
            return 0;
        }

        return (
            this.state.ticket_count /
            this.maxActivityCount
        ) * 170;
    }

    get leadBarY() {
        return 200 - this.leadBarHeight;
    }

    get ticketBarY() {
        return 200 - this.ticketBarHeight;
    }

    get leadValueY() {
        return Math.max(
            20,
            this.leadBarY - 10
        );
    }

    get ticketValueY() {
        return Math.max(
            20,
            this.ticketBarY - 10
        );
    }

    get maxEngineerCount() {
        return Math.max(
            ...this.state.engineer_data.map(
                engineer => engineer.count
            ),
            1
        );
    }

    getEngineerBarHeight(count) {
        if (!count) {
            return 0;
        }

        return (
            count /
            this.maxEngineerCount
        ) * 170;
    }

    getEngineerBarY(count) {
        return 200 -
            this.getEngineerBarHeight(count);
    }

    getEngineerValueY(count) {
        return Math.max(
            20,
            this.getEngineerBarY(count) - 10
        );
    }

    formatAmount(amount) {
        return Number(
            amount || 0
        ).toLocaleString("en-US", {
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
                ],
            ]);
        } else if (stage === "rejected") {
            domain.push([
                "state",
                "=",
                "rejected",
            ]);
        } else if (stage === "survey_done") {
            domain.push([
                "state",
                "=",
                "survey_done",
            ]);
        } else if (stage === "report_submitted") {
            domain.push([
                "state",
                "=",
                "report_submitted",
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

EngineeringDashboard.template =
    "engineering_dashboard_template";

registry
    .category("actions")
    .add(
        "engineering_dashboard_tag",
        EngineeringDashboard
    );