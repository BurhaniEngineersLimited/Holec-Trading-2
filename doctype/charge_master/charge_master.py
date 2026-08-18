# Copyright (c) 2026, Holec
# Charge Master: the single catalogue of every buy-side, sell-side, and
# internal cost. Cost Ledger Entry looks up charge_type against this table
# to inherit default_borne_by, posting_treatment, and gl_account.

import frappe
from frappe.model.document import Document


class ChargeMaster(Document):
	pass


def get_charge_defaults(charge_name: str) -> dict:
	"""
	Helper used by Cost Ledger Entry when a new line is created.
	Returns the default borne_by / posting_treatment / gl_account
	for a given charge, so the user only overrides when a trade
	genuinely deviates from the rule.
	"""
	charge = frappe.get_cached_doc("Charge Master", charge_name)
	return {
		"direction": charge.direction,
		"borne_by": charge.default_borne_by,
		"posting_treatment": charge.posting_treatment,
		"gl_account": charge.gl_account,
		"requires_reason_code": charge.requires_reason_code,
	}
