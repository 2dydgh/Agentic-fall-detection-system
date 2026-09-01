% ============================================================
%  낙상 심각도 판정 규칙
%  개념 계층(is_a/2)은 generated/ontology_facts.pl 에서 온다.
%  이 파일에 is_a/2 사실을 직접 쓰지 말 것.
% ============================================================

:- set_prolog_flag(encoding, utf8).

% facts.py / history.py 가 런타임에 주입하는 술어
:- dynamic occurred_in/2.
:- dynamic involves/2.
:- dynamic has_posture/2.
:- dynamic has_audio_event/2.
:- dynamic no_movement_duration/2.
:- dynamic has_hazard/2.
:- dynamic prior_incident/3.

:- discontiguous rule/3.
:- discontiguous rule_text/2.

% ------------------------------------------------------------
%  파생 술어
% ------------------------------------------------------------

% is_a 의 이행 폐쇄
kind_of(X, Y) :- is_a(X, Y).
kind_of(X, Y) :- is_a(X, Z), kind_of(Z, Y).

% 직접 관측된 구역 + 상위 개념으로 승격된 구역
in_zone(I, Z) :- occurred_in(I, Z).
in_zone(I, Z) :- occurred_in(I, L), kind_of(L, Z).

% 취약 계층 여부 (노인 또는 아동)
is_vulnerable(I) :- involves(I, P), kind_of(P, vulnerable_person).

% ------------------------------------------------------------
%  판정 규칙
% ------------------------------------------------------------
rule(r1, high, I) :-
    in_zone(I, high_risk_zone),
    no_movement_duration(I, S), S >= 30.

rule_text(r1, '고위험 구역에서 30초 이상 무동작').

rule(r2, high, I) :-
    is_vulnerable(I),
    has_audio_event(I, scream).

rule(r3, high, I) :-
    no_movement_duration(I, S), S >= 60.

rule(r4, high, I) :-
    has_posture(I, collapsed),
    has_audio_event(I, impact_sound),
    no_movement_duration(I, S), S >= 20.

rule(r5, high, I) :-
    is_vulnerable(I),
    in_zone(I, high_risk_zone),
    no_movement_duration(I, S), S >= 15.

rule(r7, medium, I) :-
    in_zone(I, high_risk_zone),
    no_movement_duration(I, S), S >= 10, S < 30.

rule(r8, medium, I) :-
    has_audio_event(I, scream).

rule(r9, medium, I) :-
    is_vulnerable(I),
    no_movement_duration(I, S), S >= 15.

rule(r10, medium, I) :-
    has_posture(I, collapsed),
    no_movement_duration(I, S), S >= 10.

rule(r11, medium, I) :-
    has_audio_event(I, impact_sound),
    has_posture(I, collapsed).

rule(r12, medium, I) :-
    has_hazard(I, _),
    has_posture(I, collapsed).

rule_text(r2,  '취약 계층(노인/아동) + 비명 감지').
rule_text(r3,  '무동작 60초 이상').
rule_text(r4,  '붕괴 자세 + 충격음 + 무동작 20초 이상').
rule_text(r5,  '취약 계층 + 고위험 구역 + 무동작 15초 이상').
rule_text(r7,  '고위험 구역에서 10~30초 무동작').
rule_text(r8,  '비명 감지').
rule_text(r9,  '취약 계층 + 무동작 15초 이상').
rule_text(r10, '붕괴 자세 + 무동작 10초 이상').
rule_text(r11, '충격음 + 붕괴 자세').
rule_text(r12, '주변 위험물 + 붕괴 자세').

% 시간축 규칙
% history.py 가 동일 카메라(=동일 구역) 이력만 주입하므로,
% prior_incident/3 의 존재 자체가 '같은 구역 재낙상' 을 뜻한다.
rule(r6, high, I) :-
    prior_incident(_, _, _),
    no_movement_duration(I, S), S >= 10.

rule(r13, medium, _) :-
    prior_incident(_, _, _).

rule_text(r6,  '3일 내 동일 구역 재낙상 + 무동작 10초 이상').
rule_text(r13, '3일 내 동일 구역 재낙상').

% ------------------------------------------------------------
%  최종 심각도 — 발동한 규칙 중 가장 높은 등급
% ------------------------------------------------------------
fired(I, R, Sev) :- rule(R, Sev, I).

severity(I, high)   :- fired(I, _, high), !.
severity(I, medium) :- fired(I, _, medium), !.
severity(_, low).

% ------------------------------------------------------------
%  대응 액션 (설계 문서의 r14 / r15 / r16)
%  나열 순서가 곧 출력 순서다. 기존 decision.py 의 순서를 따른다.
% ------------------------------------------------------------
requires_action(high,   log_action).        % r14
requires_action(high,   alert_action).      % r14
requires_action(high,   emergency_action).  % r14
requires_action(medium, log_action).        % r15
requires_action(medium, alert_action).      % r15
requires_action(low,    log_action).        % r16

action_tool(log_action,       log_to_db).
action_tool(alert_action,     save_snapshot).
action_tool(alert_action,     notify_security_room).
action_tool(emergency_action, send_email_alert).
action_tool(emergency_action, generate_report).
