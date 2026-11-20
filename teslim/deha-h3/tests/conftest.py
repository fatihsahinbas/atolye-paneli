import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app as fastapi_app
from app.models import Workshop, Customer, Order, Notification
from app.notifiers.multi import MultiNotifier
from app.notifiers.sms import SmsNotifier
from app.notifiers.email import EmailNotifier


# ---- Sahte SMTP ----
class FakeSMTP:
    instances = []
    fail = False

    def __init__(self, host, port):
        self.host, self.port = host, port
        self.sent = []
        FakeSMTP.instances.append(self)

    def __enter__(self): return self
    def __exit__(self, *a): return False
    def starttls(self): pass
    def login(self, u, p): pass
    def send_message(self, msg):
        if FakeSMTP.fail:
            import smtplib
            raise smtplib.SMTPException("boom")
        self.sent.append(msg)


@pytest.fixture
def db_engine():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def db(db_engine):
    Session = sessionmaker(bind=db_engine)
    s = Session()
    yield s
    s.close()


@pytest.fixture
def client(db, monkeypatch):
    def override_get_db():
        yield db

    FakeSMTP.instances.clear()
    FakeSMTP.fail = False

    email = EmailNotifier("h", 587, "u", "p", "from@x", smtp_factory=FakeSMTP)
    fastapi_app.state.notifier = MultiNotifier(sms=SmsNotifier(), email=email)

    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app) as c:
        yield c
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def workshop(db):
    ws = Workshop(name="Test Atölye")
    db.add(ws); db.commit(); db.refresh(ws)
    return ws


@pytest.fixture
def other_workshop(db):
    ws = Workshop(name="Başka Atölye")
    db.add(ws); db.commit(); db.refresh(ws)
    return ws


@pytest.fixture
def customer_phone(db):
    c = Customer(name="Ali", phone="+905551112233", email=None)
    db.add(c); db.commit(); db.refresh(c)
    return c


@pytest.fixture
def customer_email(db):
    c = Customer(name="Veli", phone=None, email="veli@example.com")
    db.add(c); db.commit(); db.refresh(c)
    return c


@pytest.fixture
def customer_none(db):
    c = Customer(name="Boş", phone=None, email=None)
    db.add(c); db.commit(); db.refresh(c)
    return c


@pytest.fixture
def make_order(db, workshop):
    def _make(customer, status="NEW"):
        o = Order(workshop_id=workshop.id, customer_id=customer.id, status=status)
        db.add(o); db.commit(); db.refresh(o)
        return o
    return _make


@pytest.fixture
def headers(workshop):
    return {"X-Workshop-Id": str(workshop.id), "X-CSRF-Token": "test-token"}