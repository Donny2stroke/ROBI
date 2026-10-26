from robi.settings import backend_id, capture_config, setting


def test_default_setting(monkeypatch):
    monkeypatch.delenv('ROBI_TEST_SAMPLE', raising=False)
    assert setting('ROBI_TEST_SAMPLE', 3, int) == 3


def test_numeric_setting(monkeypatch):
    monkeypatch.setenv('ROBI_TEST_SAMPLE', '25')
    assert setting('ROBI_TEST_SAMPLE', 3, int) == 25
