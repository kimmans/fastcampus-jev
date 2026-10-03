import { ProbabilityBars } from '../components/ProbabilityBars'
import { groupByTurn, totalLatencyMs, type JevDecision } from './timeline'

const KIND_LABEL: Record<JevDecision['kind'], string> = {
  guardrail: '가드레일',
  tool_select: '도구 선택',
  risk_gate: '위험 게이트',
}
const KIND_QUESTION: Record<JevDecision['kind'], string> = {
  guardrail: '인젝션, 욕설, 비방, 개인정보에 해당하는가?',
  tool_select: '다음에 실행할 도구는 무엇인가?',
  risk_gate: '사용자가 이 작업을 직접 요청했는가?',
}

const GUARDRAIL_LABEL: Record<string, string> = {
  injection: '인젝션',
  abuse: '비방·위협',
  profanity: '욕설',
  pii: '개인정보',
}

function toneOf(verdict: string): 'good' | 'warn' | 'bad' {
  if (verdict.includes('차단')) return 'bad'
  if (['사람', 'LLM', '가림', '표시', '개인정보', '꺼짐'].some((word) => verdict.includes(word))) return 'warn'
  return 'good'
}

function DecisionCard({ decision }: { decision: JevDecision }) {
  return (
    <li className={`decision kind-${decision.kind}`}>
      <div className="decision-head">
        <span className="badge">{KIND_LABEL[decision.kind]}</span>
        {decision.latency_ms != null && <span className="latency">{decision.latency_ms}ms</span>}
      </div>
      <p className="decision-question">{KIND_QUESTION[decision.kind]}</p>
      <p className="decision-title">{decision.title}</p>
      <p className={`verdict tone-${toneOf(decision.verdict)}`}>{decision.verdict}</p>
      {decision.detail && <p className="detail">{decision.detail}</p>}
      {decision.probabilities && (
        <ProbabilityBars
          probabilities={decision.probabilities}
          thresholds={decision.thresholds}
          highlighted={decision.offered}
          labels={decision.kind === 'guardrail' ? GUARDRAIL_LABEL : undefined}
          keepOrder={decision.kind === 'guardrail'}
        />
      )}
      {decision.confidence != null && (
        <p className="confidence">confidence {Math.round(decision.confidence * 100)}%</p>
      )}
    </li>
  )
}

export function DecisionPanel({ decisions }: { decisions: JevDecision[] }) {
  const groups = groupByTurn(decisions)
  return (
    <aside className="panel" aria-label="Jev 판단 기록">
      <header className="panel-head">
        <h2>Jev 판단</h2>
        <p className="panel-summary">
          {decisions.length}회 · 합계 {totalLatencyMs(decisions)}ms
        </p>
      </header>
      {groups.length === 0 && (
        <p className="empty">메시지를 보내면 Jev 가 내린 판단과 probability 가 턴별로 쌓입니다.</p>
      )}
      {groups.map((group) => (
        <section key={group.turn} className="turn">
          <h3 className="turn-title">턴 {group.turn}</h3>
          <ol>
            {group.decisions.map((decision, index) => (
              <DecisionCard key={`${group.turn}-${index}`} decision={decision} />
            ))}
          </ol>
        </section>
      ))}
      <p className="legend">막대 위 세로선은 판정 기준값, 진한 막대는 LLM 에 노출한 도구입니다.</p>
    </aside>
  )
}
