"""Pure lxml helpers used by the _get_view overrides (no odoo import, easy to test)."""
from lxml import etree


def _orig_invisible(node):
    """Return the node's original `invisible` expression (converting legacy `states`)."""
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
# stock.location
# --------------------------------------------------------------------------
def inject_location_form(arch):
    if arch.xpath("//field[@name='location_owner_ids']"):
        return
    usage = _first(arch, "//field[@name='usage'][not(ancestor::field)]")
    node = etree.Element('field', {
        'name': 'location_owner_ids', 'widget': 'many2many_tags',
        'options': "{'no_create': True}"})
    if usage is not None:
        _insert_after(usage, node)
        return
    group = _first(arch, "//sheet//group")
    if group is not None:
        group.append(node)


def inject_location_list(arch):
    if arch.xpath("//field[@name='location_owner_ids']"):
        return
    ref = _first(arch, "//field[@name='complete_name']")
    if ref is None:
        ref = _first(arch, "//field[@name='usage']")
    if ref is not None:
        _insert_after(ref, etree.Element('field', {
            'name': 'location_owner_ids', 'widget': 'many2many_tags',
            'optional': 'show'}))


# --------------------------------------------------------------------------
# stock.picking
# --------------------------------------------------------------------------
def inject_picking_form(arch):
    if arch.xpath("//field[@name='pending_validation']"):
        return
    vbtns = arch.xpath("//header/button[@name='button_validate']")
    if not vbtns:
        return
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
    hidden = [
        etree.Element('field', {'name': name, 'invisible': '1'})
        for name in ('pending_validation', 'is_dest_owner',
                     'hide_validation_buttons', 'hide_dest_buttons')
    ]
    _insert_after(vbtns[-1], pending_btn, reject_btn, *hidden)

    src_owner = etree.Element('field', {
        'name': 'location_owner_ids', 'widget': 'many2many_tags',
        'invisible': 'not location_owner_ids'})
    dest_owner = etree.Element('field', {
        'name': 'location_dest_owner_ids', 'widget': 'many2many_tags',
        'invisible': 'not location_dest_owner_ids'})
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
