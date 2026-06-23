import { useState, useEffect, useRef } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Cell } from 'recharts'

const WS_URL  = import.meta.env.VITE_WS_URL  || 'ws://localhost:8000/ws'
const API_URL = import.meta.env.VITE_API_URL  || 'http://localhost:8000'

const ALERT_COLOR = { NORMAL:'#00d4aa', WARN:'#ffaa00', ALERT:'#ff6b35', CRITICAL:'#ff3366' }
const NODE_COLOR  = { home:'#00aaff', car:'#aa55ff', office:'#00d4aa' }
const EMOTION_COLOR = { neutral:'#888', calm:'#00d4aa', happy:'#00aaff', angry:'#ff3366', fearful:'#ff6b35', surprised:'#ffaa00' }

function Badge({ level, small }) {
  const c = ALERT_COLOR[level] || '#888'
  return <span style={{ background:c+'22', border:`1px solid ${c}`, color:c, borderRadius:4, padding: small?'1px 6px':'2px 8px', fontSize:small?10:11, fontWeight:700 }}>{level}</span>
}

function NodeCard({ name, data }) {
  const c = NODE_COLOR[name] || '#888'
  const alive = data && (Date.now()/1000 - (data.ts||0)) < 8
  return (
    <div style={{ background:'#0d0d0d', border:`1px solid ${c}33`, borderRadius:8, padding:'12px 14px' }}>
      <div style={{ display:'flex', justifyContent:'space-between', marginBottom:8 }}>
        <span style={{ color:c, fontWeight:700, fontSize:13 }}>{name.toUpperCase()} NODE</span>
        <span style={{ color: alive?c:'#333', fontSize:10 }}>{alive?'● LIVE':'○ OFFLINE'}</span>
      </div>
      {data ? <>
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:6, marginBottom:8 }}>
          <div>
            <div style={{ color:'#555', fontSize:10 }}>Keyword</div>
            <div style={{ color: data.is_threat?'#ff3366':c, fontSize:12, fontWeight:700 }}>{data.keyword||'—'}</div>
          </div>
          <div>
            <div style={{ color:'#555', fontSize:10 }}>Confidence</div>
            <div style={{ color:'#ddd', fontSize:12 }}>{data.kw_conf?(data.kw_conf*100).toFixed(0)+'%':'—'}</div>
          </div>
          <div>
            <div style={{ color:'#555', fontSize:10 }}>Emotion</div>
            <div style={{ color: EMOTION_COLOR[data.emotion]||'#888', fontSize:12, fontWeight:700 }}>{data.emotion||'—'}</div>
          </div>
          <div>
            <div style={{ color:'#555', fontSize:10 }}>IF Score</div>
            <div style={{ color: (data.if_score||0)>0.65?'#ff3366':'#00d4aa', fontSize:12 }}>{data.if_score?.toFixed(3)||'—'}</div>
          </div>
        </div>
        <Badge level={data.alert_level||'NORMAL'} />
        {data.is_threat && <span style={{ marginLeft:8, color:'#ff3366', fontSize:10 }}>⚠ THREAT KEYWORD</span>}
      </> : <div style={{ color:'#333', fontSize:12 }}>Waiting for audio...</div>}
    </div>
  )
}

function AlertFeed({ alerts }) {
  return (
    <div style={{ background:'#0d0d0d', border:'1px solid #1e1e1e', borderRadius:8, overflow:'hidden' }}>
      <div style={{ padding:'8px 14px', borderBottom:'1px solid #1e1e1e', color:'#555', fontSize:11 }}>
        LIVE ALERT FEED — {alerts.length} events
      </div>
      <div style={{ maxHeight:260, overflowY:'auto' }}>
        {alerts.length === 0
          ? <div style={{ padding:14, color:'#333' }}>No alerts yet...</div>
          : alerts.map((a,i) => (
            <div key={i} style={{ display:'flex', alignItems:'center', gap:10, padding:'7px 14px', borderBottom:'1px solid #111' }}>
              <span style={{ color:'#444', fontSize:10, minWidth:65 }}>{a.time}</span>
              <Badge level={a.level||a.alert_level||'NORMAL'} small />
              <span style={{ color: NODE_COLOR[a.node_name]||'#888', fontSize:10, minWidth:45 }}>{a.node_name||''}</span>
              <span style={{ color:'#888', fontSize:11, flex:1 }}>
                {a.keyword ? `${a.keyword} · ${a.emotion}` : a.message || a.attack || ''}
              </span>
            </div>
          ))
        }
      </div>
    </div>
  )
}

export default function App() {
  const [nodes, setNodes]         = useState({})
  const [ifChart, setIfChart]     = useState([])
  const [alerts, setAlerts]       = useState([])
  const [flState, setFlState]     = useState({})
  const [blockCount, setBlockCount] = useState(0)
  const [kwCounts, setKwCounts]   = useState({})
  const [wsStatus, setWsStatus]   = useState('connecting')
  const wsRef = useRef(null)

  const ts = () => new Date().toLocaleTimeString('en',{hour12:false})

  useEffect(() => {
    function connect() {
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws
      ws.onopen  = () => setWsStatus('connected')
      ws.onclose = () => { setWsStatus('reconnecting'); setTimeout(connect, 3000) }
      ws.onerror = () => setWsStatus('error')
      ws.onmessage = e => {
        try { handle(JSON.parse(e.data)) } catch {}
      }
    }
    connect()
    return () => wsRef.current?.close()
  }, [])

  function handle(msg) {
    if (msg.type === 'audio_event') {
      setNodes(prev => ({ ...prev, [msg.node_name]: { ...msg, ts: msg.ts } }))
      setIfChart(prev => {
        const p = { time: ts(), [msg.node_name]: parseFloat((msg.if_score||0).toFixed(3)) }
        const last = prev[prev.length-1]
        if (last && last.time === p.time) return [...prev.slice(0,-1), {...last,...p}]
        return [...prev.slice(-60), p]
      })
      setBlockCount(n => n+1)
      setKwCounts(prev => {
        const kw = msg.keyword||'unknown'
        return { ...prev, [kw]: (prev[kw]||0)+1 }
      })
      if (msg.alert_level && msg.alert_level !== 'NORMAL') {
        setAlerts(prev => [{ ...msg, time:ts(), level:msg.alert_level }, ...prev].slice(0,50))
      }
    }
    if (msg.type === 'alert') {
      setAlerts(prev => [{ ...msg, time:ts() }, ...prev].slice(0,50))
    }
    if (msg.type === 'fl_update') {
      setFlState({ round:msg.round, valid:msg.n_valid, rejected:msg.n_rejected })
      if ((msg.n_rejected||0) > 0)
        setAlerts(prev => [{ time:ts(), level:'WARN', message:`FL round ${msg.round}: ${msg.n_rejected} malicious update(s) rejected` }, ...prev].slice(0,50))
    }
    if (msg.type === 'fl_alert') {
      setAlerts(prev => [{ time:ts(), level:'WARN', message: msg.message }, ...prev].slice(0,50))
    }
  }

  const kwChartData = Object.entries(kwCounts)
    .sort((a,b) => b[1]-a[1]).slice(0,8)
    .map(([kw,cnt]) => ({ kw: kw.slice(0,14), cnt }))

  const wsC = { connected:'#00d4aa', reconnecting:'#ffaa00', error:'#ff3366', connecting:'#555' }

  return (
    <div style={{ minHeight:'100vh', padding:20, fontFamily:'JetBrains Mono,monospace' }}>
      {/* Header */}
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:20, paddingBottom:14, borderBottom:'1px solid #1a1a1a' }}>
        <div>
          <div style={{ fontSize:15, fontWeight:700, color:'#00d4aa' }}>🎙 AUDIO SECURITY MONITOR</div>
          <div style={{ fontSize:10, color:'#444', marginTop:2 }}>Smart assistant · Home · Car · Office · CNN+LSTM+IF · Flower FL · Ganache</div>
        </div>
        <div style={{ display:'flex', alignItems:'center', gap:8 }}>
          <span style={{ width:8,height:8,borderRadius:'50%',background:wsC[wsStatus],display:'inline-block' }}/>
          <span style={{ color:wsC[wsStatus], fontSize:11 }}>{wsStatus.toUpperCase()}</span>
        </div>
      </div>

      {/* Stats row */}
      <div style={{ display:'flex', gap:10, marginBottom:18, flexWrap:'wrap' }}>
        {[
          ['BLOCKS', blockCount, '#00aaff'],
          ['FL ROUND', flState.round??'—', '#aa55ff'],
          ['FL CLIENTS', flState.valid??'—', '#aa55ff'],
          ['ALERTS', alerts.filter(a=>a.level!=='NORMAL').length, '#ff3366'],
        ].map(([l,v,c]) => (
          <div key={l} style={{ background:'#0d0d0d', border:'1px solid #1e1e1e', borderRadius:8, padding:'10px 14px', minWidth:110 }}>
            <div style={{ color:'#555', fontSize:10, marginBottom:4 }}>{l}</div>
            <div style={{ color:c, fontSize:20, fontWeight:700 }}>{v}</div>
          </div>
        ))}
      </div>

      {/* Node cards */}
      <div style={{ display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:12, marginBottom:18 }}>
        {['home','car','office'].map(n => <NodeCard key={n} name={n} data={nodes[n]} />)}
      </div>

      {/* IF Score chart */}
      <div style={{ background:'#0d0d0d', border:'1px solid #1e1e1e', borderRadius:8, padding:14, marginBottom:14 }}>
        <div style={{ color:'#555', fontSize:11, marginBottom:10 }}>ISOLATION FOREST SCORE — all nodes live</div>
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={ifChart}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1a1a1a"/>
            <XAxis dataKey="time" tick={{fill:'#444',fontSize:10}} interval="preserveStartEnd"/>
            <YAxis domain={[0,1]} tick={{fill:'#444',fontSize:10}}/>
            <Tooltip contentStyle={{background:'#111',border:'1px solid #333',borderRadius:4,fontSize:11}}/>
            <Line type="monotone" dataKey="home"   stroke="#00aaff" dot={false} strokeWidth={1.5} name="Home"/>
            <Line type="monotone" dataKey="car"    stroke="#aa55ff" dot={false} strokeWidth={1.5} name="Car"/>
            <Line type="monotone" dataKey="office" stroke="#00d4aa" dot={false} strokeWidth={1.5} name="Office"/>
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Keyword frequency */}
      {kwChartData.length > 0 && (
        <div style={{ background:'#0d0d0d', border:'1px solid #1e1e1e', borderRadius:8, padding:14, marginBottom:14 }}>
          <div style={{ color:'#555', fontSize:11, marginBottom:10 }}>KEYWORD FREQUENCY</div>
          <ResponsiveContainer width="100%" height={140}>
            <BarChart data={kwChartData} layout="vertical">
              <XAxis type="number" tick={{fill:'#444',fontSize:10}}/>
              <YAxis type="category" dataKey="kw" tick={{fill:'#888',fontSize:10}} width={100}/>
              <Tooltip contentStyle={{background:'#111',border:'1px solid #333',fontSize:11}}/>
              <Bar dataKey="cnt" name="Count" radius={[0,4,4,0]}>
                {kwChartData.map((e,i) => {
                  const isThreat = ['unlock','override','disable','emergency','bypass','deactivate'].some(t => e.kw.includes(t))
                  return <Cell key={i} fill={isThreat?'#ff3366':'#00aaff'}/>
                })}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <div style={{ display:'flex', gap:16, marginTop:6 }}>
            <span style={{ color:'#00aaff', fontSize:10 }}>■ Normal command</span>
            <span style={{ color:'#ff3366', fontSize:10 }}>■ Threat keyword</span>
          </div>
        </div>
      )}

      {/* Alert feed + FL status */}
      <div style={{ display:'grid', gridTemplateColumns:'1fr 220px', gap:14 }}>
        <AlertFeed alerts={alerts}/>
        <div style={{ background:'#0d0d0d', border:'1px solid #1e1e1e', borderRadius:8, padding:14 }}>
          <div style={{ color:'#aa55ff', fontSize:11, fontWeight:700, marginBottom:10 }}>🌸 FLOWER FL</div>
          {[['Round',flState.round??'—'],['Valid clients',flState.valid??'—'],['Rejected',flState.rejected??'0'],['Min clients','3'],].map(([k,v])=>(
            <div key={k} style={{ display:'flex',justifyContent:'space-between',padding:'4px 0',borderBottom:'1px solid #111',fontSize:11 }}>
              <span style={{ color:'#555' }}>{k}</span>
              <span style={{ color:'#aa55ff' }}>{v}</span>
            </div>
          ))}
          <div style={{ marginTop:10, color:'#333', fontSize:10, lineHeight:1.6 }}>
            Edge nodes train locally.<br/>Only weights sent to server.<br/>Raw audio never leaves edge.
          </div>
        </div>
      </div>
    </div>
  )
}
