# Copyright (c) 2026, Holec
#
# Buy Ticket: captures a trade before goods exist. The estimated margin
# calculation here is what turns the rate-card tolerance band from a
# compliance check into a decision tool, shown before the price is agreed.

import frappe
from frappe.model.document import Document


class BuyTicket(Document):
	pass


def calculate_estimated_margin(doc, method=None):
	"""
	estimated_margin_pct = (negotiated_price - reference_rate) / reference_rate
	Run on every save via hooks.py doc_events, so the number on screen is
	never stale relative to what's typed in.
	"""
	if not doc.reference_rate:
		doc.estimated_margin_pct = 0
		return

	doc.estimated_margin_pct = (
		(doc.negotiated_price - doc.reference_rate) / doc.reference_rate
	) * 100


@frappe.whitelist()
def convert_to_lot(ticket_name: str, split_into: int = 1):
	"""
	Converts a Buy Ticket into one or more Lots at intake.
	split_into > 1 covers the case where one supplier delivery is
	divided into multiple Lots at the weighbridge (e.g. going to
	different storage stacks or different eventual customers).
	Each created Lot points back to the same buy_ticket and starts
	at state = Intake.
	"""
	ticket = frappe.get_doc("Buy Ticket", ticket_name)
	if ticket.status == "Converted":
		frappe.throw("This ticket has already been converted.")

	split_into = int(split_into)
	qty_per_lot = ticket.quantity_kg / split_into

	created_lots = []
	for _i in range(split_into):
		lot = frappe.get_doc({
			"doctype": "Lot",
			"buy_ticket": ticket.name,
			"supplier": ticket.supplier,
			"state": "Intake",
			"gross_weight_kg": qty_per_lot,
		})
		lot.insert()
		created_lots.append(lot.name)

	ticket.status = "Converted"
	ticket.save()

	return created_lots
