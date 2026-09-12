import { StrictMode, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { AlertCircle, ArrowUpRight, Braces, LoaderCircle, Search, Sparkles } from 'lucide-react'
import './styles.css'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')

function ListSection({ title, items, empty = 'None identified' }) {
  return (
    <section className="report-section">
      <h3>{title}</h3>
      {items?.length ? (
        <ul className="item-list">
          {items.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
        </ul>
      ) : <p className="muted">{empty}</p>}
    </section>
  )
}

function Report({ report }) {
  const status = report.status || 'unknown'
  const statusLabel = status.replace('_', ' ')
  return (
    <article className="report" aria-live="polite">
      <header className="report-header">
        <div>
          <p className="eyebrow">Analysis report</p>
          <h2>{report.repo?.owner && report.repo?.name ? `${report.repo.owner}/${report.repo.name}` : 'Repository'}</h2>
        </div>
        <div className={`status-badge ${status}`}><span />{statusLabel}</div>
      </header>
      <div className="confidence-row">
        <span>Confidence</span><strong>{Math.round((Number(report.confidence) || 0) * 100)}%</strong>
        <div className="confidence-track"><div style={{ width: `${Math.max(0, Math.min(100, (Number(report.confidence) || 0) * 100))}%` }} /></div>
      </div>
      <section className="goal-section"><p className="eyebrow">Goal</p><p className="goal">{report.goal || 'No clear goal found.'}</p></section>
      <div className="report-grid">
        <ListSection title="Inputs" items={report.inputs} />
        <ListSection title="Outputs" items={report.outputs} />
        <ListSection title="Stack" items={report.stack} />
        <ListSection title="Gaps" items={report.gaps} />
      </div>
      <section className="report-section how"><h3>How it works</h3><p>{report.how_it_works || 'No workflow description found.'}</p></section>
      <section className="report-section sources"><h3>Sources</h3>{report.sources?.length ? report.sources.map((source, index) => <code key={`${source}-${index}`}>{source}</code>) : <p className="muted">No sources returned.</p>}</section>
    </article>
  )
}

function App() {
  const [repoUrl, setRepoUrl] = useState('')
  const [report, setReport] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function analyze(event) {
    event.preventDefault()
    setError('')
    setReport(null)
    setLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/api/analyze`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ repo_url: repoUrl.trim() }),
      })
      const body = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(body.detail || 'The analysis service could not complete the request.')
      setReport(body)
    } catch (requestError) {
      setError(requestError instanceof TypeError ? 'The API is unreachable. Check that the backend is running.' : requestError.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="page-shell">
      <nav className="topbar"><a className="brand" href="/"><span className="brand-mark"><Braces size={18} /></span>Repo Sense</a><span className="nav-note">Public repositories, made legible.</span></nav>
      <section className="hero">
        <div className="hero-copy"><p className="eyebrow"><Sparkles size={15} /> Repository intelligence</p><h1>Understand the code<br /><em>before</em> you open the editor.</h1><p className="lede">Paste a public GitHub repository and get a concise, evidence-based map of what it does, how it works, and where the unknowns remain.</p></div>
        <form className="analyze-form" onSubmit={analyze}><label htmlFor="repo-url">GitHub repository URL</label><div className="input-row"><Search size={19} /><input id="repo-url" value={repoUrl} onChange={(event) => setRepoUrl(event.target.value)} placeholder="github.com/owner/repository" required /><button type="submit" disabled={loading}>{loading ? <><LoaderCircle className="spin" size={18} /> Reading</> : <>Analyze <ArrowUpRight size={18} /></>}</button></div><p className="form-hint">Public repositories only · no account required</p></form>
      </section>
      {error && <div className="error-banner" role="alert"><AlertCircle size={19} /><span>{error}</span></div>}
      {loading && <div className="loading-state"><div className="loading-line" /><p>Inspecting the repository tree and key files...</p></div>}
      {report && !loading && <Report report={report} />}
      {!report && !loading && !error && <div className="empty-state"><span>01</span><p>A report appears here once the repository has been read.</p></div>}
      <footer><span>Repo Sense / v1</span><span>Evidence over guesswork</span></footer>
    </main>
  )
}

createRoot(document.getElementById('root')).render(<StrictMode><App /></StrictMode>)
