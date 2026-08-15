// A. View the complete MVP graph.
MATCH (source)-[relationship]->(target)
WHERE type(relationship) IN ['MITIGATES', 'OBSERVED_AS']
RETURN source, relationship, target;

// B. Find controls that mitigate one risk. Parameter: $risk_id.
MATCH (control:KiemSoat)-[relationship:MITIGATES]->(risk:RuiRo {id: $risk_id})
RETURN control.id AS control_id, control.name AS control,
       relationship.evidence_quote AS evidence_quote,
       relationship.verification_status AS verification_status,
       risk.id AS risk_id, risk.name AS risk;

// C. Find events observed for one risk. Parameter: $risk_id.
MATCH (risk:RuiRo {id: $risk_id})-[relationship:OBSERVED_AS]->(event:SuKienRuiRo)
RETURN risk.id AS risk_id, risk.name AS risk,
       relationship.evidence_quote AS evidence_quote,
       relationship.verification_status AS verification_status,
       event.id AS event_id, event.name AS event;

// D. Find Control -> Risk -> Risk Event paths.
MATCH path = (control:KiemSoat)-[:MITIGATES]->(risk:RuiRo)-[:OBSERVED_AS]->(event:SuKienRuiRo)
RETURN path;

// E. Find risks that have no mitigating control.
MATCH (risk:RuiRo)
WHERE NOT EXISTS { MATCH (:KiemSoat)-[:MITIGATES]->(risk) }
RETURN risk.id AS risk_id, risk.name AS risk
ORDER BY risk.id;

// F. Find relationships that are not VERIFIED.
MATCH (source)-[relationship]->(target)
WHERE type(relationship) IN ['MITIGATES', 'OBSERVED_AS']
  AND coalesce(relationship.verification_status, '') <> 'VERIFIED'
RETURN source.id AS source_id, type(relationship) AS relationship_type,
       target.id AS target_id,
       relationship.verification_status AS verification_status,
       relationship.evidence_quote AS evidence_quote;