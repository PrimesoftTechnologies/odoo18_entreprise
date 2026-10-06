/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";
import { Component, useState, onWillStart, onMounted, useRef } from "@odoo/owl";

export class SasDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ data: null, loading: true });

        this.stateChartRef = useRef("stateChart");
        this.modeChartRef = useRef("modeChart");
        this.dutyChartRef = useRef("dutyChart");
        this.consigneeChartRef = useRef("consigneeChart");

        onWillStart(async () => {
            await loadJS("/web/static/lib/Chart/Chart.js");
            this.state.data = await this.orm.call("shipping.order", "get_dashboard_data", []);
            this.state.loading = false;
        });

        onMounted(() => {
            if (this.state.data) {
                this._renderCharts();
            }
        });
    }

    _renderCharts() {
        const { charts } = this.state.data;
        const palette = ["#305496", "#70AD47", "#FFC000", "#C00000", "#7030A0", "#00B0F0", "#ED7D31", "#A5A5A5"];

        if (this.stateChartRef.el) {
            new Chart(this.stateChartRef.el.getContext("2d"), {
                type: "doughnut",
                data: {
                    labels: charts.by_state.map((r) => r.label),
                    datasets: [{ data: charts.by_state.map((r) => r.value), backgroundColor: palette }],
                },
                options: { plugins: { legend: { position: "right" } } },
            });
        }
        if (this.modeChartRef.el) {
            new Chart(this.modeChartRef.el.getContext("2d"), {
                type: "pie",
                data: {
                    labels: charts.by_mode.map((r) => r.label),
                    datasets: [{ data: charts.by_mode.map((r) => r.value), backgroundColor: palette }],
                },
            });
        }
        if (this.dutyChartRef.el) {
            new Chart(this.dutyChartRef.el.getContext("2d"), {
                type: "bar",
                data: {
                    labels: charts.duty_trend.map((r) => r.label),
                    datasets: [{
                        label: "Duty Amount",
                        data: charts.duty_trend.map((r) => r.value),
                        backgroundColor: "#305496",
                    }],
                },
                options: { plugins: { legend: { display: false } } },
            });
        }
        if (this.consigneeChartRef.el) {
            new Chart(this.consigneeChartRef.el.getContext("2d"), {
                type: "bar",
                data: {
                    labels: charts.top_consignees.map((r) => r.label),
                    datasets: [{
                        label: "Active Shipments",
                        data: charts.top_consignees.map((r) => r.value),
                        backgroundColor: "#70AD47",
                    }],
                },
                options: { indexAxis: "y", plugins: { legend: { display: false } } },
            });
        }
    }

    openReport(stateName) {
        this.action.doAction({
            name: "Shipping Orders",
            type: "ir.actions.act_window",
            res_model: "shipping.order",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: stateName ? [["state", "=", stateName]] : [],
        });
    }
}

SasDashboard.template = "sas.Dashboard";

registry.category("actions").add("sas_dashboard", SasDashboard);
