from collections import Counter
from datetime import date, datetime, time, timedelta

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.models import (
    AdminUser,
    Appointment,
    Block,
    Service,
    Settings,
    WorkingHours,
    STATUS_CANCELADO,
    STATUS_CONCLUIDO,
    STATUS_CONFIRMADO,
    STATUS_PENDENTE,
    STATUS_LABELS,
)
from app.utils.validators import parse_date, parse_time, validate_service_form

admin_bp = Blueprint("admin", __name__)


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = AdminUser.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash(f"Bem-vindo(a), {user.nome_completo}!", "success")
            next_url = request.args.get("next")
            return redirect(next_url or url_for("admin.dashboard"))

        flash("Usuário ou senha inválidos.", "error")

    return render_template("admin/login.html")


@admin_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sessão encerrada.", "success")
    return redirect(url_for("admin.login"))


# ---------------------------------------------------------------------------
# Dashboard: visão diária/semanal + indicadores
# ---------------------------------------------------------------------------


@admin_bp.route("/")
@login_required
def dashboard():
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    today_appointments = (
        Appointment.query.filter(Appointment.date == today)
        .order_by(Appointment.start_time)
        .all()
    )

    week_appointments = (
        Appointment.query.filter(
            Appointment.date >= start_of_week, Appointment.date <= end_of_week
        )
        .order_by(Appointment.date, Appointment.start_time)
        .all()
    )

    # Agrupa a semana por dia para exibir em colunas
    week_days = []
    for i in range(7):
        day = start_of_week + timedelta(days=i)
        day_appts = [a for a in week_appointments if a.date == day]
        week_days.append({"date": day, "appointments": day_appts})

    # Indicadores
    active_week = [a for a in week_appointments if a.status != STATUS_CANCELADO]
    cancelled_week = [a for a in week_appointments if a.status == STATUS_CANCELADO]

    service_counter = Counter(a.service.name for a in active_week)
    top_services = service_counter.most_common(5)

    return render_template(
        "admin/dashboard.html",
        today=today,
        today_appointments=today_appointments,
        week_days=week_days,
        start_of_week=start_of_week,
        end_of_week=end_of_week,
        kpi_week_total=len(active_week),
        kpi_cancelled=len(cancelled_week),
        top_services=top_services,
    )


# ---------------------------------------------------------------------------
# Agendamentos: busca, confirmação, cancelamento, conclusão
# ---------------------------------------------------------------------------


@admin_bp.route("/agendamentos")
@login_required
def appointments():
    query = Appointment.query

    name = request.args.get("name", "").strip()
    date_str = request.args.get("date", "").strip()
    status = request.args.get("status", "").strip()

    if name:
        query = query.filter(Appointment.client_name.ilike(f"%{name}%"))
    if date_str:
        parsed = parse_date(date_str)
        if parsed:
            query = query.filter(Appointment.date == parsed)
    if status:
        query = query.filter(Appointment.status == status)

    results = query.order_by(Appointment.date.desc(), Appointment.start_time.desc()).all()

    return render_template(
        "admin/appointments.html",
        appointments=results,
        filters={"name": name, "date": date_str, "status": status},
        status_labels=STATUS_LABELS,
    )


@admin_bp.route("/agendamentos/<int:appointment_id>/status", methods=["POST"])
@login_required
def update_appointment_status(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    new_status = request.form.get("status")

    valid_transitions = {STATUS_CONFIRMADO, STATUS_CANCELADO, STATUS_CONCLUIDO}
    if new_status not in valid_transitions:
        flash("Ação inválida.", "error")
        return redirect(request.referrer or url_for("admin.appointments"))

    appointment.status = new_status
    if new_status == STATUS_CANCELADO:
        appointment.cancelled_at = datetime.utcnow()
        appointment.cancelled_by = "negocio"

    db.session.commit()
    flash("Agendamento atualizado com sucesso.", "success")
    return redirect(request.referrer or url_for("admin.appointments"))


# ---------------------------------------------------------------------------
# Serviços: cadastro, edição e desativação
# ---------------------------------------------------------------------------


@admin_bp.route("/servicos", methods=["GET", "POST"])
@login_required
def services():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        duration = request.form.get("duration_minutes", "")
        price = request.form.get("price", "")

        errors = validate_service_form(name, duration, price)
        if errors:
            for msg in errors.values():
                flash(msg, "error")
        else:
            service = Service(
                name=name,
                description=description,
                duration_minutes=int(duration),
                price=float(str(price).replace(",", ".")),
                active=True,
            )
            db.session.add(service)
            db.session.commit()
            flash("Serviço cadastrado com sucesso.", "success")
            return redirect(url_for("admin.services"))

    all_services = Service.query.order_by(Service.active.desc(), Service.name).all()
    return render_template("admin/services.html", services=all_services)


@admin_bp.route("/servicos/<int:service_id>/editar", methods=["POST"])
@login_required
def edit_service(service_id):
    service = Service.query.get_or_404(service_id)

    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    duration = request.form.get("duration_minutes", "")
    price = request.form.get("price", "")

    errors = validate_service_form(name, duration, price)
    if errors:
        for msg in errors.values():
            flash(msg, "error")
    else:
        service.name = name
        service.description = description
        service.duration_minutes = int(duration)
        service.price = float(str(price).replace(",", "."))
        db.session.commit()
        flash("Serviço atualizado com sucesso.", "success")

    return redirect(url_for("admin.services"))


@admin_bp.route("/servicos/<int:service_id>/alternar", methods=["POST"])
@login_required
def toggle_service(service_id):
    service = Service.query.get_or_404(service_id)
    service.active = not service.active
    db.session.commit()
    estado = "ativado" if service.active else "desativado"
    flash(f"Serviço {estado} com sucesso.", "success")
    return redirect(url_for("admin.services"))


# ---------------------------------------------------------------------------
# Horários de funcionamento e políticas gerais
# ---------------------------------------------------------------------------


@admin_bp.route("/horarios", methods=["GET", "POST"])
@login_required
def schedule_settings():
    working_hours = WorkingHours.query.order_by(WorkingHours.weekday).all()
    settings = Settings.get()

    if request.method == "POST":
        form_type = request.form.get("form_type")

        if form_type == "policies":
            settings.business_name = request.form.get("business_name", settings.business_name).strip()
            settings.business_type = request.form.get("business_type", settings.business_type).strip()
            settings.phone = request.form.get("phone", settings.phone).strip()
            settings.address = request.form.get("address", settings.address).strip()
            try:
                settings.slot_interval_minutes = int(request.form.get("slot_interval_minutes", 15))
                settings.buffer_minutes = int(request.form.get("buffer_minutes", 10))
                settings.cancellation_hours = int(request.form.get("cancellation_hours", 2))
                db.session.commit()
                flash("Configurações gerais atualizadas.", "success")
            except ValueError:
                flash("Valores numéricos inválidos.", "error")

        elif form_type == "working_hours":
            for wh in working_hours:
                prefix = f"day_{wh.weekday}"
                is_open = request.form.get(f"{prefix}_is_open") == "on"
                wh.is_open = is_open
                if is_open:
                    open_t = parse_time(request.form.get(f"{prefix}_open"))
                    close_t = parse_time(request.form.get(f"{prefix}_close"))
                    break_start = parse_time(request.form.get(f"{prefix}_break_start"))
                    break_end = parse_time(request.form.get(f"{prefix}_break_end"))

                    if not open_t or not close_t or open_t >= close_t:
                        flash(
                            f"Horário inválido para {wh.weekday_name}. Verifique abertura e fechamento.",
                            "error",
                        )
                        continue

                    wh.open_time = open_t
                    wh.close_time = close_t
                    wh.break_start = break_start
                    wh.break_end = break_end
                else:
                    wh.open_time = None
                    wh.close_time = None
                    wh.break_start = None
                    wh.break_end = None
            db.session.commit()
            flash("Horário de funcionamento atualizado.", "success")

        return redirect(url_for("admin.schedule_settings"))

    return render_template(
        "admin/schedule_settings.html", working_hours=working_hours, settings=settings
    )


# ---------------------------------------------------------------------------
# Bloqueios manuais de horários/datas
# ---------------------------------------------------------------------------


@admin_bp.route("/bloqueios", methods=["GET", "POST"])
@login_required
def blocks():
    if request.method == "POST":
        date_str = request.form.get("date", "")
        full_day = request.form.get("full_day") == "on"
        start_str = request.form.get("start_time", "")
        end_str = request.form.get("end_time", "")
        reason = request.form.get("reason", "").strip()

        target_date = parse_date(date_str)
        if not target_date:
            flash("Selecione uma data válida.", "error")
        else:
            start_time = None
            end_time = None
            if not full_day:
                start_time = parse_time(start_str)
                end_time = parse_time(end_str)
                if not start_time or not end_time or start_time >= end_time:
                    flash("Horário de bloqueio inválido.", "error")
                    return redirect(url_for("admin.blocks"))

            block = Block(
                date=target_date, start_time=start_time, end_time=end_time, reason=reason
            )
            db.session.add(block)
            db.session.commit()
            flash("Bloqueio criado com sucesso.", "success")

        return redirect(url_for("admin.blocks"))

    all_blocks = Block.query.filter(Block.date >= date.today()).order_by(Block.date).all()
    return render_template("admin/blocks.html", blocks=all_blocks, today=date.today())


@admin_bp.route("/bloqueios/<int:block_id>/excluir", methods=["POST"])
@login_required
def delete_block(block_id):
    block = Block.query.get_or_404(block_id)
    db.session.delete(block)
    db.session.commit()
    flash("Bloqueio removido.", "success")
    return redirect(url_for("admin.blocks"))
