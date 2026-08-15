from pydantic import BaseModel, Field


class IntentSpecification(BaseModel):
    statement: str
    domain: str
    complexity_tier: str = "medium"
    capabilities: list[str] = Field(default_factory=list)
    constraints: dict[str, str] = Field(default_factory=dict)
