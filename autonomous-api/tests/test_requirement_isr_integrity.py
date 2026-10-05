from app.engine.requirement_isr_integrity import validate_isr_integrity
from app.engine.requirement_isr import EngineeringISR,EngineeringEntity

def base():
 return EngineeringISR("v",("R-1",),(EngineeringEntity("E-1",("R-1",),"entity","account"),),(),(),(),{"R-1":{}})
def test_valid_isr():
 assert validate_isr_integrity(base()).valid
def test_dangling_source_fails():
 x=base()
 x=EngineeringISR(x.schema_version,x.source_requirement_ids,(EngineeringEntity("E-1",("R-X",),"entity","account"),),x.invariants,x.policies,x.interfaces,x.traceability)
 assert not validate_isr_integrity(x).valid
def test_technology_leak_fails():
 x=base()
 x=EngineeringISR(x.schema_version,x.source_requirement_ids,(EngineeringEntity("E-1",("R-1",),"entity","PostgreSQL"),),x.invariants,x.policies,x.interfaces,x.traceability)
 assert "technology-leak:entities:E-1" in validate_isr_integrity(x).errors
