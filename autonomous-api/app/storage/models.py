from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Text
from sqlalchemy.sql import func
from .db import Base


class GenomeRecord(Base):
    """Stores individual genome data"""
    __tablename__ = "genomes"

    id = Column(Integer, primary_key=True, index=True)
    genome_data = Column(JSON)  # Full genome configuration
    fitness_score = Column(Float, default=0.0)
    generation = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def to_dict(self):
        return {
            "id": self.id,
            "genome_data": self.genome_data,
            "fitness_score": self.fitness_score,
            "generation": self.generation,
            "created_at": str(self.created_at) if self.created_at else None
        }


class EvolutionRun(Base):
    """Tracks evolution runs and their metadata"""
    __tablename__ = "evolution_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String, unique=True, index=True)
    status = Column(String, default="running")  # running, completed, failed
    total_generations = Column(Integer, default=0)
    best_fitness = Column(Float, default=0.0)
    best_genome = Column(JSON)
    history = Column(JSON)  # Fitness history per generation
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "run_id": self.run_id,
            "status": self.status,
            "total_generations": self.total_generations,
            "best_fitness": self.best_fitness,
            "best_genome": self.best_genome,
            "history": self.history,
            "started_at": str(self.started_at) if self.started_at else None,
            "completed_at": str(self.completed_at) if self.completed_at else None
        }
