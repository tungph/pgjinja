import logging
from functools import cache
from pathlib import Path

from pydantic import BaseModel

logger = logging.getLogger(__name__)


@cache
def read_template(file: Path) -> str:
    return file.read_text(encoding="utf8")


@cache
def get_model_fields(model: type(BaseModel)) -> str:
    if not issubclass(model, BaseModel):
        raise TypeError(f"{model} is not a subclass of pydantic.BaseModel")

    fields = []
    for name, field_info in model.model_fields.items():
        if alias := field_info.validation_alias:
            fields.append(alias)
        else:
            fields.append(name)
    return ", ".join(fields)
