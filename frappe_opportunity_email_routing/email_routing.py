import frappe
from frappe.utils import get_email_address, split_emails

def route_email(doc, method=None):
    """
    Interupt incoming Communication documents right before they are saved to the database.
    Only process if it's an incoming email and reference is empty.
    """
    if doc.communication_medium != "Email" or doc.sent_or_received != "Received":
        return

    # Only process if reference_doctype and reference_name are currently empty
    if doc.reference_doctype or doc.reference_name:
        return

    # Extract all email addresses from sender, recipients, and cc
    emails_to_check = set()
    
    # Sender
    if doc.sender:
        emails_to_check.add(get_email_address(doc.sender).strip().lower())
        
    # Recipients
    if doc.recipients:
        for email in split_emails(doc.recipients):
            emails_to_check.add(get_email_address(email).strip().lower())
            
    # CC
    if doc.cc:
        for email in split_emails(doc.cc):
            emails_to_check.add(get_email_address(email).strip().lower())

    # Remove any empty or None values
    emails_to_check = {e for e in emails_to_check if e}
    
    if not emails_to_check:
        return

    # Query Opportunity for an Open deal matching the extracted emails.
    # The contact_email field on the Opportunity must match one of the extracted emails.
    # The Opportunity status must not be closed.
    
    # Status criteria: Status must not be closed.
    # Closed statuses in Opportunity: "Closed", "Converted", "Quotation Sent" (sometimes considered active, but usually Open/Replied are active)
    # Frappe's default Opportunity statuses are often: "Open", "Replied", "Converted", "Closed".
    # We should exclude "Closed" and "Converted".
    
    opportunities = frappe.get_all(
        "Opportunity",
        filters={
            "contact_email": ["in", list(emails_to_check)],
            "status": ["not in", ["Closed", "Converted"]]
        },
        fields=["name", "modified"],
        order_by="modified desc",
        limit=1
    )

    if opportunities:
        match = opportunities[0]
        doc.reference_doctype = "Opportunity"
        doc.reference_name = match.name
        # Note: We don't call doc.save() here as this is called in before_insert hook
