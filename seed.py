"""
Popula o banco com dados de demonstração para apresentação do projeto:
  - 1 usuário administrador
  - configurações gerais do negócio (exemplo: salão de beleza)
  - horário de funcionamento semanal
  - 5 serviços
  - alguns bloqueios e vários agendamentos fictícios (passados, hoje e futuros,
    em diferentes status) para o painel já nascer com conteúdo para mostrar.

Rode com o ambiente virtual ativado:
    python seed.py

Atenção: este script APAGA todos os dados existentes antes de recriar o banco,
pois é pensado para preparar uma demonstração limpa.
"""

from datetime import date, datetime, time, timedelta

from app import create_app
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
)

app = create_app()


def run():
    with app.app_context():
        print("Recriando o banco de dados...")
        db.drop_all()
        db.create_all()

        # ------------------------------------------------------------------
        # Usuário administrador de demonstração
        # ------------------------------------------------------------------
        admin = AdminUser(username="admin", nome_completo="Mariana Duarte")
        admin.set_password("admin123")
        db.session.add(admin)

        # ------------------------------------------------------------------
        # Configurações gerais (exemplo: salão de beleza)
        # ------------------------------------------------------------------
        settings = Settings(
            business_name="Espaço Renove",
            business_type="Salão de Beleza",
            phone="(11) 98888-4321",
            address="Rua das Flores, 210 — Centro",
            slot_interval_minutes=15,
            buffer_minutes=10,
            cancellation_hours=3,
        )
        db.session.add(settings)

        # ------------------------------------------------------------------
        # Horário de funcionamento: Terça a Sábado, com pausa de almoço.
        # weekday: 0=Segunda ... 6=Domingo
        # ------------------------------------------------------------------
        schedule = {
            0: None,  # Segunda: fechado
            1: (time(9, 0), time(19, 0), time(12, 30), time(13, 30)),
            2: (time(9, 0), time(19, 0), time(12, 30), time(13, 30)),
            3: (time(9, 0), time(19, 0), time(12, 30), time(13, 30)),
            4: (time(9, 0), time(19, 0), time(12, 30), time(13, 30)),
            5: (time(9, 0), time(15, 0), None, None),
            6: None,  # Domingo: fechado
        }

        for weekday, config in schedule.items():
            if config is None:
                db.session.add(WorkingHours(weekday=weekday, is_open=False))
            else:
                open_t, close_t, brk_s, brk_e = config
                db.session.add(
                    WorkingHours(
                        weekday=weekday,
                        is_open=True,
                        open_time=open_t,
                        close_time=close_t,
                        break_start=brk_s,
                        break_end=brk_e,
                    )
                )

        db.session.commit()

        # ------------------------------------------------------------------
        # Serviços
        # ------------------------------------------------------------------
        services_data = [
            dict(
                name="Corte feminino",
                description="Corte com lavagem, finalização e hidratação leve.",
                duration_minutes=60,
                price=90.00,
            ),
            dict(
                name="Corte masculino",
                description="Corte na tesoura ou máquina, acabamento na navalha.",
                duration_minutes=30,
                price=50.00,
            ),
            dict(
                name="Coloração",
                description="Coloração completa com produtos profissionais.",
                duration_minutes=120,
                price=220.00,
            ),
            dict(
                name="Manicure e pedicure",
                description="Cuidado completo para mãos e pés, com esmaltação.",
                duration_minutes=75,
                price=70.00,
            ),
            dict(
                name="Escova modelada",
                description="Escova com finalização modelada para o dia a dia ou eventos.",
                duration_minutes=45,
                price=60.00,
            ),
        ]

        services = []
        for data in services_data:
            service = Service(active=True, **data)
            db.session.add(service)
            services.append(service)

        db.session.commit()

        corte_fem, corte_masc, coloracao, manicure, escova = services

        # ------------------------------------------------------------------
        # Bloqueio manual de exemplo
        # ------------------------------------------------------------------
        next_saturday = date.today() + timedelta(
            days=(5 - date.today().weekday()) % 7 + 7
        )
        db.session.add(
            Block(
                date=next_saturday,
                start_time=None,
                end_time=None,
                reason="Confraternização da equipe",
            )
        )

        today = date.today()
        db.session.add(
            Block(
                date=today,
                start_time=time(16, 0),
                end_time=time(17, 0),
                reason="Compromisso pessoal",
            )
        )

        # ------------------------------------------------------------------
        # Agendamentos fictícios: passados, hoje e futuros
        # ------------------------------------------------------------------
        def add_appointment(service, day_offset, start, client, contact, status, notes=""):
            target_date = today + timedelta(days=day_offset)
            start_dt = datetime.combine(target_date, start)
            end_dt = start_dt + timedelta(minutes=service.duration_minutes)
            appt = Appointment(
                code=Appointment.generate_code(),
                service=service,
                client_name=client,
                client_contact=contact,
                notes=notes,
                date=target_date,
                start_time=start,
                end_time=end_dt.time(),
                status=status,
            )
            if status == STATUS_CANCELADO:
                appt.cancelled_at = datetime.utcnow()
                appt.cancelled_by = "cliente"
            db.session.add(appt)

        demo_appointments = [
            # Alguns concluídos/cancelados em dias passados (histórico p/ busca e KPIs)
            (corte_fem, -6, time(10, 0), "Ana Beatriz Souza", "(11) 91234-1111", STATUS_CONCLUIDO, ""),
            (corte_masc, -5, time(11, 0), "Rafael Lima", "(11) 91234-2222", STATUS_CONCLUIDO, ""),
            (coloracao, -4, time(14, 0), "Juliana Prado", "juliana.prado@email.com", STATUS_CONCLUIDO, ""),
            (manicure, -3, time(9, 30), "Camila Ferreira", "(11) 91234-3333", STATUS_CANCELADO, "Remarcar depois"),
            (escova, -2, time(16, 0), "Beatriz Nunes", "(11) 91234-4444", STATUS_CONCLUIDO, ""),

            # Hoje
            (corte_fem, 0, time(9, 30), "Fernanda Alves", "(11) 98888-1010", STATUS_CONFIRMADO, ""),
            (corte_masc, 0, time(11, 0), "Bruno Castro", "(11) 98888-2020", STATUS_CONFIRMADO, ""),
            (manicure, 0, time(14, 0), "Larissa Martins", "larissa.m@email.com", STATUS_PENDENTE, "Primeira vez no salão"),

            # Próximos dias
            (coloracao, 1, time(10, 0), "Patrícia Gomes", "(11) 98888-3030", STATUS_CONFIRMADO, ""),
            (corte_fem, 1, time(15, 0), "Isabela Rocha", "(11) 98888-4040", STATUS_PENDENTE, ""),
            (escova, 2, time(9, 0), "Manuela Duarte", "(11) 98888-5050", STATUS_CONFIRMADO, ""),
            (corte_masc, 2, time(17, 0), "Diego Santos", "diego.santos@email.com", STATUS_PENDENTE, ""),
            (manicure, 3, time(10, 30), "Sofia Cardoso", "(11) 98888-6060", STATUS_CONFIRMADO, ""),
            (corte_fem, 4, time(13, 45), "Helena Teixeira", "(11) 98888-7070", STATUS_PENDENTE, ""),
            (coloracao, 5, time(9, 30), "Valentina Ramos", "(11) 98888-8080", STATUS_CONFIRMADO, ""),
        ]

        for service, offset, start, client, contact, status, notes in demo_appointments:
            add_appointment(service, offset, start, client, contact, status, notes)

        db.session.commit()

        print("Banco de dados populado com sucesso!")
        print("-" * 50)
        print("Login do painel: admin / admin123")
        print(f"Serviços cadastrados: {len(services)}")
        print(f"Agendamentos de demonstração: {len(demo_appointments)}")
        print("-" * 50)


if __name__ == "__main__":
    run()
