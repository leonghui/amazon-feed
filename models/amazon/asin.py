from typing import Annotated
from pydantic import AfterValidator, BaseModel

from models.validators import validate_asin


class Asin(BaseModel):
    id: Annotated[str, AfterValidator(func=validate_asin)]
