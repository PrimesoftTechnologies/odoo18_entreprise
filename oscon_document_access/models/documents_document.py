from odoo import api, models


class DocumentsDocument(models.Model):
    _inherit = "documents.document"

    @api.model_create_multi
    def create(self, vals_list):
        docs = super().create(vals_list)
        docs._oscon_grant_bosses()
        return docs

    def _oscon_grant_bosses(self, only_partners=None):
        """Give every configured boss (View role) access to these documents."""
        docs = self.sudo().exists()
        if not docs:
            return
        Access = self.env["documents.access"].sudo()
        companies = {}
        for doc in docs:
            company = doc.company_id or self.env.company
            companies.setdefault(company, self.env["documents.document"])
            companies[company] |= doc
        for company, company_docs in companies.items():
            partners = company.sudo().oscon_boss_ids.partner_id
            if only_partners is not None:
                partners &= only_partners
            if not partners:
                continue
            existing = Access.search(
                [
                    ("document_id", "in", company_docs.ids),
                    ("partner_id", "in", partners.ids),
                ]
            )
            done = {(a.document_id.id, a.partner_id.id) for a in existing}
            to_create = [
                {
                    "document_id": doc.id,
                    "partner_id": partner.id,
                    "role": "view",
                    "oscon_auto": True,
                }
                for doc in company_docs
                for partner in partners
                if (doc.id, partner.id) not in done
            ]
            if to_create:
                Access.create(to_create)

    @api.model
    def _oscon_sync_company(self, company, added_partners):
        """Apply newly added bosses to ALL existing documents of the company."""
        domain = [("company_id", "in", [company.id, False])]
        docs = self.sudo().with_context(active_test=False).search(domain)
        step = 500
        for i in range(0, len(docs), step):
            docs[i:i + step]._oscon_grant_bosses(only_partners=added_partners)
