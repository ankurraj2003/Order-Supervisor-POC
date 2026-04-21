'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { runApi, supervisorApi, type RunListItem, type Supervisor } from '@/lib/api';
import { StatusBadge } from '../page';
import ContentPasteIcon from '@mui/icons-material/ContentPaste';
import RocketLaunchIcon from '@mui/icons-material/RocketLaunch';

export default function RunsPage() {
  const [runs, setRuns] = useState<RunListItem[]>([]);
  const [supervisors, setSupervisors] = useState<Supervisor[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [filter, setFilter] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
    const interval = setInterval(() => loadRuns(), 5000);
    return () => clearInterval(interval);
  }, [filter]);

  async function loadData() {
    try {
      const [runsData, supsData] = await Promise.all([
        runApi.list(filter || undefined),
        supervisorApi.list(),
      ]);
      setRuns(runsData);
      setSupervisors(supsData);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }

  async function loadRuns() {
    try {
      const runsData = await runApi.list(filter || undefined);
      setRuns(runsData);
    } catch {
      // Silent refresh failure
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="text-muted animate-pulse text-lg">Loading runs...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Runs</h1>
          <p className="text-muted text-sm mt-1">Manage and monitor order supervision runs</p>
        </div>
        <button onClick={() => setShowCreate(!showCreate)} className="btn btn-primary">
          {showCreate ? 'Cancel' : '+ Start Run'}
        </button>
      </div>

      {error && (
        <div className="glass-card p-4 border-danger/30 bg-danger/5">
          <div className="text-danger text-sm">{error}</div>
        </div>
      )}

      {/* Create Run Form */}
      {showCreate && supervisors.length > 0 && (
        <CreateRunForm
          supervisors={supervisors}
          onCreated={() => {
            setShowCreate(false);
            loadData();
          }}
        />
      )}

      {/* Filters */}
      <div className="flex gap-2">
        {['', 'running', 'sleeping', 'paused', 'completed', 'terminated'].map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              filter === s
                ? 'bg-primary/20 text-primary border border-primary/30'
                : 'bg-surface text-muted border border-border hover:border-border-bright'
            }`}
          >
            {s || 'All'}
          </button>
        ))}
      </div>

      {/* Runs Table */}
      {runs.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <div className="text-4xl mb-4 flex justify-center text-muted"><ContentPasteIcon fontSize="inherit" /></div>
          <div className="text-foreground font-medium mb-2">No runs found</div>
          <div className="text-muted text-sm">
            {filter ? `No runs with status "${filter}"` : 'Start your first run to begin monitoring orders.'}
          </div>
        </div>
      ) : (
        <div className="glass-card overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left p-4 text-xs font-medium text-muted uppercase tracking-wider">Order ID</th>
                <th className="text-left p-4 text-xs font-medium text-muted uppercase tracking-wider">Supervisor</th>
                <th className="text-left p-4 text-xs font-medium text-muted uppercase tracking-wider">Status</th>
                <th className="text-left p-4 text-xs font-medium text-muted uppercase tracking-wider">Next Wake</th>
                <th className="text-left p-4 text-xs font-medium text-muted uppercase tracking-wider">Created</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run, i) => (
                <tr
                  key={run.id}
                  className="border-b border-border/50 hover:bg-surface-hover transition-colors cursor-pointer animate-fade-in"
                  style={{ animationDelay: `${i * 30}ms` }}
                >
                  <td className="p-4">
                    <Link href={`/runs/${run.id}`} className="font-mono text-sm text-primary hover:text-primary-dim transition-colors">
                      {run.order_id}
                    </Link>
                  </td>
                  <td className="p-4 text-sm text-muted-light">{run.supervisor_name || '—'}</td>
                  <td className="p-4"><StatusBadge status={run.status} /></td>
                  <td className="p-4 text-xs text-muted">
                    {run.next_wake_at ? new Date(run.next_wake_at).toLocaleString() : '—'}
                  </td>
                  <td className="p-4 text-xs text-muted">
                    {new Date(run.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function CreateRunForm({ supervisors, onCreated }: { supervisors: Supervisor[]; onCreated: () => void }) {
  const [supervisorId, setSupervisorId] = useState(supervisors[0]?.id || '');
  const [orderId, setOrderId] = useState(`ORD-${String(Date.now()).slice(-6)}`);
  const [creating, setCreating] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    try {
      await runApi.create({
        supervisor_id: supervisorId,
        order_id: orderId,
        initial_context: {
          order_total: 129.99,
          items: 3,
          customer: 'John Doe',
          shipping_address: '123 Main St, Springfield, IL 62701',
        },
      });
      onCreated();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to create run');
    } finally {
      setCreating(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="glass-card p-6 space-y-4 animate-slide-in">
      <h3 className="text-lg font-semibold text-foreground">Start New Run</h3>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-sm text-muted-light block mb-1">Supervisor Template *</label>
          <select
            className="select"
            value={supervisorId}
            onChange={(e) => setSupervisorId(e.target.value)}
            required
          >
            {supervisors.map((sup) => (
              <option key={sup.id} value={sup.id}>{sup.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-sm text-muted-light block mb-1">Order ID *</label>
          <input
            type="text"
            className="input"
            value={orderId}
            onChange={(e) => setOrderId(e.target.value)}
            placeholder="e.g., ORD-001"
            required
          />
        </div>
      </div>

      <div className="flex gap-3 pt-2">
        <button type="submit" className="btn btn-accent flex items-center gap-1.5" disabled={creating || !supervisorId || !orderId}>
          {creating ? 'Starting...' : <><RocketLaunchIcon fontSize="small" /> Start Run</>}
        </button>
      </div>
    </form>
  );
}
