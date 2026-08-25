#!/usr/bin/env python3
"""
Quick test script to verify the evolution engine works correctly.
Run this after installing dependencies.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all modules can be imported"""
    print("🧪 Testing imports...")
    
    try:
        from app.engine.genome import Genome
        print("  ✓ Genome module")
        
        from app.core.population import Population
        print("  ✓ Population module")
        
        from app.core.crossover import crossover
        print("  ✓ Crossover module")
        
        from app.core.mutation import mutate
        print("  ✓ Mutation module")
        
        from app.engine.fitness import calculate_fitness
        print("  ✓ Fitness module")
        
        from app.engine.security import calculate_security_score
        print("  ✓ Security module")
        
        from app.engine.builder import build_genome_output
        print("  ✓ Builder module")
        
        from app.engine.evolution import EvolutionEngine
        print("  ✓ Evolution engine")
        
        from app.storage.db import init_db
        print("  ✓ Database module")
        
        return True
    except Exception as e:
        print(f"  ✗ Import failed: {e}")
        return False


def test_genome_creation():
    """Test genome creation and encoding"""
    print("\n🧬 Testing genome creation...")
    
    from app.engine.genome import Genome
    
    # Create random genome
    genome = Genome()
    print(f"  Created genome: {genome}")
    
    # Encode
    encoded = genome.encode()
    print(f"  Encoded keys: {list(encoded.keys())}")
    
    # Create from data
    genome2 = Genome(genome_data=encoded)
    print(f"  Decoded genome: {genome2}")
    
    print("  ✓ Genome creation works")
    return True


def test_fitness_evaluation():
    """Test fitness calculation"""
    print("\n📊 Testing fitness evaluation...")
    
    from app.engine.genome import Genome
    from app.engine.fitness import calculate_fitness
    
    # Test with different genomes
    genome1 = Genome()
    fitness1 = calculate_fitness(genome1)
    print(f"  Random genome fitness: {fitness1:.3f}")
    
    # Create a high-quality genome
    good_genome = Genome(genome_data={
        "services": ["auth", "users", "payments"],
        "auth": "jwt",
        "database": "postgres",
        "cache_enabled": True,
        "rate_limiting": True,
        "cors_enabled": True,
        "logging_level": "INFO",
        "api_version": "v2",
        "security_score": 1.0
    })
    fitness2 = calculate_fitness(good_genome)
    print(f"  Good genome fitness: {fitness2:.3f}")
    
    if fitness2 > fitness1:
        print("  ✓ Fitness evaluation distinguishes quality")
    else:
        print("  ⚠ Fitness scores unexpected")
    
    return True


def test_code_generation():
    """Test API code generation"""
    print("\n🏗️ Testing code generation...")
    
    from app.engine.genome import Genome
    from app.engine.builder import build_genome_output
    import os
    
    genome = Genome()
    output_path = build_genome_output(genome, "output/test_api")
    
    # Check files were created
    expected_files = [
        "main.py",
        "requirements.txt",
        "Dockerfile",
        "README.md",
        "services/__init__.py"
    ]
    
    for file in expected_files:
        full_path = os.path.join(output_path, file)
        if os.path.exists(full_path):
            print(f"  ✓ {file}")
        else:
            print(f"  ✗ {file} missing")
            return False
    
    print(f"  Generated at: {output_path}")
    print("  ✓ Code generation works")
    return True


async def test_evolution_run():
    """Test a small evolution run"""
    print("\n🚀 Testing evolution run (3 generations)...")
    
    from app.engine.evolution import EvolutionEngine
    
    engine = EvolutionEngine()
    result = engine.run_synchronous(
        generations=3,
        population_size=6,
        use_docker=False
    )
    
    print(f"  Completed {result['total_generations']} generations")
    print(f"  Best fitness: {result['best_fitness']:.3f}")
    print(f"  Output path: {result['output_path']}")
    
    if result['history']:
        print(f"  History entries: {len(result['history'])}")
        for h in result['history']:
            print(f"    Gen {h['generation']}: best={h['best_score']:.3f}, avg={h['avg_score']:.3f}")
    
    print("  ✓ Evolution run successful")
    return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("🧬 Autonomous Evolution Engine - Test Suite")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Genome Creation", test_genome_creation),
        ("Fitness Evaluation", test_fitness_evaluation),
        ("Code Generation", test_code_generation),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n✗ {name} failed with error: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Async test
    try:
        success = asyncio.run(test_evolution_run())
        results.append(("Evolution Run", success))
    except Exception as e:
        print(f"\n✗ Evolution Run failed with error: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Evolution Run", False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! System is ready.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
