# Frappe Email Routing

Custom email routing and automatic document linking for Mimirio's internal CRM workflows.

## Features

- **Automatic Linking:** Incoming emails are automatically linked to relevant records (Opportunities, Leads, Contacts, Projects, etc.) based on email addresses found in the Sender, Recipients, or CC fields.
- **Multi-Record Linking:** Automatically adds "Timeline Links" so the email appears in the history of all matching records.
- **Intelligent Prioritization:** Automatically sets the primary reference to the most relevant record (e.g., an open Opportunity or Project) if multiple matches are found.
- **Broad Search:** Searches across:
  - Opportunities (by contact email)
  - Leads (by email)
  - Contacts (by primary email and additional email IDs)
  - Issues (by reporter email)
  - Projects (by contact email)
  - Customers/Suppliers (by email or via linked Contacts)
  - Users (by email)

## Logic

The app intercepts `Communication` documents right before they are saved (`before_insert`). It extracts all email addresses from:
- Sender
- Recipients (To)
- CC fields

It then identifies all matching documents across the supported DocTypes. 
1. If the communication doesn't have a primary reference, one is assigned based on a priority list (Opportunity > Issue > Project > Lead > Customer > Supplier > Contact > User).
2. All identified matches are added as "Timeline Links" to the communication, ensuring the email is visible in the activity stream of every related record.

## License

MIT
