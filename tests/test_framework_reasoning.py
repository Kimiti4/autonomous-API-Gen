from tiannara.application.framework_knowledge import FrameworkKnowledgeClaim, FrameworkKnowledgePack
from tiannara.application.framework_reasoning import FrameworkNeed, assess_framework, rank_frameworks

def test_unknown_framework_need_is_not_assumed():
    pack=FrameworkKnowledgePack("x","x",("1",),(),{"latency":"strong"},(),(),())
    a=assess_framework(pack,[FrameworkNeed("realtime",1.0,"needed")])
    assert a.unknown_needs==("realtime",)
    assert a.score==0.0

def test_framework_selection_is_evidence_bounded():
    packs=[
      FrameworkKnowledgePack("a","x",("1",),(),{"realtime":"strong"},(),(),()),
      FrameworkKnowledgePack("b","x",("1",),(),{"realtime":"partial"},(),(),()),
    ]
    ranked=rank_frameworks(packs,[FrameworkNeed("realtime",1.0,"needed")])
    assert ranked[0].framework_id=="a"
    assert ranked[0].score==1.0

def test_claims_are_provenance_bearing():
    claim=FrameworkKnowledgeClaim("c","statement","official_docs","ref")
    assert claim.source_kind=="official_docs"
