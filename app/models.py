import random
import string
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db

# ---------------------------------------------------------------------------
# Usuário administrador (responsável pelo negócio)
# ---------------------------------------------------------------------------


class AdminUser(UserMixin, db.Model):
    __tablename__ = "admin_users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    nome_completo = db.Column(db.String(120), nullable=False, default="Responsável")

    def set_password(self, senha):
        self.password_hash = generate_password_hash(senha)

    def check_password(self, senha):
        return check_password_hash(self.password_hash, senha)


# ---------------------------------------------------------------------------
# Configurações gerais do negócio (linha única)
# ---------------------------------------------------------------------------


class Settings(db.Model):
    __tablename__ = "settings"

    id = db.Column(db.Integer, primary_key=True)
    business_name = db.Column(db.String(150), nullable=False, default="Meu Negócio")
    business_type = db.Column(db.String(80), nullable=False, default="Serviços")
    phone = db.Column(db.String(40), nullable=False, default="")
    address = db.Column(db.String(255), nullable=False, default="")
    slot_interval_minutes = db.Column(db.Integer, nullable=False, default=15)
    buffer_minutes = db.Column(db.Integer, nullable=False, default=10)
    cancellation_hours = db.Column(db.Integer, nullable=False, default=2)

    @staticmethod
    def get():
        """Retorna a linha única de configurações, criando-a se necessário."""
        settings = Settings.query.first()
        if settings is None:
            settings = Settings()
            db.session.add(settings)
            db.session.commit()
        return settings


# ---------------------------------------------------------------------------
# Serviços oferecidos pelo negócio
# ---------------------------------------------------------------------------


class Service(db.Model):
    __tablename__ = "services"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    duration_minutes = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    appointments = db.relationship("Appointment", back_populates="service")

    @property
    def price_formatted(self):
        return f"R$ {self.price:.2f}".replace(".", ",")

    @property
    def duration_formatted(self):
        h, m = divmod(self.duration_minutes, 60)
        if h and m:
            return f"{h}h{m:02d}min"
        if h:
            return f"{h}h"
        return f"{m}min"


# ---------------------------------------------------------------------------
# Horário de funcionamento por dia da semana (0 = segunda ... 6 = domingo)
# ---------------------------------------------------------------------------


class WorkingHours(db.Model):
    __tablename__ = "working_hours"

    id = db.Column(db.Integer, primary_key=True)
    weekday = db.Column(db.Integer, nullable=False, unique=True)  # 0=Seg ... 6=Dom
    is_open = db.Column(db.Boolean, nullable=False, default=False)
    open_time = db.Column(db.Time, nullable=True)
    close_time = db.Column(db.Time, nullable=True)
    break_start = db.Column(db.Time, nullable=True)
    break_end = db.Column(db.Time, nullable=True)

    WEEKDAY_NAMES = [
        "Segunda-feira",
        "Terça-feira",
        "Quarta-feira",
        "Quinta-feira",
        "Sexta-feira",
        "Sábado",
        "Domingo",
    ]

    @property
    def weekday_name(self):
        return self.WEEKDAY_NAMES[self.weekday]


# ---------------------------------------------------------------------------
# Bloqueios manuais (feriados, folgas, compromissos pessoais etc.)
# ---------------------------------------------------------------------------


class Block(db.Model):
    __tablename__ = "blocks"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=True)  # None + end None = dia inteiro
    end_time = db.Column(db.Time, nullable=True)
    reason = db.Column(db.String(200), nullable=False, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def is_full_day(self):
        return self.start_time is None or self.end_time is None


# ---------------------------------------------------------------------------
# Agendamentos
# ---------------------------------------------------------------------------


STATUS_PENDENTE = "pendente"
STATUS_CONFIRMADO = "confirmado"
STATUS_CONCLUIDO = "concluido"
STATUS_CANCELADO = "cancelado"

STATUS_LABELS = {
    STATUS_PENDENTE: "Pendente",
    STATUS_CONFIRMADO: "Confirmado",
    STATUS_CONCLUIDO: "Concluído",
    STATUS_CANCELADO: "Cancelado",
}

ACTIVE_STATUSES = (STATUS_PENDENTE, STATUS_CONFIRMADO)


class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False, index=True)

    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False)
    service = db.relationship("Service", back_populates="appointments")

    client_name = db.Column(db.String(120), nullable=False)
    client_contact = db.Column(db.String(120), nullable=False)
    notes = db.Column(db.String(300), nullable=False, default="")

    date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

    status = db.Column(db.String(20), nullable=False, default=STATUS_PENDENTE)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    cancelled_by = db.Column(db.String(20), nullable=True)  # 'cliente' | 'negocio'

    @property
    def status_label(self):
        return STATUS_LABELS.get(self.status, self.status)

    @staticmethod
    def generate_code():
        alphabet = string.ascii_uppercase + string.digits
        while True:
            code = "".join(random.choices(alphabet, k=7))
            if not Appointment.query.filter_by(code=code).first():
                return code
