def CompilerBridge(*args, **kwargs):
    from constitutional_architecture.engine.bridges.compiler_bridge import CompilerBridge as _cls
    return _cls(*args, **kwargs)

def VerificationBridge(*args, **kwargs):
    from constitutional_architecture.engine.bridges.verification_bridge import VerificationBridge as _cls
    return _cls(*args, **kwargs)

def FitnessBridge(*args, **kwargs):
    from constitutional_architecture.engine.bridges.fitness_bridge import FitnessBridge as _cls
    return _cls(*args, **kwargs)

def AutonomousPipeline(*args, **kwargs):
    from constitutional_architecture.engine.bridges.autonomous_pipeline import AutonomousPipeline as _cls
    return _cls(*args, **kwargs)

def ProductTopologyResolver(*args, **kwargs):
    from constitutional_architecture.engine.bridges.topology_bridge import ProductTopologyResolver as _cls
    return _cls(*args, **kwargs)

__all__ = [
    "CompilerBridge",
    "VerificationBridge",
    "FitnessBridge",
    "AutonomousPipeline",
    "ProductTopologyResolver",
]
