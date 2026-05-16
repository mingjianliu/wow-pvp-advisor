import pytest
import sqlite3


@pytest.fixture
def tmp_db(tmp_path):
    return str(tmp_path / "test.db")
