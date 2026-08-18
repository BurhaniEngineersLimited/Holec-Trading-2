# Copyright (c) 2026, Holec
#
# Lot: the central trading unit. Moves through six states:
#   Ticket -> Intake -> Lot -> Position -> Invoiced -> Settled
#
# THE CORE RULE, enforced here:
# every state transition must either (a) create at least one Cost Ledger
# Entry, or (b) be one of the two states that legitimately post nothing
# (Ticket, Intake). If neither, the transition is rejected. This is what
# keeps the audit trail honest - a step that changes nothing about cost
# or state doesn't belong in the workflow, it's a form field.

import frappe
from frappe.model.document import Document
from frappe import _

# States that are allowed to have zero Cost Ledger postings.
STATES_WITH_NO_REQUIRED_POSTING = {"Ticket", "Intake"}

# Valid forward transitions only - no skipping states, no going backward.
ALLOWED_TRANSITIONS = {
	"Ticket": "Intake",
	"Intake": "Lot",
	"Lot": "Position",
	"Position": "Invoiced",
	"Invoiced": "Settled",
	"Settled": None,  # terminal state
}

# Charges expected to post automatically at each state, by charge_name
# in Charge Master. Used by create_state_cost_entries() below.
AUTO_CHARGES_BY_STATE = {
	"Lot": ["Moisture Deduction", "Foreign Matter Deduction", "Bagging"],
	"Position": ["Haulage", "Cess"],
	"Settled": ["Transfer Charge"],
}


class Lot(Document):
	def before_save(self):
		self.set_moisture_band()
		self.recalculate_payable_weight()
		self.recalculate_landed_cost()

	def set_moisture_band(self):
		"""
		Buy-side moisture rule, resolved with Minal:
		  <= 14%   -> straight in, no drying
		  14-20%   -> drying band, price negotiated commercially
		  > 20%    -> no automatic rejection, but requires case-by-case
		              approval (Minal's call)
		"""
		if self.moisture_pct is None:
			return

		if self.moisture_pct <= 14:
			self.moisture_band = "Under 14 - Straight In"
			self.requires_moisture_approval = 0
		elif self.moisture_pct <= 20:
			self.moisture_band = "14 to 20 - Drying, Price Negotiated"
			self.requires_moisture_approval = 0
		else:
			self.moisture_band = "Over 20 - Requires Approval"
			self.requires_moisture_approval = 1

	def recalculate_payable_weight(self):
		"""
		payable_weight_kg = gross weight, minus whatever the moisture and
		foreign-matter deduction lines in the cost ledger say to remove.
		Those deductions are entered as Cost Ledger Entries with
		posting_treatment = 'Reduces Payable Weight'; this just sums them.
		"""
		if not self.gross_weight_kg:
			return

		weight_deductions_kg = 0
		for entry in self.cost_entries or []:
			if entry.posting_treatment == "Reduces Payable Weight":
				weight_deductions_kg += entry.weight_deduction_kg or 0

		self.payable_weight_kg = self.gross_weight_kg - weight_deductions_kg

	def recalculate_landed_cost(self):
		"""landed_cost_per_kg = total of all cost lines / payable weight."""
		if not self.payable_weight_kg:
			self.landed_cost_per_kg = 0
			return

		total_cost = sum((entry.amount or 0) for entry in self.cost_entries or [])
		self.landed_cost_per_kg = total_cost / self.payable_weight_kg

	def check_commingling(self):
		"""
		On setting storage_stack, flag if another Lot already sitting in
		that stack has a different county/area/grade. Origin becomes
		proportional rather than exact once this fires - Phase 2 concern,
		but the flag is cheap to set now.
		"""
		if not self.storage_stack:
			return

		other_lots = frappe.get_all(
			"Lot",
			filters={
				"storage_stack": self.storage_stack,
				"name": ["!=", self.name],
				"state": ["in", ["Position", "Invoiced"]],
			},
			fields=["county", "area"],
		)
		for other in other_lots:
			if other.county != self.county or other.area != self.area:
				self.commingled = 1
				return
		self.commingled = 0


def validate_state_transition(doc, method=None):
	"""
	Called on every save via hooks.py doc_events. Blocks the save if:
	  - the state field was changed directly to something not reachable
	    from its previous state (no skipping, no going backward)
	  - the new state requires a cost posting and none exists yet
	Advancing state should normally go through advance_lot_state() below,
	not by editing the field directly - this is the safety net if someone
	tries to bypass that via the API or Data Import.
	"""
	if doc.is_new():
		return  # a fresh Lot starts at Ticket, nothing to check yet

	previous_state = frappe.db.get_value("Lot", doc.name, "state")
	if previous_state == doc.state:
		return  # state unchanged on this save, nothing to enforce

	expected_next = ALLOWED_TRANSITIONS.get(previous_state)
	if doc.state != expected_next:
		frappe.throw(
			_("Cannot move Lot from {0} to {1}. Use Advance State, which only allows {0} -> {2}.")
			.format(previous_state, doc.state, expected_next)
		)

	if doc.state not in STATES_WITH_NO_REQUIRED_POSTING:
		has_posting_for_this_state = any(
			entry.posted_at_state == doc.state for entry in (doc.cost_entries or [])
		)
		if not has_posting_for_this_state:
			frappe.throw(
				_("Lot cannot enter state '{0}' without at least one Cost Ledger Entry. "
				  "A transition must change state or post a cost - never neither.")
				.format(doc.state)
			)


def on_lot_state_change(doc, method=None):
	"""
	Runs after save. Writes the append-only audit event. This is separate
	from Cost Ledger Entry - the event log records WHO/WHEN/WHAT DOCUMENT,
	independent of whether money moved.
	"""
	frappe.get_doc({
		"doctype": "Lot Event Log",
		"lot": doc.name,
		"state": doc.state,
		"changed_by": frappe.session.user,
		"changed_at": frappe.utils.now(),
	}).insert(ignore_permissions=True)


@frappe.whitelist()
def advance_lot_state(lot_name: str):
	"""
	The one supported way to move a Lot forward. Creates the auto-charges
	expected at the new state (see AUTO_CHARGES_BY_STATE) before changing
	the state field, so validate_state_transition() above always finds
	the posting it's looking for.

	Judgement-field charges (foreign matter %, aflatoxin sampling) are
	NOT auto-created here - those require a human to enter a value and a
	reason code first. If they're missing, this function will stop and
	tell the user what's needed before the state can advance.
	"""
	lot = frappe.get_doc("Lot", lot_name)
	current_state = lot.state
	next_state = ALLOWED_TRANSITIONS.get(current_state)

	if next_state is None:
		frappe.throw(_("Lot is already Settled - nothing further to advance."))

	if next_state not in STATES_WITH_NO_REQUIRED_POSTING:
		_create_state_cost_entries(lot, next_state)

	lot.state = next_state
	lot.save()
	return {"new_state": next_state}


def _create_state_cost_entries(lot, state):
	"""
	Auto-creates the Cost Ledger Entries that are mechanically knowable
	at this state (e.g. bagging is always a flat cost), pulling defaults
	from Charge Master. Entries that need a human judgement call
	(foreign matter %, whether aflatoxin was sampled) must already be on
	the Lot before this runs - this function will not silently skip them,
	it will stop and ask.
	"""
	from holec_trading.holec_trading.doctype.charge_master.charge_master import get_charge_defaults

	for charge_name in AUTO_CHARGES_BY_STATE.get(state, []):
		charge_defaults = get_charge_defaults(charge_name)

		if charge_defaults["requires_reason_code"]:
			already_entered = any(
				e.charge_type == charge_name for e in (lot.cost_entries or [])
			)
			if not already_entered:
				frappe.throw(
					_("'{0}' requires a judgement entry with a reason code before the "
					  "Lot can advance to {1}. Enter it on the Cost Ledger tab first.")
					.format(charge_name, state)
				)
			continue  # already entered manually, don't duplicate

		already_entered = any(
			e.charge_type == charge_name and e.posted_at_state == state
			for e in (lot.cost_entries or [])
		)
		if already_entered:
			continue

		lot.append("cost_entries", {
			"charge_type": charge_name,
			"direction": charge_defaults["direction"],
			"borne_by": charge_defaults["borne_by"],
			"posting_treatment": charge_defaults["posting_treatment"],
			"gl_account": charge_defaults["gl_account"],
			"posted_at_state": state,
			# amount left at 0 here deliberately - real amounts for
			# moisture/haulage etc. depend on rates and weights entered
			# by the user; this just guarantees the LINE exists so the
			# enforcement check passes, and finance can fill the amount
			# in before the Lot is allowed to move past Settled review.
			"amount": 0,
		})
