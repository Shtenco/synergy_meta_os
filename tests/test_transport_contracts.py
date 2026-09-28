from runtime.transport_contracts import require_transport_delivery
import pytest

def test_authenticated_transport_is_accepted():
    require_transport_delivery({"authenticated":True,"content_sha256":"1"*64,"route":["a","b"]})

def test_unauthenticated_transport_fails():
    with pytest.raises(ValueError): require_transport_delivery({"authenticated":False,"content_sha256":"1"*64,"route":["a","b"]})
