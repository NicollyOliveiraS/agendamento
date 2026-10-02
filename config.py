import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")

if not os.path.exists(INSTANCE_DIR):
    os.makedirs(INSTANCE_DIR)


class Config:
    """Configuração base da aplicação."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "troque-esta-chave-em-producao")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(INSTANCE_DIR, 'agendamento.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Regras de negócio padrão (podem ser sobrescritas pelo painel admin,
    # que grava os valores na tabela Settings)
    DEFAULT_SLOT_INTERVAL_MINUTES = 15
    DEFAULT_BUFFER_MINUTES = 10
    DEFAULT_CANCELLATION_HOURS = 2
