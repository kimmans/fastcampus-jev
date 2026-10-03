import type { TimelineItem, ToolStatus } from './timeline'

type ToolItem = Extract<TimelineItem, { kind: 'tool' }>

const STATUS_LABEL: Record<ToolStatus, string> = {
  running: '실행 대기',
  done: '완료',
  blocked: '결과 차단',
  refused: '실행 안 함',
}

function summarize(args: Record<string, unknown>): string {
  return Object.entries(args)
    .map(([key, value]) => `${key}: ${typeof value === 'string' ? value : JSON.stringify(value)}`)
    .join(', ')
}

/** 도구 호출 한 건. 접힌 상태에서는 이름과 인자 요약만, 펼치면 인자와 결과 전체를 보여 준다. */
export function ToolCallCard({ item }: { item: ToolItem }) {
  return (
    <details className={`tool-card is-${item.status}`}>
      <summary>
        <span className="tool-icon" aria-hidden="true">
          ⚙
        </span>
        <span className="tool-name">{item.name}</span>
        <span className="tool-args">{summarize(item.args)}</span>
        <span className="tool-status">{STATUS_LABEL[item.status]}</span>
      </summary>
      <dl className="tool-detail">
        <dt>인자</dt>
        <dd>
          <pre>{JSON.stringify(item.args, null, 2)}</pre>
        </dd>
        <dt>결과</dt>
        <dd>
          <pre>{item.result ?? '아직 결과가 없습니다.'}</pre>
        </dd>
      </dl>
    </details>
  )
}
