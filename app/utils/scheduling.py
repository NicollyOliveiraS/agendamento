"""
Motor de disponibilidade de horários.

Responsável por calcular quais horários de um determinado dia estão livres
para um determinado serviço, levando em conta:
  - se o negócio está aberto naquele dia da semana;
  - o horário de funcionamento e o intervalo (pausa) do dia;
  - a duração do serviço escolhido;
  - o intervalo mínimo (buffer) exigido entre atendimentos;
  - bloqueios manuais (parciais ou de dia inteiro);
  - agendamentos já existentes (pendentes ou confirmados) na data.
"""

from datetime import datetime, timedelta, date as date_cls

from app.models import Appointment, Block, Settings, WorkingHours, ACTIVE_STATUSES


def _overlaps(a_start, a_end, b_start, b_end):
    """True se os intervalos [a_start, a_end) e [b_start, b_end) se sobrepõem."""
    return a_start < b_end and b_start < a_end


def get_working_hours_for_date(target_date):
    return WorkingHours.query.filter_by(weekday=target_date.weekday()).first()


def _busy_periods(target_date, buffer_minutes, exclude_appointment_id=None):
    """Períodos ocupados por agendamentos existentes, já com o buffer aplicado."""
    buffer = timedelta(minutes=buffer_minutes)
    query = Appointment.query.filter(
        Appointment.date == target_date,
        Appointment.status.in_(ACTIVE_STATUSES),
    )
    if exclude_appointment_id:
        query = query.filter(Appointment.id != exclude_appointment_id)

    periods = []
    for appt in query.all():
        start = datetime.combine(target_date, appt.start_time) - buffer
        end = datetime.combine(target_date, appt.end_time) + buffer
        periods.append((start, end))
    return periods


def _block_periods(target_date, working_hours):
    periods = []
    for block in Block.query.filter_by(date=target_date).all():
        if block.is_full_day:
            periods.append(
                (
                    datetime.combine(target_date, working_hours.open_time),
                    datetime.combine(target_date, working_hours.close_time),
                )
            )
        else:
            periods.append(
                (
                    datetime.combine(target_date, block.start_time),
                    datetime.combine(target_date, block.end_time),
                )
            )
    return periods


def get_available_slots(service, target_date, exclude_appointment_id=None):
    """Retorna uma lista de horários (objetos time) livres para o serviço na data."""
    working_hours = get_working_hours_for_date(target_date)
    if not working_hours or not working_hours.is_open:
        return []
    if not working_hours.open_time or not working_hours.close_time:
        return []

    settings = Settings.get()
    interval = timedelta(minutes=settings.slot_interval_minutes)
    duration = timedelta(minutes=service.duration_minutes)
    buffer_minutes = settings.buffer_minutes

    day_start = datetime.combine(target_date, working_hours.open_time)
    day_end = datetime.combine(target_date, working_hours.close_time)

    break_period = None
    if working_hours.break_start and working_hours.break_end:
        break_period = (
            datetime.combine(target_date, working_hours.break_start),
            datetime.combine(target_date, working_hours.break_end),
        )

    block_periods = _block_periods(target_date, working_hours)
    busy_periods = _busy_periods(target_date, buffer_minutes, exclude_appointment_id)

    now = datetime.now()
    slots = []
    current = day_start
    while current + duration <= day_end:
        slot_end = current + duration
        conflict = False

        if target_date == now.date() and current <= now:
            conflict = True

        if not conflict and break_period and _overlaps(current, slot_end, *break_period):
            conflict = True

        if not conflict:
            for period in block_periods:
                if _overlaps(current, slot_end, *period):
                    conflict = True
                    break

        if not conflict:
            for period in busy_periods:
                if _overlaps(current, slot_end, *period):
                    conflict = True
                    break

        if not conflict:
            slots.append(current.time())

        current += interval

    return slots


def is_slot_available(service, target_date, start_time, exclude_appointment_id=None):
    """Revalida no backend se um horário específico ainda está livre."""
    available = get_available_slots(service, target_date, exclude_appointment_id)
    return start_time in available


def compute_end_time(target_date, start_time, service):
    start_dt = datetime.combine(target_date, start_time)
    end_dt = start_dt + timedelta(minutes=service.duration_minutes)
    return end_dt.time()


def can_cancel(appointment):
    """Verifica se o prazo mínimo de cancelamento ainda permite o cancelamento."""
    settings = Settings.get()
    appt_datetime = datetime.combine(appointment.date, appointment.start_time)
    deadline = appt_datetime - timedelta(hours=settings.cancellation_hours)
    return datetime.now() <= deadline
