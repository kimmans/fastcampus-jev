import type { CSSProperties } from 'react'

type Props = {
  probabilities: Record<string, number>
  thresholds?: Record<string, number>
  highlighted?: string[]
  maxBars?: number
  /** 화면에 보일 이름. 없는 키는 원래 이름을 쓴다. */
  labels?: Record<string, string>
  /** true 면 probability 순으로 정렬하지 않고 받은 순서를 지킨다. 여러 카드를 같은 순서로 비교할 때 쓴다. */
  keepOrder?: boolean
}

function clamp(value: number): number {
  return Math.min(Math.max(value, 0), 1)
}

/** probability 막대 묶음. 기준값이 있으면 막대 위에 눈금으로 표시한다. */
export function ProbabilityBars({
  probabilities,
  thresholds = {},
  highlighted = [],
  maxBars = 4,
  labels = {},
  keepOrder = false,
}: Props) {
  const all = Object.entries(probabilities)
  const entries = (keepOrder ? all : all.sort(([, left], [, right]) => right - left)).slice(0, maxBars)
  if (entries.length === 0) return null

  return (
    <ul className="bars">
      {entries.map(([key, probability]) => {
        const label = labels[key] ?? key
        const threshold = thresholds[key]
        // 막대 길이와 눈금 위치는 실행 중에 정해지는 값이라 CSS 변수로 넘긴다.
        const style = {
          '--fill': `${clamp(probability) * 100}%`,
          '--mark': threshold === undefined ? undefined : `${clamp(threshold) * 100}%`,
        } as CSSProperties
        const isOver = threshold !== undefined && probability >= threshold
        const className = ['bar', highlighted.includes(key) && 'is-highlighted', isOver && 'is-over']
          .filter(Boolean)
          .join(' ')
        return (
          <li key={key} className={className}>
            <span className="bar-label" title={label}>
              {label}
            </span>
            <span
              className="bar-track"
              style={style}
              role="meter"
              aria-label={`${label} probability`}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={Math.round(clamp(probability) * 100)}
            >
              <span className="bar-fill" />
              {threshold !== undefined && <span className="bar-mark" title={`기준 ${threshold}`} />}
            </span>
            <span className="bar-value">{Math.round(clamp(probability) * 100)}%</span>
          </li>
        )
      })}
    </ul>
  )
}
