import pytest
from app.engine.generation_scope import GenerationScope
from app.engine.governed_pipeline import PipelineStage, StageArtifact, execute_governed_pipeline
from app.engine.project_scope import ProjectScope
from app.engine.work_capability import WorkCapabilityContract
from app.engine.work_mode import WorkMode
from app.marketplace.listing import HumanMarketplaceAuthorization
from app.marketplace.productization import prepare_certified_product, materialize_listing

def pipeline():
    c=WorkCapabilityContract.create(ProjectScope.create_new(),WorkMode.CREATE,GenerationScope.FULL_APPLICATION)
    def runner(stage, prior):
        ev=(stage.value+"-evidence",) if stage in {PipelineStage.VERIFICATION,PipelineStage.EVIDENCE,PipelineStage.CERTIFICATION} else ()
        return StageArtifact(stage,stage.value,"a"*64,evidence_ids=ev)
    return execute_governed_pipeline(
        work_id="product-work",contract=c,surface="full_application",
        authoritative_obligation_ids=("req-1",),completed_obligation_ids=("req-1",),
        verification_evidence_complete=True,stage_runner=runner)

def candidate():
    p=pipeline()
    return prepare_certified_product(p,product_id="product-1",version="1.0.0",name="Certified App",
        price_minor=1000,currency="USD",license="standard-commercial",
        certification_digest=p.closure.digest,artifact_digest="a"*64,evidence_digest="b"*64,
        documentation_digest="c"*64)

def auth():
    return HumanMarketplaceAuthorization("auth-1","human-operator","list","product-1","b"*64)

def test_productization_requires_completed_pipeline():
    p=pipeline(); assert candidate().pipeline_digest==p.pipeline_digest

def test_listing_is_materialized_only_from_certified_candidate():
    listing=materialize_listing(candidate())
    assert listing.status.value=="certified"
    assert listing.publish(auth()).status.value=="listed"

def test_certification_mismatch_fails_closed():
    p=pipeline()
    with pytest.raises(ValueError,match="certification-mismatch"):
        prepare_certified_product(p,product_id="x",version="1",name="x",price_minor=0,currency="USD",
            license="x",certification_digest="d"*64,artifact_digest="a"*64,evidence_digest="b"*64,documentation_digest="c"*64)
