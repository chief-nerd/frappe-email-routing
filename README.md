# Frappe Opportunity Email Routing

Custom email routing and automatic document linking for Mimirio's internal CRM workflows.

## Features

- **Automatic Linking:** Incoming emails are automatically linked to the correct Opportunity based on the primary contact's email address.
- **Intelligent Filtering:** Only processes incoming emails that haven't been manually linked yet.
- **Prioritization:** Automatically links to the most recently active deal if multiple matching Opportunities exist.

## Logic

The app intercepts `Communication` documents right before they are saved. It extracts all email addresses from:
- Sender
- Recipients (To)
- CC fields

It then queries for an `Opportunity` where:
- `contact_email` matches any of the extracted emails.
- `status` is not Closed or Converted.
- Sorted by the most recently modified.

## License

MIT
