from typing import LiteralString, Any

from pydantic import BaseModel


class PgModel(BaseModel):
    __table_name__: str = ''

    def save(self, on_conflict: LiteralString['do nothing', 'do update'] = 'do update'):
        pass

    def delete(self):
        pass

    @classmethod
    def select(cls, limit: int=0, offset: int=0, where:dict[str, Any]=None):
        pass

    @classmethod
    def get_table_name(cls)->str:
        return cls.__table_name__ or cls.__name__.lower()
