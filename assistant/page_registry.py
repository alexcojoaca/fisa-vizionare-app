# Page-aware help: map Flask endpoint -> page_id for "Ghid pagina".
# Used by context processor and /assistant/context.

ENDPOINT_TO_PAGE_ID = {
    "home": "home",
    "about": "about",  # /despre
    "menu.menu_home": "menu",
    "marketplace.hub": "marketplace_hub",
    "marketplace.list_requests": "marketplace_list",
    "marketplace.list_offers": "marketplace_offers_list",
    "marketplace.detail": "marketplace_detail",
    "marketplace.detail_offer": "marketplace_offer_detail",
    "marketplace.new_request": "marketplace_form_new",
    "marketplace.edit_request": "marketplace_form_edit",
    "marketplace.new_offer": "marketplace_form_new_offer",
    "marketplace.edit_offer": "marketplace_form_edit_offer",
    "marketplace.profile_page": "marketplace_profile",
    "marketplace.my_offers_page": "marketplace_my_offers",
    "marketplace.my_requests_page": "marketplace_my_requests",
    "chirie.form_page": "fisa_chirie",
    "chirie.done_page": "chirie_done",
    "chirie.remote_agent_page": "remote_chirie",
    "chirie.remote_public_page": "remote_chirie",
    "chirie.remote_list": "remote_list",
    "vanzare.form_page": "fisa_vanzare",
    "vanzare.done_page": "vanzare_done",
    "vanzare.remote_agent_page": "remote_vanzare",
    "vanzare.remote_public_page": "remote_vanzare",
    "contract.form_page": "contract_inchiriere",
    "contract.done_page": "contract_done",
    "prestari.form_page": "prestari_servicii",
    "prestari.done_page": "prestari_done",
    "todo.list_tasks": "todo",
    "todo.new_task": "todo_form",
    "todo.edit_task": "todo_form",
    "payments": "payments",
    "menu.agent_profile": "account_profile",
    "menu.agency_profile": "agency_profile",
    "account.email": "account_profile",
    "account.password": "account_profile",
    "agent_profile": "account_profile",
    "agency_profile": "agency_profile",
    "agent_signature": "account_profile",
    "login": "home",
    "auth.login": "home",
    "register": "home",
    "auth.register": "home",
    "terms": "terms",
    "privacy": "privacy",
    "team.index": "team",
    "team.dashboard": "team_dashboard",
    "team.agents_list": "team_agents",
    "team.agent_detail": "team_agent_detail",
    "team.tasks_list": "team_tasks",
    "team.task_new": "team_task_new",
    "team.task_detail": "team_task_detail",
    "team.add_agent": "team_add_agent",
    "team.agent_dashboard": "team_agent_dashboard",
    "team.create_team": "team_create",
    "team.invitation": "team_invitation",
}


def get_page_id(request):
    """Return page_id for current request. Fallback: generic."""
    if not request:
        return "generic"
    endpoint = getattr(request, "endpoint", None) or ""
    return ENDPOINT_TO_PAGE_ID.get(endpoint, "generic")
