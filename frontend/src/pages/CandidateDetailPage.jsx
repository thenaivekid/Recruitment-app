import React, { useEffect, useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getCandidate, submitScore, generateSummary, updateCandidate } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip as RechartsTooltip } from 'recharts';

const STATUS_COLORS = {
  new: 'badge-blue', reviewed: 'badge-yellow',
  hired: 'badge-green', rejected: 'badge-red', archived: 'badge-gray',
};

const CATEGORIES = ['Technical', 'Communication', 'Problem Solving', 'Culture Fit', 'Leadership'];
const STATUSES = ['new', 'reviewed', 'hired', 'rejected', 'archived'];

export default function CandidateDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { isAdmin } = useAuth();
  const queryClient = useQueryClient();

  const { data: candidate, isLoading: loading, isError } = useQuery({
    queryKey: ['candidate', id],
    queryFn: async () => {
      const res = await getCandidate(id);
      return res.data;
    }
  });

  // Calculate aggregated averages for Radar Chart visually
  const chartData = useMemo(() => {
    if (!candidate?.scores?.length) return [];
    const catMap = {};
    candidate.scores.forEach(s => {
      if (!catMap[s.category]) catMap[s.category] = { total: 0, count: 0 };
      catMap[s.category].total += s.score;
      catMap[s.category].count += 1;
    });
    return Object.entries(catMap).map(([category, data]) => ({
      subject: category,
      score: Number((data.total / data.count).toFixed(1)),
      fullMark: 5,
    }));
  }, [candidate?.scores]);

  const [scoreForm, setScoreForm] = useState({ category: CATEGORIES[0], score: 3, note: '' });
  const [notes, setNotes] = useState('');

  // Sync internal notes to state when candidate data loads
  useEffect(() => {
    if (candidate) setNotes(candidate.internal_notes || '');
  }, [candidate]);

  useEffect(() => {
    // Stretch goal: Real-time SSE score updates
    const token = localStorage.getItem('token');
    if (!token) return;

    const baseUrl = import.meta.env.VITE_API_URL || '';
    const sse = new EventSource(`${baseUrl}/candidates/${id}/stream?token=${token}`);

    sse.onmessage = (event) => {
      try {
        const newScore = JSON.parse(event.data);
        queryClient.setQueryData(['candidate', id], (oldData) => {
          if (!oldData) return oldData;
          if (oldData.scores.some((s) => s.id === newScore.id)) return oldData;
          return { ...oldData, scores: [newScore, ...oldData.scores] };
        });
      } catch (e) {
        console.error("SSE parse error", e);
      }
    };

    return () => sse.close();
  }, [id, queryClient]);

  const scoreMutation = useMutation({
    mutationFn: (data) => submitScore(id, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['candidate', id] })
  });

  const summaryMutation = useMutation({
    mutationFn: () => generateSummary(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['candidate', id] })
  });

  const notesMutation = useMutation({
    mutationFn: (newNotes) => updateCandidate(id, { internal_notes: newNotes })
  });

  const statusMutation = useMutation({
    mutationFn: (newStatus) => updateCandidate(id, { status: newStatus }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['candidate', id] })
  });

  if (loading) return <div className="center-spinner full-page"><div className="spinner" /></div>;
  if (isError) return <div className="center-spinner full-page"><div className="alert alert-error">Candidate not found.</div></div>;

  return (
    <div className="app-layout">
      <nav className="topnav">
        <button className="btn btn-ghost back-btn" onClick={() => navigate('/')}>← Back</button>
        <div className="topnav-brand">
          <img src="https://techkraftinc.com/wp-content/uploads/2024/05/TechKraft-Logo.svg" alt="TechKraft" />
        </div>
        <div className="topnav-right" />
      </nav>

      <main className="content detail-grid">
        {/* Left: Profile + Scores */}
        <div className="detail-left">
          {/* Profile card */}
          <div className="card">
            <div className="profile-header">
              <div className="avatar">{candidate.name.charAt(0)}</div>
              <div>
                <h2 className="candidate-full-name">{candidate.name}</h2>
                <div className="candidate-email">{candidate.email}</div>
                <div className="candidate-role">{candidate.role_applied}</div>
              </div>
            </div>
            <div className="profile-meta">
              <div className="meta-row">
                <span className="meta-label">Status</span>
                {isAdmin ? (
                  <select
                    className="status-select"
                    value={candidate.status}
                    disabled={statusMutation.isPending}
                    onChange={(e) => statusMutation.mutate(e.target.value)}
                  >
                    {STATUSES.map((s) => (
                      <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
                    ))}
                  </select>
                ) : (
                  <span className={`badge ${STATUS_COLORS[candidate.status] || 'badge-gray'}`}>
                    {candidate.status}
                  </span>
                )}
              </div>
              <div className="meta-row">
                <span className="meta-label">Applied</span>
                <span>{new Date(candidate.created_at).toLocaleDateString()}</span>
              </div>
              <div className="meta-row">
                <span className="meta-label">Skills</span>
                <div className="skill-tags">
                  {candidate.skills.map((s) => <span key={s} className="skill-tag">{s}</span>)}
                </div>
              </div>
            </div>
          </div>

          {/* Scores panel with beautiful Recharts Radar Chart */}
          <div className="card">
            <h3 className="card-title">Scores {isAdmin && <span className="dimmed">(all reviewers)</span>}</h3>
            {chartData.length > 0 && (
              <div style={{ width: '100%', height: 320, marginBottom: '2rem' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart cx="50%" cy="50%" outerRadius="75%" data={chartData}>
                    <PolarGrid stroke="#e2e8f0" />
                    <PolarAngleAxis dataKey="subject" tick={{ fill: '#475569', fontSize: 13 }} />
                    <PolarRadiusAxis angle={30} domain={[0, 5]} tick={{ fill: '#94a3b8' }} />
                    <Radar 
                      name="Avg Score" 
                      dataKey="score" 
                      stroke="#f97316" 
                      fill="#f97316" 
                      fillOpacity={0.65} 
                    />
                    <RechartsTooltip 
                      formatter={(value) => [`${value} / 5`, 'Avg Score']}
                      contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            )}
            
            {candidate.scores.length === 0 ? (
              <p className="dimmed">No scores yet.</p>
            ) : (
              <div className="scores-list">
                {candidate.scores.map((s) => (
                  <div key={s.id} className="score-row">
                    <div className="score-left">
                      <span className="score-category">{s.category}</span>
                      {isAdmin && s.reviewer_email && (
                        <span className="reviewer-email">by {s.reviewer_email}</span>
                      )}
                      {s.note && <span className="score-note">{s.note}</span>}
                    </div>
                    <div className={`score-value score-${s.score}`}>{s.score}/5</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right: Scoring form + AI Summary + Admin Notes */}
        <div className="detail-right">
          {/* Score submission form */}
          <div className="card">
            <h3 className="card-title">Submit Score</h3>
            <form onSubmit={(e) => { e.preventDefault(); scoreMutation.mutate(scoreForm); }} className="score-form">
              {scoreMutation.isError && <div className="alert alert-error">{scoreMutation.error?.response?.data?.detail || 'Failed to submit score.'}</div>}
              {scoreMutation.isSuccess && <div className="alert alert-success">Score submitted!</div>}
              <div className="form-group">
                <label htmlFor="category">Category</label>
                <select
                  id="category"
                  value={scoreForm.category}
                  onChange={(e) => setScoreForm((f) => ({ ...f, category: e.target.value }))}
                >
                  {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label htmlFor="score-value">Score (1–5)</label>
                <div className="star-row">
                  {[1, 2, 3, 4, 5].map((n) => (
                    <button
                      key={n}
                      type="button"
                      className={`star-btn ${scoreForm.score >= n ? 'active' : ''}`}
                      onClick={() => setScoreForm((f) => ({ ...f, score: n }))}
                    >★</button>
                  ))}
                  <span className="score-label">{scoreForm.score}/5</span>
                </div>
              </div>
              <div className="form-group">
                <label htmlFor="note">Note (optional)</label>
                <textarea
                  id="note"
                  rows={3}
                  value={scoreForm.note}
                  onChange={(e) => setScoreForm((f) => ({ ...f, note: e.target.value }))}
                  placeholder="Add context or observations…"
                />
              </div>
              <button type="submit" className="btn btn-primary" disabled={scoreMutation.isPending}>
                {scoreMutation.isPending ? <span className="spinner-sm" /> : 'Submit Score'}
              </button>
            </form>
          </div>

          {/* AI Summary */}
          <div className="card">
            <h3 className="card-title">AI Summary</h3>
            {candidate.ai_summary ? (
              <p className="ai-summary-text">{candidate.ai_summary}</p>
            ) : (
              <p className="dimmed">No summary generated yet.</p>
            )}
            {summaryMutation.isError && <div className="alert alert-error" style={{marginTop: '0.75rem'}}>Failed to generate summary. Please try again.</div>}
            <button
              className="btn btn-secondary"
              style={{ marginTop: '1rem' }}
              onClick={() => summaryMutation.mutate()}
              disabled={summaryMutation.isPending}
            >
              {summaryMutation.isPending ? (
                <><span className="spinner-sm" /> Generating…</>
              ) : (
                candidate.ai_summary ? '↺ Regenerate Summary' : '✨ Generate AI Summary'
              )}
            </button>
            {summaryMutation.isPending && (
              <p className="dimmed" style={{ marginTop: '0.5rem', fontSize: '0.8rem' }}>
                Analyzing candidate profile via LLM… (~2s)
              </p>
            )}
          </div>

          {/* Admin-only: internal notes */}
          {isAdmin && (
            <div className="card admin-card">
              <h3 className="card-title">🔒 Internal Notes <span className="admin-label">Admin Only</span></h3>
              <textarea
                rows={5}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Internal notes visible only to admins…"
              />
              {notesMutation.isSuccess && <div className="alert alert-success" style={{marginTop:'0.5rem'}}>Notes saved.</div>}
              <button
                className="btn btn-primary"
                style={{ marginTop: '0.75rem' }}
                onClick={() => notesMutation.mutate(notes)}
                disabled={notesMutation.isPending}
              >
                {notesMutation.isPending ? <span className="spinner-sm" /> : 'Save Notes'}
              </button>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
