import { useState, useEffect } from 'react';
import './ActiveProjects.css';

interface Project {
  id: number;
  name: string;
  completed_items: number;
  total_items: number;
  created_at: string;
}

export default function ActiveProjects() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/dashboard/projects');

      if (!response.ok) {
        throw new Error('Failed to fetch projects');
      }

      const data = await response.json();
      setProjects(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      console.error('Error fetching projects:', err);
    } finally {
      setLoading(false);
    }
  };

  const calculateProgress = (completed: number, total: number): number => {
    if (total === 0) return 0;
    return Math.round((completed / total) * 100);
  };

  if (loading) {
    return (
      <div className="active-projects">
        <div className="active-projects-header">
          <h3>Active Projects</h3>
        </div>
        <div className="loading-state">Loading projects...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="active-projects">
        <div className="active-projects-header">
          <h3>Active Projects</h3>
        </div>
        <div className="error-state">Error: {error}</div>
      </div>
    );
  }

  if (projects.length === 0) {
    return (
      <div className="active-projects">
        <div className="active-projects-header">
          <h3>Active Projects</h3>
        </div>
        <div className="empty-state">
          <div className="empty-icon">➕</div>
          <p>No active projects</p>
        </div>
      </div>
    );
  }

  return (
    <div className="active-projects">
      <div className="active-projects-header">
        <h3>Active Projects</h3>
      </div>
      <div className="projects-list">
        {projects.map((project) => {
          const progress = calculateProgress(project.completed_items, project.total_items);

          return (
            <div key={project.id} className="project-item">
              <div className="project-info">
                <div className="project-name">{project.name}</div>
                <div className="project-status">
                  {project.completed_items}/{project.total_items} items
                </div>
              </div>
              <div className="progress-bar-container">
                <div
                  className="progress-bar"
                  role="progressbar"
                  aria-valuenow={progress}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
