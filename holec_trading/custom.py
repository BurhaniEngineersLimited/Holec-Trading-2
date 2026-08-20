import frappe

def make_page():
    if not frappe.db.exists("Page", "holec-trading"):
        doc = frappe.new_doc("Page")
        doc.page_name = "holec-trading"
        doc.title = "Holec Trading"
        doc.module = "Holec Trading"
        doc.standard = "Yes"
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print("Page created successfully!")