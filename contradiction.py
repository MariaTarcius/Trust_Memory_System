from src.models import Claim
from src.agents.base_agent import BaseAgent
from src.claim_logic import detect_conflict, is_corroboration, merge_conflict_with_llm


class ContradictionAgent(BaseAgent):
    def process(self, verified_data: dict) -> dict:
        claim: Claim = verified_data["claim"]
        duplicate_of = verified_data["duplicate_of"]
        corroborates = verified_data.get("corroborates")
        matching_memory = verified_data.get("matching_memory")

        if duplicate_of or corroborates:
            return {
                "verified_data": verified_data,
                "contradictions": [],
                "has_conflicts": False,
            }

        contradictions = []

        active_mems = self.memory.get_all_active()
        for mem in active_mems:
            if mem.subject.lower() != claim.subject.lower():
                continue
            if mem.predicate.lower() != claim.predicate.lower():
                continue
            if not mem.object or not claim.object:
                continue

            rule_result = detect_conflict(mem.object, claim.object)
            if rule_result.get("type") == "CORROBORATION" or is_corroboration(mem.object, claim.object):
                verified_data["corroborates"] = mem
                self.log(f"Corroboration detected for {claim.id} against memory '{mem.object}'")
                return {
                    "verified_data": verified_data,
                    "contradictions": [],
                    "has_conflicts": False,
                }

            llm_result = self.llm.detect_contradiction(
                f"{mem.subject} {mem.predicate} {mem.object}",
                f"{claim.subject} {claim.predicate} {claim.object}",
            )
            conflict_res = merge_conflict_with_llm(rule_result, llm_result)

            if conflict_res.get("is_contradiction", False):
                contradictions.append({
                    "memory_entry": mem,
                    "type": conflict_res.get("type", "VALUE_CONFLICT"),
                    "explanation": conflict_res.get("explanation", "Detected conflict"),
                })
                self.log(
                    f"Contradiction detected for {claim.id}: "
                    f"{conflict_res.get('type')} ({conflict_res.get('explanation')})"
                )

        if not contradictions and matching_memory and claim.object and matching_memory.object:
            rule_result = detect_conflict(matching_memory.object, claim.object)
            if rule_result.get("is_contradiction", False):
                contradictions.append({
                    "memory_entry": matching_memory,
                    "type": rule_result.get("type", "VALUE_CONFLICT"),
                    "explanation": rule_result.get("explanation", "Detected conflict"),
                })
                self.log(
                    f"Late contradiction detected for {claim.id} against matching memory "
                    f"({rule_result.get('type')})"
                )

        return {
            "verified_data": verified_data,
            "contradictions": contradictions,
            "has_conflicts": len(contradictions) > 0,
        }
