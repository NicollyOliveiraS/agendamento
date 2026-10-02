# Sistema de Agendamento para Pequenos Negócios

Aplicação web completa de agendamento online, pensada para pequenos negócios
baseados em horário marcado: salões de beleza, barbearias, oficinas mecânicas,
professores particulares, clínicas de estética, consultórios, entre outros.

O sistema tem duas frentes:

- **Área do cliente** (pública): o cliente escolhe um serviço, vê os horários
  realmente disponíveis, faz a solicitação e recebe um código para consultar
  ou cancelar depois.
- **Painel do negócio** (protegido por login): o responsável gerencia
  serviços, horário de funcionamento, bloqueios, e confirma/cancela/conclui
  os atendimentos, além de ver indicadores simples.

Vem com **dados de demonstração** de um salão de beleza fictício (serviços,
horário semanal, bloqueios e ~15 agendamentos em diferentes status e datas),
prontos para uma apresentação.

---

## Tecnologias

- **Backend:** Python 3 + Flask, Flask-SQLAlchemy, Flask-Login
- **Banco de dados:** SQLite (arquivo local, zero configuração)
- **Frontend:** HTML + CSS + JavaScript "puro" (sem build step, sem framework),
  renderizado por templates Jinja2 no servidor
- **Senhas:** hash com `werkzeug.security` (nunca armazenadas em texto puro)

---

## Estrutura de pastas

```
agendamento/
├── app/
│   ├── __init__.py            # application factory (create_app)
│   ├── extensions.py          # instâncias do SQLAlchemy e do LoginManager
│   ├── models.py              # modelos do banco (Service, Appointment, ...)
│   ├── routes/
│   │   ├── public.py          # rotas da área do cliente
│   │   └── admin.py           # rotas do painel do negócio (login_required)
│   ├── utils/
│   │   ├── scheduling.py      # cálculo dos horários disponíveis
│   │   └── validators.py      # validações de formulário no backend
│   ├── templates/
│   │   ├── base.html          # layout do site público
│   │   ├── public/            # páginas do cliente
│   │   └── admin/             # páginas do painel (base.html próprio)
│   └── static/
│       ├── css/style.css      # design system completo (mobile-first)
│       └── js/
│           ├── booking.js     # busca de horários via AJAX
│           └── admin.js       # menu mobile + edição inline de serviços
├── instance/                  # onde o arquivo agendamento.db é criado
├── config.py                  # configuração (SECRET_KEY, banco, etc.)
├── run.py                     # ponto de entrada (python run.py)
├── seed.py                    # popula o banco com dados de demonstração
├── requirements.txt
└── README.md
```

A separação segue responsabilidades claras: **models** (dados) → **utils**
(regras de negócio puras, sem depender do Flask) → **routes** (orquestram
tudo e respondem HTTP) → **templates/static** (apresentação). Isso facilita
tanto adaptar o sistema para outro tipo de negócio quanto dar manutenção.

---

## Modelo de dados

| Tabela           | Finalidade                                                         |
|------------------|---------------------------------------------------------------------|
| `admin_users`    | Login do responsável pelo negócio (senha em hash)                  |
| `settings`       | Configurações gerais: nome do negócio, intervalo de horários, buffer entre atendimentos, prazo de cancelamento |
| `services`       | Serviços oferecidos: nome, descrição, duração, preço, ativo/inativo |
| `working_hours`  | Horário de funcionamento por dia da semana, com pausa opcional      |
| `blocks`         | Bloqueios manuais (dia inteiro ou faixa de horário)                 |
| `appointments`   | Agendamentos: serviço, cliente, data/hora, status, código único     |

O cálculo de horários disponíveis (`app/utils/scheduling.py`) considera, nesta
ordem: o negócio estar aberto naquele dia → não cair na pausa (ex.: almoço) →
não cair em um bloqueio manual → não conflitar com outro agendamento já
existente, respeitando o intervalo mínimo (buffer) configurado entre
atendimentos. O mesmo horário nunca pode ser ocupado duas vezes: a
disponibilidade é **recalculada no servidor** no momento de confirmar o
agendamento, não apenas no frontend.

---

## Como rodar localmente

### Pré-requisitos

- Python 3.10 ou superior instalado

### Passo a passo

```bash
# 1. Entre na pasta do projeto
cd agendamento

# 2. Crie e ative um ambiente virtual
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Popule o banco com dados de demonstração
python seed.py

# 5. Rode a aplicação
python run.py
```

A aplicação sobe em **http://localhost:5000**.

- Site do cliente: `http://localhost:5000/`
- Painel do negócio: `http://localhost:5000/admin/login`

### Login de demonstração do painel

```
Usuário: admin
Senha:   admin123
```

> O script `seed.py` **apaga e recria o banco do zero** — rode-o sempre que
> quiser voltar a um estado limpo para uma nova apresentação. Se quiser só
> subir a aplicação sem repopular os dados, pule o passo 4 (o banco e as
> tabelas são criados automaticamente na primeira execução, só que vazios).

---

## Adaptando para outro tipo de negócio

O sistema foi feito para ser genérico. Para adaptar para uma oficina,
professor particular, clínica etc., normalmente basta:

1. **Painel → Horários e políticas:** trocar nome, tipo de negócio, telefone
   e endereço exibidos no site.
2. **Painel → Serviços:** cadastrar os serviços com a duração e o preço reais
   (ex.: "Aula de reforço — 50 min", "Troca de óleo — 40 min").
3. **Painel → Horários e políticas → horário semanal:** ajustar os dias e
   horários de funcionamento e a pausa de cada dia.
4. **Painel → Horários e políticas → regras gerais:** ajustar o intervalo
   mínimo entre atendimentos (buffer) e o prazo mínimo de cancelamento.
5. **Painel → Bloqueios:** usar para folgas, feriados ou qualquer
   indisponibilidade pontual.

Nenhuma dessas mudanças exige alterar código — tudo é feito pelo painel.

---

## Segurança e validações

- Senha do painel armazenada com **hash** (`werkzeug.security`), nunca em
  texto puro.
- Todas as rotas do painel (`/admin/...`, exceto `/admin/login`) exigem
  login via `flask-login` (`@login_required`).
- Toda validação feita no frontend (JavaScript/HTML5) é **repetida no
  backend** — nome, contato, data, horário, e principalmente a
  disponibilidade do horário são sempre revalidados no servidor antes de
  gravar no banco.
- Mensagens de erro claras e específicas (ex.: "Esse horário acabou de ficar
  indisponível. Escolha outro.", "Informe um telefone ou e-mail válido.").

---

## Principais fluxos implementados

**Cliente**
- Lista de serviços com descrição, duração e preço.
- Escolha de data → busca assíncrona (AJAX) dos horários livres → escolha do
  horário → dados de contato → confirmação com resumo e código.
- Consulta e cancelamento por código, respeitando o prazo mínimo configurado.

**Painel do negócio**
- Login protegido.
- Visão do dia e da semana, com indicadores (agendamentos da semana,
  cancelamentos, serviços mais procurados).
- Busca de agendamentos por nome, data e status.
- Confirmar, concluir ou cancelar qualquer agendamento.
- Cadastro, edição e ativação/desativação de serviços.
- Configuração completa de horário semanal (com pausa por dia), intervalo
  entre horários, buffer entre atendimentos e prazo de cancelamento.
- Bloqueios manuais de dia inteiro ou de uma faixa de horário específica.

---

## Notas para produção

### Publicação na Vercel

O projeto define `run:app` como entrada Flask em `pyproject.toml` e usa
`vercel.json` para configurar o build. O comando `python build.py` copia CSS e JavaScript para
`public/static/`, mantendo os endereços `/static/...` usados nos templates.

1. Importe o repositório na Vercel com a pasta raiz do projeto e o framework
   **Flask**. Remova configurações antigas de build/output de outros frameworks;
   o build está definido em `vercel.json`.
2. Conecte um banco **PostgreSQL externo** e configure `DATABASE_URL` nas
   variáveis de ambiente dos ambientes desejados (Production/Preview).
   Use a URL fornecida pelo provedor, incluindo os parâmetros de SSL.
   URLs `postgres://` e `postgresql://` são aceitas.
3. Configure também `SECRET_KEY` com um valor aleatório e estável. Você pode
   gerar um localmente com `python -c "import secrets; print(secrets.token_hex(32))"`.
4. Publique novamente depois de salvar essas variáveis. As tabelas são
   criadas na inicialização; o banco precisa permitir a criação delas.

SQLite continua disponível para uso local. Na Vercel, um arquivo SQLite
não é um banco persistente compartilhado entre execuções. O projeto rejeita
essa configuração para evitar perda de agendamentos.

Um banco novo começa sem serviços e sem administrador. Para cadastrar o
primeiro administrador, instale as dependências localmente, configure
`DATABASE_URL` para o mesmo banco e execute `python -m flask --app run shell`:

```python
from getpass import getpass
from app.extensions import db
from app.models import AdminUser
admin = AdminUser(username="admin", nome_completo="Responsável")
admin.set_password(getpass("Senha do administrador: "))
db.session.add(admin)
db.session.commit()
```

Depois entre em `/admin/login` para cadastrar serviços e horários.
Não execute `seed.py` em um banco com dados reais: ele apaga todas as tabelas
antes de inserir a demonstração. Os dados do SQLite local não são migrados
automaticamente para o PostgreSQL.

Referências: [Flask na Vercel](https://vercel.com/docs/frameworks/backend/flask)
e [limitação do SQLite](https://vercel.com/kb/guide/is-sqlite-supported-in-vercel).

Este projeto está pronto para demonstração e uso local. Para um ambiente de
produção real, vale complementar com:

- Definir `SECRET_KEY` própria via variável de ambiente (não usar a padrão).
- Rodar atrás de um servidor WSGI como Gunicorn, e não com `debug=True`.
- Migração para um banco mais robusto (PostgreSQL) se o volume crescer, já
  que o SQLAlchemy facilita a troca sem reescrever a lógica.
- Envio de e-mail/SMS de confirmação e lembrete (hoje o aviso fica só na
  tela de confirmação e na consulta por código).
- Backup periódico do arquivo `instance/agendamento.db`.
