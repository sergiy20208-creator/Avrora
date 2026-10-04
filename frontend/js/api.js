const API_BASE = '/api';

async function apiFetch(url, options = {}) {
  const response = await fetch(`${API_BASE}${url}`, {
    headers: {
      ...(options.headers || {})
    },
    ...options,
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(typeof data.detail === 'string' ? data.detail : `Помилка сервера: ${response.status}`);
  }

  return response.json();
}

async function listProjects() {
  return apiFetch('/projects');
}

async function createProject(file) {
  const formData = new FormData();
  formData.append('file', file);

  return fetch(`${API_BASE}/projects`, {
    method: 'POST',
    body: formData,
  }).then(async (response) => {
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || 'Upload failed');
    }
    return data;
  });
}
