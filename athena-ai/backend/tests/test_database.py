import uuid

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from app.core.settings import get_settings
from app.models.decision import Decision
from app.models.enums import EffortLevel, EventActivityType, EventSeverity, EventStatus, UserRole
from app.models.event import Event, EventActivity
from app.models.investigation import Investigation
from app.models.prediction import Prediction
from app.models.recommendation import Recommendation
from app.models.report import Report
from app.models.user import User
from app.repositories.event_repository import EventRepository
from app.repositories.user_repository import UserRepository


@pytest.mark.asyncio
async def test_migrations_create_expected_tables() -> None:
    settings = get_settings()
    engine: AsyncEngine = create_async_engine(settings.database_url, pool_pre_ping=True)

    async with engine.connect() as connection:
        table_names = await connection.run_sync(
            lambda sync_conn: inspect(sync_conn).get_table_names()
        )

    await engine.dispose()

    expected_tables = {
        "users",
        "events",
        "event_activities",
        "investigations",
        "predictions",
        "recommendations",
        "decisions",
        "reports",
        "alembic_version",
    }
    assert expected_tables.issubset(set(table_names))


@pytest.mark.asyncio
async def test_user_email_unique_constraint(db_session: AsyncSession) -> None:
    user_a = User(
        name="Alice",
        email="alice.unique@athena.test",
        password_hash="hash-a",
        role=UserRole.ANALYST,
    )
    user_b = User(
        name="Bob",
        email="alice.unique@athena.test",
        password_hash="hash-b",
        role=UserRole.VIEWER,
    )

    db_session.add(user_a)
    await db_session.flush()

    db_session.add(user_b)
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_event_foreign_key_restricts_user_delete(db_session: AsyncSession) -> None:
    user = User(
        name="Creator",
        email=f"creator.{uuid.uuid4()}@athena.test",
        password_hash="hash",
        role=UserRole.MANAGER,
    )
    db_session.add(user)
    await db_session.flush()

    event = Event(
        title="Supply delay",
        event_type="logistics",
        severity=EventSeverity.HIGH,
        status=EventStatus.NEW,
        source="erp",
        created_by=user.id,
    )
    db_session.add(event)
    await db_session.flush()

    await db_session.delete(user)
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_event_child_records_cascade_on_delete(db_session: AsyncSession) -> None:
    user = User(
        name="Cascade User",
        email=f"cascade.{uuid.uuid4()}@athena.test",
        password_hash="hash",
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    await db_session.flush()

    event = Event(
        title="Cascade event",
        event_type="billing",
        severity=EventSeverity.MEDIUM,
        status=EventStatus.IN_PROGRESS,
        source="billing-service",
        created_by=user.id,
    )
    db_session.add(event)
    await db_session.flush()

    db_session.add_all(
        [
            Investigation(event_id=event.id, evidence={"logs": ["entry-1"]}, confidence=0.8),
            Prediction(event_id=event.id, revenue_risk=0.2, confidence=0.7),
            Recommendation(
                event_id=event.id,
                title="Refund policy update",
                effort=EffortLevel.LOW,
                confidence=0.6,
            ),
            Decision(event_id=event.id, selected_action={"action": "notify"}, confidence=0.9),
            Report(event_id=event.id, report_type="summary", report_text="Investigation complete"),
            EventActivity(
                event_id=event.id,
                activity_type=EventActivityType.CREATED,
                actor_id=user.id,
                details={"source": "test"},
            ),
        ]
    )
    await db_session.flush()

    event_id = event.id
    await db_session.delete(event)
    await db_session.flush()

    counts = await db_session.execute(
        text(
            """
            SELECT
              (SELECT COUNT(*) FROM investigations WHERE event_id = :event_id) AS investigations,
              (SELECT COUNT(*) FROM predictions WHERE event_id = :event_id) AS predictions,
              (SELECT COUNT(*) FROM recommendations WHERE event_id = :event_id) AS recommendations,
              (SELECT COUNT(*) FROM decisions WHERE event_id = :event_id) AS decisions,
              (SELECT COUNT(*) FROM reports WHERE event_id = :event_id) AS reports,
              (SELECT COUNT(*) FROM event_activities WHERE event_id = :event_id) AS event_activities
            """
        ),
        {"event_id": str(event_id)},
    )
    row = counts.one()
    assert row.investigations == 0
    assert row.predictions == 0
    assert row.recommendations == 0
    assert row.decisions == 0
    assert row.reports == 0
    assert row.event_activities == 0


@pytest.mark.asyncio
async def test_event_relationships_load_correctly(db_session: AsyncSession) -> None:
    user = User(
        name="Relationship User",
        email=f"relationship.{uuid.uuid4()}@athena.test",
        password_hash="hash",
        role=UserRole.ANALYST,
    )
    db_session.add(user)
    await db_session.flush()

    event = Event(
        title="Relationship event",
        event_type="ops",
        severity=EventSeverity.CRITICAL,
        status=EventStatus.NEW,
        source="monitoring",
        created_by=user.id,
    )
    db_session.add(event)
    await db_session.flush()

    db_session.add(
        Investigation(
            event_id=event.id,
            root_cause="API timeout",
            evidence={"traces": ["trace-1"]},
            confidence=0.85,
        )
    )
    await db_session.flush()

    repo = EventRepository(db_session)
    loaded = await repo.get_with_relations(event.id)

    assert loaded is not None
    assert loaded.creator.id == user.id
    assert len(loaded.investigations) == 1
    assert loaded.investigations[0].root_cause == "API timeout"


@pytest.mark.asyncio
async def test_soft_deleted_users_are_excluded(db_session: AsyncSession) -> None:
    user = User(
        name="Soft Delete User",
        email=f"softdelete.{uuid.uuid4()}@athena.test",
        password_hash="hash",
        role=UserRole.VIEWER,
    )
    repo = UserRepository(db_session)
    await repo.add(user)
    await repo.soft_delete(user)

    fetched = await repo.get_by_id(user.id)
    assert fetched is None

    fetched_deleted = await repo.get_by_id(user.id, include_deleted=True)
    assert fetched_deleted is not None
    assert fetched_deleted.is_deleted is True
