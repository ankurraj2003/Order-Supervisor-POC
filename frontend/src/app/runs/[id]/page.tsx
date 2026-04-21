'use client';

import { useEffect, useState, useRef, use } from 'react';
import Link from 'next/link';
import { runApi, simulatorApi, type Run, type Activity } from '@/lib/api';
import BoltIcon from '@mui/icons-material/Bolt';
import TrackChangesIcon from '@mui/icons-material/TrackChanges';
import PsychologyIcon from '@mui/icons-material/Psychology';
import NotificationsIcon from '@mui/icons-material/Notifications';
import SnoozeIcon from '@mui/icons-material/Snooze';
import EditNoteIcon from '@mui/icons-material/EditNote';
import PushPinIcon from '@mui/icons-material/PushPin';
import FlagIcon from '@mui/icons-material/Flag';
import SettingsIcon from '@mui/icons-material/Settings';
import PauseIcon from '@mui/icons-material/Pause';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import StopIcon from '@mui/icons-material/Stop';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import Inventory2Icon from '@mui/icons-material/Inventory2';
import CreditCardIcon from '@mui/icons-material/CreditCard';
import AttachMoneyIcon from '@mui/icons-material/AttachMoney';
import MovieIcon from '@mui/icons-material/Movie';
import ContentPasteIcon from '@mui/icons-material/ContentPaste';
import SaveIcon from '@mui/icons-material/Save';
import AssessmentIcon from '@mui/icons-material/Assessment';
import SyncIcon from '@mui/icons-material/Sync';

// ── Activity Timeline Component ────────────────────────────────────────────

function ActivityTimeline({ activities }: { activities: Activity[] }) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activities.length]);

  if (activities.length === 0) {
    return (
      <div className="text-center py-8 text-muted text-sm">
        No activities yet. The agent will start recording activities when it wakes up.
      </div>
    );
  }

  const typeLabels: Record<string, React.ReactNode> = {
    event: <><BoltIcon fontSize="inherit" className="mr-1 inline-block -mt-1" />Event</>,
    agent_action: <><TrackChangesIcon fontSize="inherit" className="mr-1 inline-block -mt-1" />Action</>,
    agent_reasoning: <><PsychologyIcon fontSize="inherit" className="mr-1 inline-block -mt-1" />Reasoning</>,
    wake_decision: <><NotificationsIcon fontSize="inherit" className="mr-1 inline-block -mt-1" />Wake Decision</>,
    sleep_decision: <><SnoozeIcon fontSize="inherit" className="mr-1 inline-block -mt-1" />Sleep Decision</>,
    state_update: <><EditNoteIcon fontSize="inherit" className="mr-1 inline-block -mt-1" />State Update</>,
    instruction_added: <><PushPinIcon fontSize="inherit" className="mr-1 inline-block -mt-1" />Instruction</>,
    final_output: <><FlagIcon fontSize="inherit" className="mr-1 inline-block -mt-1" />Final Output</>,
    system: <><SettingsIcon fontSize="inherit" className="mr-1 inline-block -mt-1" />System</>,
  };

  return (
    <div className="space-y-2 max-h-[600px] overflow-y-auto pr-2">
      {activities.map((activity, i) => (
        <div
          key={activity.id}
          className={`activity-${activity.type} glass-card p-3 pl-4 animate-fade-in`}
          style={{ animationDelay: `${Math.min(i * 20, 500)}ms` }}
        >
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-medium text-foreground">
              {typeLabels[activity.type] || activity.type}
              {activity.subtype && (
                <span className="text-muted ml-1.5">/ {activity.subtype.replace(/_/g, ' ')}</span>
              )}
            </span>
            <span className="text-xs text-muted font-mono">
              {new Date(activity.created_at).toLocaleTimeString()}
            </span>
          </div>
          <ActivityContent activity={activity} />
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}

function ActivityContent({ activity }: { activity: Activity }) {
  const content = activity.content;

  if (activity.type === 'event') {
    return (
      <div className="text-sm text-muted-light">
        {Object.entries(content).map(([key, value]) => (
          <div key={key} className="flex gap-2">
            <span className="text-muted">{key}:</span>
            <span>{String(value)}</span>
          </div>
        ))}
      </div>
    );
  }

  if (activity.type === 'agent_action') {
    const message = (content.message as string) || (content.note as string) || '';
    const priority = content.priority as string;
    const team = content.team as string;
    const subject = content.subject as string;
    const category = content.category as string;

    return (
      <div className="text-sm space-y-1">
        {team && <div className="text-accent text-xs">Team: {team}</div>}
        {subject && <div className="text-primary text-xs">Subject: {subject}</div>}
        {category && <div className="text-muted text-xs">Category: {category}</div>}
        {priority && (
          <span className={`inline-block px-2 py-0.5 rounded text-xs ${priority === 'urgent' ? 'bg-danger/20 text-danger' :
            priority === 'high' ? 'bg-warning/20 text-warning' :
              'bg-primary/20 text-primary'
            }`}>
            {priority}
          </span>
        )}
        <div className="text-muted-light">{message}</div>
      </div>
    );
  }

  if (activity.type === 'agent_reasoning') {
    return (
      <div className="text-sm text-muted-light whitespace-pre-wrap">
        {content.reasoning as string}
      </div>
    );
  }

  if (activity.type === 'wake_decision') {
    const decision = content.decision as string;
    return (
      <div className="text-sm">
        <span className={`inline-block px-2 py-0.5 rounded text-xs mr-2 ${decision === 'wake' ? 'bg-accent/20 text-accent' : 'bg-muted/20 text-muted-light'
          }`}>
          {decision}
        </span>
        <span className="text-muted-light">{content.reason as string}</span>
      </div>
    );
  }

  if (activity.type === 'sleep_decision') {
    return (
      <div className="text-sm text-muted-light">
        <div>Wake at: <span className="text-primary font-mono">{content.wake_at as string}</span></div>
        <div className="mt-1">{content.reason as string}</div>
      </div>
    );
  }

  if (activity.type === 'final_output') {
    const summary = content.summary as string | undefined;
    const actionsTaken = content.actions_taken as string[] | undefined;
    const keyLearnings = content.key_learnings as string[] | undefined;
    const recommendations = content.recommendations as string[] | undefined;

    return (
      <div className="text-sm space-y-3">
        {summary ? (
          <div>
            <div className="text-xs font-medium text-foreground mb-1">Summary</div>
            <div className="text-muted-light">{summary}</div>
          </div>
        ) : null}
        {actionsTaken && actionsTaken.length > 0 ? (
          <div>
            <div className="text-xs font-medium text-foreground mb-1">Actions Taken</div>
            <ul className="list-disc list-inside text-muted-light text-xs space-y-0.5">
              {actionsTaken.map((a, i) => <li key={i}>{a}</li>)}
            </ul>
          </div>
        ) : null}
        {keyLearnings && keyLearnings.length > 0 ? (
          <div>
            <div className="text-xs font-medium text-foreground mb-1">Key Learnings</div>
            <ul className="list-disc list-inside text-muted-light text-xs space-y-0.5">
              {keyLearnings.map((l, i) => <li key={i}>{l}</li>)}
            </ul>
          </div>
        ) : null}
        {recommendations && recommendations.length > 0 ? (
          <div>
            <div className="text-xs font-medium text-foreground mb-1">Recommendations</div>
            <ul className="list-disc list-inside text-muted-light text-xs space-y-0.5">
              {recommendations.map((r, i) => <li key={i}>{r}</li>)}
            </ul>
          </div>
        ) : null}
      </div>
    );
  }

  if (activity.type === 'instruction_added') {
    return (
      <div className="text-sm text-muted-light italic">
        &quot;{content.instruction as string}&quot;
      </div>
    );
  }

  // Default: show JSON
  return (
    <pre className="text-xs text-muted-light font-mono overflow-x-auto">
      {JSON.stringify(content, null, 2)}
    </pre>
  );
}

// ── Event Injector Component ───────────────────────────────────────────────

function EventInjector({ runId, onInjected }: { runId: string; onInjected: () => void }) {
  const [eventType, setEventType] = useState('payment_confirmed');
  const [payload, setPayload] = useState('{}');
  const [injecting, setInjecting] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  const eventTypes = [
    { value: 'order_created', label: 'Order Created', defaultPayload: '{"order_total": 129.99, "items": 3}' },
    { value: 'payment_confirmed', label: 'Payment Confirmed', defaultPayload: '{"method": "credit_card", "amount": 129.99}' },
    { value: 'payment_failed', label: 'Payment Failed', defaultPayload: '{"reason": "Insufficient funds"}' },
    { value: 'shipment_created', label: 'Shipment Created', defaultPayload: '{"carrier": "FedEx", "tracking": "FX123456789"}' },
    { value: 'shipment_delayed', label: 'Shipment Delayed', defaultPayload: '{"reason": "Weather conditions", "new_estimate": "7-10 days"}' },
    { value: 'delivered', label: 'Delivered', defaultPayload: '{"signed_by": "Customer"}' },
    { value: 'refund_requested', label: 'Refund Requested', defaultPayload: '{"reason": "Item damaged"}' },
    { value: 'customer_message_received', label: 'Customer Message', defaultPayload: '{"message": "Where is my order?"}' },
    { value: 'no_update_for_n_hours', label: 'No Update (N hours)', defaultPayload: '{"hours": 24}' },
  ];

  function handleEventTypeChange(value: string) {
    setEventType(value);
    const ev = eventTypes.find(e => e.value === value);
    if (ev) setPayload(ev.defaultPayload);
  }

  async function handleInject() {
    setInjecting(true);
    setResult(null);
    try {
      let parsedPayload = {};
      try { parsedPayload = JSON.parse(payload); } catch { /* ignore */ }
      const res = await runApi.injectEvent(runId, eventType, parsedPayload);
      setResult(res.message);
      onInjected();
    } catch (err) {
      setResult(err instanceof Error ? err.message : 'Failed to inject event');
    } finally {
      setInjecting(false);
    }
  }

  return (
    <div className="space-y-3">
      <div>
        <label className="text-xs text-muted font-medium block mb-1">Event Type</label>
        <select className="select" value={eventType} onChange={(e) => handleEventTypeChange(e.target.value)}>
          {eventTypes.map((et) => (
            <option key={et.value} value={et.value}>{et.label}</option>
          ))}
        </select>
      </div>
      <div>
        <label className="text-xs text-muted font-medium block mb-1">Payload (JSON)</label>
        <textarea
          className="textarea font-mono text-xs"
          value={payload}
          onChange={(e) => setPayload(e.target.value)}
          rows={3}
        />
      </div>
      <button
        onClick={handleInject}
        className="btn btn-primary w-full flex items-center justify-center gap-1.5"
        disabled={injecting}
      >
        {injecting ? <><SyncIcon fontSize="small" className="animate-spin" /> Injecting...</> : <><BoltIcon fontSize="small" /> Inject Event</>}
      </button>
      {result && (
        <div className="text-xs text-muted-light p-2 rounded bg-surface border border-border">
          {result}
        </div>
      )}
    </div>
  );
}

// ── Scenario Runner Component ──────────────────────────────────────────────

function ScenarioRunner({ runId, onFired }: { runId: string; onFired: () => void }) {
  const [scenario, setScenario] = useState('happy_path');
  const [firing, setFiring] = useState(false);

  const scenarios = [
    { value: 'happy_path', label: <span className="flex items-center"><CheckCircleIcon fontSize="inherit" className="mr-1.5" /> Happy Path</span>, desc: 'Order → Payment → Ship → Deliver' },
    { value: 'delayed_shipment', label: <span className="flex items-center"><Inventory2Icon fontSize="inherit" className="mr-1.5" /> Delayed Shipment</span>, desc: 'Includes delay + customer complaint' },
    { value: 'payment_failure', label: <span className="flex items-center"><CreditCardIcon fontSize="inherit" className="mr-1.5" /> Payment Failure</span>, desc: 'Failed payment then recovery' },
    { value: 'refund', label: <span className="flex items-center"><AttachMoneyIcon fontSize="inherit" className="mr-1.5" /> Refund Request</span>, desc: 'Full flow ending with refund' },
  ];

  async function handleFire() {
    setFiring(true);
    try {
      await simulatorApi.fireScenario(runId, scenario);
      onFired();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to fire scenario');
    } finally {
      setFiring(false);
    }
  }

  return (
    <div className="space-y-3">
      <div>
        <label className="text-xs text-muted font-medium block mb-1">Scenario</label>
        <select className="select" value={scenario} onChange={(e) => setScenario(e.target.value)}>
          {scenarios.map((s) => (
            <option key={s.value} value={s.value}>{s.label}</option>
          ))}
        </select>
        <div className="text-xs text-muted mt-1">
          {scenarios.find(s => s.value === scenario)?.desc}
        </div>
      </div>
      <button
        onClick={handleFire}
        className="btn btn-accent w-full flex items-center justify-center gap-1.5"
        disabled={firing}
      >
        {firing ? <><SyncIcon fontSize="small" className="animate-spin" /> Firing...</> : <><MovieIcon fontSize="small" /> Run Scenario</>}
      </button>
    </div>
  );
}

// ── Instructions Panel Component ───────────────────────────────────────────

function InstructionsPanel({ run, onAdded }: { run: Run; onAdded: () => void }) {
  const [instruction, setInstruction] = useState('');
  const [adding, setAdding] = useState(false);

  const presets = [
    'Prioritize speed over cost for this order.',
    'If shipment is delayed, escalate immediately.',
    'Do not contact the customer without human review.',
    'This is a VIP customer — extra care required.',
  ];

  async function handleAdd() {
    if (!instruction.trim()) return;
    setAdding(true);
    try {
      await runApi.addInstruction(run.id, instruction);
      setInstruction('');
      onAdded();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to add instruction');
    } finally {
      setAdding(false);
    }
  }

  return (
    <div className="space-y-3">
      {/* Existing instructions */}
      {run.additional_instructions && run.additional_instructions.length > 0 && (
        <div className="space-y-1.5">
          <div className="text-xs text-muted font-medium">Active Instructions</div>
          {run.additional_instructions.map((inst, i) => (
            <div key={i} className="text-xs text-muted-light p-2 rounded bg-surface border border-border italic">
              &quot;{inst}&quot;
            </div>
          ))}
        </div>
      )}

      {/* Presets */}
      <div>
        <div className="text-xs text-muted font-medium mb-1.5">Quick Add</div>
        <div className="flex flex-wrap gap-1.5">
          {presets.map((preset) => (
            <button
              key={preset}
              onClick={() => setInstruction(preset)}
              className="text-xs px-2 py-1 rounded bg-surface border border-border text-muted-light hover:text-foreground hover:border-border-bright transition-all"
            >
              {preset.slice(0, 40)}...
            </button>
          ))}
        </div>
      </div>

      {/* Custom instruction */}
      <div>
        <textarea
          className="textarea text-sm"
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          placeholder="Add a custom instruction for this run..."
          rows={2}
        />
      </div>
      <button
        onClick={handleAdd}
        className="btn btn-primary w-full flex items-center justify-center gap-1.5"
        disabled={adding || !instruction.trim()}
      >
        {adding ? <><SyncIcon fontSize="small" className="animate-spin" /> Adding...</> : <><PushPinIcon fontSize="small" /> Add Instruction</>}
      </button>
    </div>
  );
}

// ── State Viewer Component ─────────────────────────────────────────────────

function StateViewer({ state }: { state: Record<string, unknown> }) {
  return (
    <div className="space-y-2">
      {Object.entries(state).map(([key, value]) => (
        <div key={key} className="flex flex-col gap-0.5">
          <span className="text-xs text-muted font-medium">{key}</span>
          <span className="text-sm text-muted-light font-mono break-all">
            {typeof value === 'object' ? JSON.stringify(value) : String(value)}
          </span>
        </div>
      ))}
    </div>
  );
}

// ── Run Controls Component ─────────────────────────────────────────────────

function RunControls({ run, onAction }: { run: Run; onAction: () => void }) {
  const [acting, setActing] = useState(false);

  async function handleAction(action: 'pause' | 'resume' | 'terminate') {
    if (action === 'terminate' && !confirm('Are you sure you want to terminate this run? A final summary will be generated.')) {
      return;
    }
    setActing(true);
    try {
      if (action === 'pause') await runApi.pause(run.id);
      else if (action === 'resume') await runApi.resume(run.id);
      else if (action === 'terminate') await runApi.terminate(run.id);
      onAction();
    } catch (err) {
      alert(err instanceof Error ? err.message : `Failed to ${action} run`);
    } finally {
      setActing(false);
    }
  }

  const isActive = ['running', 'sleeping', 'paused'].includes(run.status);
  const isPaused = run.status === 'paused';

  return (
    <div className="flex gap-2">
      {isActive && !isPaused && (
        <button
          onClick={() => handleAction('pause')}
          className="btn btn-warning flex-1 flex justify-center items-center gap-1.5"
          disabled={acting}
        >
          <PauseIcon fontSize="small" /> Pause
        </button>
      )}
      {isPaused && (
        <button
          onClick={() => handleAction('resume')}
          className="btn btn-accent flex-1 flex justify-center items-center gap-1.5"
          disabled={acting}
        >
          <PlayArrowIcon fontSize="small" /> Resume
        </button>
      )}
      {isActive && (
        <button
          onClick={() => handleAction('terminate')}
          className="btn btn-danger flex-1 flex justify-center items-center gap-1.5"
          disabled={acting}
        >
          <StopIcon fontSize="small" /> Terminate
        </button>
      )}
    </div>
  );
}

// ── Main Run Detail Page ───────────────────────────────────────────────────

export default function RunDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const [run, setRun] = useState<Run | null>(null);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'timeline' | 'state' | 'summary'>('timeline');

  useEffect(() => {
    loadRun();
    const interval = setInterval(loadRun, 3000);
    return () => clearInterval(interval);
  }, [resolvedParams.id]);

  async function loadRun() {
    try {
      const [runData, activitiesData] = await Promise.all([
        runApi.get(resolvedParams.id),
        runApi.getActivities(resolvedParams.id, 500),
      ]);
      setRun(runData);
      setActivities(activitiesData);
    } catch (err) {
      console.error('Failed to load run:', err);
    } finally {
      setLoading(false);
    }
  }

  if (loading || !run) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="text-muted animate-pulse text-lg">Loading run details...</div>
      </div>
    );
  }

  const isActive = ['running', 'sleeping', 'paused'].includes(run.status);

  const statusColors: Record<string, string> = {
    running: 'from-cyan-500/20 to-cyan-600/5',
    sleeping: 'from-indigo-500/20 to-indigo-600/5',
    paused: 'from-amber-500/20 to-amber-600/5',
    completed: 'from-emerald-500/20 to-emerald-600/5',
    terminated: 'from-red-500/20 to-red-600/5',
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/runs" className="text-muted hover:text-foreground transition-colors">
          ← Back
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-foreground font-mono">{run.order_id}</h1>
            <span className={`status-${run.status} inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium`}>
              {run.status === 'running' && <span className="w-2 h-2 rounded-full bg-cyan-400 pulse-dot" />}
              {run.status === 'sleeping' && <span className="w-2 h-2 rounded-full bg-indigo-400" />}
              {run.status}
            </span>
          </div>
          <div className="text-sm text-muted mt-1">
            Supervisor: {run.supervisor?.name || 'Unknown'} • Created: {new Date(run.created_at).toLocaleString()}
            {run.next_wake_at && (
              <span className="ml-3 text-primary">Next wake: {new Date(run.next_wake_at).toLocaleString()}</span>
            )}
          </div>
        </div>
      </div>

      {/* Status Banner */}
      <div className={`rounded-xl bg-gradient-to-r ${statusColors[run.status] || ''} border border-border p-4`}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <div className="text-xs text-muted">Order Status</div>
            <div className="font-medium text-foreground">{(run.state?.order_status as string) || 'Unknown'}</div>
          </div>
          <div>
            <div className="text-xs text-muted">Events</div>
            <div className="font-medium text-foreground">{activities.filter(a => a.type === 'event').length}</div>
          </div>
          <div>
            <div className="text-xs text-muted">Actions</div>
            <div className="font-medium text-foreground">{activities.filter(a => a.type === 'agent_action').length}</div>
          </div>
          <div>
            <div className="text-xs text-muted">Instructions</div>
            <div className="font-medium text-foreground">{run.additional_instructions?.length || 0}</div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Timeline */}
        <div className="lg:col-span-2 space-y-4">
          {/* Tabs */}
          <div className="flex gap-1 p-1 bg-surface rounded-lg border border-border">
            {(['timeline', 'state', 'summary'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`flex-1 px-3 py-2 rounded-md text-sm font-medium transition-all ${activeTab === tab
                  ? 'bg-primary/20 text-primary'
                  : 'text-muted hover:text-foreground'
                  }`}
              >
                {tab === 'timeline' ? <span className="flex items-center justify-center gap-1.5"><ContentPasteIcon fontSize="small" /> Timeline</span> :
                  tab === 'state' ? <span className="flex items-center justify-center gap-1.5"><SaveIcon fontSize="small" /> State</span> :
                    <span className="flex items-center justify-center gap-1.5"><AssessmentIcon fontSize="small" /> Summary</span>}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div className="glass-card p-4">
            {activeTab === 'timeline' && (
              <ActivityTimeline activities={activities} />
            )}
            {activeTab === 'state' && (
              <StateViewer state={run.state || {}} />
            )}
            {activeTab === 'summary' && (
              run.final_summary ? (
                <ActivityContent activity={{
                  id: 'summary',
                  run_id: run.id,
                  type: 'final_output',
                  subtype: 'final_summary',
                  content: run.final_summary as unknown as Record<string, unknown>,
                  created_at: run.updated_at,
                }} />
              ) : (
                <div className="text-center py-8 text-muted text-sm">
                  {isActive
                    ? 'Final summary will be generated when the run completes.'
                    : 'No final summary available.'}
                </div>
              )
            )}
          </div>
        </div>

        {/* Right: Controls */}
        <div className="space-y-4">
          {/* Run Controls */}
          {isActive && (
            <div className="glass-card p-4">
              <h3 className="text-sm font-semibold text-foreground mb-3">Controls</h3>
              <RunControls run={run} onAction={loadRun} />
            </div>
          )}

          {/* Event Injector */}
          {isActive && (
            <div className="glass-card p-4">
              <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-1.5"><BoltIcon fontSize="small" className="text-primary" /> Inject Event</h3>
              <EventInjector runId={run.id} onInjected={loadRun} />
            </div>
          )}

          {/* Scenario Runner */}
          {isActive && (
            <div className="glass-card p-4">
              <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-1.5"><MovieIcon fontSize="small" className="text-accent" /> Event Scenario</h3>
              <ScenarioRunner runId={run.id} onFired={loadRun} />
            </div>
          )}

          {/* Instructions */}
          {isActive && (
            <div className="glass-card p-4">
              <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-1.5"><PushPinIcon fontSize="small" className="text-muted" /> Instructions</h3>
              <InstructionsPanel run={run} onAdded={loadRun} />
            </div>
          )}

          {/* Wake Guidance */}
          {run.wake_guidance && (
            <div className="glass-card p-4">
              <h3 className="text-sm font-semibold text-foreground mb-2 flex items-center gap-1.5"><NotificationsIcon fontSize="small" className="text-yellow-500" /> Wake Guidance</h3>
              <p className="text-xs text-muted-light">{run.wake_guidance}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
