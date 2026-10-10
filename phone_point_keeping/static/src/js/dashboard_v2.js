/** @odoo-module */

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { session } from "@web/session";


class PhoneDashboard extends Component {

    static template = "phone_point_keeping.PhoneDashboard";

    setup() {

        this.action = useService("action");
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.dialog = useService("dialog");

        this.state = useState({

            activeTab: "dashboard",
            sidebarCollapsed: false,

            user: { name: "User" },

            dashboard: {
                today_sales: 0,
                gross_profit: 0,
                pending_debts: 0,
                sales_chart_available: false,
                top_brands: [],
            },

            dashboardFilters: { period: "all" },

            phones: [],
            brands: [],
            categories: [],
            conditions: [],
            customers: [],
            tradeIns: [],
            suppliers: [],
            staff: [],
            departments: [],

            tradeInFilters: { search: "", state: "" },

            showTradeInModal: false,

            newTradeIn: {
                customer_id: null,
                customer_phone: "",
                old_phone_model: "",
                old_phone_brand_id: null,
                old_phone_imei_1: "",
                old_phone_imei_2: "",
                old_phone_serial_number: "",
                old_phone_condition_id: null,
                old_phone_storage: "",
                old_phone_battery_health: "",
                old_phone_accessories: "",
                old_phone_physical_condition: "",
                old_phone_notes: "",
                estimated_value: 0,
                adjustment_amount: 0,
                trade_in_value: 0,
                new_phone_id: null,
                amount_to_pay: 0,
                amount_paid: 0,
                balance: 0,
                payment_method: "",
                payment_reference: "",
                notes: "",
            },

            stockFilters: {
                search: "",
                brand_id: null,
                category_id: null,
                condition_id: null,
                status: "",
            },

            currentPage: 1,
            itemsPerPage: 10,

            tradeInCurrentPage: 1,
            tradeInItemsPerPage: 10,

            supplierFilters: { search: "", status: "active" },
            supplierCurrentPage: 1,
            supplierItemsPerPage: 10,

            showSupplierModal: false,
            showEditSupplierModal: false,

            newSupplier: {
                name: "", phone: "", email: "", street: "",
                city: "", vat: "", contact_person: "", comment: "",
            },

            editSupplier: {
                id: null, name: "", phone: "", email: "", street: "",
                city: "", vat: "", contact_person: "", comment: "",
            },

            staffFilters: { search: "", status: "active" },
            staffCurrentPage: 1,
            staffItemsPerPage: 10,

            showStaffModal: false,
            showEditStaffModal: false,

            newStaff: {
                name: "", job_title: "", department_id: null,
                date_join: "", work_phone: "", mobile_phone: "",
                work_email: "", salary_amount: 0, commission_rate: 0, notes: "",
            },

            editStaff: {
                id: null, name: "", job_title: "", department_id: null,
                date_join: "", work_phone: "", mobile_phone: "",
                work_email: "", salary_amount: 0, commission_rate: 0, notes: "",
            },

            // =========================================================
            // REPORTS
            // =========================================================

            reportTab: "all",              // ✅ MPYA: "all" | "daily"

            reportFilters: { period: "all" },

            reportTotalSales: 0,
            reportTotalProfit: 0,
            reportPhonesSold: 0,
            reportPhonesInStock: 0,
            reportTotalTradeIns: 0,
            reportTotalDebts: 0,

            topSellingPhones: [],
            topCustomers: [],
            salesByBrand: [],

            // ✅ DAILY REPORT STATE (MPYA)
            dailyReportFilters: {
                from_date: "",
                to_date: "",
            },

            dailyReportLines: [],
            dailyReportTotalSales: 0,
            dailyReportTotalProfit: 0,
            dailyReportTotalQty: 0,

            categoryCurrentPage: 1,
            categoryItemsPerPage: 5,

            debts: [],

            debtFilters: { search: "", state: "" },
            debtCurrentPage: 1,
            debtItemsPerPage: 10,

            showDebtModal: false,
            showInstallmentsModal: false,

            selectedDebtId: null,
            currentDebtInstallments: [],

            newDebt: {
                customer_id: null,
                phone_id: null,
                phone_description: "",
                total_amount: 0,
                down_payment: 0,
                interest_rate: 0,
                num_installments: 1,
                interval_type: "monthly",
                first_due_date: "",
                payment_method: "",
                notes: "",
            },

            showPaymentModal: false,
            selectedInstallmentId: null,
            currentInstallment: null,

            paymentData: {
                paid_amount: 0,
                payment_date: "",
                payment_method: "",
                payment_reference: "",
                notes: "",
            },

            showModal: false,
            showEditModal: false,

            newPhoneImages: [],
            editPhoneNewImages: [],
            editPhoneExistingImages: [],

            editPhone: {
                id: null,
                model_name: "",
                brand_id: null,
                category_id: null,
                imei_1: "",
                imei_2: "",
                condition_id: null,
                buying_price: 0,
                selling_price: 0,
                quantity: 1,
                status: "in_stock",
            },

            newPhone: {
                model_name: "",
                brand_id: null,
                category_id: null,
                imei_1: "",
                imei_2: "",
                condition_id: null,
                buying_price: 0,
                selling_price: 0,
                quantity: 1,
                status: "in_stock",
            },

            newBrandName: "",
            newCategoryName: "",
            selectedBrandForCategory: null,
            newConditionName: "",

            posFilters: { search: "", brand_id: null },

            posCart: [],

            posData: {
                customer_id: null,
                customer_phone: "",
                payment_type: "cash",
                payment_method: "cash",
                amount_paid: 0,
                notes: "",
            },

            userAccesses: [],
            allowedTabs: [],

            showUserAccessModal: false,

            newUserAccess: {
                name: "", login: "", password: "", email: "",
                allow_dashboard: true, allow_pos: true, allow_phones: true,
                allow_trade_in: true, allow_debts: true, allow_purchases: true,
                allow_suppliers: true, allow_staff: false,
                allow_reports: true, allow_settings: false,
            },

            showEditUserAccessModal: false,

            editUserAccess: {
                id: null, user_id: null, name: "", login: "",
                password: "", email: "",
                allow_dashboard: true, allow_pos: true, allow_phones: true,
                allow_trade_in: true, allow_debts: true, allow_purchases: true,
                allow_suppliers: true, allow_staff: false,
                allow_reports: true, allow_settings: false,
            },

            // =========================================================
            // PURCHASES
            // =========================================================

            purchases: [],

            purchaseFilters: { search: "", state: "" },
            purchaseCurrentPage: 1,
            purchaseItemsPerPage: 10,

            showPurchaseModal: false,

            newPurchase: {
                supplier_id: null,
                date_order: "",
                date_expected: "",
                payment_method: "cash",
                notes: "",
            },

            newPurchaseLines: [],

            newPurchaseLine: {
                phone_id: null,
                phone_model: "",
                brand_id: null,
                category_id: null,
                condition_id: null,
                imei_1: "",
                imei_2: "",
                quantity: 1,
                price_unit: 0,
            },

            showQuickCreatePhoneModal: false,

            quickPhone: {
                model_name: "",
                brand_id: null,
                category_id: null,
                condition_id: null,
                imei_1: "",
                imei_2: "",
                buying_price: 0,
                selling_price: 0,
                quantity: 1,
            },

            showPurchaseDetailModal: false,
            currentPurchaseDetail: null,
            currentPurchaseLines: [],

            showReceivePurchaseModal: false,
            currentReceivePurchase: null,
            currentReceiveLines: [],
        });


        // ============================================================
        // ON WILL START
        // ============================================================

        onWillStart(async () => {

            try {
                const saved = localStorage.getItem("phone_sidebar_collapsed");
                this.state.sidebarCollapsed = saved === "1";
            } catch (e) {}

            // ✅ Set daily report default date = today
            const today = new Date().toISOString().split("T")[0];
            this.state.dailyReportFilters.from_date = today;
            this.state.dailyReportFilters.to_date = today;

            await this.loadCurrentUser();
            await this.loadCurrentUserTabs();

            await Promise.all([
                this.loadBrands(),
                this.loadCategories(),
                this.loadConditions(),
                this.loadCustomers(),
                this.loadSuppliers(),
                this.loadStaff(),
                this.loadDepartments(),
                this.loadUserAccesses(),
            ]);

            await this.loadPhones();

            await Promise.all([
                this.loadDebts(),
                this.loadTradeIns(),
                this.loadPurchases(),
            ]);

            await this.loadDashboard();
            await this.loadReports();
            await this._loadDailyReport();   // ✅ MPYA

        });

    }


    // ============================================================
    // TOGGLE SIDEBAR
    // ============================================================

    toggleSidebar(ev) {
        if (ev) ev.preventDefault();
        this.state.sidebarCollapsed = !this.state.sidebarCollapsed;
        try {
            localStorage.setItem(
                "phone_sidebar_collapsed",
                this.state.sidebarCollapsed ? "1" : "0"
            );
        } catch (e) {}
    }


    // ============================================================
    // HELPERS
    // ============================================================

    formatNumber(value) {
        const num = Number(value || 0);
        return num.toLocaleString("en-US", {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        });
    }


    getBrandName(brandId) {
        const brand = this.state.brands.find(b => b.id === Number(brandId));
        return brand ? brand.name : "-";
    }


    getConditionName(conditionId) {
        const cond = this.state.conditions.find(c => c.id === Number(conditionId));
        return cond ? cond.name : "-";
    }


    // ============================================================
    // RECEIVE MODAL — TOTAL HELPERS
    // ============================================================

    getTotalOrdered() {
        return (this.state.currentReceiveLines || []).reduce(
            (sum, line) => sum + (parseInt(line.quantity) || 0),
            0
        );
    }

    getTotalReceived() {
        return (this.state.currentReceiveLines || []).reduce(
            (sum, line) => sum + (parseInt(line.qty_received) || 0),
            0
        );
    }

    getTotalPending() {
        return (this.state.currentReceiveLines || []).reduce(
            (sum, line) => sum + (parseInt(line.qty_pending) || 0),
            0
        );
    }

    getTotalReceivingNow() {
        return (this.state.currentReceiveLines || []).reduce(
            (sum, line) => sum + (parseInt(line.receiving_now) || 0),
            0
        );
    }

    hasAnyReceivingNow() {
        return (this.state.currentReceiveLines || []).some(
            line => (parseInt(line.receiving_now) || 0) > 0
        );
    }


    // ============================================================
    // CURRENT USER
    // ============================================================

    async loadCurrentUser() {
        try {
            const userId = session.user_id;
            if (!userId) return;
            const users = await this.orm.searchRead(
                "res.users", [["id", "=", userId]], ["id", "name"]
            );
            if (users.length) {
                this.state.user = { name: users[0].name };
            }
        } catch (error) {
            console.error("Failed to load current user:", error);
        }
    }


    async loadCurrentUserTabs() {
        try {
            const tabs = await this.orm.call(
                "phone.user.access", "get_current_user_access", []
            );
            this.state.allowedTabs = Array.isArray(tabs) ? tabs : [];
        } catch (error) {
            console.error("Failed to load user tabs:", error);
            this.state.allowedTabs = [];
        }
    }


    hasTabAccess(tab) {
        if (!this.state.allowedTabs || !this.state.allowedTabs.length) {
            return true;
        }
        return this.state.allowedTabs.includes(tab);
    }


    get menuTabs() {
        const allTabs = [
            "dashboard", "pos", "phones", "trade_in", "debts",
            "purchases", "suppliers", "staff", "reports", "settings",
        ];
        if (!this.state.allowedTabs || !this.state.allowedTabs.length) {
            return allTabs;
        }
        return allTabs.filter(tab => this.state.allowedTabs.includes(tab));
    }


    // ============================================================
    // LOAD PHONES
    // ============================================================

    async loadPhones() {
        try {
            this.state.phones = await this.orm.searchRead(
                "phone.stock", [],
                [
                    "id", "model_name", "brand_id", "category_id",
                    "imei_1", "imei_2", "condition_id",
                    "buying_price", "selling_price", "quantity",
                    "gross_profit", "status", "image_count", "primary_image",
                ],
                { order: "id desc" }
            );
        } catch (error) {
            console.error("Failed to load phones:", error);
            this.notification.add("Failed to load phone stock.",
                { title: "Loading Error", type: "danger" });
        }
    }


    async loadBrands() {
        try {
            this.state.brands = await this.orm.searchRead(
                "phone.brand", [], ["id", "name"], { order: "name asc" }
            );
        } catch (error) { console.error("Failed to load brands:", error); }
    }


    async loadCategories() {
        try {
            this.state.categories = await this.orm.searchRead(
                "phone.category", [], ["id", "name", "brand_id"], { order: "name asc" }
            );
        } catch (error) { console.error("Failed to load categories:", error); }
    }


    async loadConditions() {
        try {
            this.state.conditions = await this.orm.searchRead(
                "phone.condition", [], ["id", "name"], { order: "name asc" }
            );
        } catch (error) { console.error("Failed to load conditions:", error); }
    }


    async loadCustomers() {
        try {
            this.state.customers = await this.orm.searchRead(
                "res.partner", [["active", "=", true]],
                ["id", "name", "phone", "mobile"],
                { order: "name asc", limit: 500 }
            );
        } catch (error) {
            console.error("Failed to load customers:", error);
            this.state.customers = [];
        }
    }


    async loadSuppliers() {
        try {
            this.state.suppliers = await this.orm.searchRead(
                "res.partner", [["supplier_rank", ">", 0]],
                ["id", "name", "phone", "email", "street", "city", "vat", "active"],
                { order: "name asc", limit: 500 }
            );
        } catch (error) {
            console.error("Failed to load suppliers:", error);
            this.state.suppliers = [];
        }
    }


    async loadStaff() {
        try {
            this.state.staff = await this.orm.searchRead(
                "hr.employee", [],
                ["id", "name", "job_title", "department_id",
                 "work_phone", "mobile_phone", "work_email", "active"],
                { order: "name asc", limit: 500 }
            );
        } catch (error) {
            console.error("Failed to load staff:", error);
            this.state.staff = [];
        }
    }


    async loadDepartments() {
        try {
            this.state.departments = await this.orm.searchRead(
                "hr.department", [], ["id", "name"], { order: "name asc" }
            );
        } catch (error) {
            console.error("Failed to load departments:", error);
            this.state.departments = [];
        }
    }


    async loadTradeIns() {
        try {
            this.state.tradeIns = await this.orm.searchRead(
                "phone.trade.in", [],
                [
                    "id", "name", "customer_id", "customer_phone",
                    "old_phone_model", "old_phone_brand_id",
                    "old_phone_imei_1", "old_phone_imei_2", "old_phone_serial_number",
                    "old_phone_condition_id", "old_phone_storage",
                    "old_phone_battery_health", "old_phone_accessories",
                    "old_phone_physical_condition", "old_phone_notes",
                    "estimated_value", "adjustment_amount", "trade_in_value",
                    "new_phone_id", "new_phone_model", "new_phone_imei_1",
                    "new_phone_imei_2", "new_phone_price",
                    "amount_to_pay", "amount_paid", "balance",
                    "payment_method", "payment_reference",
                    "date", "state", "notes",
                ],
                { order: "id desc" }
            );
        } catch (error) {
            console.error("Failed to load trade-ins:", error);
            this.state.tradeIns = [];
        }
    }


    async loadDebts() {
        try {
            this.state.debts = await this.orm.searchRead(
                "phone.debt", [],
                [
                    "id", "name", "customer_id", "phone_id", "phone_description",
                    "total_amount", "down_payment", "financed_amount",
                    "interest_rate", "interest_amount", "total_financed",
                    "paid_amount", "balance", "num_installments",
                    "installment_amount", "interval_type",
                    "date", "first_due_date", "payment_method", "state", "notes",
                    "installment_count", "paid_installments", "pending_installments",
                ],
                { order: "id desc" }
            );
        } catch (error) {
            console.error("Failed to load debts:", error);
            this.state.debts = [];
        }
    }


    async loadPurchases() {
        try {
            this.state.purchases = await this.orm.searchRead(
                "phone.purchase.order", [],
                [
                    "id", "name", "supplier_id", "supplier_phone",
                    "date_order", "date_expected",
                    "payment_method", "state",
                    "subtotal", "total", "amount_paid", "balance",
                    "line_count", "notes",
                    "total_ordered", "total_received", "total_pending",
                    "is_fully_received",
                    "received_amount", "can_be_paid",
                ],
                { order: "id desc" }
            );
        } catch (error) {
            console.error("Failed to load purchases:", error);
            this.state.purchases = [];
        }
    }


    async loadUserAccesses() {
        try {
            this.state.userAccesses = await this.orm.searchRead(
                "phone.user.access", [],
                [
                    "id", "user_id", "user_login", "user_email",
                    "allow_dashboard", "allow_pos", "allow_phones",
                    "allow_trade_in", "allow_debts", "allow_purchases",
                    "allow_suppliers", "allow_staff", "allow_reports",
                    "allow_settings", "active",
                ],
                { order: "id desc", context: { active_test: false } }
            );
        } catch (error) {
            console.error("Failed to load user accesses:", error);
            this.state.userAccesses = [];
        }
    }


    // ============================================================
    // LOAD DASHBOARD
    // ============================================================

    async loadDashboard() {
        try {
            const period = this.state.dashboardFilters.period || "all";
            const dateDomain = this._getReportDateDomain(period);

            const orders = await this.orm.searchRead(
                "phone.sale.order", dateDomain, ["id", "total", "total_profit"]
            );
            const totalSales = orders.reduce((sum, o) => sum + Number(o.total || 0), 0);
            const totalProfit = orders.reduce((sum, o) => sum + Number(o.total_profit || 0), 0);

            const activeDebts = await this.orm.searchRead(
                "phone.debt",
                [["state", "in", ["active", "overdue"]]],
                ["id", "balance"]
            );
            const pendingDebts = activeDebts.reduce((sum, d) => sum + Number(d.balance || 0), 0);

            const brandCounts = {};
            this.state.phones.forEach(phone => {
                if (!phone.brand_id) return;
                const brandId = phone.brand_id[0];
                const brandName = phone.brand_id[1];
                if (!brandCounts[brandId]) {
                    brandCounts[brandId] = { id: brandId, name: brandName, count: 0 };
                }
                brandCounts[brandId].count += 1;
            });

            const topBrands = Object.values(brandCounts)
                .sort((a, b) => b.count - a.count)
                .slice(0, 5);

            this.state.dashboard = {
                today_sales: totalSales,
                gross_profit: totalProfit,
                pending_debts: pendingDebts,
                sales_chart_available: orders.length > 0,
                top_brands: topBrands,
            };
        } catch (error) {
            console.error("Failed to load dashboard:", error);
        }
    }


    onDashboardPeriodChange(ev) {
        this.state.dashboardFilters.period = ev.target.value || "all";
        this.loadDashboard();
    }


    _getReportDateDomain(period) {
        const today = new Date();
        let startDate = null;
        let endDate = null;

        if (period === "today") {
            startDate = new Date(today.getFullYear(), today.getMonth(), today.getDate());
            endDate = new Date(today.getFullYear(), today.getMonth(), today.getDate() + 1);
        } else if (period === "week") {
            const dayOfWeek = today.getDay() || 7;
            startDate = new Date(today);
            startDate.setDate(today.getDate() - dayOfWeek + 1);
            startDate.setHours(0, 0, 0, 0);
            endDate = new Date(startDate);
            endDate.setDate(startDate.getDate() + 7);
        } else if (period === "month") {
            startDate = new Date(today.getFullYear(), today.getMonth(), 1);
            endDate = new Date(today.getFullYear(), today.getMonth() + 1, 1);
        } else if (period === "year") {
            startDate = new Date(today.getFullYear(), 0, 1);
            endDate = new Date(today.getFullYear() + 1, 0, 1);
        }

        if (!startDate || !endDate) return [];

        const formatDate = (d) => {
            const yyyy = d.getFullYear();
            const mm = String(d.getMonth() + 1).padStart(2, "0");
            const dd = String(d.getDate()).padStart(2, "0");
            return `${yyyy}-${mm}-${dd} 00:00:00`;
        };

        return [["date", ">=", formatDate(startDate)], ["date", "<", formatDate(endDate)]];
    }


    // ============================================================
    // REPORT TAB
    // ============================================================

    async onReportTabChange(tab) {
        this.state.reportTab = tab || "all";

        if (this.state.reportTab === "daily") {
            await this._loadDailyReport();
        } else {
            await this.loadReports();
        }
    }


    // ============================================================
    // DAILY REPORT — FILTERS
    // ============================================================

    onDailyReportFromChange(ev) {
        this.state.dailyReportFilters.from_date = ev.target.value || "";
        this._loadDailyReport();
    }

    onDailyReportToChange(ev) {
        this.state.dailyReportFilters.to_date = ev.target.value || "";
        this._loadDailyReport();
    }

    async resetDailyReportFilters() {
        const today = new Date().toISOString().split("T")[0];
        this.state.dailyReportFilters.from_date = today;
        this.state.dailyReportFilters.to_date = today;
        await this._loadDailyReport();
    }


    // ============================================================
    // DAILY REPORT — LOAD
    // ============================================================

    async _loadDailyReport() {
        try {
            const fromDate = this.state.dailyReportFilters.from_date;
            const toDate = this.state.dailyReportFilters.to_date;

            // Build domain
            const domain = [];
            if (fromDate) {
                domain.push(["date", ">=", fromDate + " 00:00:00"]);
            }
            if (toDate) {
                domain.push(["date", "<=", toDate + " 23:59:59"]);
            }

            // Load sale orders
            const orders = await this.orm.searchRead(
                "phone.sale.order", domain,
                ["id", "name", "date", "state", "total", "total_profit"]
            );

            if (!orders.length) {
                this.state.dailyReportLines = [];
                this.state.dailyReportTotalSales = 0;
                this.state.dailyReportTotalProfit = 0;
                this.state.dailyReportTotalQty = 0;
                return;
            }

            const orderIds = orders.map(o => o.id);

            // Build order map (id → date)
            const orderMap = {};
            orders.forEach(o => {
                orderMap[o.id] = {
                    date: (o.date || "").split(" ")[0],
                    state: o.state,
                };
            });

            // Load lines
            const lines = await this.orm.searchRead(
                "phone.sale.order.line",
                [["order_id", "in", orderIds]],
                [
                    "id", "order_id", "phone_id",
                    "phone_name", "phone_brand",
                    "price_unit", "cost_price", "quantity",
                    "subtotal", "profit",
                ]
            );

            // Build dailyReportLines
            const reportLines = [];
            let totalSales = 0;
            let totalProfit = 0;
            let totalQty = 0;

            lines.forEach(line => {
                const order = orderMap[line.order_id[0]];
                if (!order) return;

                const qty = Number(line.quantity || 0);
                const sales = Number(line.subtotal || 0);
                const profit = Number(line.profit || 0);

                reportLines.push({
                    id: line.id,
                    date: order.date,
                    product_name: line.phone_name || "Unknown",
                    brand_name: line.phone_brand || "",
                    qty: qty,
                    unit_price: Number(line.price_unit || 0),
                    total_sales: sales,
                    profit: profit,
                });

                totalSales += sales;
                totalProfit += profit;
                totalQty += qty;
            });

            // Sort: latest date first
            reportLines.sort((a, b) => {
                if (a.date === b.date) return 0;
                return a.date < b.date ? 1 : -1;
            });

            this.state.dailyReportLines = reportLines;
            this.state.dailyReportTotalSales = totalSales;
            this.state.dailyReportTotalProfit = totalProfit;
            this.state.dailyReportTotalQty = totalQty;

        } catch (error) {
            console.error("Failed to load daily report:", error);
            this.notification.add("Failed to load daily report.",
                { title: "Error", type: "danger" });
        }
    }


    // ============================================================
    // LOAD REPORTS
    // ============================================================

    async loadReports() {
        try {
            const period = this.state.reportFilters.period || "all";
            const dateDomain = this._getReportDateDomain(period);

            const saleOrders = await this.orm.searchRead(
                "phone.sale.order", dateDomain,
                [
                    "id", "name", "date", "customer_id", "customer_phone",
                    "payment_type", "payment_method", "state",
                    "total", "total_profit", "amount_paid", "balance",
                ],
                { order: "date desc" }
            );

            const saleOrderIds = saleOrders.map(o => o.id);
            let saleLines = [];

            if (saleOrderIds.length) {
                saleLines = await this.orm.searchRead(
                    "phone.sale.order.line",
                    [["order_id", "in", saleOrderIds]],
                    [
                        "id", "order_id", "phone_id", "phone_name", "phone_brand",
                        "imei_1", "price_unit", "cost_price", "quantity",
                        "subtotal", "profit",
                    ]
                );
            }

            const tradeIns = await this.orm.searchRead(
                "phone.trade.in",
                [["state", "=", "completed"], ...dateDomain],
                [
                    "id", "name", "customer_id", "customer_phone",
                    "new_phone_id", "new_phone_model", "new_phone_price",
                    "trade_in_value", "amount_to_pay", "amount_paid",
                    "date", "state",
                ]
            );

            const debts = await this.orm.searchRead(
                "phone.debt", [],
                [
                    "id", "name", "customer_id", "phone_description",
                    "total_amount", "paid_amount", "balance", "date", "state",
                ]
            );

            const posSales = saleOrders.reduce((sum, o) => sum + Number(o.total || 0), 0);
            const tradeInSales = tradeIns.reduce((sum, t) => sum + Number(t.amount_to_pay || 0), 0);
            this.state.reportTotalSales = posSales + tradeInSales;

            this.state.reportTotalProfit = saleLines.reduce(
                (sum, l) => sum + Number(l.profit || 0), 0
            );

            const posPhonesSold = saleLines.reduce((sum, l) => sum + Number(l.quantity || 0), 0);
            this.state.reportPhonesSold = posPhonesSold + tradeIns.length;

            this.state.reportPhonesInStock = this.state.phones.filter(
                phone => phone.status === "in_stock"
            ).length;

            this.state.reportTotalTradeIns = tradeIns.length;

            this.state.reportTotalDebts = debts.reduce(
                (sum, d) => sum + Number(d.balance || 0), 0
            );

            const phoneSalesMap = {};
            saleLines.forEach(line => {
                const phoneName = line.phone_name || "Unknown";
                const phoneId = line.phone_id ? line.phone_id[0] : phoneName;
                const key = phoneId + "|" + phoneName;
                if (!phoneSalesMap[key]) {
                    phoneSalesMap[key] = {
                        id: key, model_name: phoneName,
                        brand_name: line.phone_brand || "",
                        sold_count: 0, revenue: 0,
                    };
                }
                phoneSalesMap[key].sold_count += Number(line.quantity || 0);
                phoneSalesMap[key].revenue += Number(line.subtotal || 0);
            });

            this.state.topSellingPhones = Object.values(phoneSalesMap)
                .sort((a, b) => b.sold_count - a.sold_count)
                .slice(0, 5);

            const customerMap = {};
            saleOrders.forEach(order => {
                if (!order.customer_id) return;
                const customerId = order.customer_id[0];
                const customerName = order.customer_id[1];
                if (!customerMap[customerId]) {
                    customerMap[customerId] = {
                        id: customerId, name: customerName,
                        phone: order.customer_phone || "",
                        purchases: 0, total_spent: 0,
                    };
                }
                customerMap[customerId].purchases += 1;
                customerMap[customerId].total_spent += Number(order.total || 0);
            });

            tradeIns.forEach(trade => {
                if (!trade.customer_id) return;
                const customerId = trade.customer_id[0];
                const customerName = trade.customer_id[1];
                if (!customerMap[customerId]) {
                    customerMap[customerId] = {
                        id: customerId, name: customerName,
                        phone: trade.customer_phone || "",
                        purchases: 0, total_spent: 0,
                    };
                }
                customerMap[customerId].purchases += 1;
                customerMap[customerId].total_spent += Number(trade.amount_to_pay || 0);
            });

            this.state.topCustomers = Object.values(customerMap)
                .sort((a, b) => b.total_spent - a.total_spent)
                .slice(0, 5);

            const brandMap = {};
            saleLines.forEach(line => {
                const brandName = line.phone_brand || "Unknown";
                const brandKey = brandName;
                if (!brandMap[brandKey]) {
                    brandMap[brandKey] = {
                        id: brandKey, brand_name: brandName,
                        sold_count: 0, revenue: 0, profit: 0,
                    };
                }
                brandMap[brandKey].sold_count += Number(line.quantity || 0);
                brandMap[brandKey].revenue += Number(line.subtotal || 0);
                brandMap[brandKey].profit += Number(line.profit || 0);
            });

            this.state.salesByBrand = Object.values(brandMap)
                .sort((a, b) => b.revenue - a.revenue);
        } catch (error) {
            console.error("Failed to load reports:", error);
            this.notification.add("Failed to load reports.",
                { title: "Error", type: "danger" });
        }
    }


    onReportPeriodChange(ev) {
        this.state.reportFilters.period = ev.target.value || "all";
        this.loadReports();
    }


    async refreshReports() {
        await this.loadReports();
        await this.loadDashboard();
        await this._loadDailyReport();
        this.notification.add("Reports refreshed.",
            { title: "Success", type: "success" });
    }


    // ============================================================
    // PURCHASES — GETTERS
    // ============================================================

    get allFilteredPurchases() {
        const search = (this.state.purchaseFilters.search || "").trim().toLowerCase();
        return this.state.purchases.filter(po => {
            const reference = (po.name || "").toLowerCase();
            const supplier = po.supplier_id ? (po.supplier_id[1] || "").toLowerCase() : "";
            const matchesSearch = !search || reference.includes(search) || supplier.includes(search);
            const matchesState = !this.state.purchaseFilters.state ||
                po.state === this.state.purchaseFilters.state;
            return matchesSearch && matchesState;
        });
    }

    get filteredPurchases() {
        const allFiltered = this.allFilteredPurchases;
        const start = (this.state.purchaseCurrentPage - 1) * this.state.purchaseItemsPerPage;
        const end = start + this.state.purchaseItemsPerPage;
        return allFiltered.slice(start, end);
    }

    get purchaseTotalPages() {
        const total = this.allFilteredPurchases.length;
        return Math.max(Math.ceil(total / this.state.purchaseItemsPerPage), 1);
    }

    get purchaseShowingUpTo() {
        const page = this.state.purchaseCurrentPage || 1;
        const perPage = this.state.purchaseItemsPerPage || 10;
        const total = this.allFilteredPurchases.length;
        return Math.min(page * perPage, total);
    }

    get totalPurchases() { return this.state.purchases.length; }
    get draftPurchases() { return this.state.purchases.filter(p => p.state === "draft").length; }
    get confirmedPurchases() { return this.state.purchases.filter(p => p.state === "confirmed").length; }
    get receivedPurchases() { return this.state.purchases.filter(p => p.state === "received").length; }
    get partialPurchases() { return this.state.purchases.filter(p => p.state === "partial").length; }
    get totalPurchasesAmount() {
        return this.state.purchases.reduce((sum, p) => sum + Number(p.total || 0), 0);
    }
    get totalPurchasesBalance() {
        return this.state.purchases.reduce((sum, p) => sum + Number(p.balance || 0), 0);
    }
    get newPurchaseTotal() {
        return (this.state.newPurchaseLines || []).reduce(
            (sum, l) => sum + Number(l.subtotal || 0), 0
        );
    }


    // ============================================================
    // PURCHASES — FILTERS
    // ============================================================

    onPurchaseSearchChange(ev) {
        this.state.purchaseFilters.search = ev.target.value || "";
        this.state.purchaseCurrentPage = 1;
    }

    onPurchaseStateFilterChange(ev) {
        this.state.purchaseFilters.state = ev.target.value || "";
        this.state.purchaseCurrentPage = 1;
    }

    resetPurchaseFilters() {
        this.state.purchaseFilters = { search: "", state: "" };
        this.state.purchaseCurrentPage = 1;
    }

    onPurchaseNextPage() {
        if (this.state.purchaseCurrentPage < this.purchaseTotalPages) {
            this.state.purchaseCurrentPage += 1;
        }
    }

    onPurchasePrevPage() {
        if (this.state.purchaseCurrentPage > 1) {
            this.state.purchaseCurrentPage -= 1;
        }
    }


    // ============================================================
    // PURCHASE MODAL
    // ============================================================

    openAddPurchaseModal() {
        this.state.newPurchase = {
            supplier_id: null,
            date_order: new Date().toISOString().split("T")[0],
            date_expected: "",
            payment_method: "cash",
            notes: "",
        };
        this.state.newPurchaseLines = [];
        this.state.newPurchaseLine = {
            phone_id: null,
            phone_model: "",
            brand_id: null,
            category_id: null,
            condition_id: null,
            imei_1: "",
            imei_2: "",
            quantity: 1,
            price_unit: 0,
        };
        this.state.showPurchaseModal = true;
    }

    closePurchaseModal() {
        this.state.showPurchaseModal = false;
        this.state.newPurchaseLines = [];
    }


    onPurchaseLinePhoneChange(ev) {
        const phoneId = Number(ev.target.value) || null;

        if (!phoneId) {
            this.state.newPurchaseLine.phone_id = null;
            return;
        }

        const phone = this.state.phones.find(p => p.id === phoneId);
        if (!phone) return;

        this.state.newPurchaseLine.phone_id = phoneId;
        this.state.newPurchaseLine.phone_model = phone.model_name || "";
        this.state.newPurchaseLine.brand_id = phone.brand_id ? phone.brand_id[0] : null;
        this.state.newPurchaseLine.category_id = phone.category_id ? phone.category_id[0] : null;
        this.state.newPurchaseLine.condition_id = phone.condition_id ? phone.condition_id[0] : null;
        this.state.newPurchaseLine.imei_1 = phone.imei_1 || "";
        this.state.newPurchaseLine.imei_2 = phone.imei_2 || "";
        this.state.newPurchaseLine.price_unit = Number(phone.buying_price || 0);
    }


    addPurchaseLine() {
        const line = this.state.newPurchaseLine;

        if (!line.phone_model || !line.brand_id) {
            this.notification.add("Please fill phone model and brand.",
                { title: "Missing Fields", type: "warning" });
            return;
        }

        if (!line.price_unit || Number(line.price_unit) <= 0) {
            this.notification.add("Please enter valid price.",
                { title: "Missing Price", type: "warning" });
            return;
        }

        this.state.newPurchaseLines.push({
            temp_id: Date.now() + Math.random(),
            phone_id: line.phone_id ? Number(line.phone_id) : null,
            phone_model: line.phone_model,
            brand_id: Number(line.brand_id),
            category_id: line.category_id ? Number(line.category_id) : null,
            condition_id: line.condition_id ? Number(line.condition_id) : null,
            imei_1: line.imei_1 || "",
            imei_2: line.imei_2 || "",
            quantity: Number(line.quantity || 1),
            price_unit: Number(line.price_unit || 0),
            subtotal: Number(line.quantity || 1) * Number(line.price_unit || 0),
        });

        this.state.newPurchaseLine = {
            phone_id: null,
            phone_model: "",
            brand_id: null,
            category_id: null,
            condition_id: null,
            imei_1: "",
            imei_2: "",
            quantity: 1,
            price_unit: 0,
        };
    }

    removePurchaseLine(temp_id) {
        this.state.newPurchaseLines = this.state.newPurchaseLines.filter(
            l => l.temp_id !== temp_id
        );
    }


    openCreatePhoneModal() {
        this.state.quickPhone = {
            model_name: "",
            brand_id: null,
            category_id: null,
            condition_id: null,
            imei_1: "",
            imei_2: "",
            buying_price: 0,
            selling_price: 0,
            quantity: 1,
        };
        this.state.showQuickCreatePhoneModal = true;
    }

    closeCreatePhoneModal() {
        this.state.showQuickCreatePhoneModal = false;
    }


    async _onQuickCreatePhone() {
        const qp = this.state.quickPhone;

        if (!qp.model_name || !qp.brand_id || !qp.category_id || !qp.condition_id) {
            this.notification.add(
                "Phone Model, Brand, Category na Condition ni lazima.",
                { title: "Missing Fields", type: "warning" }
            );
            return;
        }

        try {
            const phoneIdArray = await this.orm.create("phone.stock", [{
                model_name: qp.model_name,
                brand_id: Number(qp.brand_id),
                category_id: Number(qp.category_id),
                condition_id: Number(qp.condition_id),
                imei_1: qp.imei_1 || false,
                imei_2: qp.imei_2 || false,
                buying_price: Number(qp.buying_price || 0),
                selling_price: Number(qp.selling_price || 0),
                quantity: Number(qp.quantity || 0),
            }]);

            const newPhoneId = Array.isArray(phoneIdArray) ? phoneIdArray[0] : phoneIdArray;

            this.notification.add("Phone created successfully.",
                { title: "Success", type: "success" });

            await this.loadPhones();

            this.state.newPurchaseLine.phone_id = newPhoneId;
            this.state.newPurchaseLine.phone_model = qp.model_name;
            this.state.newPurchaseLine.brand_id = Number(qp.brand_id);
            this.state.newPurchaseLine.category_id = Number(qp.category_id);
            this.state.newPurchaseLine.condition_id = Number(qp.condition_id);
            this.state.newPurchaseLine.imei_1 = qp.imei_1 || "";
            this.state.newPurchaseLine.imei_2 = qp.imei_2 || "";
            this.state.newPurchaseLine.price_unit = Number(qp.buying_price || 0);
            this.state.newPurchaseLine.quantity = Number(qp.quantity || 1);

            this.closeCreatePhoneModal();
        } catch (error) {
            console.error("Failed to create phone:", error);
            this.notification.add("Failed to create phone.",
                { title: "Error", type: "danger" });
        }
    }


    async _onSavePurchase() {
        const po = this.state.newPurchase;

        if (!po.supplier_id) {
            this.notification.add("Please select a supplier.",
                { title: "Missing Supplier", type: "warning" });
            return;
        }

        if (!this.state.newPurchaseLines.length) {
            this.notification.add("Please add at least one phone.",
                { title: "No Lines", type: "warning" });
            return;
        }

        try {
            const poVals = {
                supplier_id: Number(po.supplier_id),
                date_expected: po.date_expected || false,
                payment_method: po.payment_method || "cash",
                notes: po.notes || false,
            };

            const poIdArray = await this.orm.create("phone.purchase.order", [poVals]);
            const poId = Array.isArray(poIdArray) ? poIdArray[0] : poIdArray;

            const lineVals = this.state.newPurchaseLines.map(line => ({
                order_id: poId,
                phone_id: line.phone_id || false,
                phone_model: line.phone_model,
                brand_id: Number(line.brand_id),
                category_id: line.category_id ? Number(line.category_id) : false,
                condition_id: line.condition_id ? Number(line.condition_id) : false,
                imei_1: line.imei_1 || false,
                imei_2: line.imei_2 || false,
                quantity: Number(line.quantity || 1),
                price_unit: Number(line.price_unit || 0),
            }));

            await this.orm.create("phone.purchase.order.line", lineVals);

            this.notification.add("Purchase Order (RFQ) created successfully.",
                { title: "Success", type: "success" });

            this.closePurchaseModal();
            await this.loadPurchases();
        } catch (error) {
            console.error("Failed to create purchase:", error);
            this.notification.add("Failed to create purchase.",
                { title: "Error", type: "danger" });
        }
    }


    async _onOpenPurchaseDetail(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        if (!id) return;

        try {
            const orders = await this.orm.searchRead(
                "phone.purchase.order",
                [["id", "=", id]],
                [
                    "id", "name", "supplier_id", "supplier_phone",
                    "date_order", "date_expected",
                    "payment_method", "state",
                    "subtotal", "total", "amount_paid", "balance",
                    "line_count", "notes",
                    "total_ordered", "total_received", "total_pending",
                    "is_fully_received",
                    "received_amount", "can_be_paid",
                ]
            );

            if (!orders.length) {
                this.notification.add("Purchase Order not found.",
                    { title: "Error", type: "danger" });
                return;
            }

            const lines = await this.orm.searchRead(
                "phone.purchase.order.line",
                [["order_id", "=", id]],
                [
                    "id", "order_id", "phone_id",
                    "phone_model", "brand_id", "category_id", "condition_id",
                    "imei_1", "imei_2",
                    "quantity", "price_unit", "subtotal",
                    "qty_received", "qty_pending", "receive_status",
                ],
                { order: "id asc" }
            );

            this.state.currentPurchaseDetail = orders[0];
            this.state.currentPurchaseLines = lines;
            this.state.showPurchaseDetailModal = true;

        } catch (error) {
            console.error("Failed to load PO details:", error);
            this.notification.add("Failed to load PO details.",
                { title: "Error", type: "danger" });
        }
    }


    closePurchaseDetail() {
        this.state.showPurchaseDetailModal = false;
        this.state.currentPurchaseDetail = null;
        this.state.currentPurchaseLines = [];
    }


    async _onConfirmFromDetail(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        if (!id) return;
        try {
            await this.orm.call("phone.purchase.order", "action_confirm", [[id]]);
            this.notification.add("RFQ confirmed as Purchase Order.",
                { title: "Success", type: "success" });
            this.closePurchaseDetail();
            await this.loadPurchases();
        } catch (error) {
            console.error("Failed to confirm PO:", error);
            this.notification.add("Failed to confirm PO.",
                { title: "Error", type: "danger" });
        }
    }


    async _onReceiveFromDetail(ev) {
        await this.openReceivePurchaseModal(ev);
    }


    async _onInvoiceFromDetail(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        if (!id) return;
        try {
            await this.orm.call("phone.purchase.order", "action_create_invoice", [[id]]);
            this.notification.add("Invoice created.",
                { title: "Success", type: "success" });
            this.closePurchaseDetail();
            await this.loadPurchases();
        } catch (error) {
            console.error("Failed to create invoice:", error);
            this.notification.add("Failed to create invoice.",
                { title: "Error", type: "danger" });
        }
    }


    async _onMarkPaidFromDetail(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        if (!id) return;
        try {
            await this.orm.call("phone.purchase.order", "action_mark_paid", [[id]]);
            this.notification.add("Purchase marked as paid.",
                { title: "Success", type: "success" });
            this.closePurchaseDetail();
            await this.loadPurchases();
        } catch (error) {
            console.error("Failed to mark paid:", error);
            this.notification.add("Failed to mark paid.",
                { title: "Error", type: "danger" });
        }
    }


    _onCancelFromDetail(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        if (!id) return;
        this.dialog.add(ConfirmationDialog, {
            title: "Cancel Purchase",
            body: "Are you sure you want to cancel this PO?",
            confirm: async () => {
                try {
                    await this.orm.call("phone.purchase.order", "action_cancel", [[id]]);
                    this.notification.add("Purchase cancelled.",
                        { title: "Success", type: "success" });
                    this.closePurchaseDetail();
                    await this.loadPurchases();
                } catch (error) {
                    console.error("Failed to cancel PO:", error);
                }
            },
            cancel: () => {},
        });
    }


    async openReceivePurchaseModal(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        if (!id) return;

        try {
            const orders = await this.orm.searchRead(
                "phone.purchase.order",
                [["id", "=", id]],
                [
                    "id", "name", "supplier_id", "supplier_phone",
                    "date_order", "date_expected",
                    "payment_method", "state",
                    "total_ordered", "total_received", "total_pending",
                ]
            );

            if (!orders.length) {
                this.notification.add("Purchase Order not found.",
                    { title: "Error", type: "danger" });
                return;
            }

            const lines = await this.orm.searchRead(
                "phone.purchase.order.line",
                [["order_id", "=", id]],
                [
                    "id", "order_id", "phone_id",
                    "phone_model", "brand_id",
                    "quantity", "qty_received", "qty_pending",
                    "price_unit", "subtotal",
                ],
                { order: "id asc" }
            );

            const linesWithDefault = lines.map(line => ({
                ...line,
                receiving_now: line.qty_pending || 0,
            }));

            this.state.currentReceivePurchase = orders[0];
            this.state.currentReceiveLines = linesWithDefault;
            this.state.showReceivePurchaseModal = true;

            if (this.state.showPurchaseDetailModal) {
                this.state.showPurchaseDetailModal = false;
            }

        } catch (error) {
            console.error("Failed to open receive modal:", error);
            this.notification.add("Failed to open receive modal.",
                { title: "Error", type: "danger" });
        }
    }


    closeReceivePurchaseModal() {
        this.state.showReceivePurchaseModal = false;
        this.state.currentReceivePurchase = null;
        this.state.currentReceiveLines = [];
    }


    onReceiveQtyChange(lineId, ev) {
        const lineIdNum = Number(lineId);
        let newQty = parseInt(ev.target.value) || 0;

        if (newQty < 0) newQty = 0;

        const line = this.state.currentReceiveLines.find(l => l.id === lineIdNum);
        if (!line) return;

        if (newQty > line.qty_pending) {
            newQty = line.qty_pending;
            ev.target.value = newQty;
        }

        line.receiving_now = newQty;
    }


    async _onConfirmReceive() {
        const po = this.state.currentReceivePurchase;
        const lines = this.state.currentReceiveLines;

        if (!po || !po.id) {
            this.notification.add("No purchase order selected.",
                { title: "Error", type: "danger" });
            return;
        }

        const receiveData = {};
        let totalReceiving = 0;

        lines.forEach(line => {
            const qty = Number(line.receiving_now) || 0;
            if (qty > 0) {
                receiveData[line.id] = qty;
                totalReceiving += qty;
            }
        });

        if (totalReceiving === 0) {
            this.notification.add("Weka qty angalau moja ili ku-receive.",
                { title: "No Qty", type: "warning" });
            return;
        }

        try {
            await this.orm.call(
                "phone.purchase.order",
                "action_receive",
                [[po.id], receiveData]
            );

            this.notification.add(
                `Ume-receive ${totalReceiving} phone(s) successfully.`,
                { title: "Success", type: "success" }
            );

            this.closeReceivePurchaseModal();
            await this.loadPurchases();
            await this.loadPhones();
            await this.loadReports();
            await this.loadDashboard();
            await this._loadDailyReport();

        } catch (error) {
            console.error("Failed to receive:", error);
            this.notification.add("Failed to receive phones.",
                { title: "Error", type: "danger" });
        }
    }


    async _onConfirmPurchase(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        if (!id) return;
        try {
            await this.orm.call("phone.purchase.order", "action_confirm", [[id]]);
            this.notification.add("RFQ confirmed as Purchase Order.",
                { title: "Success", type: "success" });
            await this.loadPurchases();
        } catch (error) {
            console.error("Failed to confirm PO:", error);
            this.notification.add("Failed to confirm PO.",
                { title: "Error", type: "danger" });
        }
    }


    async _onReceivePurchase(ev) {
        await this.openReceivePurchaseModal(ev);
    }


    async _onInvoicePurchase(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        if (!id) return;
        try {
            await this.orm.call("phone.purchase.order", "action_create_invoice", [[id]]);
            this.notification.add("Invoice created.",
                { title: "Success", type: "success" });
            await this.loadPurchases();
        } catch (error) {
            console.error("Failed to create invoice:", error);
            this.notification.add("Failed to create invoice.",
                { title: "Error", type: "danger" });
        }
    }


    async _onMarkPurchasePaid(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        if (!id) return;
        try {
            await this.orm.call("phone.purchase.order", "action_mark_paid", [[id]]);
            this.notification.add("Purchase marked as paid.",
                { title: "Success", type: "success" });
            await this.loadPurchases();
        } catch (error) {
            console.error("Failed to mark paid:", error);
            this.notification.add("Failed to mark paid.",
                { title: "Error", type: "danger" });
        }
    }


    _onCancelPurchase(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        if (!id) return;
        this.dialog.add(ConfirmationDialog, {
            title: "Cancel Purchase",
            body: "Are you sure you want to cancel this PO?",
            confirm: async () => {
                try {
                    await this.orm.call("phone.purchase.order", "action_cancel", [[id]]);
                    this.notification.add("Purchase cancelled.",
                        { title: "Success", type: "success" });
                    await this.loadPurchases();
                } catch (error) {
                    console.error("Failed to cancel PO:", error);
                }
            },
            cancel: () => {},
        });
    }


    async _onDeletePurchase(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        if (!id) return;
        this.dialog.add(ConfirmationDialog, {
            title: "Delete Purchase Order",
            body: "Are you sure you want to delete this PO and all its lines?",
            confirm: async () => {
                try {
                    await this.orm.unlink("phone.purchase.order", [id]);
                    this.notification.add("Purchase deleted.",
                        { title: "Success", type: "success" });
                    await this.loadPurchases();
                } catch (error) {
                    console.error("Failed to delete PO:", error);
                }
            },
            cancel: () => {},
        });
    }


    async _onPrintPurchaseReport(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        if (!id) return;
        try {
            const url = `/report/pdf/phone_point_keeping.report_phone_purchase_document/${id}`;
            window.open(url, "_blank");
            this.notification.add("PDF report opened in new tab.",
                { title: "Success", type: "success" });
        } catch (error) {
            console.error("Failed to open PDF:", error);
            this.notification.add("Failed to open PDF report.",
                { title: "Error", type: "danger" });
        }
    }


    // ============================================================
    // POS — GETTERS
    // ============================================================

    get posProducts() {
        const search = (this.state.posFilters.search || "").trim().toLowerCase();
        return this.state.phones.filter(phone => {
            if (phone.status !== "in_stock" || Number(phone.quantity || 0) <= 0) {
                return false;
            }
            const model = (phone.model_name || "").toLowerCase();
            const imei1 = (phone.imei_1 || "").toLowerCase();
            const brandId = phone.brand_id ? phone.brand_id[0] : null;

            const matchesSearch = !search || model.includes(search) || imei1.includes(search);
            const matchesBrand = !this.state.posFilters.brand_id ||
                Number(this.state.posFilters.brand_id) === Number(brandId);

            return matchesSearch && matchesBrand;
        });
    }

    get posCartTotal() {
        return this.state.posCart.reduce(
            (total, item) => total + (Number(item.price_unit || 0) * Number(item.quantity || 1)),
            0
        );
    }

    get posCartTotalQty() {
        return this.state.posCart.reduce((sum, item) => sum + Number(item.quantity || 0), 0);
    }

    get posCartBalance() {
        const total = this.posCartTotal;
        const paid = Number(this.state.posData.amount_paid || 0);
        return Math.max(total - paid, 0);
    }


    onPosSearchChange(ev) {
        this.state.posFilters.search = ev.target.value || "";
    }

    onPosBrandFilter(brand_id) {
        this.state.posFilters.brand_id = brand_id || null;
    }

    resetPosFilters() {
        this.state.posFilters = { search: "", brand_id: null };
    }


    onAddToCart(phone) {
        const exists = this.state.posCart.find(item => item.phone_id === phone.id);
        if (exists) {
            this.notification.add("Phone already in cart.",
                { title: "Already Added", type: "warning" });
            return;
        }

        const maxQty = Number(phone.quantity || 0);
        if (maxQty <= 0) {
            this.notification.add("No stock available for this phone.",
                { title: "Out of Stock", type: "danger" });
            return;
        }

        this.state.posCart.push({
            temp_id: Date.now() + Math.random(),
            phone_id: phone.id,
            model_name: phone.model_name || "",
            brand_name: phone.brand_id ? phone.brand_id[1] : "",
            imei_1: phone.imei_1 || "",
            price_unit: Number(phone.selling_price || 0),
            cost_price: Number(phone.buying_price || 0),
            quantity: 1,
            max_qty: maxQty,
        });
    }


    onIncrementCart(temp_id) {
        const item = this.state.posCart.find(i => i.temp_id === temp_id);
        if (!item) return;
        if (item.quantity >= item.max_qty) {
            this.notification.add(`Maximum ${item.max_qty} units available.`,
                { title: "Stock Limit", type: "warning" });
            return;
        }
        item.quantity += 1;
    }


    onDecrementCart(temp_id) {
        const item = this.state.posCart.find(i => i.temp_id === temp_id);
        if (!item) return;
        if (item.quantity <= 1) {
            this.onRemoveFromCart(temp_id);
            return;
        }
        item.quantity -= 1;
    }


    onChangeCartQuantity(temp_id, ev) {
        const item = this.state.posCart.find(i => i.temp_id === temp_id);
        if (!item) return;
        let newQty = parseInt(ev.target.value) || 1;
        if (newQty < 1) newQty = 1;
        if (newQty > item.max_qty) {
            this.notification.add(`Maximum ${item.max_qty} units available.`,
                { title: "Stock Limit", type: "warning" });
            newQty = item.max_qty;
            ev.target.value = newQty;
        }
        item.quantity = newQty;
    }


    onRemoveFromCart(temp_id) {
        this.state.posCart = this.state.posCart.filter(item => item.temp_id !== temp_id);
    }


    clearPosCart() {
        this.state.posCart = [];
        this.state.posData.amount_paid = 0;
        this.state.posData.customer_id = null;
        this.state.posData.customer_phone = "";
    }


    onPosPaymentTypeChange(type) {
        this.state.posData.payment_type = type || "cash";
    }

    onPosCustomerChange(ev) {
        const customerId = Number(ev.target.value) || null;
        this.state.posData.customer_id = customerId;
        const customer = this.state.customers.find(c => c.id === customerId);
        if (customer) {
            this.state.posData.customer_phone = customer.phone || customer.mobile || "";
        } else {
            this.state.posData.customer_phone = "";
        }
    }

    onPosAmountPaidChange(ev) {
        this.state.posData.amount_paid = Number(ev.target.value) || 0;
    }


    async _onSaveSaleOrder() {
        if (!this.state.posCart.length) {
            this.notification.add("Cart is empty.",
                { title: "Missing Items", type: "warning" });
            return;
        }

        const posData = this.state.posData;
        const paymentType = posData.payment_type || "cash";
        const total = this.posCartTotal;

        let amountPaid = 0;
        let state = "paid";

        if (paymentType === "cash") {
            amountPaid = total;
            state = "paid";
        } else {
            amountPaid = Number(posData.amount_paid || 0);
            state = amountPaid >= total ? "paid" : "partial";
        }

        try {
            const orderVals = {
                customer_id: posData.customer_id || false,
                customer_phone: posData.customer_phone || false,
                payment_type: paymentType,
                payment_method: posData.payment_method || "cash",
                amount_paid: amountPaid,
                state: state,
                notes: posData.notes || false,
            };

            const orderIdArray = await this.orm.create("phone.sale.order", [orderVals]);
            const orderId = Array.isArray(orderIdArray) ? orderIdArray[0] : orderIdArray;

            const lineVals = this.state.posCart.map(item => ({
                order_id: orderId,
                phone_id: item.phone_id,
                price_unit: Number(item.price_unit || 0),
                cost_price: Number(item.cost_price || 0),
                quantity: Number(item.quantity || 1),
            }));

            await this.orm.create("phone.sale.order.line", lineVals);
            await this.orm.call("phone.sale.order", "action_confirm", [[orderId]]);

            if (paymentType === "credit" && amountPaid < total && posData.customer_id) {
                const debtVals = {
                    customer_id: posData.customer_id,
                    phone_description: "POS Sale: " +
                        this.state.posCart.map(i => i.model_name).join(", "),
                    total_amount: total,
                    down_payment: amountPaid,
                    num_installments: 1,
                    interval_type: "monthly",
                    first_due_date: new Date().toISOString().split("T")[0],
                    payment_method: posData.payment_method || "cash",
                    notes: "Auto-created from POS Sale",
                    state: "active",
                };
                const debtIdArray = await this.orm.create("phone.debt", [debtVals]);
                const debtId = Array.isArray(debtIdArray) ? debtIdArray[0] : debtIdArray;
                await this.orm.call("phone.debt", "action_generate_installments", [[debtId]]);
            }

            this.notification.add("Sale completed successfully.",
                { title: "Success", type: "success" });

            this.clearPosCart();
            await Promise.all([this.loadPhones(), this.loadDebts()]);
            await this.loadReports();
            await this.loadDashboard();
            await this._loadDailyReport();

        } catch (error) {
            console.error("Failed to save sale order:", error);
            this.notification.add("Failed to save sale order.",
                { title: "Error", type: "danger" });
        }
    }


    // ============================================================
    // IMAGE UPLOAD
    // ============================================================

    onImageUpload(ev) {
        const files = Array.from(ev.target.files || []);
        if (!files.length) return;

        const maxImages = 5;
        const remaining = maxImages - this.state.newPhoneImages.length;
        if (remaining <= 0) {
            this.notification.add(`Maximum ${maxImages} images allowed.`,
                { title: "Limit Reached", type: "warning" });
            ev.target.value = "";
            return;
        }

        const filesToProcess = files.slice(0, remaining);
        if (filesToProcess.length < files.length) {
            this.notification.add(`Only ${remaining} more image(s) can be added.`,
                { title: "Limit Reached", type: "warning" });
        }

        filesToProcess.forEach(file => {
            const reader = new FileReader();
            const tempId = Date.now() + Math.random();
            reader.onload = (e) => {
                const base64 = e.target.result.split(",")[1] || "";
                this.state.newPhoneImages.push({
                    temp_id: tempId, filename: file.name,
                    data_url: e.target.result, base64: base64,
                });
            };
            reader.readAsDataURL(file);
        });

        ev.target.value = "";
    }

    onRemoveNewImage(tempId) {
        this.state.newPhoneImages = this.state.newPhoneImages.filter(
            img => img.temp_id !== tempId
        );
    }


    onEditImageUpload(ev) {
        const files = Array.from(ev.target.files || []);
        if (!files.length) return;

        const maxImages = 5;
        const existingCount = this.state.editPhoneExistingImages.length +
            this.state.editPhoneNewImages.length;
        const remaining = maxImages - existingCount;

        if (remaining <= 0) {
            this.notification.add(`Maximum ${maxImages} images allowed.`,
                { title: "Limit Reached", type: "warning" });
            ev.target.value = "";
            return;
        }

        const filesToProcess = files.slice(0, remaining);
        if (filesToProcess.length < files.length) {
            this.notification.add(`Only ${remaining} more image(s) can be added.`,
                { title: "Limit Reached", type: "warning" });
        }

        filesToProcess.forEach(file => {
            const reader = new FileReader();
            const tempId = Date.now() + Math.random();
            reader.onload = (e) => {
                const base64 = e.target.result.split(",")[1] || "";
                this.state.editPhoneNewImages.push({
                    temp_id: tempId, filename: file.name,
                    data_url: e.target.result, base64: base64,
                });
            };
            reader.readAsDataURL(file);
        });

        ev.target.value = "";
    }

    onRemoveEditNewImage(tempId) {
        this.state.editPhoneNewImages = this.state.editPhoneNewImages.filter(
            img => img.temp_id !== tempId
        );
    }


    async _onDeleteExistingImage(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        if (!id) return;

        this.dialog.add(ConfirmationDialog, {
            title: "Delete Image",
            body: "Are you sure you want to delete this image?",
            confirm: async () => {
                try {
                    await this.orm.unlink("phone.stock.image", [id]);
                    this.state.editPhoneExistingImages =
                        this.state.editPhoneExistingImages.filter(img => img.id !== id);
                    this.notification.add("Image deleted.",
                        { title: "Success", type: "success" });
                    await this.loadPhones();
                } catch (error) {
                    console.error("Failed to delete image:", error);
                    this.notification.add("Failed to delete image.",
                        { title: "Error", type: "danger" });
                }
            },
            cancel: () => {},
        });
    }


    // ============================================================
    // CATEGORY GETTERS
    // ============================================================

    get filteredCategories() {
        if (!this.state.newPhone.brand_id) return [];
        return this.state.categories.filter(category =>
            category.brand_id && category.brand_id[0] === Number(this.state.newPhone.brand_id)
        );
    }

    get editFilteredCategories() {
        if (!this.state.editPhone.brand_id) return [];
        return this.state.categories.filter(category =>
            category.brand_id && category.brand_id[0] === Number(this.state.editPhone.brand_id)
        );
    }

    get filteredStockCategories() {
        if (!this.state.stockFilters.brand_id) return this.state.categories;
        return this.state.categories.filter(category =>
            category.brand_id && category.brand_id[0] === Number(this.state.stockFilters.brand_id)
        );
    }

    get allFilteredCategoriesForSettings() { return this.state.categories; }

    get filteredCategoriesForSettings() {
        const allFiltered = this.allFilteredCategoriesForSettings;
        const start = (this.state.categoryCurrentPage - 1) * this.state.categoryItemsPerPage;
        const end = start + this.state.categoryItemsPerPage;
        return allFiltered.slice(start, end);
    }

    get categoryTotalPages() {
        const total = this.allFilteredCategoriesForSettings.length;
        return Math.max(Math.ceil(total / this.state.categoryItemsPerPage), 1);
    }

    get categoryShowingUpTo() {
        const page = this.state.categoryCurrentPage || 1;
        const perPage = this.state.categoryItemsPerPage || 5;
        const total = this.allFilteredCategoriesForSettings.length;
        return Math.min(page * perPage, total);
    }

    onCategoryNextPage() {
        if (this.state.categoryCurrentPage < this.categoryTotalPages) {
            this.state.categoryCurrentPage += 1;
        }
    }

    onCategoryPrevPage() {
        if (this.state.categoryCurrentPage > 1) {
            this.state.categoryCurrentPage -= 1;
        }
    }

    get tradeInBrands() { return this.state.brands; }


    // ============================================================
    // ALL FILTERED PHONES
    // ============================================================

    get allFilteredPhones() {
        const search = (this.state.stockFilters.search || "").trim().toLowerCase();
        return this.state.phones.filter(phone => {
            const model = (phone.model_name || "").toLowerCase();
            const imei1 = (phone.imei_1 || "").toLowerCase();
            const imei2 = (phone.imei_2 || "").toLowerCase();
            const brandId = phone.brand_id ? phone.brand_id[0] : null;
            const categoryId = phone.category_id ? phone.category_id[0] : null;
            const conditionId = phone.condition_id ? phone.condition_id[0] : null;

            const matchesSearch = !search || model.includes(search) ||
                imei1.includes(search) || imei2.includes(search);
            const matchesBrand = !this.state.stockFilters.brand_id ||
                Number(this.state.stockFilters.brand_id) === Number(brandId);
            const matchesCategory = !this.state.stockFilters.category_id ||
                Number(this.state.stockFilters.category_id) === Number(categoryId);
            const matchesCondition = !this.state.stockFilters.condition_id ||
                Number(this.state.stockFilters.condition_id) === Number(conditionId);
            const matchesStatus = !this.state.stockFilters.status ||
                this.state.stockFilters.status === phone.status;

            return matchesSearch && matchesBrand && matchesCategory &&
                matchesCondition && matchesStatus;
        });
    }

    get filteredPhones() {
        const allFiltered = this.allFilteredPhones;
        const start = (this.state.currentPage - 1) * this.state.itemsPerPage;
        const end = start + this.state.itemsPerPage;
        return allFiltered.slice(start, end);
    }

    get totalPages() {
        const total = this.allFilteredPhones.length;
        return Math.max(Math.ceil(total / this.state.itemsPerPage), 1);
    }

    get showingUpTo() {
        const page = this.state.currentPage || 1;
        const perPage = this.state.itemsPerPage || 10;
        const total = this.allFilteredPhones.length;
        return Math.min(page * perPage, total);
    }

    onNextPage() {
        if (this.state.currentPage < this.totalPages) this.state.currentPage += 1;
    }

    onPrevPage() {
        if (this.state.currentPage > 1) this.state.currentPage -= 1;
    }


    // ============================================================
    // ALL FILTERED TRADE-INS
    // ============================================================

    get allFilteredTradeIns() {
        const search = (this.state.tradeInFilters.search || "").trim().toLowerCase();
        return this.state.tradeIns.filter(trade => {
            const reference = (trade.name || "").toLowerCase();
            const customer = trade.customer_id ? (trade.customer_id[1] || "").toLowerCase() : "";
            const oldModel = (trade.old_phone_model || "").toLowerCase();
            const oldImei = (trade.old_phone_imei_1 || "").toLowerCase();
            const newModel = (trade.new_phone_model || "").toLowerCase();

            const matchesSearch = !search || reference.includes(search) ||
                customer.includes(search) || oldModel.includes(search) ||
                oldImei.includes(search) || newModel.includes(search);
            const matchesState = !this.state.tradeInFilters.state ||
                trade.state === this.state.tradeInFilters.state;

            return matchesSearch && matchesState;
        });
    }

    get filteredTradeIns() {
        const allFiltered = this.allFilteredTradeIns;
        const start = (this.state.tradeInCurrentPage - 1) * this.state.tradeInItemsPerPage;
        const end = start + this.state.tradeInItemsPerPage;
        return allFiltered.slice(start, end);
    }

    get tradeInTotalPages() {
        const total = this.allFilteredTradeIns.length;
        return Math.max(Math.ceil(total / this.state.tradeInItemsPerPage), 1);
    }

    get tradeInShowingUpTo() {
        const page = this.state.tradeInCurrentPage || 1;
        const perPage = this.state.tradeInItemsPerPage || 10;
        const total = this.allFilteredTradeIns.length;
        return Math.min(page * perPage, total);
    }

    onTradeInNextPage() {
        if (this.state.tradeInCurrentPage < this.tradeInTotalPages) {
            this.state.tradeInCurrentPage += 1;
        }
    }

    onTradeInPrevPage() {
        if (this.state.tradeInCurrentPage > 1) {
            this.state.tradeInCurrentPage -= 1;
        }
    }


    // ============================================================
    // ALL FILTERED SUPPLIERS
    // ============================================================

    get allFilteredSuppliers() {
        const search = (this.state.supplierFilters.search || "").trim().toLowerCase();
        return this.state.suppliers.filter(supplier => {
            const name = (supplier.name || "").toLowerCase();
            const phone = (supplier.phone || "").toLowerCase();
            const email = (supplier.email || "").toLowerCase();
            const city = (supplier.city || "").toLowerCase();

            const matchesSearch = !search || name.includes(search) ||
                phone.includes(search) || email.includes(search) || city.includes(search);
            const matchesStatus =
                this.state.supplierFilters.status === "all" ||
                (this.state.supplierFilters.status === "active" && supplier.active) ||
                (this.state.supplierFilters.status === "archived" && !supplier.active);

            return matchesSearch && matchesStatus;
        });
    }

    get filteredSuppliers() {
        const allFiltered = this.allFilteredSuppliers;
        const start = (this.state.supplierCurrentPage - 1) * this.state.supplierItemsPerPage;
        const end = start + this.state.supplierItemsPerPage;
        return allFiltered.slice(start, end);
    }

    get supplierTotalPages() {
        const total = this.allFilteredSuppliers.length;
        return Math.max(Math.ceil(total / this.state.supplierItemsPerPage), 1);
    }

    get supplierShowingUpTo() {
        const page = this.state.supplierCurrentPage || 1;
        const perPage = this.state.supplierItemsPerPage || 10;
        const total = this.allFilteredSuppliers.length;
        return Math.min(page * perPage, total);
    }

    onSupplierNextPage() {
        if (this.state.supplierCurrentPage < this.supplierTotalPages) {
            this.state.supplierCurrentPage += 1;
        }
    }

    onSupplierPrevPage() {
        if (this.state.supplierCurrentPage > 1) {
            this.state.supplierCurrentPage -= 1;
        }
    }


    // ============================================================
    // ALL FILTERED STAFF
    // ============================================================

    get allFilteredStaff() {
        const search = (this.state.staffFilters.search || "").trim().toLowerCase();
        return this.state.staff.filter(staff => {
            const name = (staff.name || "").toLowerCase();
            const job = (staff.job_title || "").toLowerCase();
            const phone = (staff.work_phone || staff.mobile_phone || "").toLowerCase();
            const email = (staff.work_email || "").toLowerCase();

            const matchesSearch = !search || name.includes(search) ||
                job.includes(search) || phone.includes(search) || email.includes(search);
            const matchesStatus =
                this.state.staffFilters.status === "all" ||
                (this.state.staffFilters.status === "active" && staff.active) ||
                (this.state.staffFilters.status === "archived" && !staff.active);

            return matchesSearch && matchesStatus;
        });
    }

    get filteredStaff() {
        const allFiltered = this.allFilteredStaff;
        const start = (this.state.staffCurrentPage - 1) * this.state.staffItemsPerPage;
        const end = start + this.state.staffItemsPerPage;
        return allFiltered.slice(start, end);
    }

    get staffTotalPages() {
        const total = this.allFilteredStaff.length;
        return Math.max(Math.ceil(total / this.state.staffItemsPerPage), 1);
    }

    get staffShowingUpTo() {
        const page = this.state.staffCurrentPage || 1;
        const perPage = this.state.staffItemsPerPage || 10;
        const total = this.allFilteredStaff.length;
        return Math.min(page * perPage, total);
    }

    onStaffNextPage() {
        if (this.state.staffCurrentPage < this.staffTotalPages) {
            this.state.staffCurrentPage += 1;
        }
    }

    onStaffPrevPage() {
        if (this.state.staffCurrentPage > 1) {
            this.state.staffCurrentPage -= 1;
        }
    }


    // ============================================================
    // ALL FILTERED DEBTS
    // ============================================================

    get allFilteredDebts() {
        const search = (this.state.debtFilters.search || "").trim().toLowerCase();
        return this.state.debts.filter(debt => {
            const reference = (debt.name || "").toLowerCase();
            const customer = debt.customer_id ? (debt.customer_id[1] || "").toLowerCase() : "";
            const phoneDesc = (debt.phone_description || "").toLowerCase();

            const matchesSearch = !search || reference.includes(search) ||
                customer.includes(search) || phoneDesc.includes(search);
            const matchesState = !this.state.debtFilters.state ||
                debt.state === this.state.debtFilters.state;

            return matchesSearch && matchesState;
        });
    }

    get filteredDebts() {
        const allFiltered = this.allFilteredDebts;
        const start = (this.state.debtCurrentPage - 1) * this.state.debtItemsPerPage;
        const end = start + this.state.debtItemsPerPage;
        return allFiltered.slice(start, end);
    }

    get debtTotalPages() {
        const total = this.allFilteredDebts.length;
        return Math.max(Math.ceil(total / this.state.debtItemsPerPage), 1);
    }

    get debtShowingUpTo() {
        const page = this.state.debtCurrentPage || 1;
        const perPage = this.state.debtItemsPerPage || 10;
        const total = this.allFilteredDebts.length;
        return Math.min(page * perPage, total);
    }

    onDebtNextPage() {
        if (this.state.debtCurrentPage < this.debtTotalPages) {
            this.state.debtCurrentPage += 1;
        }
    }

    onDebtPrevPage() {
        if (this.state.debtCurrentPage > 1) {
            this.state.debtCurrentPage -= 1;
        }
    }


    // ============================================================
    // DEBT SUMMARY
    // ============================================================

    get totalDebtsCount() { return this.state.debts.length; }
    get activeDebtsCount() {
        return this.state.debts.filter(d => d.state === "active" || d.state === "overdue").length;
    }
    get paidDebtsCount() {
        return this.state.debts.filter(d => d.state === "paid").length;
    }
    get totalDebtsBalance() {
        return this.state.debts.reduce((total, debt) => total + Number(debt.balance || 0), 0);
    }

    get selectedDebt() {
        const id = Number(this.state.selectedDebtId) || null;
        if (!id) return null;
        return this.state.debts.find(d => d.id === id) || null;
    }

    get selectedDebtInstallments() { return this.state.currentDebtInstallments || []; }
    get selectedInstallment() { return this.state.currentInstallment || null; }


    // ============================================================
    // DEBT FILTERS
    // ============================================================

    onDebtSearchChange(ev) {
        this.state.debtFilters.search = ev.target.value || "";
        this.state.debtCurrentPage = 1;
    }

    onDebtStateFilterChange(ev) {
        this.state.debtFilters.state = ev.target.value || "";
        this.state.debtCurrentPage = 1;
    }

    resetDebtFilters() {
        this.state.debtFilters = { search: "", state: "" };
        this.state.debtCurrentPage = 1;
    }


    // ============================================================
    // DEBT CRUD
    // ============================================================

    openAddDebtModal() {
        this.state.newDebt = {
            customer_id: null, phone_id: null, phone_description: "",
            total_amount: 0, down_payment: 0, interest_rate: 0,
            num_installments: 1, interval_type: "monthly",
            first_due_date: "", payment_method: "", notes: "",
        };
        this.state.showDebtModal = true;
    }

    closeDebtModal() { this.state.showDebtModal = false; }

    closeInstallmentsModal() {
        this.state.showInstallmentsModal = false;
        this.state.selectedDebtId = null;
        this.state.currentDebtInstallments = [];
    }

    onNewDebtChange(field, ev) {
        this.state.newDebt[field] = ev.target.value || "";
    }

    onNewDebtCustomerChange(ev) {
        this.state.newDebt.customer_id = Number(ev.target.value) || null;
    }

    onNewDebtPhoneChange(ev) {
        const phoneId = Number(ev.target.value) || null;
        this.state.newDebt.phone_id = phoneId;
        if (phoneId) {
            const phone = this.state.phones.find(p => p.id === phoneId);
            if (phone) {
                this.state.newDebt.phone_description = phone.model_name || "";
                this.state.newDebt.total_amount = Number(phone.selling_price || 0);
            }
        }
    }


    async _onSaveDebt() {
        const debt = this.state.newDebt;

        if (!debt.customer_id) {
            this.notification.add("Please select a customer.",
                { title: "Missing Customer", type: "warning" });
            return;
        }
        if (!debt.total_amount || Number(debt.total_amount) <= 0) {
            this.notification.add("Please enter a valid total amount.",
                { title: "Missing Amount", type: "warning" });
            return;
        }
        if (!debt.num_installments || Number(debt.num_installments) <= 0) {
            this.notification.add("Please enter number of installments.",
                { title: "Missing Installments", type: "warning" });
            return;
        }
        if (!debt.first_due_date) {
            this.notification.add("Please select first due date.",
                { title: "Missing Due Date", type: "warning" });
            return;
        }

        try {
            const vals = {
                customer_id: Number(debt.customer_id),
                phone_id: debt.phone_id ? Number(debt.phone_id) : false,
                phone_description: debt.phone_description || false,
                total_amount: Number(debt.total_amount || 0),
                down_payment: Number(debt.down_payment || 0),
                interest_rate: Number(debt.interest_rate || 0),
                num_installments: Number(debt.num_installments || 1),
                interval_type: debt.interval_type || "monthly",
                first_due_date: debt.first_due_date,
                payment_method: debt.payment_method || false,
                notes: debt.notes || false,
                state: "active",
            };

            const debtIdArray = await this.orm.create("phone.debt", [vals]);
            const debtId = Array.isArray(debtIdArray) ? debtIdArray[0] : debtIdArray;

            await this.orm.call("phone.debt", "action_generate_installments", [[debtId]]);

            this.notification.add("Debt created successfully.",
                { title: "Success", type: "success" });

            this.state.showDebtModal = false;
            await this.loadDebts();
            await this.loadReports();
            await this.loadDashboard();
        } catch (error) {
            console.error("Failed to create debt:", error);
            this.notification.add("Failed to save debt.",
                { title: "Error", type: "danger" });
        }
    }


    async _onViewDebt(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        if (!id) return;
        try {
            const installments = await this.orm.searchRead(
                "phone.installment", [["debt_id", "=", id]],
                [
                    "id", "debt_id", "sequence", "due_date", "amount",
                    "paid_amount", "balance", "payment_date",
                    "payment_method", "payment_reference", "state", "notes",
                ],
                { order: "sequence asc" }
            );
            this.state.selectedDebtId = id;
            this.state.currentDebtInstallments = installments;
            this.state.showInstallmentsModal = true;
        } catch (error) {
            console.error("Failed to load installments:", error);
            this.notification.add("Failed to load installments.",
                { title: "Error", type: "danger" });
        }
    }


    _onDeleteDebt(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        this.dialog.add(ConfirmationDialog, {
            title: "Delete Debt",
            body: "Are you sure you want to delete this debt and all its installments?",
            confirm: async () => {
                try {
                    await this.orm.unlink("phone.debt", [id]);
                    this.notification.add("Debt deleted successfully.",
                        { title: "Success", type: "success" });
                    await this.loadDebts();
                    await this.loadReports();
                    await this.loadDashboard();
                } catch (error) {
                    console.error("Failed to delete debt:", error);
                    this.notification.add("Failed to delete debt.",
                        { title: "Error", type: "danger" });
                }
            },
            cancel: () => {},
        });
    }


    async _onMarkInstallmentPaid(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        if (!id) return;
        try {
            await this.orm.call("phone.installment", "action_mark_paid", [id]);
            this.notification.add("Installment marked as paid.",
                { title: "Success", type: "success" });
            await this._reloadInstallmentsAndDebts();
        } catch (error) {
            console.error("Failed to mark installment paid:", error);
            this.notification.add("Failed to mark installment paid.",
                { title: "Error", type: "danger" });
        }
    }


    async _onOpenPaymentModal(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        if (!id) return;
        try {
            const installment = this.state.currentDebtInstallments.find(i => i.id === id) || null;
            if (!installment) {
                this.notification.add("Installment not found.",
                    { title: "Error", type: "danger" });
                return;
            }
            this.state.selectedInstallmentId = id;
            this.state.currentInstallment = installment;
            this.state.paymentData = {
                paid_amount: installment.balance || 0,
                payment_date: new Date().toISOString().split("T")[0],
                payment_method: "", payment_reference: "", notes: "",
            };
            this.state.showPaymentModal = true;
        } catch (error) {
            console.error("Failed to open payment modal:", error);
            this.notification.add("Failed to open payment modal.",
                { title: "Error", type: "danger" });
        }
    }


    closePaymentModal() {
        this.state.showPaymentModal = false;
        this.state.selectedInstallmentId = null;
        this.state.currentInstallment = null;
        this.state.paymentData = {
            paid_amount: 0, payment_date: "",
            payment_method: "", payment_reference: "", notes: "",
        };
    }

    onPaymentChange(field, ev) {
        this.state.paymentData[field] = ev.target.value || "";
    }


    async _onSavePayment() {
        const data = this.state.paymentData;
        const installment = this.state.currentInstallment;

        if (!installment || !installment.id) {
            this.notification.add("No installment selected.",
                { title: "Error", type: "danger" });
            return;
        }

        const paidAmount = Number(data.paid_amount || 0);
        if (paidAmount <= 0) {
            this.notification.add("Please enter a valid amount.",
                { title: "Missing Amount", type: "warning" });
            return;
        }

        const totalPaid = Number(installment.paid_amount || 0) + paidAmount;
        if (totalPaid > installment.amount) {
            this.notification.add("Total paid cannot exceed installment amount.",
                { title: "Invalid Amount", type: "warning" });
            return;
        }

        try {
            const vals = {
                paid_amount: totalPaid,
                payment_date: data.payment_date || new Date().toISOString().split("T")[0],
                payment_method: data.payment_method || false,
                payment_reference: data.payment_reference || false,
                notes: data.notes || false,
            };
            await this.orm.write("phone.installment", [installment.id], vals);
            this.notification.add("Payment recorded successfully.",
                { title: "Success", type: "success" });
            this.closePaymentModal();
            await this._reloadInstallmentsAndDebts();
        } catch (error) {
            console.error("Failed to save payment:", error);
            this.notification.add("Failed to save payment.",
                { title: "Error", type: "danger" });
        }
    }


    async _reloadInstallmentsAndDebts() {
        const debtId = this.state.selectedDebtId;
        if (debtId) {
            try {
                const installments = await this.orm.searchRead(
                    "phone.installment", [["debt_id", "=", debtId]],
                    [
                        "id", "debt_id", "sequence", "due_date", "amount",
                        "paid_amount", "balance", "payment_date",
                        "payment_method", "payment_reference", "state", "notes",
                    ],
                    { order: "sequence asc" }
                );
                this.state.currentDebtInstallments = installments;
            } catch (error) {
                console.error("Failed to reload installments:", error);
            }
        }
        await this.loadDebts();
        await this.loadReports();
        await this.loadDashboard();
    }


    // ============================================================
    // TRADE-IN SUMMARY
    // ============================================================

    get totalTradeIns() { return this.state.tradeIns.length; }
    get pendingTradeIns() {
        return this.state.tradeIns.filter(
            trade => trade.state === "draft" || trade.state === "evaluation"
        ).length;
    }
    get approvedTradeIns() {
        return this.state.tradeIns.filter(trade => trade.state === "approved").length;
    }
    get completedTradeIns() {
        return this.state.tradeIns.filter(trade => trade.state === "completed").length;
    }
    get cancelledTradeIns() {
        return this.state.tradeIns.filter(trade => trade.state === "cancelled").length;
    }
    get totalTradeInValue() {
        return this.state.tradeIns.reduce(
            (total, trade) => total + Number(trade.trade_in_value || 0), 0
        );
    }
    get totalTradeInTopUp() {
        return this.state.tradeIns.reduce(
            (total, trade) => total + Number(trade.amount_to_pay || 0), 0
        );
    }


    get totalSuppliers() { return this.state.suppliers.length; }
    get activeSuppliers() { return this.state.suppliers.filter(s => s.active).length; }
    get archivedSuppliers() { return this.state.suppliers.filter(s => !s.active).length; }


    get totalStaff() { return this.state.staff.length; }
    get activeStaff() { return this.state.staff.filter(s => s.active).length; }
    get archivedStaff() { return this.state.staff.filter(s => !s.active).length; }


    // ============================================================
    // STOCK FILTERS
    // ============================================================

    onStockSearchChange(ev) {
        this.state.stockFilters.search = ev.target.value || "";
        this.state.currentPage = 1;
    }

    onStockBrandFilterChange(ev) {
        this.state.stockFilters.brand_id = Number(ev.target.value) || null;
        this.state.stockFilters.category_id = null;
        this.state.currentPage = 1;
    }

    onStockCategoryFilterChange(ev) {
        this.state.stockFilters.category_id = Number(ev.target.value) || null;
        this.state.currentPage = 1;
    }

    onStockConditionFilterChange(ev) {
        this.state.stockFilters.condition_id = Number(ev.target.value) || null;
        this.state.currentPage = 1;
    }

    onStockStatusFilterChange(ev) {
        this.state.stockFilters.status = ev.target.value || "";
        this.state.currentPage = 1;
    }

    resetStockFilters() {
        this.state.stockFilters = {
            search: "", brand_id: null, category_id: null,
            condition_id: null, status: "",
        };
        this.state.currentPage = 1;
    }


    // ============================================================
    // SUPPLIER FILTERS
    // ============================================================

    onSupplierSearchChange(ev) {
        this.state.supplierFilters.search = ev.target.value || "";
        this.state.supplierCurrentPage = 1;
    }

    onSupplierStatusFilterChange(ev) {
        this.state.supplierFilters.status = ev.target.value || "active";
        this.state.supplierCurrentPage = 1;
    }

    resetSupplierFilters() {
        this.state.supplierFilters = { search: "", status: "active" };
        this.state.supplierCurrentPage = 1;
    }


    // ============================================================
    // STAFF FILTERS
    // ============================================================

    onStaffSearchChange(ev) {
        this.state.staffFilters.search = ev.target.value || "";
        this.state.staffCurrentPage = 1;
    }

    onStaffStatusFilterChange(ev) {
        this.state.staffFilters.status = ev.target.value || "active";
        this.state.staffCurrentPage = 1;
    }

    resetStaffFilters() {
        this.state.staffFilters = { search: "", status: "active" };
        this.state.staffCurrentPage = 1;
    }


    // ============================================================
    // SUPPLIER CRUD
    // ============================================================

    openAddSupplierModal() {
        this.state.newSupplier = {
            name: "", phone: "", email: "", street: "",
            city: "", vat: "", contact_person: "", comment: "",
        };
        this.state.showSupplierModal = true;
    }

    closeSupplierModal() { this.state.showSupplierModal = false; }
    closeEditSupplierModal() { this.state.showEditSupplierModal = false; }


    async _onSaveSupplier() {
        const supplier = this.state.newSupplier;
        if (!supplier.name) {
            this.notification.add("Please enter supplier name.",
                { title: "Missing Name", type: "warning" });
            return;
        }

        try {
            await this.orm.create("res.partner", [{
                name: supplier.name,
                phone: supplier.phone || false,
                email: supplier.email || false,
                street: supplier.street || false,
                city: supplier.city || false,
                vat: supplier.vat || false,
                comment: supplier.comment || false,
                supplier_rank: 1,
            }]);
            this.notification.add("Supplier added successfully.",
                { title: "Success", type: "success" });
            this.state.showSupplierModal = false;
            await this.loadSuppliers();
        } catch (error) {
            console.error("Failed to create supplier:", error);
            this.notification.add("Failed to save supplier.",
                { title: "Error", type: "danger" });
        }
    }


    _onEditSupplier(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        const supplier = this.state.suppliers.find(s => s.id === id);
        if (!supplier) return;

        this.state.editSupplier = {
            id: supplier.id, name: supplier.name || "",
            phone: supplier.phone || "", email: supplier.email || "",
            street: supplier.street || "", city: supplier.city || "",
            vat: supplier.vat || "", contact_person: "", comment: "",
        };
        this.state.showEditSupplierModal = true;
    }


    async _onUpdateSupplier() {
        const supplier = this.state.editSupplier;
        if (!supplier.id) return;
        if (!supplier.name) {
            this.notification.add("Please enter supplier name.",
                { title: "Missing Name", type: "warning" });
            return;
        }

        try {
            await this.orm.write("res.partner", [supplier.id], {
                name: supplier.name,
                phone: supplier.phone || false,
                email: supplier.email || false,
                street: supplier.street || false,
                city: supplier.city || false,
                vat: supplier.vat || false,
                comment: supplier.comment || false,
            });
            this.notification.add("Supplier updated successfully.",
                { title: "Success", type: "success" });
            this.state.showEditSupplierModal = false;
            await this.loadSuppliers();
        } catch (error) {
            console.error("Failed to update supplier:", error);
            this.notification.add("Failed to update supplier.",
                { title: "Error", type: "danger" });
        }
    }


    _onDeleteSupplier(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        this.dialog.add(ConfirmationDialog, {
            title: "Delete Supplier",
            body: "Are you sure you want to delete this supplier?",
            confirm: async () => {
                try {
                    await this.orm.unlink("res.partner", [id]);
                    this.notification.add("Supplier deleted successfully.",
                        { title: "Success", type: "success" });
                    await this.loadSuppliers();
                } catch (error) {
                    console.error("Failed to delete supplier:", error);
                    this.notification.add("Failed to delete supplier.",
                        { title: "Error", type: "danger" });
                }
            },
            cancel: () => {},
        });
    }


    onNewSupplierChange(field, ev) {
        this.state.newSupplier[field] = ev.target.value || "";
    }

    onEditSupplierChange(field, ev) {
        this.state.editSupplier[field] = ev.target.value || "";
    }


    // ============================================================
    // STAFF CRUD
    // ============================================================

    openAddStaffModal() {
        this.state.newStaff = {
            name: "", job_title: "", department_id: null,
            date_join: "", work_phone: "", mobile_phone: "",
            work_email: "", salary_amount: 0, commission_rate: 0, notes: "",
        };
        this.state.showStaffModal = true;
    }

    closeStaffModal() { this.state.showStaffModal = false; }
    closeEditStaffModal() { this.state.showEditStaffModal = false; }


    async _onSaveStaff() {
        const staff = this.state.newStaff;
        if (!staff.name) {
            this.notification.add("Please enter staff name.",
                { title: "Missing Name", type: "warning" });
            return;
        }

        try {
            await this.orm.create("hr.employee", [{
                name: staff.name,
                job_title: staff.job_title || false,
                department_id: staff.department_id ? Number(staff.department_id) : false,
                work_phone: staff.work_phone || false,
                mobile_phone: staff.mobile_phone || false,
                work_email: staff.work_email || false,
                active: true,
            }]);
            this.notification.add("Staff added successfully.",
                { title: "Success", type: "success" });
            this.state.showStaffModal = false;
            await this.loadStaff();
        } catch (error) {
            console.error("Failed to create staff:", error);
            this.notification.add("Failed to save staff.",
                { title: "Error", type: "danger" });
        }
    }


    _onEditStaff(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        const staff = this.state.staff.find(s => s.id === id);
        if (!staff) return;

        this.state.editStaff = {
            id: staff.id, name: staff.name || "",
            job_title: staff.job_title || "",
            department_id: staff.department_id ? staff.department_id[0] : null,
            date_join: "", work_phone: staff.work_phone || "",
            mobile_phone: staff.mobile_phone || "",
            work_email: staff.work_email || "",
            salary_amount: 0, commission_rate: 0, notes: "",
        };
        this.state.showEditStaffModal = true;
    }


    async _onUpdateStaff() {
        const staff = this.state.editStaff;
        if (!staff.id) return;
        if (!staff.name) {
            this.notification.add("Please enter staff name.",
                { title: "Missing Name", type: "warning" });
            return;
        }

        try {
            await this.orm.write("hr.employee", [staff.id], {
                name: staff.name,
                job_title: staff.job_title || false,
                department_id: staff.department_id ? Number(staff.department_id) : false,
                work_phone: staff.work_phone || false,
                mobile_phone: staff.mobile_phone || false,
                work_email: staff.work_email || false,
            });
            this.notification.add("Staff updated successfully.",
                { title: "Success", type: "success" });
            this.state.showEditStaffModal = false;
            await this.loadStaff();
        } catch (error) {
            console.error("Failed to update staff:", error);
            this.notification.add("Failed to update staff.",
                { title: "Error", type: "danger" });
        }
    }


    _onDeleteStaff(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        this.dialog.add(ConfirmationDialog, {
            title: "Delete Staff",
            body: "Are you sure you want to delete this staff member?",
            confirm: async () => {
                try {
                    await this.orm.unlink("hr.employee", [id]);
                    this.notification.add("Staff deleted successfully.",
                        { title: "Success", type: "success" });
                    await this.loadStaff();
                } catch (error) {
                    console.error("Failed to delete staff:", error);
                    this.notification.add("Failed to delete staff.",
                        { title: "Error", type: "danger" });
                }
            },
            cancel: () => {},
        });
    }


    onNewStaffChange(field, ev) {
        this.state.newStaff[field] = ev.target.value || "";
    }

    onEditStaffChange(field, ev) {
        this.state.editStaff[field] = ev.target.value || "";
    }


    // ============================================================
    // ADD PHONE (WITH IMAGES)
    // ============================================================

    openAddPhoneModal() {
        this.state.newPhone = {
            model_name: "", brand_id: null, category_id: null,
            imei_1: "", imei_2: "", condition_id: null,
            buying_price: 0, selling_price: 0,
            quantity: 1, status: "in_stock",
        };
        this.state.newPhoneImages = [];
        this.state.showModal = true;
    }

    closeModal() {
        this.state.showModal = false;
        this.state.newPhoneImages = [];
    }

    onBrandChange(ev) {
        this.state.newPhone.brand_id = Number(ev.target.value) || null;
        this.state.newPhone.category_id = null;
    }

    onCategoryChange(ev) {
        this.state.newPhone.category_id = Number(ev.target.value) || null;
    }

    onConditionChange(ev) {
        this.state.newPhone.condition_id = Number(ev.target.value) || null;
    }

    onStatusChange(ev) {
        this.state.newPhone.status = ev.target.value || "in_stock";
    }


    async _onSavePhone() {
        const phone = this.state.newPhone;

        if (!phone.model_name) {
            this.notification.add("Please enter the phone model.",
                { title: "Missing Phone Model", type: "warning" });
            return;
        }
        if (!phone.brand_id) {
            this.notification.add("Please select a brand.",
                { title: "Missing Brand", type: "warning" });
            return;
        }
        if (!phone.category_id) {
            this.notification.add("Please select a category.",
                { title: "Missing Category", type: "warning" });
            return;
        }
        if (!phone.condition_id) {
            this.notification.add("Please select a condition.",
                { title: "Missing Condition", type: "warning" });
            return;
        }
        if (!phone.imei_1) {
            this.notification.add("Please enter IMEI 1.",
                { title: "Missing IMEI", type: "warning" });
            return;
        }

        try {
            const phoneIdArray = await this.orm.create("phone.stock", [{
                model_name: phone.model_name,
                brand_id: Number(phone.brand_id),
                category_id: Number(phone.category_id),
                imei_1: phone.imei_1,
                imei_2: phone.imei_2 || false,
                condition_id: Number(phone.condition_id),
                buying_price: Number(phone.buying_price || 0),
                selling_price: Number(phone.selling_price || 0),
                quantity: Number(phone.quantity || 0),
                status: phone.status,
            }]);

            const phoneId = Array.isArray(phoneIdArray) ? phoneIdArray[0] : phoneIdArray;

            if (this.state.newPhoneImages.length && phoneId) {
                const imageVals = this.state.newPhoneImages.map((img, index) => ({
                    phone_id: phoneId,
                    image: img.base64,
                    filename: img.filename || `phone_image_${index + 1}`,
                    sequence: (index + 1) * 10,
                    is_primary: index === 0,
                }));
                await this.orm.create("phone.stock.image", imageVals);
            }

            this.notification.add("Phone added successfully.",
                { title: "Success", type: "success" });

            this.state.showModal = false;
            this.state.newPhoneImages = [];

            await this.loadPhones();
            await this.loadReports();
            await this.loadDashboard();
        } catch (error) {
            console.error("Failed to create phone:", error);
            this.notification.add("Failed to save phone.",
                { title: "Error", type: "danger" });
        }
    }


    async _onEditPhone(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        const phone = this.state.phones.find(record => record.id === id);
        if (!phone) return;

        this.state.editPhone = {
            id: phone.id,
            model_name: phone.model_name || "",
            brand_id: phone.brand_id ? phone.brand_id[0] : null,
            category_id: phone.category_id ? phone.category_id[0] : null,
            imei_1: phone.imei_1 || "",
            imei_2: phone.imei_2 || "",
            condition_id: phone.condition_id ? phone.condition_id[0] : null,
            buying_price: Number(phone.buying_price || 0),
            selling_price: Number(phone.selling_price || 0),
            quantity: Number(phone.quantity || 0),
            status: phone.status || "in_stock",
        };
        this.state.editPhoneNewImages = [];

        try {
            const existingImages = await this.orm.searchRead(
                "phone.stock.image", [["phone_id", "=", id]],
                ["id", "name", "filename", "sequence", "is_primary"],
                { order: "sequence asc, id asc" }
            );
            this.state.editPhoneExistingImages = existingImages;
        } catch (error) {
            console.error("Failed to load existing images:", error);
            this.state.editPhoneExistingImages = [];
        }

        this.state.showEditModal = true;
    }


    closeEditModal() {
        this.state.showEditModal = false;
        this.state.editPhoneNewImages = [];
        this.state.editPhoneExistingImages = [];
    }

    onEditBrandChange(ev) {
        this.state.editPhone.brand_id = Number(ev.target.value) || null;
        this.state.editPhone.category_id = null;
    }

    onEditCategoryChange(ev) {
        this.state.editPhone.category_id = Number(ev.target.value) || null;
    }

    onEditConditionChange(ev) {
        this.state.editPhone.condition_id = Number(ev.target.value) || null;
    }

    onEditStatusChange(ev) {
        this.state.editPhone.status = ev.target.value || "in_stock";
    }


    async _onUpdatePhone() {
        const phone = this.state.editPhone;
        if (!phone.id) return;

        if (!phone.model_name) {
            this.notification.add("Please enter the phone model.",
                { title: "Missing Phone Model", type: "warning" });
            return;
        }
        if (!phone.brand_id) {
            this.notification.add("Please select a brand.",
                { title: "Missing Brand", type: "warning" });
            return;
        }
        if (!phone.category_id) {
            this.notification.add("Please select a category.",
                { title: "Missing Category", type: "warning" });
            return;
        }
        if (!phone.condition_id) {
            this.notification.add("Please select a condition.",
                { title: "Missing Condition", type: "warning" });
            return;
        }

        try {
            await this.orm.write("phone.stock", [phone.id], {
                model_name: phone.model_name,
                brand_id: Number(phone.brand_id),
                category_id: Number(phone.category_id),
                imei_1: phone.imei_1,
                imei_2: phone.imei_2 || false,
                condition_id: Number(phone.condition_id),
                buying_price: Number(phone.buying_price || 0),
                selling_price: Number(phone.selling_price || 0),
                quantity: Number(phone.quantity || 0),
                status: phone.status,
            });

            if (this.state.editPhoneNewImages.length) {
                const currentCount = this.state.editPhoneExistingImages.length;
                const hasPrimary = this.state.editPhoneExistingImages.some(img => img.is_primary);

                const imageVals = this.state.editPhoneNewImages.map((img, index) => ({
                    phone_id: phone.id,
                    image: img.base64,
                    filename: img.filename || `phone_image_${index + 1}`,
                    sequence: (currentCount + index + 1) * 10,
                    is_primary: !hasPrimary && index === 0,
                }));
                await this.orm.create("phone.stock.image", imageVals);
            }

            this.notification.add("Phone updated successfully.",
                { title: "Success", type: "success" });

            this.state.showEditModal = false;
            this.state.editPhoneNewImages = [];
            this.state.editPhoneExistingImages = [];

            await this.loadPhones();
            await this.loadReports();
            await this.loadDashboard();
        } catch (error) {
            console.error("Failed to update phone:", error);
            this.notification.add("Failed to update phone.",
                { title: "Error", type: "danger" });
        }
    }


    _onDeletePhone(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        this.dialog.add(ConfirmationDialog, {
            title: "Delete Phone",
            body: "Are you sure you want to delete this phone? All images will also be deleted.",
            confirm: async () => {
                try {
                    await this.orm.unlink("phone.stock", [id]);
                    this.notification.add("Phone deleted successfully.",
                        { title: "Success", type: "success" });
                    await this.loadPhones();
                    await this.loadReports();
                    await this.loadDashboard();
                } catch (error) {
                    console.error("Failed to delete phone:", error);
                    this.notification.add("Failed to delete phone.",
                        { title: "Error", type: "danger" });
                }
            },
            cancel: () => {},
        });
    }


    // ============================================================
    // TRADE-IN FORM
    // ============================================================

    resetTradeInForm() {
        this.state.newTradeIn = {
            customer_id: null, customer_phone: "",
            old_phone_model: "", old_phone_brand_id: null,
            old_phone_imei_1: "", old_phone_imei_2: "",
            old_phone_serial_number: "", old_phone_condition_id: null,
            old_phone_storage: "", old_phone_battery_health: "",
            old_phone_accessories: "", old_phone_physical_condition: "",
            old_phone_notes: "",
            estimated_value: 0, adjustment_amount: 0, trade_in_value: 0,
            new_phone_id: null,
            amount_to_pay: 0, amount_paid: 0, balance: 0,
            payment_method: "", payment_reference: "", notes: "",
        };
    }

    openTradeInModal() {
        this.resetTradeInForm();
        this.state.showTradeInModal = true;
    }

    closeTradeInModal() {
        this.state.showTradeInModal = false;
        this.resetTradeInForm();
    }


    onTradeInCustomerChange(ev) {
        const customerId = Number(ev.target.value) || null;
        this.state.newTradeIn.customer_id = customerId;
        const customer = this.state.customers.find(item => item.id === customerId);
        if (customer) {
            this.state.newTradeIn.customer_phone = customer.phone || customer.mobile || "";
        } else {
            this.state.newTradeIn.customer_phone = "";
        }
    }

    onTradeInBrandChange(ev) {
        this.state.newTradeIn.old_phone_brand_id = Number(ev.target.value) || null;
    }

    onTradeInConditionChange(ev) {
        this.state.newTradeIn.old_phone_condition_id = Number(ev.target.value) || null;
    }

    onTradeInNewPhoneChange(ev) {
        const phoneId = Number(ev.target.value) || null;
        this.state.newTradeIn.new_phone_id = phoneId;
        this.updateTradeInFinancials();
    }

    onNewTradeInPhoneChange(ev) {
        this.onTradeInNewPhoneChange(ev);
    }


    get selectedTradeInPhone() {
        const phoneId = Number(this.state.newTradeIn.new_phone_id) || null;
        if (!phoneId) return null;
        return this.state.phones.find(phone => phone.id === phoneId) || null;
    }

    get selectedTradeInPhoneModel() {
        const phone = this.selectedTradeInPhone;
        return phone ? phone.model_name || "" : "";
    }

    get selectedTradeInPhoneIMEI1() {
        const phone = this.selectedTradeInPhone;
        return phone ? phone.imei_1 || "" : "";
    }

    get selectedTradeInPhoneIMEI2() {
        const phone = this.selectedTradeInPhone;
        return phone ? phone.imei_2 || "" : "";
    }

    get selectedTradeInPhonePrice() {
        const phone = this.selectedTradeInPhone;
        return phone ? Number(phone.selling_price || 0) : 0;
    }


    get tradeInAmountToPay() {
        const newPhonePrice = this.selectedTradeInPhonePrice;
        const tradeInValue = Number(this.state.newTradeIn.trade_in_value || 0);
        return Math.max(newPhonePrice - tradeInValue, 0);
    }

    get tradeInBalance() {
        const amountToPay = this.tradeInAmountToPay;
        const amountPaid = Number(this.state.newTradeIn.amount_paid || 0);
        return Math.max(amountToPay - amountPaid, 0);
    }

    updateTradeInFinancials() {
        const amountToPay = this.tradeInAmountToPay;
        const amountPaid = Number(this.state.newTradeIn.amount_paid || 0);
        this.state.newTradeIn.amount_to_pay = amountToPay;
        this.state.newTradeIn.balance = Math.max(amountToPay - amountPaid, 0);
    }

    onTradeInEstimatedValueChange(ev) {
        this.state.newTradeIn.estimated_value = Number(ev.target.value) || 0;
        this.calculateTradeInValue();
    }

    onTradeInAdjustmentChange(ev) {
        this.state.newTradeIn.adjustment_amount = Number(ev.target.value) || 0;
        this.calculateTradeInValue();
    }

    calculateTradeInValue() {
        const estimated = Number(this.state.newTradeIn.estimated_value || 0);
        const adjustment = Number(this.state.newTradeIn.adjustment_amount || 0);
        this.state.newTradeIn.trade_in_value = Math.max(estimated + adjustment, 0);
        this.updateTradeInFinancials();
    }

    onTradeInValueChange(ev) {
        this.state.newTradeIn.trade_in_value = Number(ev.target.value) || 0;
        this.updateTradeInFinancials();
    }

    onTradeInAmountPaidChange(ev) {
        this.state.newTradeIn.amount_paid = Number(ev.target.value) || 0;
        this.updateTradeInFinancials();
    }

    onTradeInPaymentMethodChange(ev) {
        this.state.newTradeIn.payment_method = ev.target.value || "";
    }

    onTradeInPaymentReferenceChange(ev) {
        this.state.newTradeIn.payment_reference = ev.target.value || "";
    }

    onTradeInSearchChange(ev) {
        this.state.tradeInFilters.search = ev.target.value || "";
        this.state.tradeInCurrentPage = 1;
    }

    onTradeInStateFilterChange(ev) {
        this.state.tradeInFilters.state = ev.target.value || "";
        this.state.tradeInCurrentPage = 1;
    }


    async _onSaveTradeIn() {
        const trade = this.state.newTradeIn;
        const customerId = Number(trade.customer_id) || 0;
        const brandId = Number(trade.old_phone_brand_id) || 0;
        const conditionId = Number(trade.old_phone_condition_id) || 0;
        const newPhoneId = Number(trade.new_phone_id) || 0;
        const tradeInValue = Number(trade.trade_in_value) || 0;
        const estimatedValue = Number(trade.estimated_value) || 0;
        const adjustmentAmount = Number(trade.adjustment_amount) || 0;
        const amountPaid = Number(trade.amount_paid) || 0;

        if (!customerId) {
            this.notification.add("Please select the customer.",
                { title: "Missing Customer", type: "warning" });
            return;
        }
        if (!trade.old_phone_model) {
            this.notification.add("Please enter the old phone model.",
                { title: "Missing Old Phone Model", type: "warning" });
            return;
        }
        if (!brandId) {
            this.notification.add("Please select the old phone brand.",
                { title: "Missing Brand", type: "warning" });
            return;
        }
        if (!trade.old_phone_imei_1) {
            this.notification.add("Please enter the old phone IMEI 1.",
                { title: "Missing IMEI", type: "warning" });
            return;
        }
        if (!conditionId) {
            this.notification.add("Please select the old phone condition.",
                { title: "Missing Condition", type: "warning" });
            return;
        }
        if (tradeInValue <= 0) {
            this.notification.add("Please enter a valid final trade-in value.",
                { title: "Invalid Trade-In Value", type: "warning" });
            return;
        }
        if (!newPhoneId) {
            this.notification.add("Please select the new phone from stock.",
                { title: "Missing New Phone", type: "warning" });
            return;
        }

        const vals = {
            customer_id: customerId,
            old_phone_model: trade.old_phone_model,
            old_phone_brand_id: brandId,
            old_phone_imei_1: trade.old_phone_imei_1,
            old_phone_imei_2: trade.old_phone_imei_2 || false,
            old_phone_serial_number: trade.old_phone_serial_number || false,
            old_phone_condition_id: conditionId,
            old_phone_storage: trade.old_phone_storage || false,
            old_phone_battery_health: trade.old_phone_battery_health || false,
            old_phone_accessories: trade.old_phone_accessories || false,
            old_phone_physical_condition: trade.old_phone_physical_condition || false,
            old_phone_notes: trade.old_phone_notes || false,
            estimated_value: estimatedValue,
            adjustment_amount: adjustmentAmount,
            trade_in_value: tradeInValue,
            new_phone_id: newPhoneId,
            amount_paid: amountPaid,
            payment_method: trade.payment_method || false,
            payment_reference: trade.payment_reference || false,
            notes: trade.notes || false,
        };

        try {
            await this.orm.create("phone.trade.in", [vals]);
            this.notification.add("Trade-In created successfully.",
                { title: "Success", type: "success" });

            this.state.showTradeInModal = false;
            this.resetTradeInForm();

            await Promise.all([this.loadTradeIns(), this.loadPhones()]);
            await this.loadReports();
            await this.loadDashboard();
        } catch (error) {
            console.error("Failed to create trade-in:", error);
            this.notification.add("Failed to create Trade-In.",
                { title: "Error", type: "danger" });
        }
    }


    async _onStartEvaluation(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        if (!id) return;
        try {
            await this.orm.write("phone.trade.in", [id], { state: "evaluation" });
            this.notification.add("Trade-In moved to evaluation.",
                { title: "Success", type: "success" });
            await this.loadTradeIns();
            await this.loadReports();
            await this.loadDashboard();
        } catch (error) {
            console.error("Failed to start evaluation:", error);
            this.notification.add("Failed to start evaluation.",
                { title: "Error", type: "danger" });
        }
    }

    async _onApproveTradeIn(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        if (!id) return;
        try {
            await this.orm.write("phone.trade.in", [id], { state: "approved" });
            this.notification.add("Trade-In approved successfully.",
                { title: "Success", type: "success" });
            await this.loadTradeIns();
            await this.loadReports();
            await this.loadDashboard();
        } catch (error) {
            console.error("Failed to approve trade-in:", error);
            this.notification.add("Failed to approve Trade-In.",
                { title: "Error", type: "danger" });
        }
    }

    async _onCompleteTradeIn(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        if (!id) return;
        try {
            await this.orm.write("phone.trade.in", [id], { state: "completed" });
            this.notification.add("Trade-In completed successfully.",
                { title: "Success", type: "success" });
            await this.loadTradeIns();
            await this.loadReports();
            await this.loadDashboard();
        } catch (error) {
            console.error("Failed to complete trade-in:", error);
            this.notification.add("Failed to complete Trade-In.",
                { title: "Error", type: "danger" });
        }
    }

    async _onCancelTradeIn(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        if (!id) return;
        this.dialog.add(ConfirmationDialog, {
            title: "Cancel Trade-In",
            body: "Are you sure you want to cancel this Trade-In?",
            confirm: async () => {
                try {
                    await this.orm.write("phone.trade.in", [id], { state: "cancelled" });
                    this.notification.add("Trade-In cancelled successfully.",
                        { title: "Success", type: "success" });
                    await this.loadTradeIns();
                    await this.loadReports();
                    await this.loadDashboard();
                } catch (error) {
                    console.error("Failed to cancel trade-in:", error);
                    this.notification.add("Failed to cancel Trade-In.",
                        { title: "Error", type: "danger" });
                }
            },
            cancel: () => {},
        });
    }

    async _onResetTradeIn(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        if (!id) return;
        try {
            await this.orm.write("phone.trade.in", [id], { state: "draft" });
            this.notification.add("Trade-In reset to draft.",
                { title: "Success", type: "success" });
            await this.loadTradeIns();
            await this.loadReports();
            await this.loadDashboard();
        } catch (error) {
            console.error("Failed to reset trade-in:", error);
            this.notification.add("Failed to reset Trade-In.",
                { title: "Error", type: "danger" });
        }
    }


    // ============================================================
    // CONFIGURATION — BRAND
    // ============================================================

    async _onSaveBrand() {
        const name = (this.state.newBrandName || "").trim();
        if (!name) {
            this.notification.add("Please enter a brand name.",
                { title: "Missing Brand", type: "warning" });
            return;
        }
        try {
            await this.orm.create("phone.brand", [{ name: name }]);
            this.state.newBrandName = "";
            await this.loadBrands();
            this.notification.add("Brand created successfully.",
                { title: "Success", type: "success" });
        } catch (error) {
            console.error("Failed to create brand:", error);
            this.notification.add("Failed to create brand.",
                { title: "Error", type: "danger" });
        }
    }


    onBrandForCategoryChange(ev) {
        this.state.selectedBrandForCategory = Number(ev.target.value) || null;
    }

    onSelectedBrandForCategoryChange(ev) {
        this.state.selectedBrandForCategory = Number(ev.target.value) || null;
    }

    onCategoryBrandChange(ev) {
        this.state.selectedBrandForCategory = Number(ev.target.value) || null;
    }

    async _onSaveCategory() {
        const name = (this.state.newCategoryName || "").trim();
        const brandId = Number(this.state.selectedBrandForCategory) || 0;

        if (!brandId) {
            this.notification.add("Please select a brand.",
                { title: "Missing Brand", type: "warning" });
            return;
        }
        if (!name) {
            this.notification.add("Please enter a category name.",
                { title: "Missing Category", type: "warning" });
            return;
        }

        try {
            await this.orm.create("phone.category", [{ name: name, brand_id: brandId }]);
            this.state.newCategoryName = "";
            this.state.categoryCurrentPage = 1;
            await this.loadCategories();
            this.notification.add("Category created successfully.",
                { title: "Success", type: "success" });
        } catch (error) {
            console.error("Failed to create category:", error);
            this.notification.add("Failed to create category.",
                { title: "Error", type: "danger" });
        }
    }


    async _onSaveCondition() {
        const name = (this.state.newConditionName || "").trim();
        if (!name) {
            this.notification.add("Please enter a condition name.",
                { title: "Missing Condition", type: "warning" });
            return;
        }
        try {
            await this.orm.create("phone.condition", [{ name: name }]);
            this.state.newConditionName = "";
            await this.loadConditions();
            this.notification.add("Condition created successfully.",
                { title: "Success", type: "success" });
        } catch (error) {
            console.error("Failed to create condition:", error);
            this.notification.add("Failed to create condition.",
                { title: "Error", type: "danger" });
        }
    }


    // ============================================================
    // USER ACCESS RIGHTS — CREATE
    // ============================================================

    openAddUserAccessModal() {
        this.state.newUserAccess = {
            name: "", login: "", password: "", email: "",
            allow_dashboard: true, allow_pos: true, allow_phones: true,
            allow_trade_in: true, allow_debts: true, allow_purchases: true,
            allow_suppliers: true, allow_staff: false,
            allow_reports: true, allow_settings: false,
        };
        this.state.showUserAccessModal = true;
    }

    closeUserAccessModal() { this.state.showUserAccessModal = false; }


    async _onSaveUserAccess() {
        const data = this.state.newUserAccess;
        if (!data.name || !data.login || !data.password) {
            this.notification.add("Name, Username, and Password are required.",
                { title: "Missing Fields", type: "warning" });
            return;
        }

        const allowedTabs = [];
        if (data.allow_dashboard) allowedTabs.push("dashboard");
        if (data.allow_pos) allowedTabs.push("pos");
        if (data.allow_phones) allowedTabs.push("phones");
        if (data.allow_trade_in) allowedTabs.push("trade_in");
        if (data.allow_debts) allowedTabs.push("debts");
        if (data.allow_purchases) allowedTabs.push("purchases");
        if (data.allow_suppliers) allowedTabs.push("suppliers");
        if (data.allow_staff) allowedTabs.push("staff");
        if (data.allow_reports) allowedTabs.push("reports");
        if (data.allow_settings) allowedTabs.push("settings");

        try {
            await this.orm.call("phone.user.access", "create_user_with_access", [{
                name: data.name, login: data.login, password: data.password,
                email: data.email, allowed_tabs: allowedTabs,
            }]);

            this.notification.add("User created successfully.",
                { title: "Success", type: "success" });
            this.state.showUserAccessModal = false;
            await this.loadUserAccesses();
        } catch (error) {
            console.error("Failed to create user:", error);
            this.notification.add("Failed to create user. Login might already exist.",
                { title: "Error", type: "danger" });
        }
    }


    _onEditUserAccess(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        const access = this.state.userAccesses.find(a => a.id === id);
        if (!access) {
            this.notification.add("User access not found.",
                { title: "Error", type: "danger" });
            return;
        }

        this.state.editUserAccess = {
            id: access.id,
            user_id: access.user_id ? access.user_id[0] : null,
            name: access.user_id ? access.user_id[1] : "",
            login: access.user_login || "",
            password: "",
            email: access.user_email || "",
            allow_dashboard: access.allow_dashboard,
            allow_pos: access.allow_pos,
            allow_phones: access.allow_phones,
            allow_trade_in: access.allow_trade_in,
            allow_debts: access.allow_debts,
            allow_purchases: access.allow_purchases,
            allow_suppliers: access.allow_suppliers,
            allow_staff: access.allow_staff,
            allow_reports: access.allow_reports,
            allow_settings: access.allow_settings,
        };
        this.state.showEditUserAccessModal = true;
    }

    closeEditUserAccessModal() { this.state.showEditUserAccessModal = false; }


    async _onUpdateUserAccess() {
        const data = this.state.editUserAccess;
        if (!data.id || !data.user_id) {
            this.notification.add("User access not selected.",
                { title: "Error", type: "danger" });
            return;
        }

        try {
            const userVals = { name: data.name };
            if (data.email) userVals.email = data.email;
            if (data.password && data.password.trim() !== "") {
                userVals.password = data.password;
            }

            await this.orm.write("res.users", [data.user_id], userVals);

            const accessVals = {
                allow_dashboard: data.allow_dashboard,
                allow_pos: data.allow_pos,
                allow_phones: data.allow_phones,
                allow_trade_in: data.allow_trade_in,
                allow_debts: data.allow_debts,
                allow_purchases: data.allow_purchases,
                allow_suppliers: data.allow_suppliers,
                allow_staff: data.allow_staff,
                allow_reports: data.allow_reports,
                allow_settings: data.allow_settings,
            };
            await this.orm.write("phone.user.access", [data.id], accessVals);

            this.notification.add("User access updated successfully.",
                { title: "Success", type: "success" });
            this.state.showEditUserAccessModal = false;
            await this.loadUserAccesses();
        } catch (error) {
            console.error("Failed to update user access:", error);
            this.notification.add("Failed to update user access.",
                { title: "Error", type: "danger" });
        }
    }


    async _onToggleUserAccessActive(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        const access = this.state.userAccesses.find(a => a.id === id);
        if (!access) return;

        const isCurrentlyActive = access.active;
        const actionTitle = isCurrentlyActive ? "Deactivate User" : "Activate User";
        const actionBody = isCurrentlyActive
            ? "Are you sure you want to DEACTIVATE this user? They will NOT be able to login."
            : "Are you sure you want to ACTIVATE this user? They will be able to login again.";

        this.dialog.add(ConfirmationDialog, {
            title: actionTitle,
            body: actionBody,
            confirmLabel: isCurrentlyActive ? "Yes, Deactivate" : "Yes, Activate",
            confirm: async () => {
                try {
                    await this.orm.write("phone.user.access", [id], { active: !isCurrentlyActive });
                    if (access.user_id) {
                        await this.orm.write("res.users", [access.user_id[0]], { active: !isCurrentlyActive });
                    }
                    this.notification.add(
                        isCurrentlyActive ? "User deactivated successfully." : "User activated successfully.",
                        { title: "Success", type: "success" }
                    );
                    await this.loadUserAccesses();
                } catch (error) {
                    console.error("Failed to toggle user active:", error);
                    this.notification.add("Failed to change user status.",
                        { title: "Error", type: "danger" });
                }
            },
            cancel: () => {},
        });
    }


    _onDeleteUserAccess(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        this.dialog.add(ConfirmationDialog, {
            title: "Delete User Access",
            body: "Are you sure? This will NOT delete the Odoo user, only the access rules.",
            confirm: async () => {
                try {
                    await this.orm.unlink("phone.user.access", [id]);
                    this.notification.add("Access rule deleted.",
                        { title: "Success", type: "success" });
                    await this.loadUserAccesses();
                } catch (error) {
                    console.error("Failed to delete access:", error);
                    this.notification.add("Failed to delete access.",
                        { title: "Error", type: "danger" });
                }
            },
            cancel: () => {},
        });
    }


    // ============================================================
    // SIDEBAR MENU HANDLERS
    // ============================================================

    async _onMenuDashboard(ev) {
        ev.preventDefault();
        if (!this.hasTabAccess("dashboard")) {
            this.notification.add("Huna ruhusa ya kuona Dashboard.",
                { title: "Access Denied", type: "warning" });
            return;
        }
        this.state.activeTab = "dashboard";
        await this.loadDashboard();
    }

    _onMenuPos(ev) {
        ev.preventDefault();
        if (!this.hasTabAccess("pos")) {
            this.notification.add("Huna ruhusa ya kuona POS.",
                { title: "Access Denied", type: "warning" });
            return;
        }
        this.state.activeTab = "pos";
    }

    _onMenuPhones(ev) {
        ev.preventDefault();
        if (!this.hasTabAccess("phones")) {
            this.notification.add("Huna ruhusa ya kuona Phones & Stock.",
                { title: "Access Denied", type: "warning" });
            return;
        }
        this.state.activeTab = "phones";
    }

    _onMenuTradeIn(ev) {
        ev.preventDefault();
        if (!this.hasTabAccess("trade_in")) {
            this.notification.add("Huna ruhusa ya kuona Trade-In.",
                { title: "Access Denied", type: "warning" });
            return;
        }
        this.state.activeTab = "trade_in";
    }

    _onMenuDebts(ev) {
        ev.preventDefault();
        if (!this.hasTabAccess("debts")) {
            this.notification.add("Huna ruhusa ya kuona Debts.",
                { title: "Access Denied", type: "warning" });
            return;
        }
        this.state.activeTab = "debts";
    }

    async _onMenuPurchases(ev) {
        ev.preventDefault();
        if (!this.hasTabAccess("purchases")) {
            this.notification.add("Huna ruhusa ya kuona Purchases.",
                { title: "Access Denied", type: "warning" });
            return;
        }
        this.state.activeTab = "purchases";
        await this.loadPurchases();
    }

    _onMenuSuppliers(ev) {
        ev.preventDefault();
        if (!this.hasTabAccess("suppliers")) {
            this.notification.add("Huna ruhusa ya kuona Suppliers.",
                { title: "Access Denied", type: "warning" });
            return;
        }
        this.state.activeTab = "suppliers";
    }

    _onMenuStaff(ev) {
        ev.preventDefault();
        if (!this.hasTabAccess("staff")) {
            this.notification.add("Huna ruhusa ya kuona Staff.",
                { title: "Access Denied", type: "warning" });
            return;
        }
        this.state.activeTab = "staff";
    }

    async _onMenuReports(ev) {
        ev.preventDefault();
        if (!this.hasTabAccess("reports")) {
            this.notification.add("Huna ruhusa ya kuona Reports.",
                { title: "Access Denied", type: "warning" });
            return;
        }
        this.state.activeTab = "reports";
        await this.loadReports();
        await this.loadDashboard();
        await this._loadDailyReport();
    }

    _onMenuSettings(ev) {
        ev.preventDefault();
        if (!this.hasTabAccess("settings")) {
            this.notification.add("Huna ruhusa ya kuona Configuration.",
                { title: "Access Denied", type: "warning" });
            return;
        }
        this.state.activeTab = "settings";
    }

}


registry.category("actions").add(
    "phone_point_keeping.PhoneDashboard",
    PhoneDashboard
);