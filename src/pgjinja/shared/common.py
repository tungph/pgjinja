import logging
from functools import cache
from pathlib import Path

from pydantic import BaseModel

logger = logging.getLogger(__name__)


@cache
def read_template(file: Path) -> str:
    """Read and cache the contents of a SQL template file.

    Reads a text file containing SQL template content and caches the result
    using functools.cache to avoid repeated file I/O operations. The file
    is read with UTF-8 encoding for proper character handling.

    Args:
        file: Path object pointing to the template file to read.

    Returns:
        str: The complete content of the template file as a string.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        PermissionError: If the file cannot be read due to permissions.
        UnicodeDecodeError: If the file contains invalid UTF-8 content.

    Examples:
        Basic usage:

        >>> from pathlib import Path
        >>> template_path = Path("./templates/users.sql")
        >>> content = read_template(template_path)
        >>> print(content)
        SELECT * FROM users WHERE id = {{ user_id }}

        Subsequent calls return cached content:

        >>> # This call uses cached content, no file I/O
        >>> cached_content = read_template(template_path)
        >>> assert content == cached_content

    Notes:
        - Results are cached indefinitely using functools.cache
        - Cache is based on the file Path object, not file content
        - File modifications won't be detected once cached
        - Use UTF-8 encoding for all template files
    """
    return file.read_text(encoding="utf8")


@cache
def get_model_fields(model: type(BaseModel)) -> str:
    """Extract field names from a Pydantic model for SQL template use.

    Generates a comma-separated string of field names from a Pydantic BaseModel
    class. This function respects field aliases defined with validation_alias
    and is designed to populate the `_model_fields_` variable in SQL templates.
    Results are cached for performance.

    Args:
        model: A Pydantic BaseModel subclass from which to extract field names.

    Returns:
        str: Comma-separated field names suitable for SQL SELECT statements.
            Uses validation_alias when available, otherwise uses field name.

    Raises:
        TypeError: If the provided model is not a Pydantic BaseModel subclass.

    Examples:
        Simple model without aliases:

        >>> from pydantic import BaseModel
        >>> class User(BaseModel):
        ...     id: int
        ...     name: str
        ...     email: str
        >>> fields = get_model_fields(User)
        >>> print(fields)
        id, name, email

        Model with field aliases:

        >>> from pydantic import BaseModel, Field
        >>> class UserWithAlias(BaseModel):
        ...     user_id: int = Field(validation_alias="id")
        ...     user_name: str = Field(validation_alias="name")
        >>> fields = get_model_fields(UserWithAlias)
        >>> print(fields)
        id, name

        Usage in SQL templates:

        >>> # In template file: SELECT {{ _model_fields_ }} FROM users
        >>> # Renders as: SELECT id, name, email FROM users

    Notes:
        - Results are cached indefinitely using functools.cache
        - Validation aliases take precedence over field names
        - Field order matches the order defined in the model
        - Designed specifically for SQL SELECT statement generation
    """
    if not issubclass(model, BaseModel):
        raise TypeError(f"{model} is not a subclass of pydantic.BaseModel")

    fields = []
    for name, field_info in model.model_fields.items():
        if alias := field_info.validation_alias:
            fields.append(alias)
        else:
            fields.append(name)
    return ", ".join(fields)
