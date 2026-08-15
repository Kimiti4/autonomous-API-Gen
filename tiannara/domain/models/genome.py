import enum
import uuid
from pydantic import BaseModel, Field


class ChromosomeFamily(str, enum.Enum):
    ARCHITECTURE = "architecture"
    PERSISTENCE = "persistence"
    SECURITY = "security"
    MESSAGING = "messaging"
    OBSERVABILITY = "observability"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    PERFORMANCE = "performance"
    RELIABILITY = "reliability"


class Gene(BaseModel):
    chromosome: ChromosomeFamily
    name: str
    allele: str


class Genome(BaseModel):
    genome_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    generation: int = 0
    genes: list[Gene] = Field(default_factory=list)

    def genes_for(self, family: ChromosomeFamily) -> list[Gene]:
        return [g for g in self.genes if g.chromosome == family]
