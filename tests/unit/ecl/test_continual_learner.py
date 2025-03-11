import pytest
from src.ecl.continual_learner import ExternalContinualLearner
from src.db.connection import DBConnection

@pytest.fixture(scope="module")
def db_connection():
    db = DBConnection()
    assert db.connect(host="http://localhost:8529", username="root", password="")
    return db

@pytest.fixture(scope="module")
def continual_learner(db_connection):
    return ExternalContinualLearner(db_connection)

def test_initialization(continual_learner):
    assert isinstance(continual_learner, ExternalContinualLearner)
    assert continual_learner.db is not None