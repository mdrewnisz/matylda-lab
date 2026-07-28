from __future__ import annotations


def test_secretary_accepts_injected_client():
    from matylda_lite.secretary import Secretary

    client = object()
    secretary = Secretary(client=client)

    assert secretary.client is client
