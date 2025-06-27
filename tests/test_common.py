import tempfile
from pathlib import Path

import pytest
from pydantic import BaseModel, Field

from pgjinja.shared.common import get_model_fields, read_template


class TestReadTemplate:
    def test_template_reading_success(self):
        """Test that read_template correctly reads SQL template files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_path = Path(tmpdir) / "test.sql"
            template_content = "SELECT * FROM users WHERE id = {{ user_id }}"
            template_path.write_text(template_content, encoding="utf-8")

            result = read_template(template_path)

            assert result == template_content

    def test_template_reading_with_utf8_characters(self):
        """Test that read_template handles UTF-8 characters correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_path = Path(tmpdir) / "unicode.sql"
            template_content = "SELECT * FROM café WHERE naïve = {{ value }}"
            template_path.write_text(template_content, encoding="utf-8")

            result = read_template(template_path)

            assert result == template_content

    def test_template_reading_caching(self):
        """Test that read_template caches results correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_path = Path(tmpdir) / "cached.sql"
            original_content = "SELECT * FROM users"
            template_path.write_text(original_content, encoding="utf-8")

            # First read
            result1 = read_template(template_path)
            assert result1 == original_content

            # Modify file content (but cache should return original)
            template_path.write_text("SELECT * FROM products", encoding="utf-8")

            # Second read should return cached content
            result2 = read_template(template_path)
            assert result2 == original_content  # Should be cached
            assert result1 == result2

    def test_template_reading_file_not_found(self):
        """Test that read_template raises FileNotFoundError for missing files."""
        nonexistent_path = Path("/nonexistent/template.sql")

        with pytest.raises(FileNotFoundError):
            read_template(nonexistent_path)

    def test_template_reading_permission_error(self):
        """Test that read_template handles permission errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_path = Path(tmpdir) / "restricted.sql"
            template_path.write_text("SELECT * FROM users", encoding="utf-8")
            template_path.chmod(0o000)  # Remove all permissions

            try:
                with pytest.raises(PermissionError):
                    read_template(template_path)
            finally:
                # Restore permissions for cleanup
                template_path.chmod(0o644)

    def test_template_reading_complex_sql(self):
        """Test that read_template handles complex SQL templates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_path = Path(tmpdir) / "complex.sql"
            template_content = """
            SELECT 
                u.id,
                u.name,
                u.email,
                COUNT(o.id) as order_count
            FROM users u
            LEFT JOIN orders o ON u.id = o.user_id
            WHERE u.created_at >= {{ start_date }}
            {% if category %}
                AND u.category = {{ category }}
            {% endif %}
            GROUP BY u.id, u.name, u.email
            ORDER BY order_count DESC
            LIMIT {{ limit }}
            """
            template_path.write_text(template_content, encoding="utf-8")

            result = read_template(template_path)

            assert result == template_content
            assert "{{ start_date }}" in result
            assert "{% if category %}" in result


class TestGetModelFields:
    def test_model_field_extraction_simple_model(self, sample_user_model):
        """Test that get_model_fields extracts fields from simple models."""
        result = get_model_fields(sample_user_model)

        assert result == "id, name, email"

    def test_model_field_extraction_with_aliases(self, sample_user_with_alias):
        """Test that get_model_fields handles field aliases correctly."""
        result = get_model_fields(sample_user_with_alias)

        assert result == "id, name, email"

    def test_model_field_extraction_caching(self, sample_user_model):
        """Test that get_model_fields caches results correctly."""
        # First call
        result1 = get_model_fields(sample_user_model)

        # Second call should return cached result
        result2 = get_model_fields(sample_user_model)

        assert result1 == result2
        assert result1 == "id, name, email"

    def test_model_field_extraction_field_order(self):
        """Test that get_model_fields preserves field order."""
        class OrderedModel(BaseModel):
            first_field: str
            second_field: int
            third_field: bool

        result = get_model_fields(OrderedModel)

        assert result == "first_field, second_field, third_field"

    def test_model_field_extraction_mixed_aliases(self):
        """Test that get_model_fields handles mixed aliases and regular fields."""
        class MixedModel(BaseModel):
            id: int
            user_name: str = Field(validation_alias="name")
            email: str
            age: int = Field(validation_alias="user_age")

        result = get_model_fields(MixedModel)

        assert result == "id, name, email, user_age"

    def test_model_field_extraction_non_basemodel_error(self):
        """Test that get_model_fields raises TypeError for non-BaseModel classes."""
        class NotABaseModel:
            id: int
            name: str

        with pytest.raises(TypeError, match="is not a subclass of pydantic.BaseModel"):
            get_model_fields(NotABaseModel)

    def test_model_field_extraction_empty_model(self):
        """Test that get_model_fields handles models with no fields."""
        class EmptyModel(BaseModel):
            pass

        result = get_model_fields(EmptyModel)

        assert result == ""

    def test_model_field_extraction_single_field(self):
        """Test that get_model_fields handles models with single field."""
        class SingleFieldModel(BaseModel):
            single_field: str

        result = get_model_fields(SingleFieldModel)

        assert result == "single_field"

    def test_model_field_extraction_complex_aliases(self):
        """Test that get_model_fields handles various alias types."""
        class ComplexAliasModel(BaseModel):
            field1: str = Field(validation_alias="column_one")
            field2: int = Field(validation_alias="col_2")
            field3: bool  # No alias
            field4: str = Field(validation_alias="special.column")

        result = get_model_fields(ComplexAliasModel)

        assert result == "column_one, col_2, field3, special.column"

    def test_model_field_extraction_inheritance(self):
        """Test that get_model_fields works with model inheritance."""
        class BaseUserModel(BaseModel):
            id: int
            name: str

        class ExtendedUserModel(BaseUserModel):
            email: str
            age: int

        result = get_model_fields(ExtendedUserModel)

        assert result == "id, name, email, age"
