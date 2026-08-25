"""44.3 Candidate Generation -- 5 families."""
def generate_candidates(intent_semantics: dict) -> dict:
    return {
        "semantic": ["BoatLink","MarineRide"],
        "metaphorical": ["Tide","Harbor","Wake"],
        "constructed": ["Navora","Marivo","Nautra"],
        "compound": ["TideRide","HarborHop","NaviDock"],
        "technical": ["MarineMesh","FleetFlow"],
    }
