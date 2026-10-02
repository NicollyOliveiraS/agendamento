from datetime import date, datetime, timedelta

from flask import Blueprint, jsonify, redirect, render_template, request, url_for, flash

from app.extensions import db
from app.models import (
    Appointment,
    Service,
    Settings,
    STATUS_CANCELADO,
    STATUS_CONFIRMADO,
    STATUS_PENDENTE,
)
from app.utils.scheduling import can_cancel, compute_end_time, get_available_slots, is_slot_available
from app.utils.validators import parse_date, parse_time, validate_client_name, validate_contact

public_bp = Blueprint("public", __name__)


# ---------------------------------------------------------------------------
# Página inicial: lista de serviços
# ---------------------------------------------------------------------------


@public_bp.route("/")
def index():
    services = Service.query.filter_by(active=True).order_by(Service.name).all()
    return render_template("public/index.html", services=services)


# ---------------------------------------------------------------------------
# Página de agendamento: escolher data, horário e informar dados
# ---------------------------------------------------------------------------


@public_bp.route("/agendar/<int:service_id>", methods=["GET", "POST"])
def booking(service_id):
    service = Service.query.filter_by(id=service_id, active=True).first_or_404()
    settings = Settings.get()
    today = date.today()
    max_date = today + timedelta(days=60)

    if request.method == "POST":
        errors = {}

        client_name = request.form.get("client_name", "").strip()
        client_contact = request.form.get("client_contact", "").strip()
        notes = request.form.get("notes", "").strip()
        date_str = request.form.get("date", "")
        time_str = request.form.get("time", "")

        name_error = validate_client_name(client_name)
        if name_error:
            errors["client_name"] = name_error

        contact_error = validate_contact(client_contact)
        if contact_error:
            errors["client_contact"] = contact_error

        target_date = parse_date(date_str)
        if not target_date:
            errors["date"] = "Selecione uma data válida."
        elif target_date < today or target_date > max_date:
            errors["date"] = "Escolha uma data dentro do período disponível."

        start_time = parse_time(time_str)
        if not start_time:
            errors["time"] = "Selecione um horário válido."

        # Revalida a disponibilidade no backend (nunca confia só no frontend)
        if not errors and not is_slot_available(service, target_date, start_time):
            errors["time"] = "Esse horário acabou de ficar indisponível. Escolha outro."

        if errors:
            for msg in errors.values():
                flash(msg, "error")
            slots = get_available_slots(service, target_date) if target_date else []
            return render_template(
                "public/booking.html",
                service=service,
                today=today.isoformat(),
                max_date=max_date.isoformat(),
                selected_date=date_str,
                slots=slots,
                form_data=request.form,
                errors=errors,
            )

        end_time = compute_end_time(target_date, start_time, service)
        appointment = Appointment(
            code=Appointment.generate_code(),
            service_id=service.id,
            client_name=client_name,
            client_contact=client_contact,
            notes=notes,
            date=target_date,
            start_time=start_time,
            end_time=end_time,
            status=STATUS_PENDENTE,
        )
        db.session.add(appointment)
        db.session.commit()

        return redirect(url_for("public.confirmation", code=appointment.code))

    return render_template(
        "public/booking.html",
        service=service,
        today=today.isoformat(),
        max_date=max_date.isoformat(),
        selected_date=None,
        slots=[],
        form_data={},
        errors={},
    )


# ---------------------------------------------------------------------------
# API (AJAX) de disponibilidade de horários
# ---------------------------------------------------------------------------


@public_bp.route("/api/disponibilidade")
def api_availability():
    service_id = request.args.get("service_id", type=int)
    date_str = request.args.get("date", "")

    service = Service.query.filter_by(id=service_id, active=True).first()
    target_date = parse_date(date_str)

    if not service or not target_date:
        return jsonify({"error": "Parâmetros inválidos.", "slots": []}), 400

    if target_date < date.today():
        return jsonify({"error": "Data no passado.", "slots": []}), 400

    slots = get_available_slots(service, target_date)
    return jsonify({"slots": [t.strftime("%H:%M") for t in slots]})


# ---------------------------------------------------------------------------
# Confirmação do agendamento
# ---------------------------------------------------------------------------


@public_bp.route("/confirmacao/<code>")
def confirmation(code):
    appointment = Appointment.query.filter_by(code=code).first_or_404()
    return render_template("public/confirmation.html", appointment=appointment)


# ---------------------------------------------------------------------------
# Consultar / cancelar agendamento pelo código
# ---------------------------------------------------------------------------


@public_bp.route("/meus-agendamentos", methods=["GET", "POST"])
def manage():
    appointment = None
    searched = False

    code = None
    if request.method == "POST":
        code = request.form.get("code", "").strip().upper()
    elif request.args.get("code"):
        code = request.args.get("code", "").strip().upper()

    if request.method == "POST" and not code:
        flash("Informe o código do agendamento.", "error")
        searched = True
    elif code:
        searched = True
        appointment = Appointment.query.filter_by(code=code).first()
        if not appointment:
            flash("Não encontramos nenhum agendamento com esse código.", "error")

    return render_template(
        "public/manage.html",
        appointment=appointment,
        searched=searched,
        can_cancel_fn=can_cancel,
    )


@public_bp.route("/cancelar/<code>", methods=["POST"])
def cancel(code):
    appointment = Appointment.query.filter_by(code=code).first_or_404()

    if appointment.status == STATUS_CANCELADO:
        flash("Esse agendamento já está cancelado.", "error")
    elif not can_cancel(appointment):
        settings = Settings.get()
        flash(
            f"Não é mais possível cancelar. O prazo mínimo é de {settings.cancellation_hours}h antes do horário.",
            "error",
        )
    else:
        appointment.status = STATUS_CANCELADO
        appointment.cancelled_at = datetime.utcnow()
        appointment.cancelled_by = "cliente"
        db.session.commit()
        flash("Agendamento cancelado com sucesso.", "success")

    return redirect(url_for("public.manage") + f"?code={code}")
