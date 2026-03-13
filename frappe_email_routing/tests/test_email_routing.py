import frappe
from frappe.tests.utils import FrappeTestCase
from frappe_email_routing.email_routing import route_email

class TestEmailRouting(FrappeTestCase):
	def test_route_email_to_lead(self):
		"""Test that an incoming email is correctly linked to a matching Lead."""
		email = "test_routing@example.com"
		lead = frappe.get_doc({
			"doctype": "Lead",
			"first_name": "Test",
			"last_name": "Routing",
			"email_id": email
		}).insert()

		comm = frappe.get_doc({
			"doctype": "Communication",
			"communication_medium": "Email",
			"sent_or_received": "Received",
			"sender": f"Tester <{email}>",
			"subject": "Minimal Test"
		})

		route_email(comm)

		self.assertEqual(comm.reference_doctype, "Lead")
		self.assertEqual(comm.reference_name, lead.name)
		
		# Cleanup
		lead.delete()
