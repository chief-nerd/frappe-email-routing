import frappe
from frappe.utils import get_email_address, split_emails

def route_email(doc, method=None):
    """
    Interrupt incoming Communication documents right before they are saved to the database.
    Only process if it's an incoming email and not already linked (or we want to add more links).
    """
    if doc.communication_medium != "Email" or doc.sent_or_received != "Received":
        return

    # Extract all email addresses from sender, recipients, and cc
    emails_to_check = set()
    
    if doc.sender:
        email = get_email_address(doc.sender).strip().lower()
        if email:
            emails_to_check.add(email)
            
    if doc.recipients:
        for email in split_emails(doc.recipients):
            email = get_email_address(email).strip().lower()
            if email:
                emails_to_check.add(email)
            
    if doc.cc:
        for email in split_emails(doc.cc):
            email = get_email_address(email).strip().lower()
            if email:
                emails_to_check.add(email)

    if not emails_to_check:
        return

    matches = find_matches(emails_to_check)
    if not matches:
        return

    # 1. Primary Reference: If doc.reference_doctype is empty, pick the best match
    if not doc.reference_doctype or not doc.reference_name:
        # Prioritize: Opportunity > Issue > Project > Lead > Customer > Supplier > Contact > User
        priority = ["Opportunity", "Issue", "Project", "Lead", "Customer", "Supplier", "Contact", "User"]
        best_match = None
        
        # Sort matches by priority
        for dt_priority in priority:
            for dt, dn in matches:
                if dt == dt_priority:
                    # For some types, we might want to prioritize open ones
                    # But for now, just take the first one found (find_matches can handle order)
                    best_match = (dt, dn)
                    break
            if best_match:
                break
        
        if not best_match:
            best_match = matches[0]
            
        doc.reference_doctype = best_match[0]
        doc.reference_name = best_match[1]

    # 2. Additional Links: Add all matches to timeline_links if it exists
    if frappe.get_meta("Communication").has_field("timeline_links"):
        existing_links = set()
        if doc.get("timeline_links"):
            existing_links = {(l.link_doctype, l.link_name) for l in doc.timeline_links}
        
        # Also include the primary reference in existing links to avoid duplication
        if doc.reference_doctype and doc.reference_name:
            existing_links.add((doc.reference_doctype, doc.reference_name))

        for dt, dn in matches:
            if (dt, dn) not in existing_links:
                doc.append("timeline_links", {
                    "link_doctype": dt,
                    "link_name": dn
                })
                existing_links.add((dt, dn))

def find_matches(emails):
    """
    Find all documents that match the given email addresses across various DocTypes.
    """
    email_list = list(emails)
    matches = []
    
    # Mapping of DocType to potential email fields
    # We use a list for order of checking if needed, but mostly for field discovery
    doctype_email_fields = {
        "Opportunity": ["contact_email", "email_id"],
        "Lead": ["email_id"],
        "Contact": ["email_id"],
        "Issue": ["raised_by", "email_id"],
        "Project": ["contact_email", "email_id", "custom_email"],
        "Customer": ["email_id", "custom_email"],
        "Supplier": ["email_id", "custom_email"],
        "User": ["email"],
    }

    for doctype, fields in doctype_email_fields.items():
        if not frappe.db.exists("DocType", doctype):
            continue
        
        meta = frappe.get_meta(doctype)
        found_in_doctype = False
        for field in fields:
            if meta.has_field(field):
                filters = {field: ["in", email_list]}
                
                # For some DocTypes, we prefer active ones if we were to pick just one,
                # but since we link to ALL, we just get them all.
                # However, we'll sort by modified desc to have recent ones first.
                
                results = frappe.get_all(doctype, filters=filters, fields=["name"], order_by="modified desc")
                for r in results:
                    matches.append((doctype, r.name))
                    found_in_doctype = True
        
        # Special case for Contact: also check the email_ids child table if it exists
        if doctype == "Contact" and meta.has_field("email_ids"):
             contact_emails = frappe.get_all("Contact Email", filters={"email_id": ["in", email_list]}, fields=["parent"])
             for ce in contact_emails:
                 matches.append(("Contact", ce.parent))

    # Special handling for Contact -> Dynamic Links (Customer, Supplier, etc.)
    # This helps find Customer/Supplier even if they don't have the email directly on the record
    contact_names = [m[1] for m in matches if m[0] == "Contact"]
    if contact_names:
        links = frappe.get_all("Dynamic Link", filters={
            "parent": ["in", contact_names],
            "parenttype": "Contact",
            "link_doctype": ["not in", ["Contact"]]
        }, fields=["link_doctype", "link_name"])
        for link in links:
            matches.append((link.link_doctype, link.link_name))

    # Deduplicate matches while preserving some sense of order
    unique_matches = []
    seen = set()
    for dt, dn in matches:
        if (dt, dn) not in seen:
            unique_matches.append((dt, dn))
            seen.add((dt, dn))
    
    return unique_matches
