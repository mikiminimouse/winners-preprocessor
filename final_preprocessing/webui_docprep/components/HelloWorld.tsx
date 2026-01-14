/**
 * HelloWorld Component
 * Test component to verify the development pipeline
 */
import React, { useState, useEffect } from 'react';
import { getHello, HelloResponse } from '../services/helloService';
import { CheckCircle2, Loader2, AlertCircle } from 'lucide-react';

const HelloWorld: React.FC = () => {
  const [data, setData] = useState<HelloResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchHello = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await getHello();
        setData(response);
      } catch (err) {
        console.error('Failed to fetch hello message:', err);
        setError(err instanceof Error ? err.message : 'Unknown error occurred');
      } finally {
        setLoading(false);
      }
    };

    fetchHello();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8 bg-white rounded-[32px] border border-slate-200 shadow-sm">
        <div className="flex items-center gap-3 text-slate-600">
          <Loader2 size={24} className="animate-spin" />
          <span className="font-medium">Loading hello message...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center p-8 bg-rose-50 rounded-[32px] border border-rose-200">
        <div className="flex items-center gap-3 text-rose-700">
          <AlertCircle size={24} />
          <div>
            <div className="font-bold">Error Loading Message</div>
            <div className="text-sm opacity-80">{error}</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-[32px] p-8 border border-blue-100 shadow-sm">
      <div className="flex items-center gap-4 mb-4">
        <div className="p-3 bg-emerald-100 rounded-xl">
          <CheckCircle2 size={24} className="text-emerald-600" />
        </div>
        <div>
          <h2 className="text-2xl font-black text-slate-800">Hello World!</h2>
          <p className="text-sm text-slate-500 font-medium">Development Pipeline Test</p>
        </div>
      </div>

      {data && (
        <div className="space-y-3">
          <div className="bg-white rounded-xl p-4 border border-slate-200">
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">
              Message
            </div>
            <div className="text-lg font-bold text-slate-800">
              {data.message}
            </div>
          </div>

          <div className="bg-white rounded-xl p-4 border border-slate-200">
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">
              Timestamp
            </div>
            <div className="text-sm font-mono text-slate-600">
              {data.timestamp}
            </div>
          </div>

          <div className="bg-emerald-50 rounded-xl p-4 border border-emerald-100">
            <div className="text-xs font-bold text-emerald-600 uppercase tracking-wider mb-1">
              Status
            </div>
            <div className="text-sm text-emerald-700 font-medium">
              ✅ Pipeline is working correctly!
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default HelloWorld;
