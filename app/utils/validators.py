"""Validações simples reutilizadas pelas rotas públicas e administrativas."""

import re
from datetime import datetime

NAME_RE = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ\s'.-]{2,120}$")
# Aceita telefone (com ou sem formatação) ou e-mail simples
CONTACT_PHONE_RE = re.compile(r"^\+?[\d\s()\-]{8,20}$")
CONTACT_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_client_name(name):
    if not name or not name.strip():
        return "Informe o nome do cliente."
    if not NAME_RE.match(name.strip()):
        return "Nome inválido. Use apenas letras e espaços."
    return None


def validate_contact(contact):
    if not contact or not contact.strip():
        return "Informe um telefone ou e-mail para contato."
    contact = contact.strip()
    if not (CONTACT_PHONE_RE.match(contact) or CONTACT_EMAIL_RE.match(contact)):
        return "Informe um telefone ou e-mail válido."
    return None


def parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def parse_time(value):
    try:
        return datetime.strptime(value, "%H:%M").time()
    except (ValueError, TypeError):
        return None


def validate_service_form(name, duration, price):
    errors = {}
    if not name or not name.strip():
        errors["name"] = "Informe o nome do serviço."
    try:
        duration_int = int(duration)
        if duration_int <= 0 or duration_int > 600:
            errors["duration_minutes"] = "Duração deve ser entre 1 e 600 minutos."
    except (ValueError, TypeError):
        errors["duration_minutes"] = "Duração inválida."
    try:
        price_val = float(str(price).replace(",", "."))
        if price_val < 0:
            errors["price"] = "Preço não pode ser negativo."
    except (ValueError, TypeError):
        errors["price"] = "Preço inválido."
    return errors
