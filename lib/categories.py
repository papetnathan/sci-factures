CATEGORIES = [
    {"value": "travaux", "label": "Travaux / Rénovation", "color": "#E8A838"},
    {"value": "charges", "label": "Charges courantes", "color": "#6B8F71"},
    {"value": "honoraires", "label": "Honoraires / Comptabilité", "color": "#7B6FA0"},
    {"value": "assurances", "label": "Assurances", "color": "#4A90B8"},
    {"value": "fournitures", "label": "Fournitures", "color": "#C0625A"},
    {"value": "entretien", "label": "Entretien / Maintenance", "color": "#D4843E"},
    {"value": "notaire", "label": "Frais de notaire", "color": "#5A7A8A"},
    {"value": "autre", "label": "Autre", "color": "#8B8FA0"},
]

def get_category(value: str) -> dict:
    return next((c for c in CATEGORIES if c["value"] == value), CATEGORIES[-1])