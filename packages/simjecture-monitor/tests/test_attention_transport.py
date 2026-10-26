import json
import socket
import threading
import time

import pytest
from simjecture_monitor.attention_transport import relay


def test_lost_reply_is_replayed_identically_without_logging_credentials(tmp_path):
    path = tmp_path / "upstream.sock"
    requests = []
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
        server.bind(str(path))
        server.listen(2)
        server.settimeout(2)

        def run():
            for index in range(2):
                client, _ = server.accept()
                with client:
                    requests.append(client.makefile("rb").readline())
                    if index:
                        client.sendall(b'{"prediction":"same-seeded-result"}\n')

        worker = threading.Thread(target=run)
        worker.start()
        payload = b'{"policy":"base","seed":19,"auth_token":"private-secret"}\n'
        response, receipt = relay(
            payload, path, deadline=time.monotonic() + 2, retry_delay=0.01
        )
        worker.join(timeout=2)
    assert not worker.is_alive()
    assert requests == [payload, payload]
    assert json.loads(response) == {"prediction": "same-seeded-result"}
    assert receipt["send_attempts"] == 2
    assert "private-secret" not in json.dumps(receipt)


def test_application_error_is_returned_once(tmp_path):
    path = tmp_path / "upstream.sock"
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
        server.bind(str(path))
        server.listen(1)
        server.settimeout(2)

        def run():
            client, _ = server.accept()
            with client:
                client.makefile("rb").readline()
                client.sendall(b'{"error":"Checkpoint mismatch"}\n')

        worker = threading.Thread(target=run)
        worker.start()
        response, receipt = relay(b'{"policy":"base"}\n', path, deadline=time.monotonic() + 2)
        worker.join(timeout=2)
    assert json.loads(response) == {"error": "Checkpoint mismatch"}
    assert receipt["send_attempts"] == 1


def test_absent_link_expires_without_an_inference(tmp_path):
    started = time.monotonic()
    response, receipt = relay(
        b'{"operation":"health"}\n',
        tmp_path / "absent.sock",
        deadline=started + 0.05,
        retry_delay=0.01,
    )
    assert "error" in json.loads(response)
    assert receipt["send_attempts"] == 0
    assert receipt["status"] == "unavailable"
    assert time.monotonic() - started < 1


@pytest.mark.parametrize("payload", [b'{"operation":"dispatch"}\n', b'{}', b'[]\n'])
def test_non_inference_or_unframed_requests_are_rejected(tmp_path, payload):
    with pytest.raises(ValueError):
        relay(payload, tmp_path / "absent.sock", deadline=time.monotonic() + 1)


def test_link_can_appear_after_client_request(tmp_path):
    path = tmp_path / "recovering.sock"

    def restore_link():
        time.sleep(0.05)
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
            server.bind(str(path))
            server.listen(1)
            server.settimeout(2)
            client, _ = server.accept()
            with client:
                client.makefile("rb").readline()
                client.sendall(b'{"status":"ready"}\n')

    worker = threading.Thread(target=restore_link)
    worker.start()
    response, receipt = relay(
        b'{"operation":"health"}\n', path, deadline=time.monotonic() + 2, retry_delay=0.01
    )
    worker.join(timeout=2)
    assert not worker.is_alive()
    assert json.loads(response) == {"status": "ready"}
    assert receipt["connect_attempts"] > 1
    assert receipt["send_attempts"] == 1


def test_lost_reply_uses_connected_standby_without_a_new_primary_handshake(tmp_path):
    paths = [tmp_path / "primary.sock", tmp_path / "standby.sock"]
    requests = []
    servers = []
    for path in paths:
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(path))
        server.listen(1)
        server.settimeout(2)
        servers.append(server)

    def run(index):
        with servers[index]:
            client, _ = servers[index].accept()
            with client:
                requests.append((index, client.makefile("rb").readline()))
                if index == 1:
                    client.sendall(b'{"prediction":"same-frozen-model"}\n')

    workers = [threading.Thread(target=run, args=(i,)) for i in range(2)]
    for worker in workers:
        worker.start()
    payload = b'{"policy":"continued_sft","seed":17}\n'
    response, receipt = relay(payload, paths, deadline=time.monotonic() + 2)
    for worker in workers:
        worker.join(timeout=2)
        assert not worker.is_alive()
    assert requests == [(0, payload), (1, payload)]
    assert json.loads(response) == {"prediction": "same-frozen-model"}
    assert receipt["returned_link_index"] == 1
    assert receipt["send_attempts"] == 2
