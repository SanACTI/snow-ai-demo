import { useState, useEffect, useRef, useCallback } from 'react'
import { startAnalysis, getResult, getBatchHistory, getPending, submitDecision, getSavedResult, getNodeTrace } from './api/client'
import { confColor, riskColor, priorityColor, Badge } from './utils/helpers.jsx'
import { Shield, FileSearch, Play, Files, ChevronDown, ChevronRight, AlertTriangle, Check, X, Edit, ArrowLeft, RefreshCw, Brain, Database, Layers, GitBranch, Briefcase, Microscope, ClipboardList, LayoutDashboard } from 'lucide-react'

const NODES = ['validate_input','sanitize_input','extract_facts','chunk_large_text','summarize_chunks','generate_insights','validate_output','save_output']
const MSGS  = ['Validating fields...','Sanitising payload...','Extracting facts...','Checking tokens...','Calling Mistral...','Validating output...','Finalising...','Saving...']

// ─── Reusable UI ────────────────────────────────────────────
function Card({ children, className = '' }) {
  return (
    <div className={`bg-[#0D1E3A] border border-[#1E3356] rounded-xl p-5 ${className}`}>
      {children}
    </div>
  )
}

function SectionLabel({ children }) {
  return <div className="text-[10px] font-semibold text-[#3D5A7A] uppercase tracking-widest mb-2">{children}</div>
}

function BulletList({ items, empty = 'None specified' }) {
  if (!items?.length) return <p className="text-sm text-slate-500">{empty}</p>
  return (
    <ul className="space-y-2">
      {items.map((item, i) => (
        <li key={i} className="text-sm text-[#A8C0D8] pl-4 relative before:content-[''] before:absolute before:left-1 before:top-2 before:w-1.5 before:h-1.5 before:rounded-full before:bg-[#2563EB]">
          {item}
        </li>
      ))}
    </ul>
  )
}

function StatGrid({ stats }) {
  return (
    <div className="grid grid-cols-4 gap-3 mb-5">
      {stats.map((s, i) => (
        <div key={i} className="bg-[#0D1E3A] border border-[#1E3356] rounded-xl p-4 flex flex-col gap-1">
          <div className="text-[11px] font-medium text-[#3D5A7A] uppercase tracking-widest">{s.label}</div>
          <div className="text-2xl font-bold mt-1" style={s.color ? { color: s.color } : { color: '#C8D8EC' }}>{s.value}</div>
          {s.sub && <div className="text-xs text-[#3D5A7A]">{s.sub}</div>}
        </div>
      ))}
    </div>
  )
}
// ─── Node Track ─────────────────────────────────────────────
function NodeTrack({ doneCount, runningIdx }) {
  return (
    <div className="space-y-1">
      {NODES.map((n, i) => {
        const done = i < doneCount
        const running = i === runningIdx
        return (
          <div key={n} className={`flex items-center gap-2 px-2 py-1 rounded text-[11px] transition-all ${done ? 'text-emerald-400 bg-emerald-900/20' : running ? 'text-amber-400 bg-amber-900/20' : 'text-[#3D5A7A]'}`}>
            <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${done ? 'bg-emerald-400' : running ? 'bg-amber-400 animate-pulse' : 'bg-[#1E3356]'}`} />
            {n}
          </div>
        )
      })}
    </div>
  )
}

// ─── Tabs ────────────────────────────────────────────────────
const TABS = [
  { id: 'overview',   label: 'Overview',          Icon: LayoutDashboard },
  { id: 'executive',  label: 'Executive summary',  Icon: Briefcase },
  { id: 'rca',        label: 'Root cause',         Icon: Brain },
  { id: 'actions',    label: 'Actions',            Icon: ClipboardList },
  { id: 'evidence',   label: 'Evidence',           Icon: Microscope },
  { id: 'pipeline',   label: 'Pipeline view',      Icon: GitBranch },
]

// ─── Tab content components ──────────────────────────────────
function OverviewTab({ result }) {
  const facts = result.extracted_facts || {}
  const final = result.final_response || {}
  const conf = result.confidence_score || 0
  const risk = (final.risk_level || 'Unknown').replace('RiskLevel.', '')
  const rc = riskColor(risk)
  const pc = priorityColor(facts.priority)

  return (
    <div>
      {(result.validation_warnings || []).length > 0 && (
        <div className="flex items-start gap-2 bg-amber-900/20 border border-amber-800 rounded-lg p-3 mb-4 text-sm text-amber-400">
          <AlertTriangle size={16} className="flex-shrink-0 mt-0.5" />
          <div>Missing recommended fields: {result.validation_warnings.map(w => w.replace('Missing recommended field: ', '')).join(', ')}</div>
        </div>
      )}
      <StatGrid stats={[
        { label: 'Priority', value: facts.priority || '—', color: pc.text.replace('text-','') },
        { label: 'Duration', value: facts.outage_duration_minutes ? `${facts.outage_duration_minutes} min` : '—' },
        { label: 'Confidence', value: `${Math.round(conf * 100)}%`, color: confColor(conf) },
        { label: 'Risk level', value: risk, color: rc.text.replace('text-','') },
      ]} />
      <Card className="mb-3">
        <SectionLabel>Incident summary</SectionLabel>
        <p className="text-sm text-[#A8C0D8] leading-relaxed">{final.incident_summary || '—'}</p>
        <div className="flex flex-wrap gap-1.5 mt-3">
          {(facts.error_keywords || []).map(k => (
            <span key={k} className="text-[11px] px-2 py-0.5 rounded-full bg-[#111F35] border border-[#1E3356] text-[#5B7EA6]">{k}</span>
          ))}
        </div>
      </Card>
      <div className="grid grid-cols-2 gap-4 mb-4">
        <Card>
          <SectionLabel>Infrastructure</SectionLabel>
          <table className="w-full text-xs">
            {[
              ['CI name', facts.ci_name || '—'],
              ['Services', (facts.impacted_services || []).length],
              ['Assignment', facts.assignment_group || '—'],
              ['Problem record', facts.has_problem_record ? '✅ Linked' : '❌ None'],
              ['Change record', facts.has_change_record ? '✅ Linked' : '❌ None'],
            ].map(([k, v]) => (
              <tr key={k}><td className="text-[#3D5A7A] py-1 pr-2">{k}</td><td className="text-[#A8C0D8] text-right py-1">{v}</td></tr>
            ))}
          </table>
          <div className="flex flex-wrap gap-1 mt-2">
            {(facts.impacted_services || []).map(s => (
              <span key={s} className="text-[10px] px-2 py-0.5 rounded-full bg-[#111F35] border border-[#1E3356] text-[#5B7EA6]">{s}</span>
            ))}
          </div>
        </Card>
        <Card>
          <SectionLabel>Analysis quality</SectionLabel>
          <div className="mb-3">
            <div className="flex justify-between text-xs mb-1">
              <span className="text-[#3D5A7A]">Confidence</span>
              <span className="font-semibold" style={{ color: confColor(conf) }}>{Math.round(conf * 100)}%</span>
            </div>
            <div className="h-1 bg-[#152B4A] rounded-full overflow-hidden">
              <div className="h-full rounded-full" style={{ width: `${conf * 100}%`, background: confColor(conf) }} />
            </div>
          </div>
          <table className="w-full text-xs">
            {[
              ['Est. cost', `$${(result.cost_estimate || 0).toFixed(6)}`],
              ['Missing fields', (final.missing_information || []).length],
              ['Assignment', facts.assignment_group || '—'],
            ].map(([k, v]) => (
              <tr key={k}><td className="text-[#3D5A7A] py-1">{k}</td><td className="text-[#A8C0D8] text-right py-1">{v}</td></tr>
            ))}
          </table>
        </Card>
      </div>
    </div>
  )
}

function ExecutiveTab({ result }) {
  const facts = result.extracted_facts || {}
  const final = result.final_response || {}
  const conf = result.confidence_score || 0
  const risk = (final.risk_level || 'Unknown').replace('RiskLevel.', '')
  const ex = result.executive_summary

  return (
    <div>
      <div className="bg-[#0B2040] border border-[#1D4ED8] rounded-xl p-5 mb-4">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-9 h-9 bg-[#1D4ED8] rounded-lg flex items-center justify-center flex-shrink-0">
            <Briefcase size={18} className="text-white" />
          </div>
          <div>
            <div className="text-[15px] font-semibold text-white">Executive Summary — {result.incident_number}</div>
            <div className="text-xs text-[#5B7EA6] mt-0.5">{facts.priority} incident · {risk} risk · {Math.round(conf * 100)}% confidence</div>
          </div>
        </div>
        {ex ? (
          <table className="w-full text-sm border-collapse">
            {[
              ['What happened', ex.what_happened],
              ['Business impact', ex.business_impact],
              ['Likely cause', ex.likely_cause],
              ['What we did', ex.what_we_did],
              ['Next steps', ex.next_steps],
              ['Automation opportunity', ex.automation_opportunity],
            ].map(([k, v]) => (
              <tr key={k} className="border-b border-[#152B4A] last:border-0">
                <td className="text-[#5B7EA6] py-2 pr-4 w-44 text-xs uppercase tracking-wider">{k}</td>
                <td className="text-[#C8D8EC] py-2 font-medium">{v || '—'}</td>
              </tr>
            ))}
          </table>
        ) : (
          <div className="text-sm text-[#3D5A7A] text-center py-6">
            {(facts.priority === 'P1' || facts.priority === 'P2')
              ? 'Executive summary generated after approval and save.'
              : `${facts.priority} incident — executive summary not required.`}
          </div>
        )}
      </div>
      <Card>
        <SectionLabel>Full incident summary</SectionLabel>
        <p className="text-sm text-[#A8C0D8] leading-relaxed">{final.incident_summary || '—'}</p>
      </Card>
    </div>
  )
}

function RCATab({ result }) {
  const final = result.final_response || {}
  return (
    <div>
      <Card className="mb-3">
        <SectionLabel>Root cause analysis</SectionLabel>
        <p className="text-sm text-[#A8C0D8] leading-relaxed">{final.root_cause_analysis || '—'}</p>
      </Card>
      <div className="grid grid-cols-2 gap-4 mb-4">
        <Card>
          <SectionLabel>Prevention measures</SectionLabel>
          <BulletList items={final.prevention_measures} />
        </Card>
        <Card>
          <SectionLabel>Missing information</SectionLabel>
          {(final.missing_information || []).length
            ? <BulletList items={final.missing_information} />
            : <p className="text-sm text-emerald-400">All key fields present</p>}
        </Card>
      </div>
    </div>
  )
}

function ActionsTab({ result }) {
  const final = result.final_response || {}
  return (
    <div className="space-y-3">
      <Card>
        <SectionLabel>Resolution recommendations</SectionLabel>
        <BulletList items={final.resolution_recommendations} />
      </Card>
      <Card>
        <SectionLabel>Automation & monitoring suggestions</SectionLabel>
        <BulletList items={final.automation_monitoring_suggestions} />
      </Card>
    </div>
  )
}

function EvidenceTab({ result }) {
  const facts = result.extracted_facts || {}
  const final = result.final_response || {}
  return (
    <div className="space-y-3">
      <Card>
        <SectionLabel>Evidence used in analysis</SectionLabel>
        <BulletList items={final.evidence_used} empty="None recorded" />
      </Card>
      <Card>
        <SectionLabel>Error keywords detected</SectionLabel>
        <div className="flex flex-wrap gap-2 mt-1">
          {(facts.error_keywords || []).length
            ? facts.error_keywords.map(k => (
                <span key={k} className="text-xs px-2 py-1 rounded-full bg-[#111F35] border border-[#1E3356] text-[#5B7EA6]">{k}</span>
              ))
            : <span className="text-sm text-[#2A4870]">None detected</span>}
        </div>
      </Card>
    </div>
  )
}

function PipelineTab({ result }) {
  const [nodes, setNodes] = useState(null)
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState({})

  useEffect(() => {
    setLoading(true)
    setNodes(null)
    getNodeTrace(result.incident_number)
      .then(r => { setNodes(r.data.found ? r.data.nodes : []); setLoading(false) })
      .catch(() => { setNodes([]); setLoading(false) })
  }, [result.incident_number])

  const NODE_COLORS = {
    validate_input: '#185FA5', sanitize_input: '#0F6E56',
    extract_facts: '#854F0B', chunk_large_text: '#3B6D11',
    summarize_chunks: '#185FA5', generate_insights: '#793556',
    validate_output: '#0F6E56', save_output: '#3D5A7A'
  }

  const toggle = (name) => setExpanded(p => ({ ...p, [name]: !p[name] }))

  if (loading) return (
    <div className="flex flex-col items-center justify-center h-48 gap-3">
      <div className="w-8 h-8 border-2 border-[#1E3356] border-t-[#2563EB] rounded-full animate-spin" />
      <p className="text-sm text-[#3D5A7A]">Fetching state trace...</p>
    </div>
  )

  if (!nodes?.length) return (
    <div className="flex flex-col items-center justify-center h-48 gap-2 text-[#3D5A7A]">
      <GitBranch size={32} />
      <p className="text-sm">No log trace found. Run analysis to generate trace.</p>
    </div>
  )

  return (
    <div className="space-y-0">
      {nodes.map((node, idx) => {
        const color = NODE_COLORS[node.name] || '#3D5A7A'
        const open = expanded[node.name]
        return (
          <div key={node.name}>
            <div
              className="border rounded-xl overflow-hidden mb-1 cursor-pointer transition-all"
              style={{ borderColor: open ? color + '80' : color + '30', background: '#0D1E3A' }}
            >
              <div
                className="flex items-center gap-3 p-3"
                style={{ background: color + '12' }}
                onClick={() => toggle(node.name)}
              >
                <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 border"
                  style={{ background: color + '20', borderColor: color + '50' }}>
                  <Database size={14} style={{ color }} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-[#C8D8EC]">{node.name.replace(/_/g, ' ')}</div>
                  <div className="text-[11px] text-[#3D5A7A] font-mono flex gap-3 mt-0.5">
                    <span>{node.name}</span>
                    {node.duration && <span className="text-emerald-400">⏱ {node.duration}s</span>}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${node.status === 'done' ? 'bg-emerald-400' : node.status === 'error' ? 'bg-red-400' : 'bg-amber-400'}`} />
                  <span className="text-[10px] text-[#3D5A7A] uppercase tracking-wider">{node.status}</span>
                </div>
                <ChevronDown size={16} className="text-[#3D5A7A] transition-transform" style={{ transform: open ? 'rotate(180deg)' : '' }} />
              </div>
              {open && (
                <div className="border-t border-[#152B4A] grid grid-cols-2 divide-x divide-[#152B4A]">
                  <div className="p-4">
                    <div className="text-[10px] font-semibold text-[#3D5A7A] uppercase tracking-wider mb-2">↳ Input state</div>
                    <pre className="text-[11px] text-[#7BAFD4] font-mono whitespace-pre-wrap leading-relaxed max-h-64 overflow-y-auto">
                      {node.input ? JSON.stringify(node.input, null, 2) : 'No input logged'}
                    </pre>
                  </div>
                  <div className="p-4">
                    <div className="text-[10px] font-semibold text-emerald-500 uppercase tracking-wider mb-2">↳ Output state</div>
                    <pre className="text-[11px] text-[#A8C0D8] font-mono whitespace-pre-wrap leading-relaxed max-h-64 overflow-y-auto">
                      {node.output ? JSON.stringify(node.output, null, 2) : 'No output logged'}
                    </pre>
                  </div>
                </div>
              )}
              {node.error && (
                <div className="border-t border-red-900 bg-red-900/20 p-3 text-xs text-red-400 font-mono">{node.error}</div>
              )}
            </div>
            {idx < nodes.length - 1 && (
              <div className="flex justify-center my-0.5">
                <ChevronDown size={14} className="text-[#1E3356]" />
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

// ─── Approval Modal ──────────────────────────────────────────
function ApprovalModal({ data, onDecide }) {
  const [editMode, setEditMode] = useState(false)
  const [editedRca, setEditedRca] = useState(data?.root_cause_analysis || '')
  const pc = priorityColor(data?.priority)

  if (!data) return null

  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4">
      <div className="bg-[#0D1E3A] border border-[#2563EB] rounded-2xl p-6 w-[520px] max-w-full">
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="text-[15px] font-semibold text-white">Director approval required</div>
            <div className="text-xs text-[#5B7EA6] mt-1">
              {data.priority} · {Math.round((data.confidence_score || 0) * 100)}% confidence · Risk: {data.risk_level}
            </div>
          </div>
          <span className={`text-[10px] font-bold px-2 py-1 rounded-full border ${pc.bg} ${pc.text} ${pc.border}`}>{data.priority}</span>
        </div>
        <div className="mb-3">
          <div className="text-[10px] font-semibold text-[#3D5A7A] uppercase tracking-wider mb-1.5">Incident summary</div>
          <div className="text-sm text-[#A8C0D8] bg-[#0A1628] rounded-lg p-3 leading-relaxed">{data.incident_summary}</div>
        </div>
        <div className="mb-4">
          <div className="text-[10px] font-semibold text-[#3D5A7A] uppercase tracking-wider mb-1.5">Root cause analysis</div>
          {editMode
            ? <textarea className="w-full text-sm text-[#C8D8EC] bg-[#0A1628] border border-[#1E3356] rounded-lg p-3 resize-y min-h-[80px] font-mono"
                value={editedRca} onChange={e => setEditedRca(e.target.value)} />
            : <div className="text-sm text-[#A8C0D8] bg-[#0A1628] rounded-lg p-3 leading-relaxed">{data.root_cause_analysis}</div>}
        </div>
        <div className="flex items-center gap-2 mb-4">
          <div className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
          <span className="text-xs text-[#5B7EA6]">Pipeline paused — awaiting your decision</span>
        </div>
        <div className="flex gap-2 justify-end pt-4 border-t border-[#1E3356]">
          <button onClick={() => setEditMode(!editMode)} className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-[#111F35] border border-[#1E3356] text-[#7BAFD4] rounded-lg hover:bg-[#152B4A]">
            <Edit size={12} /> {editMode ? 'Preview' : 'Edit RCA'}
          </button>
          <button onClick={() => onDecide('rejected', '')} className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-red-900/30 border border-red-800 text-red-400 rounded-lg hover:bg-red-900/50">
            <X size={12} /> Reject
          </button>
          <button onClick={() => onDecide('approved', editMode ? editedRca : '')} className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-emerald-900/30 border border-emerald-800 text-emerald-400 rounded-lg hover:bg-emerald-900/50">
            <Check size={12} /> Approve & save
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Batch History Panel ─────────────────────────────────────
function BatchPanel({ history, onSelect, panelHeight, onResize }) {
  const handleRef = useRef(null)

  useEffect(() => {
    const handle = handleRef.current
    if (!handle) return
    let startY, startH
    const onDown = (e) => { startY = e.clientY; startH = panelHeight; document.addEventListener('mousemove', onMove); document.addEventListener('mouseup', onUp) }
    const onMove = (e) => { const delta = startY - e.clientY; onResize(Math.max(60, Math.min(startH + delta, window.innerHeight * 0.7))) }
    const onUp = () => { document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp) }
    handle.addEventListener('mousedown', onDown)
    return () => handle.removeEventListener('mousedown', onDown)
  }, [panelHeight, onResize])

  return (
    <div className="bg-[#0D1E3A] border-t border-[#1E3356] flex-shrink-0" style={{ height: panelHeight }}>
      <div ref={handleRef} className="h-1.5 cursor-ns-resize flex items-center justify-center group">
        <div className="w-8 h-0.5 bg-[#1E3356] rounded group-hover:bg-[#2563EB] transition-colors" />
      </div>
      <div className="px-5 overflow-y-auto" style={{ height: panelHeight - 6 }}>
        <div className="flex items-center justify-between py-3 mb-2">
          <div className="text-[11px] font-semibold text-[#3D5A7A] uppercase tracking-wider flex items-center gap-2">
            <Database size={12} /> Processed incidents
          </div>
        </div>
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr>
              {['Incident','Priority','Risk','Confidence','Duration','Services','Date'].map(h => (
                <th key={h} className="text-left text-[10px] font-semibold text-[#2A4870] uppercase tracking-wider pb-1.5 border-b border-[#152B4A] px-2">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {history.length === 0 ? (
              <tr><td colSpan={7} className="text-center text-[#2A4870] py-4">No processed incidents yet</td></tr>
            ) : history.map((r, i) => {
              const rc = riskColor((r.risk_level || '').replace('RiskLevel.', ''))
              const pc = priorityColor(r.priority)
              const conf = r.confidence_score || 0
              return (
                <tr key={i} onClick={() => onSelect(r)} className="hover:bg-[#111F35] cursor-pointer border-b border-[#111F35] last:border-0">
                  <td className="px-2 py-2 font-semibold text-[#C8D8EC]">{r.incident_number}</td>
                  <td className="px-2 py-2"><span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${pc.bg} ${pc.text} ${pc.border}`}>{r.priority}</span></td>
                  <td className="px-2 py-2"><span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${rc.bg} ${rc.text} ${rc.border}`}>{(r.risk_level||'—').replace('RiskLevel.','')}</span></td>
                  <td className="px-2 py-2">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-1 bg-[#152B4A] rounded-full min-w-[40px]">
                        <div className="h-full rounded-full" style={{ width: `${Math.round(conf*100)}%`, background: confColor(conf) }} />
                      </div>
                      <span className="font-semibold" style={{ color: confColor(conf) }}>{Math.round(conf*100)}%</span>
                    </div>
                  </td>
                  <td className="px-2 py-2 text-[#5B7EA6]">{r.outage_duration_minutes ? `${r.outage_duration_minutes} min` : '—'}</td>
                  <td className="px-2 py-2 text-[#5B7EA6] max-w-[140px] truncate">{(r.impacted_services||[]).join(', ')||'—'}</td>
                  <td className="px-2 py-2 text-[#3D5A7A]">{r.generated_at ? new Date(r.generated_at).toLocaleDateString() : '—'}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ─── Main App ────────────────────────────────────────────────
export default function App() {
  const [file, setFile] = useState(null)
  const [activeTab, setActiveTab] = useState('overview')
  const [nodesDone, setNodesDone] = useState(0)
  const [nodesRunning, setNodesRunning] = useState(-1)
  const [loading, setLoading] = useState(false)
  const [loadingMsg, setLoadingMsg] = useState('')
  const [result, setResult] = useState(null)
  const [history, setHistory] = useState([])
  const [pendingApproval, setPendingApproval] = useState(null)
  const [approvalStatus, setApprovalStatus] = useState(null)
  const [panelHeight, setPanelHeight] = useState(180)
  const [batchView, setBatchView] = useState(null)
  const [tokenEst, setTokenEst] = useState(null)
  const nodeIntervalRef = useRef(null)
  const pollIntervalRef = useRef(null)

  const loadHistory = useCallback(async () => {
    try { const r = await getBatchHistory(); setHistory(r.data.results || []) } catch {}
  }, [])

  useEffect(() => { loadHistory() }, [loadHistory])

  useEffect(() => {
    const id = setInterval(async () => {
      try {
        const r = await getPending()
        if (r.data.pending && r.data.data.incident_number !== pendingApproval?.incident_number) {
          setPendingApproval(r.data.data)
        } else if (!r.data.pending && pendingApproval) {
          setPendingApproval(null)
        }
      } catch {}
    }, 3000)
    pollIntervalRef.current = id
    return () => clearInterval(id)
  }, [pendingApproval])

  const handleFile = (f) => {
    if (!f) return
    setFile(f)
    setBatchView(null)
    const reader = new FileReader()
    reader.onload = (ev) => {
      try { setTokenEst(Math.floor(JSON.stringify(JSON.parse(ev.target.result)).length / 4)) } catch {}
    }
    reader.readAsText(f)
  }

  const animateNodes = () => {
    let step = 0
    setNodesDone(0); setNodesRunning(0)
    nodeIntervalRef.current = setInterval(() => {
      if (step < NODES.length - 2) {
        step++
        setNodesDone(step); setNodesRunning(step)
        setLoadingMsg(MSGS[step])
      }
    }, 900)
  }

  const runSingle = async () => {
    if (!file) return
    setLoading(true); setResult(null); setApprovalStatus(null); setBatchView(null)
    setLoadingMsg(MSGS[0]); animateNodes()
    try {
      const sr = await startAnalysis(file)
      if (!sr.data.success) { setLoading(false); clearInterval(nodeIntervalRef.current); return }
      const inc = sr.data.incident_number
      const rp = setInterval(async () => {
        try {
          const r = await getResult(inc)
          if (!r.data.ready) return
          clearInterval(rp); clearInterval(nodeIntervalRef.current)
          setNodesDone(NODES.length); setNodesRunning(-1)
          setLoading(false)
          if (r.data.success) { setResult(r.data); loadHistory() }
        } catch {}
      }, 3000)
    } catch { setLoading(false); clearInterval(nodeIntervalRef.current) }
  }

  const runBatch = async (files) => {
    setBatchView({ files: Array.from(files), rows: [], done: false })
    setResult(null); setLoading(false)
    const results = []
    for (let i = 0; i < files.length; i++) {
      const f = files[i]
      setBatchView(prev => ({ ...prev, rows: [...(prev?.rows || []), { name: f.name, status: 'running', inc: null }] }))
      try {
        const sr = await startAnalysis(f, true)
        if (!sr.data.success) throw new Error(sr.data.error)
        const inc = sr.data.incident_number
        const r = await new Promise(resolve => {
          const p = setInterval(async () => {
            try { const d = await getResult(inc); if (d.data.ready) { clearInterval(p); resolve(d.data) } } catch {}
          }, 3000)
          setTimeout(() => { clearInterval(p); resolve({ ready: true, success: false, error: 'Timeout' }) }, 600000)
        })
        setBatchView(prev => ({
          ...prev,
          rows: prev.rows.map((row, j) => j === i ? { ...row, status: r.success ? 'done' : 'error', result: r, inc: r.incident_number } : row)
        }))
        if (r.success) results.push(r)
      } catch (err) {
        setBatchView(prev => ({ ...prev, rows: prev.rows.map((row, j) => j === i ? { ...row, status: 'error' } : row) }))
      }
    }
    setBatchView(prev => ({ ...prev, done: true, results }))
    loadHistory()
  }

  const handleHistorySelect = async (r) => {
    try {
      const res = await getSavedResult(r.incident_number)
      if (res.data.found) setResult(res.data)
      else setResult({ incident_number: r.incident_number, extracted_facts: r, final_response: {}, confidence_score: r.confidence_score })
      setBatchView(null)
    } catch {}
  }

  const handleDecide = async (action, editedRca) => {
    if (!pendingApproval) return
    await submitDecision(pendingApproval.incident_number, action, editedRca)
    setApprovalStatus(action)
    setPendingApproval(null)
    setTimeout(loadHistory, 6000)
  }

  const mainContent = () => {
    if (loading) return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <div className="w-9 h-9 border-3 border-[#1E3356] border-t-[#2563EB] rounded-full animate-spin" />
        <p className="text-sm text-[#5B7EA6]">{loadingMsg}</p>
      </div>
    )
    if (batchView) return (
      <div className="space-y-3">
        <div className="text-[11px] font-semibold text-[#3D5A7A] uppercase tracking-wider">
          Batch processing — {batchView.files.length} incidents
        </div>
        {batchView.rows.map((row, i) => (
          <div key={i}
            onClick={() => row.result?.success && (() => { setResult(row.result); setBatchView(null) })()}
            className={`flex items-center gap-3 p-3 rounded-lg border text-sm transition-all
              ${row.status === 'done' ? 'bg-emerald-900/20 border-emerald-800 cursor-pointer hover:bg-emerald-900/30' :
                row.status === 'error' ? 'bg-red-900/20 border-red-900' : 'bg-[#111F35] border-[#1E3356]'}`}>
            {row.status === 'running' && <div className="w-3.5 h-3.5 border-2 border-[#1E3356] border-t-[#7BAFD4] rounded-full animate-spin flex-shrink-0" />}
            {row.status === 'done' && <Check size={16} className="text-emerald-400 flex-shrink-0" />}
            {row.status === 'error' && <X size={16} className="text-red-400 flex-shrink-0" />}
            <span className={`flex-1 font-medium ${row.status === 'done' ? 'text-[#C8D8EC]' : row.status === 'error' ? 'text-red-400' : 'text-[#7BAFD4]'}`}>
              {row.inc || row.name}
            </span>
            {row.result?.success && (
              <>
                <span className="text-xs text-[#5B7EA6]">{Math.round((row.result.confidence_score||0)*100)}% confidence</span>
                <span className="text-xs text-[#3D5A7A]">click to view →</span>
              </>
            )}
            {row.status === 'error' && <span className="text-xs text-red-500">Failed</span>}
          </div>
        ))}
        {batchView.done && batchView.results && (
          <StatGrid stats={[
            { label: 'Processed', value: batchView.files.length },
            { label: 'Succeeded', value: batchView.results.length, color: '#10B981' },
            { label: 'Failed', value: batchView.files.length - batchView.results.length, color: batchView.files.length - batchView.results.length > 0 ? '#EF4444' : '#C8D8EC' },
            { label: 'Avg confidence', value: `${Math.round(batchView.results.reduce((a,r)=>a+(r.confidence_score||0),0)/(batchView.results.length||1)*100)}%`, color: confColor(batchView.results.reduce((a,r)=>a+(r.confidence_score||0),0)/(batchView.results.length||1)) },
          ]} />
        )}
      </div>
    )
    if (!result) return (
      <div className="flex flex-col items-center justify-center h-full gap-3 text-center">
        <FileSearch size={48} className="text-[#1A3456]" />
        <h3 className="text-base font-medium text-[#3D5A7A]">No incident selected</h3>
        <p className="text-sm text-[#2A4870] max-w-xs">Upload a ServiceNow incident JSON and run analysis, or select a previous result.</p>
      </div>
    )
    const tabProps = { result }
    return (
      <div>
        {approvalStatus === 'approved' && (
          <div className="flex items-center gap-2 bg-emerald-900/20 border border-emerald-800 rounded-lg p-3 mb-4 text-sm text-emerald-400">
            <Check size={16} /> Approved — output saved to outputs/{result.incident_number}_insight.json
          </div>
        )}
        {approvalStatus === 'rejected' && (
          <div className="flex items-center gap-2 bg-red-900/20 border border-red-800 rounded-lg p-3 mb-4 text-sm text-red-400">
            <X size={16} /> Rejected — output not saved
          </div>
        )}
        {activeTab === 'overview' && <OverviewTab {...tabProps} />}
        {activeTab === 'executive' && <ExecutiveTab {...tabProps} />}
        {activeTab === 'rca' && <RCATab {...tabProps} />}
        {activeTab === 'actions' && <ActionsTab {...tabProps} />}
        {activeTab === 'evidence' && <EvidenceTab {...tabProps} />}
        {activeTab === 'pipeline' && <PipelineTab {...tabProps} />}
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col bg-[#0A1628] text-white overflow-hidden min-w-0">
      {/* Navbar */}
      <nav className="bg-[#0D1E3A] border-b border-[#1E3356] px-6 flex items-center justify-between h-14 flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 bg-gradient-to-br from-[#1A4A8A] to-[#2563EB] rounded-md flex items-center justify-center">
            <Shield size={14} className="text-white" />
          </div>
          <div>
            <div className="text-[13px] font-semibold text-white">Incident Intelligence Platform</div>
            <div className="text-[10px] text-[#5B7EA6]">Powered by AI · ServiceNow</div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {tokenEst && <span className="text-[11px] text-[#3D5A7A]">{tokenEst} tokens (est.)</span>}
          <div className="flex items-center gap-1.5 text-[11px] text-[#5B7EA6]">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" /> Mistral · Local
          </div>
        </div>
      </nav>

      <div className="flex flex-1 overflow-hidden min-h-0 min-w-0">
        {/* Sidebar */}
        <aside className="w-72 bg-[#0D1E3A] border-r border-[#1E3356] flex flex-col overflow-hidden flex-shrink-0">
          <div className="p-4 border-b border-[#152B4A]">
            <SectionLabel>Upload incident</SectionLabel>
            <label className="block border border-dashed border-[#1E3A5F] rounded-xl p-5 text-center cursor-pointer hover:border-[#2563EB] hover:bg-[#111F35] transition-all">
              <FileSearch size={22} className="text-[#3D5A7A] mx-auto mb-2" />
              <p className="text-xs text-[#5B7EA6] mb-1">Drop JSON or click to browse</p>
              <p className="text-[10px] text-[#2A4870]">.json files only</p>
              <input type="file" accept=".json" className="hidden" onChange={e => handleFile(e.target.files[0])} />
            </label>
            {file && (
              <div className="flex items-center gap-2 mt-2 p-2 bg-emerald-900/20 border border-emerald-800 rounded-lg">
                <Check size={13} className="text-emerald-400 flex-shrink-0" />
                <span className="text-[11px] text-emerald-400 truncate">{file.name}</span>
              </div>
            )}
          </div>
          <div className="p-3 border-b border-[#152B4A] space-y-2">
            <button disabled={!file} onClick={runSingle}
              className="w-full flex items-center justify-center gap-2 py-2 text-sm font-semibold rounded-lg bg-[#1D4ED8] text-white hover:bg-[#2563EB] disabled:opacity-30 disabled:cursor-not-allowed transition-colors">
              <Play size={14} /> Run analysis
            </button>
            <label className="w-full flex items-center justify-center gap-2 py-2 text-xs font-medium rounded-lg bg-[#111F35] border border-[#1E3356] text-[#7BAFD4] hover:bg-[#152B4A] cursor-pointer transition-colors">
              <Files size={13} /> Run batch
              <input type="file" accept=".json" multiple className="hidden" onChange={e => runBatch(e.target.files)} />
            </label>
          </div>
          <div className="flex-1 overflow-y-auto p-3">
            <SectionLabel>History</SectionLabel>
            {history.length === 0
              ? <p className="text-xs text-[#2A4870]">No results yet</p>
              : history.map((r, i) => {
                const pc = priorityColor(r.priority)
                return (
                  <div key={i} onClick={() => handleHistorySelect(r)}
                    className="p-2.5 rounded-lg cursor-pointer border border-transparent hover:bg-[#111F35] hover:border-[#1E3356] mb-1 transition-all">
                    <div className="text-[13px] font-medium text-[#C8D8EC]">{r.incident_number}</div>
                    <div className="text-[11px] text-[#3D5A7A] mt-0.5 truncate">{(r.impacted_services||[]).join(', ')||'—'}</div>
                    <div className="flex items-center gap-1.5 mt-1.5">
                      <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${pc.bg} ${pc.text} ${pc.border}`}>{r.priority}</span>
                    </div>
                  </div>
                )
              })}
          </div>
          <div className="p-3 border-t border-[#152B4A]">
            <SectionLabel>Pipeline</SectionLabel>
            <NodeTrack doneCount={nodesDone} runningIdx={nodesRunning} />
          </div>
        </aside>

        {/* Main */}
        <main className="flex-1 flex flex-col overflow-hidden min-w-0">
          {/* Tab bar */}
          <div className="bg-[#0D1E3A] border-b border-[#1E3356] px-5 flex items-center flex-shrink-0 overflow-x-auto scrollbar-hide">
            {TABS.map(({ id, label, Icon }) => (
              <button key={id} onClick={() => setActiveTab(id)}
                className={`flex items-center gap-2 px-4 py-3.5 text-[13px] font-medium border-b-2 transition-all whitespace-nowrap flex-shrink-0
                  ${activeTab === id ? 'text-white border-[#2563EB]' : 'text-[#3D5A7A] border-transparent hover:text-[#7BAFD4] hover:border-[#2A4870]'}`}>
                <Icon size={14} />{label}
              </button>
            ))}
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6 bg-[#0A1628]">
            {mainContent()}
          </div>

          {/* Approval bar */}
          {result?.approval_needed && !approvalStatus && !pendingApproval && (
            <div className="bg-[#0B1E36] border-t-2 border-amber-500 px-5 py-3 flex items-center justify-between flex-shrink-0">
              <div className="flex items-center gap-2 text-sm text-amber-400">
                <AlertTriangle size={15} />
                <strong>{result.incident_number}</strong> requires director sign-off before saving
              </div>
              <div className="flex gap-2">
                <button onClick={() => setApprovalStatus('rejected')} className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-red-900/30 border border-red-800 text-red-400 rounded-lg hover:bg-red-900/50">
                  <X size={12} /> Reject
                </button>
                <button onClick={() => setApprovalStatus('approved')} className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-emerald-900/30 border border-emerald-800 text-emerald-400 rounded-lg hover:bg-emerald-900/50">
                  <Check size={12} /> Approve & save
                </button>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Batch history panel */}
      <BatchPanel history={history} onSelect={handleHistorySelect} panelHeight={panelHeight} onResize={setPanelHeight} />

      {/* Approval modal */}
      {pendingApproval && <ApprovalModal data={pendingApproval} onDecide={handleDecide} />}
    </div>
  )
}