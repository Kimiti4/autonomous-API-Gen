from app.engine.compiler_graph import *

def a(i,layer,kind,target=None):
    return CompilerArtifact(i,layer,kind,"ISR" if layer!="implementation" else "compiler",target)

def test_graph_validates_cross_layer_dependencies():
    g=ArtifactGraph(
        (a("arch","architecture","service"),
         a("be","backend-ir","service"),
         a("api","implementation","api","python-fastapi")),
        (ArtifactDependency("arch","be","compiles-to"),
         ArtifactDependency("be","api","implements")),
    )
    assert validate_graph(g)==()

def test_downstream_impact_traverses_compiler_and_implementation_layers():
    g=ArtifactGraph(
        (a("arch","architecture","service"),
         a("be","backend-ir","service"),
         a("api","implementation","api","python-fastapi"),
         a("test","verification","contract-test")),
        (ArtifactDependency("arch","be","compiles-to"),
         ArtifactDependency("be","api","implements"),
         ArtifactDependency("api","test","verified-by")),
    )
    impacted=downstream_impact(g,("arch",))
    assert [x.artifact_id for x in impacted]==["be","api","test"]

def test_missing_dependencies_are_rejected():
    g=ArtifactGraph((a("a","architecture","x"),),
                    (ArtifactDependency("a","missing","x"),))
    assert "unknown-downstream:missing" in validate_graph(g)

def test_isr_artifacts_cannot_be_technology_bound():
    g=ArtifactGraph((a("arch","architecture","service","postgresql"),),())
    assert not technology_neutral(g)
