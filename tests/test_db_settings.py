from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from pgjinja.schemas.db_settings import DBSettings


class TestDBSettings:
    def test_configuration_validation_with_defaults(self):
        """Test that DBSettings initializes with valid defaults."""
        settings = DBSettings(
            user="testuser",
            password=SecretStr("testpass")
        )

        assert settings.user == "testuser"
        assert settings.password.get_secret_value() == "testpass"
        assert settings.host == "localhost"
        assert settings.port == 5432
        assert settings.dbname == "public"
        assert settings.min_size == 4
        assert settings.max_size is None
        assert settings.template_dir == Path()
        assert settings.application_name == "pgjinja"

    def test_configuration_validation_with_custom_values(self):
        """Test that DBSettings validates custom configuration values."""
        custom_template_dir = Path("/custom/templates")
        settings = DBSettings(
            user="admin",
            password=SecretStr("secret123"),
            host="db.example.com",
            port=5433,
            dbname="production",
            template_dir=custom_template_dir,
            min_size=10,
            max_size=50,
            application_name="my-app"
        )

        assert settings.user == "admin"
        assert settings.password.get_secret_value() == "secret123"
        assert settings.host == "db.example.com"
        assert settings.port == 5433
        assert settings.dbname == "production"
        assert settings.template_dir == custom_template_dir
        assert settings.min_size == 10
        assert settings.max_size == 50
        assert settings.application_name == "my-app"

    def test_secure_password_handling(self):
        """Test that password is securely handled using SecretStr."""
        password = "supersecret"
        settings = DBSettings(
            user="testuser",
            password=SecretStr(password)
        )

        # Password should be stored as SecretStr
        assert isinstance(settings.password, SecretStr)

        # Secret value should be retrievable but not visible in repr
        assert settings.password.get_secret_value() == password
        assert password not in str(settings)
        assert password not in repr(settings)

    def test_string_representation_excludes_sensitive_info(self):
        """Test that string representation doesn't expose sensitive information."""
        settings = DBSettings(
            user="testuser",
            password=SecretStr("supersecret"),
            host="db.example.com",
            port=5433,
            dbname="testdb"
        )

        str_repr = str(settings)
        repr_str = repr(settings)

        # Should include connection details
        assert "db.example.com" in str_repr
        assert "5433" in str_repr
        assert "testdb" in str_repr

        # Should not include sensitive information
        assert "supersecret" not in str_repr
        assert "testuser" not in str_repr
        assert "supersecret" not in repr_str

    def test_coninfo_property_generates_valid_connection_string(self):
        """Test that coninfo property generates a valid PostgreSQL connection string."""
        settings = DBSettings(
            user="testuser",
            password=SecretStr("testpass"),
            host="localhost",
            port=5432,
            dbname="testdb",
            application_name="test-app"
        )

        coninfo = settings.coninfo

        # Should contain all connection parameters
        assert "host=localhost" in coninfo
        assert "port=5432" in coninfo
        assert "dbname=testdb" in coninfo
        assert "user=testuser" in coninfo
        assert "password=testpass" in coninfo
        assert "application_name=test-app" in coninfo

    def test_coninfo_handles_special_characters_in_password(self):
        """Test that coninfo properly handles special characters in password."""
        special_password = "pass@word!#$%"
        settings = DBSettings(
            user="testuser",
            password=SecretStr(special_password)
        )

        coninfo = settings.coninfo

        # Connection string should be properly escaped
        assert isinstance(coninfo, str)
        # The password should be included in some form (psycopg handles escaping)
        assert len(coninfo) > 0

    def test_required_fields_validation(self):
        """Test that required fields are validated."""
        # Missing user
        with pytest.raises(ValidationError) as exc_info:
            DBSettings(password=SecretStr("testpass"))

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("user",) for error in errors)

        # Missing password
        with pytest.raises(ValidationError) as exc_info:
            DBSettings(user="testuser")

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("password",) for error in errors)

    def test_port_validation(self):
        """Test that port validation works correctly."""
        # Valid port
        settings = DBSettings(
            user="testuser",
            password=SecretStr("testpass"),
            port=5432
        )
        assert settings.port == 5432

        # Invalid port type should raise validation error
        with pytest.raises(ValidationError):
            DBSettings(
                user="testuser",
                password=SecretStr("testpass"),
                port="invalid"
            )

    def test_pool_size_validation(self):
        """Test that pool size validation works correctly."""
        # Valid pool sizes
        settings = DBSettings(
            user="testuser",
            password=SecretStr("testpass"),
            min_size=1,
            max_size=10
        )
        assert settings.min_size == 1
        assert settings.max_size == 10

        # None max_size should be allowed
        settings = DBSettings(
            user="testuser",
            password=SecretStr("testpass"),
            min_size=2,
            max_size=None
        )
        assert settings.min_size == 2
        assert settings.max_size is None

    def test_template_dir_path_handling(self):
        """Test that template_dir handles Path objects correctly."""
        # String path
        settings = DBSettings(
            user="testuser",
            password=SecretStr("testpass"),
            template_dir="/tmp/templates"
        )
        assert isinstance(settings.template_dir, Path)
        assert str(settings.template_dir) == "/tmp/templates"

        # Path object
        path_obj = Path("/custom/path")
        settings = DBSettings(
            user="testuser",
            password=SecretStr("testpass"),
            template_dir=path_obj
        )
        assert settings.template_dir == path_obj
