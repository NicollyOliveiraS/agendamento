import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")

def database_uri():
    uri = os.environ.get("DATABASE_URL", "").strip()
    if os.environ.get("VERCEL") == "1":
        if not uri or uri.startswith("sqlite:"):
            raise RuntimeError(
                "Configure DATABASE_URL com um banco PostgreSQL externo na Vercel. "
                "SQLite local não persiste os agendamentos nessa hospedagem."
            )
    if not uri:
        os.makedirs(INSTANCE_DIR, exist_ok=True)
        return f"sqlite:///{os.path.join(INSTANCE_DIR, 'agendamento.db')}"
    # Provedores entregam URLs postgres:// ou postgresql://.
    for prefix in ("postgres://", "postgresql://"):
        if uri.startswith(prefix):
            return "postgresql+psycopg://" + uri[len(prefix):]
    return uri


class Config:
    """Configuração base da aplicação."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "troque-esta-chave-em-producao")
    SQLALCHEMY_DATABASE_URI = database_uri()
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Regras de negócio padrão (podem ser sobrescritas pelo painel admin,
    # que grava os valores na tabela Settings)
    DEFAULT_SLOT_INTERVAL_MINUTES = 15
    DEFAULT_BUFFER_MINUTES = 10
    DEFAULT_CANCELLATION_HOURS = 2
