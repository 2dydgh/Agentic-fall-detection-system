% 이 파일은 schema.py 가 ontology.ttl 로부터 생성했습니다.
% 직접 수정하지 마십시오. ontology.ttl 을 고치고 재생성하십시오.

:- dynamic is_a/2.

is_a(adult, person).
is_a(alert_action, response_action).
is_a(balcony, high_risk_zone).
is_a(bathroom, wet_area).
is_a(bedroom, normal_zone).
is_a(child, vulnerable_person).
is_a(collapsed, posture).
is_a(distress_sound, audio_event).
is_a(elderly, vulnerable_person).
is_a(emergency_action, response_action).
is_a(hallway, normal_zone).
is_a(high, severity).
is_a(high_risk_zone, zone).
is_a(impact_sound, audio_event).
is_a(kitchen, wet_area).
is_a(leaning, posture).
is_a(living_room, normal_zone).
is_a(log_action, response_action).
is_a(low, severity).
is_a(medium, severity).
is_a(normal_zone, zone).
is_a(other_zone, unclassified_zone).
is_a(outdoor, unclassified_zone).
is_a(scream, distress_sound).
is_a(stairs, high_risk_zone).
is_a(unclassified_zone, zone).
is_a(unknown_person, person).
is_a(upright, posture).
is_a(vulnerable_person, person).
is_a(wet_area, high_risk_zone).
