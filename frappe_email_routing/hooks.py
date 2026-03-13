from . import __version__ as app_version

app_name = "frappe_email_routing"
app_title = "Frappe Email Routing"
app_publisher = "Mimirio"
app_description = "Custom email routing and automatic document linking for Mimirio's internal CRM workflows."
app_email = "hello@mimirio.com"
app_license = "mit"

doc_events = {
    "Communication": {"before_insert": "frappe_email_routing.email_routing.route_email"}
}
