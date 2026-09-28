from runtime.hardware_model_contracts import consume_hardware_model
import pytest

def test_hardware_model_is_not_measured_silicon():
    x=consume_hardware_model({"model_id":"x","model_status":"MODEL_NOT_SILICON","config_sha256":"1"*64,"eml_primitives_per_s":1,"hbm_bytes_per_s":1,"measured_silicon":False,"deployment_authority":False})
    assert x["measured_silicon"] is False

def test_model_cannot_self_promote():
    with pytest.raises(ValueError):
        consume_hardware_model({"model_id":"x","model_status":"MODEL_NOT_SILICON","config_sha256":"1"*64,"eml_primitives_per_s":1,"hbm_bytes_per_s":1,"measured_silicon":True,"deployment_authority":False})
