import React from 'react';
import { AuditLogEntry } from '../types/api';

interface AuditTimelineProps {
  auditTrail: AuditLogEntry[];
}

export const AuditTimeline: React.FC<AuditTimelineProps> = ({ auditTrail }) => {
  if (!auditTrail || auditTrail.length === 0) {
    return (
      <div className="rounded-lg border border-[#262B33] bg-[#14171C]/80 p-6 text-center text-[#8B93A1] text-xs font-sans">
        No audit log entries recorded for this case.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-[#262B33] bg-[#14171C]/80 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#262B33] bg-[#14171C]">
        <h4 className="text-xs font-semibold text-[#ECEFF3] uppercase tracking-wider font-heading">
          Audit Trail ({auditTrail.length} Events)
        </h4>
        <span className="text-xs text-[#8B93A1] font-sans">
          Immutable Append-Only Log
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-[#262B33] bg-[#0B0D10]/60 text-[#8B93A1] text-[11px] uppercase font-sans font-medium">
              <th className="px-4 py-2.5">Time</th>
              <th className="px-4 py-2.5">Event</th>
              <th className="px-4 py-2.5">Actor</th>
              <th className="px-4 py-2.5">Outcome / Status</th>
              <th className="px-4 py-2.5">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#262B33]/60 font-sans">
            {auditTrail.map((entry, idx) => {
              const timeStr = new Date(entry.event_timestamp).toLocaleTimeString();
              return (
                <tr key={entry.id || idx} className="hover:bg-[#262B33]/20">
                  <td className="px-4 py-2.5 font-mono text-[#8B93A1] text-[11px] whitespace-nowrap">
                    {timeStr}
                  </td>
                  <td className="px-4 py-2.5 font-mono text-[#ECEFF3]/80 font-medium">
                    {entry.event_type}
                  </td>
                  <td className="px-4 py-2.5 text-[#8B93A1]">
                    {entry.actor}
                  </td>
                  <td className="px-4 py-2.5 text-[#ECEFF3]/70">
                    {entry.policy_outcome ? (
                      <span className="font-mono text-[#2DBE8F]">{entry.policy_outcome}</span>
                    ) : entry.new_status ? (
                      <span className="font-mono text-[#ECEFF3]/70">{entry.new_status}</span>
                    ) : (
                      <span className="text-[#8B93A1]/40">—</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 font-mono text-[#8B93A1] text-[11px] max-w-xs truncate">
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
