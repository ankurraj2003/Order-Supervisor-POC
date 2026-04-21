'use client';

import { useEffect, useState } from 'react';
import { supervisorApi, type Supervisor } from '@/lib/api';
import SmartToyIcon from '@mui/icons-material/SmartToy';

export default function SupervisorsPage() {
  const [supervisors, setSupervisors] = useState<Supervisor[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadSupervisors();
  }, []);

  async function loadSupervisors() {
    try {
      const data = await supervisorApi.list();
      setSupervisors(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load supervisors');
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="text-muted animate-pulse text-lg">Loading supervisors...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Supervisor Templates</h1>
          <p className="text-muted text-sm mt-1">Configure AI supervisor behavior and actions</p>
        </div>
        <button onClick={() => setShowCreate(!showCreate)} className="btn btn-primary">
          {showCreate ? 'Cancel' : '+ New Template'}
        </button>
      </div>

      {error && (
        <div className="glass-card p-4 border-danger/30 bg-danger/5">
          <div className="text-danger text-sm">{error}</div>
        </div>
      )}

      {/* Create Form */}
      {showCreate && (
        <CreateSupervisorForm
          onCreated={() => {
            setShowCreate(false);
            loadSupervisors();
          }}
        />
      )}

      {/* Supervisor Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {supervisors.map((sup, i) => (
          <div key={sup.id} className="glass-card p-5 animate-fade-in" style={{ animationDelay: `${i * 80}ms` }}>
            <div className="flex items-start justify-between mb-3">
              <div>
                <h3 className="font-semibold text-foreground text-lg">{sup.name}</h3>
                <div className="text-xs text-muted mt-1">
                  Created {new Date(sup.created_at).toLocaleDateString()}
                </div>
              </div>
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center text-primary border border-primary/20">
                <SmartToyIcon />
              </div>
            </div>

            <p className="text-sm text-muted-light mb-4 line-clamp-3">{sup.base_instruction}</p>

            <div className="space-y-3">
              {/* Available Actions */}
              <div>
                <div className="text-xs text-muted font-medium mb-1.5">Available Actions</div>
                <div className="flex flex-wrap gap-1.5">
                  {sup.available_actions.map((action) => (
                    <span key={action} className="px-2 py-0.5 rounded-md bg-primary/10 text-primary text-xs border border-primary/20">
                      {action.replace(/_/g, ' ')}
                    </span>
                  ))}
                </div>
              </div>

              {/* Wake Behavior */}
              {sup.default_wake_behavior ? (
                <div>
                  <div className="text-xs text-muted font-medium mb-1">Wake Behavior</div>
                  <div className="text-xs text-muted-light">
                    Interval: {String((sup.default_wake_behavior as Record<string, unknown>).wake_interval_minutes ?? 30)}min •{' '}
                    Aggressiveness: {String((sup.default_wake_behavior as Record<string, unknown>).aggressiveness ?? 'balanced')}
                  </div>
                </div>
              ) : null}

              {/* Wake Guidance */}
              {sup.wake_guidance && (
                <div>
                  <div className="text-xs text-muted font-medium mb-1">Wake Guidance</div>
                  <div className="text-xs text-muted-light line-clamp-2">{sup.wake_guidance}</div>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function CreateSupervisorForm({ onCreated }: { onCreated: () => void }) {
  const [name, setName] = useState('');
  const [instruction, setInstruction] = useState('');
  const [wakeGuidance, setWakeGuidance] = useState('');
  const [aggressiveness, setAggressiveness] = useState('balanced');
  const [wakeInterval, setWakeInterval] = useState(30);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      await supervisorApi.create({
        name,
        base_instruction: instruction,
        available_actions: [
          'message_fulfillment_team',
          'message_payments_team',
          'message_logistics_team',
          'message_customer',
          'create_internal_note',
        ],
        default_wake_behavior: {
          wake_interval_minutes: wakeInterval,
          aggressiveness,
        },
        model_config_data: { model: 'llama-3.3-70b-versatile', temperature: 0.3 },
        wake_guidance: wakeGuidance || undefined,
      });
      onCreated();
    } catch {
      alert('Failed to create supervisor');
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="glass-card p-6 space-y-4 animate-slide-in">
      <h3 className="text-lg font-semibold text-foreground">Create Supervisor Template</h3>

      <div>
        <label className="text-sm text-muted-light block mb-1">Name *</label>
        <input
          type="text"
          className="input"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g., VIP Order Supervisor"
          required
        />
      </div>

      <div>
        <label className="text-sm text-muted-light block mb-1">Base Instruction *</label>
        <textarea
          className="textarea"
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          placeholder="Describe how this supervisor should behave..."
          required
        />
      </div>

      <div>
        <label className="text-sm text-muted-light block mb-1">Wake Guidance</label>
        <textarea
          className="textarea"
          value={wakeGuidance}
          onChange={(e) => setWakeGuidance(e.target.value)}
          placeholder="Instructions for when the classifier should wake the agent..."
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-sm text-muted-light block mb-1">Wake Interval (minutes)</label>
          <input
            type="number"
            className="input"
            value={wakeInterval}
            onChange={(e) => setWakeInterval(Number(e.target.value))}
            min={1}
            max={120}
          />
        </div>
        <div>
          <label className="text-sm text-muted-light block mb-1">Aggressiveness</label>
          <select
            className="select"
            value={aggressiveness}
            onChange={(e) => setAggressiveness(e.target.value)}
          >
            <option value="low">Low</option>
            <option value="balanced">Balanced</option>
            <option value="high">High</option>
          </select>
        </div>
      </div>

      <div className="flex gap-3 pt-2">
        <button type="submit" className="btn btn-accent" disabled={saving || !name || !instruction}>
          {saving ? 'Creating...' : 'Create Supervisor'}
        </button>
      </div>
    </form>
  );
}
