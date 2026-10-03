import { useState, type FormEvent } from 'react'
import { useMutation } from '@tanstack/react-query'
import { ProbabilityBars } from '../components/ProbabilityBars'
import { runPattern } from '../lib/langgraph'
import type { PatternConfig } from './config'

function splitPayload(payload: Record<string, unknown>) {
  const text: Record<string, string> = {}
  const attached: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(payload)) {
    if (typeof value === 'string') text[key] = value
    else attached[key] = value
  }
  return { text, attached }
}

/** 패턴 하나를 직접 실행해 보는 탭. 예시를 고르고, 글자를 고친 뒤, 서버에 판단을 요청한다. */
export function PatternTab({ config }: { config: PatternConfig }) {
  const [presetIndex, setPresetIndex] = useState(0)
  const [edits, setEdits] = useState<Record<string, string>>({})
  const preset = config.presets[presetIndex]
  const { text, attached } = splitPayload(preset.payload)
  const values = { ...text, ...edits }

  const mutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => runPattern(config.graphId, payload),
  })

  const choosePreset = (index: number) => {
    setPresetIndex(index)
    setEdits({})
    mutation.reset()
  }
  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    mutation.mutate({ ...attached, ...values })
  }
  const output = mutation.data

  return (
    <div className="pattern">
      <header className="topbar">
        <div>
          <h1>{config.title}</h1>
          <p>{config.tagline}</p>
        </div>
        <a className="ghost" href={config.source.url} target="_blank" rel="noreferrer">
          참고: {config.source.name}
        </a>
      </header>

      <div className="pattern-body">
        <dl className="roles">
          <div>
            <dt>Jev 가 하는 일</dt>
            <dd>{config.jevRole}</dd>
          </div>
          <div>
            <dt>LLM 이 하는 일</dt>
            <dd>{config.llmRole}</dd>
          </div>
        </dl>

        <form className="pattern-form" onSubmit={onSubmit}>
          <div className="chips" role="group" aria-label="예시 선택">
            {config.presets.map((item, index) => (
              <button
                key={item.label}
                type="button"
                className="chip"
                aria-pressed={index === presetIndex}
                onClick={() => choosePreset(index)}
              >
                {item.label}
              </button>
            ))}
          </div>

          {Object.keys(text).map((key) => (
            <div key={`${presetIndex}-${key}`} className="field">
              <label htmlFor={`${config.id}-${key}`}>{config.fieldLabels[key] ?? key}</label>
              <textarea
                id={`${config.id}-${key}`}
                rows={2}
                value={values[key]}
                onChange={(event) => setEdits((prev) => ({ ...prev, [key]: event.target.value }))}
              />
            </div>
          ))}

          {Object.keys(attached).length > 0 && (
            <details className="attached">
              <summary>함께 보내는 데이터 보기</summary>
              <pre>{JSON.stringify(attached, null, 2)}</pre>
            </details>
          )}

          <button type="submit" className="primary" disabled={mutation.isPending}>
            {mutation.isPending ? 'Jev 에 묻는 중…' : 'Jev 에 묻기'}
          </button>
        </form>

        {mutation.isError && (
          <p className="error" role="alert">
            실행하지 못했습니다: {mutation.error.message}
          </p>
        )}

        {output && (
          <section className="result" aria-label="판단 결과" aria-live="polite">
            <ul className="stats">
              {output.stats.map((item) => (
                <li key={item.label}>
                  <span>{item.label}</span>
                  <strong>{item.value}</strong>
                </li>
              ))}
              <li>
                <span>Jev 호출</span>
                <strong>
                  1회 · {output.latency_ms}ms · ${output.cost.toFixed(6)}
                </strong>
              </li>
            </ul>
            <ol className="result-rows">
              {output.rows.map((item, index) => (
                <li key={`${item.title}-${index}`} className={`result-row tone-${item.tone}`}>
                  <div className="result-head">
                    <h3>{item.title}</h3>
                    <span className={`verdict tone-${item.tone}`}>{item.verdict}</span>
                  </div>
                  {item.body && <p className="result-note">{item.body}</p>}
                  <ProbabilityBars
                    probabilities={item.probabilities}
                    thresholds={item.thresholds}
                    maxBars={5}
                    keepOrder={config.keepBarOrder}
                  />
                </li>
              ))}
            </ol>
          </section>
        )}
      </div>
    </div>
  )
}
