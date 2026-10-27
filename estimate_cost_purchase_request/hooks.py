import re

from odoo.exceptions import UserError

MODULE = "estimate_cost_purchase_request"
VIEW_NAME = "report_purchase_request_estimated_total"
REPORT_KEY = "purchase_request.report_purchase_request"

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


def _find_view_with_table(env, key, depth=0):
    """Start from the report template; if the table lives in a sub-template
    called with t-call, follow the call chain until a view with a table is found."""
    view = env["ir.ui.view"].search(
        [("key", "=", key), ("inherit_id", "=", False)], limit=1
    )
    if not view or depth > 4:
        return env["ir.ui.view"]
    arch = view.arch_db or ""
    if "<table" in arch:
        return view
    for called in re.findall(r't-call="([^"]+)"', arch):
        if called.startswith("web.") or called == key:
            continue
        found = _find_view_with_table(env, called, depth + 1)
        if found:
            return found
    return env["ir.ui.view"]


def post_init_hook(env):
    imd = env["ir.model.data"]
    View = env["ir.ui.view"]

    old = imd.search([("module", "=", MODULE), ("name", "=", VIEW_NAME)])
    if old:
        View.browse(old.mapped("res_id")).exists().unlink()
        old.unlink()

    target = _find_view_with_table(env, REPORT_KEY)
    if not target:
        keys = View.search(
            [("type", "=", "qweb"), ("key", "like", "purchase_request.%")]
        ).mapped("key")
        raise UserError(
            "Could not find a table in '%s' (or the templates it calls). "
            "purchase_request QWeb views found: %s" % (REPORT_KEY, ", ".join(keys))
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
            "module": MODULE,
            "name": VIEW_NAME,
            "model": "ir.ui.view",
            "res_id": view.id,
            "noupdate": False,
        }
    )
