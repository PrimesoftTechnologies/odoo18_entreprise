"""Pure lxml helpers used by the _get_view overrides (no odoo import, easy to test)."""
from lxml import etree


def _orig_invisible(node):
    inv = (node.get('invisible') or '').strip()
    if not inv and node.get('states'):
        inv = "state not in %s" % [s.strip() for s in node.get('states').split(',')]
    if 'states' in node.attrib:
        del node.attrib['states']
    return inv


def _or(orig, extra):
    return "(%s) or (%s)" % (orig, extra) if orig else extra


def _first(arch, expr):
    res = arch.xpath(expr)
    return res[0] if res else None


def _insert_after(node, *new_nodes):
    parent = node.getparent()
    idx = parent.index(node)
    for i, n in enumerate(new_nodes, 1):
        parent.insert(idx + i, n)


# --------------------------------------------------------------------------
# purchase.request form
# --------------------------------------------------------------------------
def inject_request_form(arch):
    if arch.xpath("//button[@name='action_create_internal_transfer']"):
        return
    candidates = arch.xpath("//header/button[@type='action']")
    rfq = [b for b in candidates if (b.get('string') or '').strip().lower() == 'create rfq']
    if not rfq and len(candidates) == 1:
        rfq = candidates
    if not rfq:
        return
    btn = rfq[0]
    orig = _orig_invisible(btn)
    btn.set('invisible', _or(orig, "is_internal_transfer"))

    base = _or("not is_internal_transfer", orig) if orig else "not is_internal_transfer"
    # before any transfer exists: main (highlighted / purple) button
    primary = etree.Element('button', {
        'name': 'action_create_internal_transfer',
        'type': 'object',
        'string': 'Internal Transfer',
        'class': 'oe_highlight',
        'invisible': _or(base, "transfer_requested or transfer_count > 0"),
    })
    # once the request has transfers: same button, normal (secondary) colour
    secondary = etree.Element('button', {
        'name': 'action_create_internal_transfer',
        'type': 'object',
        'string': 'Internal Transfer',
        'invisible': _or(base, "not transfer_requested and transfer_count == 0"),
    })
    hidden = etree.Element('field', {'name': 'is_internal_transfer', 'invisible': '1'})
    hidden_count = etree.Element('field', {'name': 'transfer_count', 'invisible': '1'})
    hidden_req = etree.Element('field', {'name': 'transfer_requested', 'invisible': '1'})
    _insert_after(btn, primary, secondary, hidden, hidden_count, hidden_req)

    # smart button with the number of transfers
    box = _first(arch, "//div[@name='button_box']")
    if box is not None:
        stat = etree.fromstring(
            '<button type="object" name="action_view_internal_transfer" '
            'class="oe_stat_button" icon="fa-exchange" '
            'invisible="transfer_count == 0">'
            '<field name="transfer_count" widget="statinfo" string="Transfers"/>'
            '</button>')
        box.append(stat)


# --------------------------------------------------------------------------
# stock.location
# --------------------------------------------------------------------------
def inject_location_form(arch):
    if arch.xpath("//field[@name='location_owner_id']"):
        return
    usage = _first(arch, "//field[@name='usage'][not(ancestor::field)]")
    node = etree.Element('field', {'name': 'location_owner_id'})
    if usage is not None:
        _insert_after(usage, node)
        return
    group = _first(arch, "//sheet//group")
    if group is not None:
        group.append(node)


def inject_location_list(arch):
    if arch.xpath("//field[@name='location_owner_id']"):
        return
    ref = _first(arch, "//field[@name='complete_name']") or _first(arch, "//field[@name='usage']")
    if ref is not None:
        _insert_after(ref, etree.Element('field', {
            'name': 'location_owner_id', 'optional': 'show'}))


# --------------------------------------------------------------------------
# stock.picking
# --------------------------------------------------------------------------
def inject_picking_form(arch):
    if arch.xpath("//field[@name='pending_validation']"):
        return
    vbtns = arch.xpath("//header/button[@name='button_validate']")
    if not vbtns:
        return
    # Snapshot of the standard header buttons (before adding ours).
    # - Validate / Mark as Todo: hidden for whoever may not act at the current step
    # - every other header button: hidden for the destination owner until the transfer is pending
    for b in arch.xpath("//header/button"):
        orig = _orig_invisible(b)
        if b.get('name') in ('button_validate', 'action_confirm'):
            b.set('invisible', _or(orig, "hide_validation_buttons"))
        else:
            b.set('invisible', _or(orig, "hide_dest_buttons"))

    pending_btn = etree.Element('button', {
        'name': 'action_pending_validation_info',
        'type': 'object',
        'string': 'Pending Validation',
        'class': 'btn-warning',
        'invisible': "not pending_validation or is_dest_owner or state in ('done', 'cancel')",
    })
    reject_btn = etree.Element('button', {
        'name': 'action_reject_pending_validation',
        'type': 'object',
        'string': 'Reject Validation',
        'invisible': "not pending_validation or not is_dest_owner or state in ('done', 'cancel')",
    })
    f_pending = etree.Element('field', {'name': 'pending_validation', 'invisible': '1'})
    f_isowner = etree.Element('field', {'name': 'is_dest_owner', 'invisible': '1'})
    f_hide = etree.Element('field', {'name': 'hide_validation_buttons', 'invisible': '1'})
    f_hide2 = etree.Element('field', {'name': 'hide_dest_buttons', 'invisible': '1'})
    _insert_after(vbtns[-1], pending_btn, reject_btn, f_pending, f_isowner, f_hide, f_hide2)

    src_owner = etree.Element('field', {
        'name': 'location_owner_id', 'invisible': 'not location_owner_id'})
    dest_owner = etree.Element('field', {
        'name': 'location_dest_owner_id', 'invisible': 'not location_dest_owner_id'})
    src = _first(arch, "//field[@name='location_id'][not(ancestor::field)]")
    dest = _first(arch, "//field[@name='location_dest_id'][not(ancestor::field)]")
    if dest is not None:
        _insert_after(dest, dest_owner)
    if src is not None:
        _insert_after(src, src_owner)
    if src is None and dest is None:
        pt = _first(arch, "//field[@name='picking_type_id'][not(ancestor::field)]")
        if pt is not None:
            _insert_after(pt, src_owner, dest_owner)
