document.addEventListener('DOMContentLoaded', () => {
  const uploadInput = document.getElementById('videoUploadInput');
  const newProjectBtn = document.getElementById('newProjectBtn');
  const projectList = document.getElementById('projectList');
  const status = document.getElementById('projectStatus');

  newProjectBtn.addEventListener('click', () => uploadInput.click());

  uploadInput.addEventListener('change', async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      newProjectBtn.disabled = true;
      status.textContent = 'Завантаження відео…';
      const result = await createProject(file);
      await loadProjects();
      openProject(result.id);
    } catch (error) {
      console.error(error);
      status.textContent = error.message || 'Не вдалося завантажити відео.';
    } finally {
      newProjectBtn.disabled = false;
      uploadInput.value = '';
    }
  });

  function openProject(id) {
    document.getElementById('editorPanel').classList.remove('hidden');
    const player = document.getElementById('videoPlayer');
    player.pause();
    player.src = `/api/projects/${encodeURIComponent(id)}/video`;
    document.dispatchEvent(new CustomEvent('project-selected', { detail: { id } }));
  }

  async function loadProjects() {
    try {
      const projects = await listProjects();
      projectList.innerHTML = '';
      status.textContent = projects.length ? '' : 'Створіть проєкт і завантажте відео для розпізнавання.';

      projects.forEach((project) => {
        const card = document.createElement('button');
        card.type = 'button';
        card.className = 'project-card';
        card.innerHTML = `
          <div class="project-preview"></div>
          <div>
            <strong></strong>
            <div class="project-meta"></div>
          </div>
        `;

        card.querySelector('strong').textContent = project.original_name || project.filename;
        const labels = { uploaded: 'Завантажено', transcribing: 'Розпізнавання', transcribed: 'Субтитри готові', transcription_failed: 'Помилка розпізнавання' };
        card.querySelector('.project-meta').textContent = `${labels[project.status] || project.status} • ${Math.round(project.duration || 0)} с`;
        card.addEventListener('click', () => openProject(project.id));

        projectList.appendChild(card);
      });
    } catch (error) {
      console.error(error);
      status.textContent = error.message;
    }
  }

  loadProjects();
  document.addEventListener('projects-changed', loadProjects);
});
