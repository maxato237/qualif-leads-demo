from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

MAX_MESSAGE_CHARS = 2000


class LeadRequest(BaseModel):
    """Formulaire de contact de l'agence fictive."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length=80)
    email: EmailStr = Field(max_length=120)
    company: str = Field(default="", max_length=80)
    message: str = Field(min_length=20, max_length=MAX_MESSAGE_CHARS)
    # Champ piège invisible pour un humain : un robot qui remplit tout se trahit.
    website: str = Field(default="", max_length=200)

    @field_validator("name", "company")
    @classmethod
    def single_line(cls, value: str) -> str:
        # Ces champs finissent dans l'objet d'un email : jamais de retour à la ligne.
        return " ".join(value.split())
