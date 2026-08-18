# Copyright (c) 2026, Holec
#
# Cost Ledger Entry: one row = one cost, tagged to one Lot. Rows never get
# edited after the Lot has moved past the state they were posted at -
# corrections must be reversing entries. This file enforces both that rule
# and the "judgement charges need a reason code" rule from Charge Master.

import frappe
from frappe.model.document import Document
from frappe import _


class CostLedgerEntry(Document):
	pass


def validate_no_edit_after_post(doc, method=None):
	"""
	doc here is the PARENT (Lot), not the child row directly - Frappe
	validates child tables through the parent's validate cycle. We walk
	the cost_entries table and check two things per row:
	  1. if requires_reason_code is set on the Charge Master row, the
	     reason_code field on this line must be filled in
	  2. if a row that existed on the last save is now different in
	     amount, that's an edit-after-post - reject it (reversal only)
	"""
	if not hasattr(doc, "cost_entries"):
		return  # not a Lot, or no cost_entries table - nothing to check

	from holec_trading.holec_trading.doctype.charge_master.charge_master import get_charge_defaults

	previous_entries = {}
	if not doc.is_new():
		previous_doc = frappe.get_doc("Lot", doc.name)
		previous_entries = {row.name: row.amount for row in previous_doc.cost_entries}

	for row in doc.cost_entries or []:
		defaults = get_charge_defaults(row.charge_type)

		if defaults["requires_reason_code"] and not row.reason_code and not row.is_reversal:
			frappe.throw(
				_("Row for '{0}': reason code is required for this charge.").format(row.charge_type)
			)

		if row.name in previous_entries and not row.is_reversal:
			if previous_entries[row.name] != row.amount:
				frappe.throw(
					_("Row for '{0}' has already been posted and cannot be edited. "
					  "Add a new reversing entry instead (tick 'Is Reversal', reference this row).")
					.format(row.charge_type)
				)
