from odoo.exceptions import UserError

VIEW_NAME = "report_purchase_request_estimated_total"

ARCH = """
<data>
    <xpath expr="(//table)[last()]" position="after">
        <div class="row justify-content-end mt-3">
            <div class="col-5">
                <table class="table table-sm">
                    <tr class="border-black">
                        <td><strong>Total Estimated Cost</strong></td>
                        <td class="text-end">
                            <strong>
                                <span t-esc="sum(o.line_ids.mapped('estimated_cost'))"
                                      t-options="{'widget': 'monetary', 'display_currency': o.company_id.currency_id}"/>
                            </strong>
                        </td>
                    </tr>
                </table>
            </div>
        </div>
    </xpath>
</data>
"""


def post_init_hook(env):
    """Find the QWeb template of the Purchase Request report (whatever its
    external ID is in the installed version) and extend it."""
    View = env["ir.ui.view"]
    imd = env["ir.model.data"]

    if imd.search_count([("module", "=", "estimate_cost_purchase_request"), ("name", "=", VIEW_NAME)]):
        return

    candidates = View.search(
        [("type", "=", "qweb"), ("inherit_id", "=", False), ("key", "like", "purchase_request.%")]
    )
    target = candidates.filtered(
        lambda v: "estimated_cost" in (v.arch_db or "") and "<table" in (v.arch_db or "")
    )[:1]
    if not target:
        target = candidates.filtered(
            lambda v: "line_ids" in (v.arch_db or "") and "<table" in (v.arch_db or "")
        )[:1]
    if not target:
        raise UserError(
            "Could not find the Purchase Request report template. "
            "Available purchase_request QWeb views: %s" % ", ".join(candidates.mapped("key"))
        )

    view = View.create(
        {
            "name": "Purchase Request Report: Total Estimated Cost",
            "type": "qweb",
            "inherit_id": target.id,
            "mode": "extension",
            "arch_base": ARCH,
        }
    )
    imd.create(
        {
            "module": "estimate_cost_purchase_request",
            "name": VIEW_NAME,
            "model": "ir.ui.view",
            "res_id": view.id,
            "noupdate": False,
        }
    )
