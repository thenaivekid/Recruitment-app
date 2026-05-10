import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getCandidates } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useQuery } from '@tanstack/react-query';

const STATUS_COLORS = {
  new: 'badge-blue',
  reviewed: 'badge-yellow',
  hired: 'badge-green',
  rejected: 'badge-red',
  archived: 'badge-gray',
};

const STATUSES = ['', 'new', 'reviewed', 'hired', 'rejected'];

export default function CandidateListPage() {
  const { user, isAdmin, signOut } = useAuth();
  const navigate = useNavigate();

  const [filters, setFilters] = useState({
    status: '', role_applied: '', skill: '', keyword: '',
  });
  const [offset, setOffset] = useState(0);
  const LIMIT = 10;

  const { data, isLoading: loading, isError } = useQuery({
    queryKey: ['candidates', filters, offset],
    queryFn: async () => {
      const params = { limit: LIMIT, offset, ...Object.fromEntries(
        Object.entries(filters).filter(([, v]) => v)
      )};
      const res = await getCandidates(params);
      return res.data;
    }
  });

  const candidates = data?.items || [];
  const total = data?.total || 0;
  const error = isError ? 'Failed to load candidates.' : '';

  const handleFilterChange = (key, val) => {
    setFilters((f) => ({ ...f, [key]: val }));
    setOffset(0);
  };

  const totalPages = Math.ceil(total / LIMIT);
  const currentPage = Math.floor(offset / LIMIT) + 1;

  return (
    <div className="app-layout">
      <nav className="topnav">
        <div className="topnav-brand">
          <img src="https://techkraftinc.com/wp-content/uploads/2024/05/TechKraft-Logo.svg" alt="TechKraft" />
        </div>
        <div className="topnav-right">
          <span className="role-badge">{isAdmin ? 'Admin' : 'Reviewer'}</span>
          <span className="user-email">{user?.email}</span>
          <button className="btn btn-ghost" onClick={signOut}>Sign Out</button>
        </div>
      </nav>

      <main className="content">
        <div className="page-header">
          <h1>Candidates</h1>
          <span className="total-count">{total} total</span>
        </div>

        {/* Filter bar */}
        <div className="filter-bar">
          <input
            id="filter-keyword"
            className="filter-input"
            placeholder="Search name, email, role…"
            value={filters.keyword}
            onChange={(e) => handleFilterChange('keyword', e.target.value)}
          />
          <select
            id="filter-status"
            className="filter-select"
            value={filters.status}
            onChange={(e) => handleFilterChange('status', e.target.value)}
          >
            <option value="">All statuses</option>
            {STATUSES.filter(Boolean).map((s) => (
              <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
            ))}
          </select>
          <input
            id="filter-role"
            className="filter-input"
            placeholder="Role applied…"
            value={filters.role_applied}
            onChange={(e) => handleFilterChange('role_applied', e.target.value)}
          />
          <input
            id="filter-skill"
            className="filter-input"
            placeholder="Skill…"
            value={filters.skill}
            onChange={(e) => handleFilterChange('skill', e.target.value)}
          />
          <button className="btn btn-ghost" onClick={() => {
            setFilters({ status: '', role_applied: '', skill: '', keyword: '' });
            setOffset(0);
          }}>Clear</button>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        {loading ? (
          <div className="center-spinner"><div className="spinner" /></div>
        ) : candidates.length === 0 ? (
          <div className="empty-state">No candidates match your filters.</div>
        ) : (
          <div className="table-container">
            <table className="candidates-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Role Applied</th>
                  <th>Skills</th>
                  <th>Status</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {candidates.map((c) => (
                  <tr key={c.id} className="table-row clickable" onClick={() => navigate(`/candidates/${c.id}`)}>
                    <td>
                      <div className="candidate-name">{c.name}</div>
                      <div className="candidate-email">{c.email}</div>
                    </td>
                    <td>{c.role_applied}</td>
                    <td>
                      <div className="skill-tags">
                        {c.skills.slice(0, 3).map((s) => (
                          <span key={s} className="skill-tag">{s}</span>
                        ))}
                        {c.skills.length > 3 && <span className="skill-tag-more">+{c.skills.length - 3}</span>}
                      </div>
                    </td>
                    <td><span className={`badge ${STATUS_COLORS[c.status] || 'badge-gray'}`}>{c.status}</span></td>
                    <td>{new Date(c.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="pagination">
            <button
              className="btn btn-ghost"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - LIMIT))}
            >← Prev</button>
            <span className="page-info">Page {currentPage} of {totalPages}</span>
            <button
              className="btn btn-ghost"
              disabled={offset + LIMIT >= total}
              onClick={() => setOffset(offset + LIMIT)}
            >Next →</button>
          </div>
        )}
      </main>
    </div>
  );
}
