from alembic import context
from app.database.session import Base, engine
from app.models import Alert, ApplicationLog, Incident, IncidentLog, User

target_metadata = Base.metadata

def run_migrations_online():
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction(): context.run_migrations()

run_migrations_online()
