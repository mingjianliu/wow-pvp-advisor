import os
import pytest
from unittest.mock import patch
from wow_advisor.config import load_config, has_credentials, setup_credentials

def test_load_config(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("KEY1=VAL1\n# Comment\n KEY2 = VAL2 \n")
    
    with patch("wow_advisor.config.get_config_path", return_value=env_file), \
         patch.dict(os.environ, {}, clear=True):
        load_config()
        assert os.environ["KEY1"] == "VAL1"
        assert os.environ["KEY2"] == "VAL2"

def test_has_credentials():
    # We need to mock load_config because has_credentials calls it
    with patch("wow_advisor.config.load_config"):
        with patch.dict(os.environ, {"BNET_CLIENT_ID": "id", "BNET_CLIENT_SECRET": "secret"}):
            assert has_credentials() is True
            
        with patch.dict(os.environ, {}, clear=True):
            assert has_credentials() is False

def test_setup_credentials_success(tmp_path):
    env_file = tmp_path / "config.env"
    # Ensure it doesn't exist yet
    if env_file.exists():
        env_file.unlink()
        
    with patch("wow_advisor.config.get_config_path", return_value=env_file), \
         patch("builtins.input", side_effect=["my_id", "my_secret"]), \
         patch.dict(os.environ, {}, clear=True):
        setup_credentials()
        assert os.environ["BNET_CLIENT_ID"] == "my_id"
        assert os.environ["BNET_CLIENT_SECRET"] == "my_secret"
        content = env_file.read_text()
        assert "BNET_CLIENT_ID=my_id" in content
        assert "BNET_CLIENT_SECRET=my_secret" in content

def test_setup_credentials_missing_input(tmp_path):
    env_file = tmp_path / "config.env"
    with patch("wow_advisor.config.get_config_path", return_value=env_file), \
         patch("builtins.input", side_effect=["", ""]), \
         patch.dict(os.environ, {}, clear=True):
        with pytest.raises(SystemExit):
            setup_credentials()

def test_setup_credentials_already_configured():
    with patch.dict(os.environ, {"BNET_CLIENT_ID": "id", "BNET_CLIENT_SECRET": "secret"}):
        with patch("builtins.input") as mock_input:
            setup_credentials()
            mock_input.assert_not_called()
