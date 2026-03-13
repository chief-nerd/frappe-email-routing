import frappe
from frappe.utils import get_email_address, split_emails

logger = frappe.logger("email_routing")

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
        
        # Sort matches by priority AND status (Open records first)
        for dt_priority in priority:
            # First pass: Look for OPEN records of this priority
            for m in matches:
                if m["doctype"] == dt_priority and is_open_status(m["doctype"], m.get("status")):
                    best_match = (m["doctype"], m["name"])
                    break
            if best_match:
                break
                
            # Second pass: Take the first match of this priority (most recent) if no open one found
            for m in matches:
                if m["doctype"] == dt_priority:
                    best_match = (m["doctype"], m["name"])
                    break
            if best_match:
                break
        
        if not best_match and matches:
            best_match = (matches[0]["doctype"], matches[0]["name"])
            
        if best_match:
            doc.reference_doctype = best_match[0]
            doc.reference_name = best_match[1]
            logger.debug(f"Assigned primary reference {doc.reference_doctype} {doc.reference_name} to Communication {doc.name or 'new'}")

    # 2. Additional Links: Add all matches to timeline_links if it exists
    if frappe.get_meta("Communication").has_field("timeline_links"):
        existing_links = set()
        if doc.get("timeline_links"):
            for l in doc.timeline_links:
                # Use .get for safety in case l is a dict
                dt = l.get("link_doctype")
                dn = l.get("link_name")
                if dt and dn:
                    existing_links.add((dt, dn))
        
        # Also include the primary reference in existing links to avoid duplication
        if doc.reference_doctype and doc.reference_name:
            existing_links.add((doc.reference_doctype, doc.reference_name))

        for m in matches:
            dt, dn = m["doctype"], m["name"]
            if (dt, dn) not in existing_links:
                doc.append("timeline_links", {
                    "link_doctype": dt,
                    "link_name": dn
                })
                existing_links.add((dt, dn))
                logger.debug(f"Added timeline link {dt} {dn} to Communication {doc.name or 'new'}")

def find_matches(emails):
    """
    Find all documents that match the given email addresses across various DocTypes.
    """
    email_list = list(emails)
    matches = []
    
    # Mapping of DocType to potential email fields
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
        has_status = meta.has_field("status")
        
        for field in fields:
            if meta.has_field(field):
                filters = {field: ["in", email_list]}
                
                fields_to_get = ["name"]
                if has_status:
                    fields_to_get.append("status")
                
                results = frappe.get_all(doctype, filters=filters, fields=fields_to_get, order_by="modified desc")
                for r in results:
                    matches.append({
                        "doctype": doctype, 
                        "name": r.name,
                        "status": r.get("status")
                    })
        
        # Special case for Contact: also check the email_ids child table
        if doctype == "Contact" and meta.has_field("email_ids"):
             contact_emails = frappe.get_all("Contact Email", filters={"email_id": ["in", email_list]}, fields=["parent"])
             for ce in contact_emails:
                 matches.append({
                     "doctype": "Contact", 
                     "name": ce.parent,
                     "status": None # We'll check status if needed, but Contact doesn't have open/closed in the same way
                 })

    # Special handling for Contact -> Dynamic Links (Customer, Supplier, etc.)
    contact_names = [m["name"] for m in matches if m["doctype"] == "Contact"]
    if contact_names:
        links = frappe.get_all("Dynamic Link", filters={
            "parent": ["in", contact_names],
            "parenttype": "Contact",
            "link_doctype": ["not in", ["Contact"]]
        }, fields=["link_doctype", "link_name"])
        for link in links:
            # We don't have status here easily without another query, 
            # but usually these are already found if they have the email directly.
            matches.append({
                "doctype": link.link_doctype, 
                "name": link.link_name,
                "status": None
            })

    # Deduplicate matches while preserving order
    unique_matches = []
    seen = set()
    for m in matches:
        key = (m["doctype"], m["name"])
        if key not in seen:
            unique_matches.append(m)
            seen.add(key)
    
    return unique_matches

def is_open_status(doctype, status):
    """
    Determine if a document status is considered 'Open' for prioritization.
    """
    if not status:
        return False
        
    closed_statuses = {
        "Opportunity": ["Converted", "Lost", "Closed"],
        "Issue": ["Closed", "Resolved"],
        "Lead": ["Converted", "Do Not Contact"],
        "Project": ["Completed", "Cancelled"],
    }
    
    if doctype in closed_statuses:
        return status not in closed_statuses[doctype]
    
    # For others, if status is not 'Closed', consider it open
    return status not in ["Closed", "Cancelled", "Completed", "Disabled"]
