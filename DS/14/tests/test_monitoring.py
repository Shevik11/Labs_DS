import numpy as np
from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families

from drift import psi, compare, severity, AlertManager
from app import create_app


def metrics(psi_value, p=.00001):
    return {k: dict(psi=psi_value, pvalue=p) for k in ('a', 'b', 'c')}


def test_psi_identity_and_extreme_tails():
    x = np.linspace(1, 10, 3000)
    assert psi(x, x) == 0
    assert psi(x, x * 100) > .25


def test_psi_rejects_invalid():
    import pytest
    for bad in ([1, np.nan], [], [1]):
        with pytest.raises(ValueError):
            psi([1, 2, 3], bad)


def test_shift_both_methods():
    rng = np.random.default_rng(42)
    ref = {k: rng.normal(size=3000) for k in ('a', 'b', 'c')}
    cur = {k: rng.normal(1, 1, 3000) for k in ref}
    result = compare(ref, cur)
    assert all(v['psi'] > .25 and v['pvalue'] < .01 / 3 for v in result.values())
    assert severity(result) == 'critical'


def test_confirmation_and_ks_effect_gate():
    data = metrics(.3)
    data['b']['psi'] = data['c']['psi'] = 0
    assert severity(data) is None
    assert severity(metrics(.3, p=.5)) is None
    assert severity(metrics(.15)) == 'warning'


def test_cooldown_expiry_escalation_and_independent_incidents():
    manager = AlertManager(900)
    assert not manager.check(metrics(.15), 0)['suppressed']
    assert manager.check(metrics(.15), 1)['suppressed']
    assert not manager.check(metrics(.3), 2)['suppressed']
    assert manager.check(metrics(.3), 3)['suppressed']
    assert not manager.check(metrics(.3), 903)['suppressed']
    assert manager.check({}, 904, llm_failed=True)['kind'] == 'llm_failure'
    assert manager.check({}, 905, defect=True)['kind'] == 'data_defect'


class Fake:
    chunks = []
    def ask(self, *args):
        return dict(answer='test', status='answered', sources=[], graph=[],
                    raw_model_answer='test', prompt_tokens=10, output_tokens=2)
    def health(self):
        return dict(neo4j='ok', faiss=1, llm='loaded')


def samples(text):
    return {s.name + str(sorted(s.labels.items())): s.value
            for family in text_string_to_metric_families(text) for s in family.samples}


def test_api_counter_error_histogram_tokens_and_scrape_exclusion():
    with TestClient(create_app(Fake())) as client:
        ok = client.post('/ask', json={'question': 'test question'})
        assert ok.status_code == 200
        bad = client.post('/ask', json={'question': 'x'})
        assert bad.status_code == 422
        text = client.get('/metrics').text
        first = samples(text)
        assert first == samples(client.get('/metrics').text)
        assert 'lab14_requests_total{route="/ask",status="200"} 1.0' in text
        assert 'lab14_errors_total{route="/ask",status="422"} 1.0' in text
        assert 'lab14_latency_seconds_count{route="/ask"} 2.0' in text
        assert 'lab14_tokens_total{kind="input"} 10.0' in text
        assert 'lab14_tokens_total{kind="output"} 2.0' in text
        assert ok.headers['x-request-id'] == ok.json()['request_id']


def test_failure_is_observed_and_redacted():
    class Broken(Fake):
        def ask(self, *args):
            raise RuntimeError('do not expose secret')
    with TestClient(create_app(Broken())) as client:
        r = client.post('/ask', json={'question': 'test question'})
        assert r.status_code == 503 and 'secret' not in r.text
        assert 'lab14_errors_total{route="/ask",status="503"} 1.0' in client.get('/metrics').text


def test_constant_reference_changes_are_detected():
    x = np.ones(3000)
    assert psi(x, x) == 0
    assert psi(x, x + 1) > .25
    assert psi(x, x - 1) > .25
