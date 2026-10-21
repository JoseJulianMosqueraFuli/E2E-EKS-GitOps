from unittest.mock import Mock

import pandas as pd
import pytest

from src.pipelines import validation


@pytest.mark.parametrize('failure', ['missing-target', 'null-target', 'duplicate', 'infinity', 'null-feature', None])
def test_data_validation_rejects_bad_data_without_publishing(monkeypatch, failure):
    frame = pd.DataFrame({'feature': range(100), 'target': [0, 1] * 50})
    if failure == 'missing-target':
        frame = frame.drop(columns='target')
    elif failure == 'null-target':
        frame.loc[0, 'target'] = None
    elif failure == 'duplicate':
        frame = pd.concat([frame, frame])
    elif failure == 'infinity':
        frame.loc[0, 'feature'] = float('inf')
    elif failure == 'null-feature':
        frame.loc[:20, 'feature'] = None
    monkeypatch.setattr(validation, 'read_table', lambda uri: frame)
    publish = Mock()
    monkeypatch.setattr(validation, 'write_table', publish)
    if failure:
        with pytest.raises(ValueError):
            validation.validate_data('input.csv', 'output', 'target', 'production')
        publish.assert_not_called()
    else:
        result = validation.validate_data('input.csv', 'output', 'target', 'production')
        assert result['rows'] == 100 and result['data_uri'].endswith('/data.parquet')
        assert len(result['sha256']) == 64
        pd.testing.assert_frame_equal(publish.call_args.args[0], frame)


@pytest.mark.parametrize('response', [{'metadata': 'only'}, {'predictions': [1]}, {'predictions': [None, 1]}, {'predictions': [0, 1]}])
def test_inference_validation_checks_prediction_contract(monkeypatch, response):
    monkeypatch.setattr(validation, 'read_table', lambda uri: pd.DataFrame({'feature': [1, 2], 'target': [0, 1]}))
    monkeypatch.setattr(validation.time, 'monotonic', Mock(side_effect=[0, 0, 2]))
    monkeypatch.setattr(validation.time, 'sleep', lambda seconds: None)
    post = Mock(return_value=Mock(json=lambda: response))
    monkeypatch.setattr(validation.requests, 'post', post)
    if response == {'predictions': [0, 1]}:
        validation.validate_deployment('http://service/invocations', 'data.csv', 'target', timeout=1)
    else:
        with pytest.raises(RuntimeError):
            validation.validate_deployment('http://service/invocations', 'data.csv', 'target', timeout=1)
    assert post.call_args.kwargs['json']['dataframe_split']['columns'] == ['feature']


def test_notification_without_webhook_is_local(monkeypatch):
    monkeypatch.delenv('SLACK_WEBHOOK_URL', raising=False)
    post = Mock()
    monkeypatch.setattr(validation.requests, 'post', post)
    validation.notify_pipeline('model', '1', 'Succeeded')
    post.assert_not_called()
