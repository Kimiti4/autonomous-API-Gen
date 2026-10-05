from app.engine.evolution_population import (
    ArchitectureLineage,
    EvolutionMember,
    EvolutionPopulation,
)
from app.engine.pareto_architecture import ArchitectureScore, Objective
from app.engine.architecture_pareto_evolution import evolve_architecture_population


OBJECTIVES = (
    Objective("quality", "maximize"),
    Objective("latency", "minimize"),
)


def member(i, q, latency, generation=0, parents=()):
    score = ArchitectureScore(i, {"quality": q, "latency": latency}, ("verified:" + i,))
    lineage = ArchitectureLineage(i, tuple(parents), generation, score.evidence)
    return EvolutionMember(lineage, score)


def test_evolution_retains_pareto_frontier_and_can_admit_tradeoff():
    parent = member("a", 10, 100)
    population = EvolutionPopulation(0, (parent,))
    child = member("b", 9, 80, 1, ("a",))

    result = evolve_architecture_population(population, (child,), OBJECTIVES)

    assert result.next_generation == 1
    assert set(result.population.members[i].lineage.architecture_id for i in range(len(result.population.members))) == {"a", "b"}
    assert result.admitted_ids == ("b",)
    assert result.retained_ids == ("a",)
    assert "single global optimum" in result.rationale


def test_evolution_drops_dominated_offspring_from_frontier():
    parent = member("a", 10, 100)
    population = EvolutionPopulation(0, (parent,))
    child = member("b", 9, 120, 1, ("a",))

    result = evolve_architecture_population(population, (child,), OBJECTIVES)

    assert tuple(m.lineage.architecture_id for m in result.population.members) == ("a",)
    assert result.admitted_ids == ()
    assert result.retained_ids == ("a",)


def test_evolution_rejects_unknown_parent_lineage():
    population = EvolutionPopulation(0, (member("a", 10, 100),))
    child = member("b", 11, 90, 1, ("missing",))

    try:
        evolve_architecture_population(population, (child,), OBJECTIVES)
    except ValueError as exc:
        assert str(exc) == "evolution-lineage-or-evidence-invalid:b"
        return
    assert False


def test_evolution_rejects_wrong_generation():
    population = EvolutionPopulation(2, (member("a", 10, 100, 2),))
    child = member("b", 11, 90, 4, ("a",))

    try:
        evolve_architecture_population(population, (child,), OBJECTIVES)
    except ValueError as exc:
        assert str(exc) == "evolution-lineage-or-evidence-invalid:b"
        return
    assert False


def test_evolution_requires_evidence():
    parent = member("a", 10, 100)
    population = EvolutionPopulation(0, (parent,))
    score = ArchitectureScore("b", {"quality": 11, "latency": 90}, ())
    child = EvolutionMember(
        ArchitectureLineage("b", ("a",), 1, ()),
        score,
    )

    try:
        evolve_architecture_population(population, (child,), OBJECTIVES)
    except ValueError as exc:
        assert str(exc) == "evolution-lineage-or-evidence-invalid:b"
        return
    assert False
