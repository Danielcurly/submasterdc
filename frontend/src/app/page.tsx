'use client';

import { useEffect, useState, useCallback } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { getLibraries, getTasks, triggerScan, clearCompleted, retryTask, cancelTask, cancelAllTasks, getTaskStats, updateLibraryStyles, getLibraryMediaStats } from '@/lib/api';
import {
  LayoutDashboard, FolderOpen, ListTodo, Clock, CheckCircle2, AlertCircle,
  Play, RefreshCw, Trash2, RotateCcw, FileVideo, Loader2, XCircle, Eye, EyeOff, Search, FileText, List
} from 'lucide-react';

interface Library { id: string; name: string; path: string; scan_mode: string; path_exists: boolean; }
interface Task { id: number; file_path: string; status: string; progress: number; log: string; updated_at: string; }

export default function HomePage() {
  const [libraries, setLibraries] = useState<Library[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [stats, setStats] = useState({ pending: 0, processing: 0, completed: 0, failed: 0 });
  const [mediaStats, setMediaStats] = useState({ generated_subs: 0, embedded_subs: 0, existing_ass: 0, existing_ass_list: [] as any[] });
  const [scanning, setScanning] = useState<string | null>(null);
  const [scanResult, setScanResult] = useState<string | null>(null);
  const [hideParams, setHideParams] = useState({ completed: false, failed: false, skipped: false, pending: false, cancelled: false, permission_error: false });
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(10);
  const [searchQuery, setSearchQuery] = useState('');
  const [showAssModal, setShowAssModal] = useState(false);
  const [assSearchQuery, setAssSearchQuery] = useState('');
  const { t } = useLanguage();

  const load = useCallback(async () => {
    try {
      const [libs, t, s, ms] = await Promise.all([getLibraries(), getTasks(), getTaskStats(), getLibraryMediaStats()]);
      setLibraries(libs);
      setStats(s);
      setMediaStats(ms);
      const order: Record<string, number> = { processing: 0, pending: 1, failed: 2, skipped: 3, completed: 4, cancelled: 5 };
      t.sort((a: Task, b: Task) => (order[a.status] ?? 4) - (order[b.status] ?? 4));
      setTasks(t);
    } catch (e) { console.error(e); }
  }, []);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { const i = setInterval(load, 5000); return () => clearInterval(i); }, [load]);

  const handleScan = async (path: string) => {
    setScanning(path); setScanResult(null);
    try {
      const res = await triggerScan(path);
      const addedMatch = res.message?.match(/Added (\d+) new media files/);
      if (addedMatch) {
        setScanResult(t('Added {n} new media files').replace('{n}', addedMatch[1]));
      } else if (res.message === 'No new media found') {
        setScanResult(t('No new media found'));
      } else {
        setScanResult(t(res.message));
      }
      await load();
    } catch (e: unknown) { setScanResult(`Error: ${e instanceof Error ? e.message : 'Unknown'}`); }
    finally { setScanning(null); }
  };

  const handleUpdateStyles = async (id: string, name: string) => {
    try {
      const res = await updateLibraryStyles(id);
      setScanResult(res.message || t('Style update queued for {name}').replace('{name}', name));
      await load();
    } catch (e: unknown) {
      setScanResult(`Error: ${e instanceof Error ? e.message : 'Unknown'}`);
    }
  };

  const statusChip = (status: string) => {
    const map: Record<string, { cls: string; label: string }> = {
      processing: { cls: 'chip-blue', label: t('Processing') },
      pending: { cls: 'chip-amber', label: t('Pending') },
      completed: { cls: 'chip-green', label: t('Completed') },
      failed: { cls: 'chip-red', label: t('Failed') },
      permission_error: { cls: 'chip-red', label: t('Permission Error') },
      cancelled: { cls: 'chip-gray', label: t('Cancelled') },
      skipped: { cls: 'chip-blue', label: t('Skipped') },
      quota_exhausted: { cls: 'chip-red', label: t('Quota Exhausted') },
    };
    const s = map[status] || { cls: 'chip-gray', label: t(status) };
    return (
      <span className={`chip ${s.cls}`}>
        <span className="chip-dot" />
        {s.label}
      </span>
    );
  };

  const fileName = (p: string) => p.replace(/\\/g, '/').split('/').pop() || p;

  const filteredTasks = tasks.filter(task => {
    if (hideParams.completed && task.status === 'completed') return false;
    if (hideParams.failed && (task.status === 'failed' || task.status === 'permission_error' || task.status === 'quota_exhausted')) return false;
    if (hideParams.skipped && task.status === 'skipped') return false;
    if (hideParams.pending && task.status === 'pending') return false;
    if (hideParams.cancelled && task.status === 'cancelled') return false;
    if (searchQuery && !task.file_path.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const totalPages = Math.ceil(filteredTasks.length / itemsPerPage) || 1;
  const paginatedTasks = filteredTasks.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  // Adjust page if out of bounds after filtering
  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [totalPages, currentPage]);

  return (
    <>
      {/* Page Header */}
      <div className="page-header">
        <h1 className="page-title">
          <span className="page-title-icon"><LayoutDashboard size={20} /></span>
          {t('Dashboard')}
        </h1>
        <p className="page-subtitle">{t('Monitor your task queue and trigger library scans.')}</p>
      </div>

      {/* Global Library Stats */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'var(--accent-primary-soft)', color: 'var(--accent-primary)' }}>
            <FolderOpen size={22} />
          </div>
          <div>
            <div className="stat-value">{libraries.length}</div>
            <div className="stat-label">{t('Libraries')}</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'var(--accent-green-soft)', color: 'var(--accent-green)' }}>
            <FileText size={22} />
          </div>
          <div>
            <div className="stat-value">{mediaStats.generated_subs}</div>
            <div className="stat-label">{t('Generated Subs')}</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'var(--accent-blue-soft)', color: 'var(--accent-blue)' }}>
            <FileVideo size={22} />
          </div>
          <div>
            <div className="stat-value">{mediaStats.embedded_subs}</div>
            <div className="stat-label">{t('Embedded Subs')}</div>
          </div>
        </div>
        <div className="stat-card" style={{ position: 'relative' }}>
          <div className="stat-icon" style={{ background: 'var(--accent-amber-soft)', color: 'var(--accent-amber)' }}>
            <FileText size={22} />
          </div>
          <div>
            <div className="stat-value">{mediaStats.existing_ass}</div>
            <div className="stat-label">{t('External Subs')}</div>
          </div>
          <button
            className="btn btn-ghost btn-sm btn-icon"
            onClick={() => setShowAssModal(true)}
            style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', padding: 6 }}
            title={t('View List')}
          >
            <List size={20} style={{ color: 'var(--text-muted)' }} />
          </button>
        </div>
      </div>

      <div>
        {/* Libraries */}
        <div className="section">
          <div className="section-header">
            <div className="section-title">
              <FolderOpen size={18} className="section-title-icon" />
              <h2>{t('Libraries')}</h2>
            </div>
          </div>

          {libraries.length === 0 ? (
            <div className="empty-state">
              <FolderOpen size={48} className="empty-state-icon" />
              <p>{t('No libraries configured')}</p>
              <p className="text-muted" style={{ fontSize: 12, marginTop: 4 }}>{t('Go to Libraries to add one.')}</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
              {libraries.map(lib => (
                <div key={lib.id} className="card" style={{ width: 320, flexShrink: 0 }}>
                  <div className="card-header" style={{ alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
                    <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start', flex: 1, minWidth: 0 }}>
                      <div className="card-icon purple" style={{ flexShrink: 0 }}><FolderOpen size={18} /></div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <strong style={{ fontSize: '15px', display: 'block', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{lib.name}</strong>
                        <p className="text-caption text-mono" style={{ marginTop: 2, fontSize: '12px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{lib.path}</p>
                      </div>
                    </div>
                    <span className="chip chip-gray" style={{ flexShrink: 0, fontSize: '11px', padding: '2px 8px', textTransform: 'capitalize' }}>{t(lib.scan_mode)}</span>
                  </div>
                  <div style={{ display: 'flex', gap: 8, marginTop: 14 }}>
                    <button
                      className="btn btn-primary"
                      style={{ flex: 1, padding: '8px 4px', fontSize: '13px' }}
                      onClick={() => handleScan(lib.path)}
                      disabled={scanning === lib.path}
                    >
                      {scanning === lib.path ? (
                        <><Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> {t('Scanning...')}</>
                      ) : (
                        <><Play size={14} /> {t('Analyze')}</>
                      )}
                    </button>
                    <button
                      className="btn btn-secondary"
                      style={{ flex: 1, padding: '8px 4px', fontSize: '13px', backgroundColor: 'var(--bg-card-hover)' }}
                      onClick={() => handleUpdateStyles(lib.id, lib.name)}
                      title={t('Apply current subtitle styles to all generated subtitles in this library')}
                    >
                      <RefreshCw size={14} /> {t('Update Styles')}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {scanResult && <div className="info-box" style={{ marginTop: 12 }}>{scanResult}</div>}
        </div>

        {/* Task Queue */}
        <div className="section">
          <div className="section-header" style={{ gap: 10, marginBottom: 16 }}>
            <div className="section-title">
              <ListTodo size={18} className="section-title-icon" />
              <h2>{t('Processing Queue')}</h2>
            </div>
          </div>

          {/* Queue Stats Row */}
          <div className="stats-grid" style={{ marginBottom: 20, gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
            <div className="stat-card" style={{ padding: '12px 16px', minHeight: 'auto', gap: 12 }}>
              <div className="stat-icon" style={{ background: 'var(--accent-amber-soft)', color: 'var(--accent-amber)', width: 36, height: 36 }}>
                <Clock size={18} />
              </div>
              <div>
                <div className="stat-value" style={{ fontSize: 20 }}>{stats.pending}</div>
                <div className="stat-label" style={{ fontSize: 12 }}>{t('Pending')}</div>
              </div>
            </div>
            <div className="stat-card" style={{ padding: '12px 16px', minHeight: 'auto', gap: 12 }}>
              <div className="stat-icon" style={{ background: 'var(--accent-blue-soft)', color: 'var(--accent-blue)', width: 36, height: 36 }}>
                <Loader2 size={18} />
              </div>
              <div>
                <div className="stat-value" style={{ fontSize: 20 }}>{stats.processing}</div>
                <div className="stat-label" style={{ fontSize: 12 }}>{t('Processing')}</div>
              </div>
            </div>
            <div className="stat-card" style={{ padding: '12px 16px', minHeight: 'auto', gap: 12 }}>
              <div className="stat-icon" style={{ background: 'var(--accent-green-soft)', color: 'var(--accent-green)', width: 36, height: 36 }}>
                <CheckCircle2 size={18} />
              </div>
              <div>
                <div className="stat-value" style={{ fontSize: 20 }}>{stats.completed}</div>
                <div className="stat-label" style={{ fontSize: 12 }}>{t('Completed')}</div>
              </div>
            </div>
            <div className="stat-card" style={{ padding: '12px 16px', minHeight: 'auto', gap: 12 }}>
              <div className="stat-icon" style={{ background: 'var(--accent-red-soft)', color: 'var(--accent-red)', width: 36, height: 36 }}>
                <AlertCircle size={18} />
              </div>
              <div>
                <div className="stat-value" style={{ fontSize: 20 }}>{tasks.filter(t => t.status === 'failed' || t.status === 'permission_error' || t.status === 'quota_exhausted').length}</div>
                <div className="stat-label" style={{ fontSize: 12 }}>{t('Failed')}</div>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 16, flexWrap: 'wrap' }}>
            <button
              className="btn btn-ghost btn-sm"
              onClick={() => {
                const anyVisible = Object.values(hideParams).some(v => !v);
                setHideParams({
                  pending: anyVisible,
                  completed: anyVisible,
                  failed: anyVisible,
                  permission_error: anyVisible,
                  skipped: anyVisible,
                  cancelled: anyVisible
                });
              }}
              style={{ padding: '4px 8px', color: Object.values(hideParams).every(v => v) ? 'var(--text-muted)' : 'var(--text-main)', opacity: Object.values(hideParams).every(v => v) ? 0.6 : 1 }}
            >
              {Object.values(hideParams).every(v => v) ? <EyeOff size={14} /> : <Eye size={14} />} {t('All')}
            </button>

            <button
              className="btn btn-ghost btn-sm"
              onClick={() => setHideParams(p => ({ ...p, pending: !p.pending }))}
              style={{ padding: '4px 8px', color: hideParams.pending ? 'var(--text-muted)' : 'var(--text-main)', opacity: hideParams.pending ? 0.6 : 1 }}
            >
              {hideParams.pending ? <EyeOff size={14} /> : <Eye size={14} />} {t('Pending')}
            </button>

            <button
              className="btn btn-ghost btn-sm"
              onClick={() => setHideParams(p => ({ ...p, completed: !p.completed }))}
              style={{ padding: '4px 8px', color: hideParams.completed ? 'var(--text-muted)' : 'var(--text-main)', opacity: hideParams.completed ? 0.6 : 1 }}
            >
              {hideParams.completed ? <EyeOff size={14} /> : <Eye size={14} />} {t('Completed')}
            </button>

            <button
              className="btn btn-ghost btn-sm"
              onClick={() => setHideParams(p => ({ ...p, failed: !p.failed, permission_error: !p.permission_error }))}
              style={{ padding: '4px 8px', color: (hideParams.failed || hideParams.permission_error) ? 'var(--text-muted)' : 'var(--text-main)', opacity: (hideParams.failed || hideParams.permission_error) ? 0.6 : 1 }}
            >
              {(hideParams.failed || hideParams.permission_error) ? <EyeOff size={14} /> : <Eye size={14} />} {t('Failed')}
            </button>

            <button
              className="btn btn-ghost btn-sm"
              onClick={() => setHideParams(p => ({ ...p, skipped: !p.skipped }))}
              style={{ padding: '4px 8px', color: hideParams.skipped ? 'var(--text-muted)' : 'var(--text-main)', opacity: hideParams.skipped ? 0.6 : 1 }}
            >
              {hideParams.skipped ? <EyeOff size={14} /> : <Eye size={14} />} {t('Skipped')}
            </button>

            <button
              className="btn btn-ghost btn-sm"
              onClick={() => setHideParams(p => ({ ...p, cancelled: !p.cancelled }))}
              style={{ padding: '4px 8px', color: hideParams.cancelled ? 'var(--text-muted)' : 'var(--text-main)', opacity: hideParams.cancelled ? 0.6 : 1 }}
            >
              {hideParams.cancelled ? <EyeOff size={14} /> : <Eye size={14} />} {t('Cancelled')}
            </button>

            <div style={{ position: 'relative', flex: 1, minWidth: '200px', maxWidth: '400px', marginLeft: 12 }}>
              <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input
                type="text"
                className="form-input"
                placeholder={t('Search tasks...')}
                value={searchQuery}
                onChange={(e) => { setSearchQuery(e.target.value); setCurrentPage(1); }}
                style={{ paddingLeft: 32, height: '32px', fontSize: '13px' }}
              />
            </div>

            <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                fontSize: '12px',
                backgroundColor: 'var(--bg-card-hover)',
                padding: '4px 10px',
                borderRadius: '20px',
                border: '1px solid var(--border-color)',
                color: 'var(--text-main)',
                fontWeight: 500
              }}>
                <ListTodo size={14} style={{ color: 'var(--accent-blue)' }} />
                <span>{filteredTasks.length}</span>
                <span style={{ opacity: 0.7, fontSize: '11px' }}>{t('tasks found')}</span>
              </div>

              <button
                className="btn btn-sm"
                style={{ backgroundColor: 'var(--accent-red-soft)', color: 'var(--accent-red)', borderColor: 'var(--accent-red)' }}
                onClick={() => cancelAllTasks().then(load)}
              >
                <XCircle size={14} /> {t('Cancel All')}
              </button>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {paginatedTasks.length === 0 ? (
              <div className="empty-state">
                <ListTodo size={48} className="empty-state-icon" />
                <p>{t('Queue is empty')}</p>
                <p className="text-muted" style={{ fontSize: 12, marginTop: 4 }}>{t('Scan a library to add tasks.')}</p>
              </div>
            ) : (
              paginatedTasks.map(task => (
                <div key={task.id} className="task-card" style={{ margin: 0, padding: '10px 16px' }}>
                  <div className="task-card-header" style={{ alignItems: 'center', gap: 12 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0, flex: 1 }}>
                      <FileVideo size={14} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
                      <span className="task-filename" style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{fileName(task.file_path)}</span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
                      <div className="task-meta" style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
                        {statusChip(task.status)}
                        <span className="text-muted" style={{ fontSize: 11, whiteSpace: 'nowrap' }}>{task.updated_at}</span>
                      </div>

                      <div style={{ display: 'flex', gap: 6 }}>
                        {(task.status === 'pending' || task.status === 'processing') && (
                          <button className="btn btn-sm btn-icon" onClick={() => cancelTask(task.id).then(load)} title={t("Cancel")} style={{ padding: 4 }}>
                            <XCircle size={14} />
                          </button>
                        )}
                        {(task.status === 'failed' || task.status === 'permission_error' || task.status === 'quota_exhausted' || task.status === 'cancelled' || task.status === 'skipped') && (
                          <button className="btn btn-sm btn-icon" onClick={() => retryTask(task.id).then(load)} title={t("Retry")} style={{ color: 'var(--accent-amber)', padding: 4 }}>
                            <RotateCcw size={14} />
                          </button>
                        )}
                      </div>
                    </div>
                  </div>

                  {(task.status === 'processing' || task.status === 'completed') && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 6 }}>
                      <div className="progress-bar" style={{ flex: 1, margin: 0 }}>
                        <div className="progress-fill" style={{ width: `${task.status === 'completed' ? 100 : task.progress}%` }} />
                      </div>
                      {task.status === 'processing' && (
                        <span style={{ color: 'var(--accent-blue)', fontSize: 12, fontWeight: 600, minWidth: 32 }}>{task.progress}%</span>
                      )}
                    </div>
                  )}

                  {task.log && (
                    <div className="text-muted text-mono" style={{ fontSize: 10, marginTop: 4, lineHeight: 1.2, opacity: 0.8 }}>
                      {task.log}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>

          {filteredTasks.length > 0 && (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--text-muted)' }}>
                <span>{t('Show')}</span>
                <select
                  className="form-select"
                  style={{ padding: '4px 24px 4px 8px', fontSize: 13, width: 'auto' }}
                  value={itemsPerPage}
                  onChange={e => { setItemsPerPage(Number(e.target.value)); setCurrentPage(1); }}
                >
                  <option value={10}>10</option>
                  <option value={20}>20</option>
                  <option value={50}>50</option>
                </select>
                <span>{t('entries')}</span>
              </div>

              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <button
                  className="btn btn-ghost btn-sm"
                  disabled={currentPage === 1}
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  style={{ padding: '4px 10px' }}
                >
                  {t('Previous')}
                </button>
                <span style={{ fontSize: 13, margin: '0 4px', fontWeight: 500 }}>
                  {currentPage} / {totalPages}
                </span>
                <button
                  className="btn btn-ghost btn-sm"
                  disabled={currentPage === totalPages}
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  style={{ padding: '4px 10px' }}
                >
                  {t('Next')}
                </button>
              </div>
            </div>
          )}

          <hr className="divider" />
          <button className="btn btn-sm" onClick={() => clearCompleted().then(load)}>
            <Trash2 size={14} /> {t('Clean List')}
          </button>
        </div>
      </div>

      {/* Existing ASS Modal */}
      {showAssModal && (
        <div className="modal-overlay" onClick={() => setShowAssModal(false)}>
          <div className="modal-content" style={{ maxWidth: 700, maxHeight: '80vh', display: 'flex', flexDirection: 'column' }} onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{t('External Subs')}</h2>
              <button className="btn btn-icon btn-ghost" onClick={() => setShowAssModal(false)}>
                <XCircle size={20} />
              </button>
            </div>
            <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: 16, overflow: 'hidden' }}>
              <div style={{ position: 'relative' }}>
                <Search size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                <input
                  type="text"
                  className="form-input"
                  style={{ paddingLeft: 36 }}
                  placeholder={t('Search files...')}
                  value={assSearchQuery}
                  onChange={e => setAssSearchQuery(e.target.value)}
                />
              </div>
              <div style={{ overflowY: 'auto', flex: 1, border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)' }}>
                {mediaStats.existing_ass_list.filter(item =>
                  !assSearchQuery ||
                  item.file_name.toLowerCase().includes(assSearchQuery.toLowerCase()) ||
                  item.rel_path.toLowerCase().includes(assSearchQuery.toLowerCase()) ||
                  item.library_name.toLowerCase().includes(assSearchQuery.toLowerCase())
                ).map((item, i) => (
                  <div key={i} style={{ padding: '12px 16px', borderBottom: '1px solid var(--border-color)' }}>
                    <div style={{ fontWeight: 500, fontSize: 14, color: 'var(--text-main)', marginBottom: 4, wordBreak: 'break-all' }}>
                      {item.file_name}
                    </div>
                    <div style={{ display: 'flex', gap: 12, fontSize: 12, color: 'var(--text-muted)' }}>
                      <span className="chip chip-gray" style={{ fontSize: 11, padding: '2px 8px' }}>{item.library_name}</span>
                      <span className="text-mono" style={{ opacity: 0.8, paddingTop: 2 }}>{item.rel_path}</span>
                    </div>
                  </div>
                ))}
                {mediaStats.existing_ass_list.length === 0 && (
                  <div className="empty-state" style={{ padding: 40 }}>
                    <FileText size={32} style={{ color: 'var(--text-muted)', marginBottom: 12, opacity: 0.5 }} />
                    <p style={{ color: 'var(--text-muted)' }}>{t('No existing ASS subtitles found.')}</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
