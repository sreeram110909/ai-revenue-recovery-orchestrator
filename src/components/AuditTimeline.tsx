import React from 'react';
import { AuditLogEntry } from '../types/api';

interface AuditTimelineProps {
  auditTrail: AuditLogEntry[];
}

export const AuditTimeline: React.FC<AuditTimelineProps> = ({ auditTrail }) => {
  if (!auditTrail || auditTrail.length === 0) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-900/30 p-6 text-center text-slate-500 text-xs font-sans">
        No audit log entries recorded for this case.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/30 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800 bg-slate-900/80">
        <h4 className="text-xs font-semibold text-white uppercase tracking-wider font-sans">
          Audit Trail ({auditTrail.length} Events)
        </h4>
        <span className="text-xs text-slate-500 font-sans">
          Immutable Append-Only Log
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-slate-800 bg-slate-950/60 text-slate-400 text-[11px] uppercase font-sans font-medium">
              <th className="px-4 py-2.5">Time</th>
              <th className="px-4 py-2.5">Event</th>
              <th className="px-4 py-2.5">Actor</th>
              <th className="px-4 py-2.5">Outcome / Status</th>
              <th className="px-4 py-2.5">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-sans">
            {auditTrail.map((entry, idx) => {
              const timeStr = new Date(entry.event_timestamp).toLocaleTimeString();
              return (
                <tr key={entry.id || idx} className="hover:bg-slate-800/20">
                  <td className="px-4 py-2.5 font-mono text-slate-400 text-[11px] whitespace-nowrap">
                    {timeStr}
                  </td>
                  <td className="px-4 py-2.5 font-mono text-slate-200 font-medium">
                    {entry.event_type}
                  </td>
                  <td className="px-4 py-2.5 text-slate-400">
                    {entry.actor}
                  </td>
                  <td className="px-4 py-2.5 text-slate-300">
                    {entry.policy_outcome ? (
                      <span className="font-mono text-emerald-400">{entry.policy_outcome}</span>
                    ) : entry.new_status ? (
                      <span className="font-mono text-slate-300">{entry.new_status}</span>
                    ) : (
                      <span className="text-slate-600">—</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 font-mono text-slate-400 text-[11px] max-w-xs truncate">
                    {entry.details ? JSON.stringify(entry.details) : '—'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
