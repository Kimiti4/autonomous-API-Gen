from app.engine.multi_objective_optimization import *
def c(i,q,l,g=True,cur=True,find=()): return MultiObjectiveCandidate(i,ArchitectureScore(i,{"quality":q,"latency":l},("e",)),g,cur,find)
def o(): return (Objective("quality","maximize"),Objective("latency","minimize"))
def test_frontier(): assert set(evaluate_multi_objective((c("a",10,100),c("b",8,80),c("x",7,120)),o()).frontier)=={"a","b"}
def test_ineligible(): assert evaluate_multi_objective((c("a",10,100),c("b",20,50,False)),o()).ineligible==("b",)
def test_no_evidence(): assert evaluate_multi_objective((MultiObjectiveCandidate("a",ArchitectureScore("a",{"quality":1,"latency":1},()),True,True),),o()).status=="ineligible-all"
def test_missing_objective():
 x=MultiObjectiveCandidate("a",ArchitectureScore("a",{"quality":1},("e",)),True,True)
 try: evaluate_multi_objective((x,),o())
 except ValueError as e: assert str(e)=="missing-or-nonnumeric-objective"
 else: assert False
def test_boolean_objective():
 x=MultiObjectiveCandidate("a",ArchitectureScore("a",{"quality":True,"latency":1},("e",)),True,True)
 try: evaluate_multi_objective((x,),o())
 except ValueError as e: assert str(e)=="missing-or-nonnumeric-objective"
 else: assert False
def test_invalid_direction():
 try: evaluate_multi_objective((c("a",1,1),),(Objective("quality","bad"),))
 except ValueError as e: assert str(e)=="invalid-objective-direction"
 else: assert False
