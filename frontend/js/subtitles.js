document.addEventListener('DOMContentLoaded', () => {
  const overlay = document.getElementById('subtitleOverlay');
  const player = document.getElementById('videoPlayer');
  const button = document.getElementById('transcribeBtn');
  const language = document.getElementById('transcriptionLanguage');
  const status = document.getElementById('transcriptionStatus');
  const progress = document.getElementById('transcriptionProgress');
  const list = document.getElementById('transcriptSegments');
  const download = document.getElementById('downloadSrt');
  let projectId = null;
  let generation = 0;
  let timer = null;
  let segments = [];
  let activeIndex = -1;

  function getWordsForSegment(segment) {
    const manualText = (segment?.text || '').trim();
    if (Array.isArray(segment?.words) && segment.words.length) {
      const originalText = segment.words.map((word) => (word.text || word.word || '').trim()).filter(Boolean).join(' ');
      if (manualText && manualText !== originalText) {
        const words = manualText.split(/\s+/).filter(Boolean);
        const start = Number(segment?.start ?? 0);
        const end = Number(segment?.end ?? start);
        const duration = Math.max(end - start, 0.2);
        return words.map((text, index) => {
          const step = words.length > 1 ? duration / words.length : duration;
          return {
            text,
            start: start + index * step,
            end: start + (index + 1) * step,
          };
        });
      }

      return segment.words.map((word) => ({
        text: (word.text || word.word || '').trim(),
        start: Number(word.start ?? segment.start ?? 0),
        end: Number(word.end ?? segment.end ?? word.start ?? segment.start ?? 0),
      })).filter((word) => word.text);
    }
    return (segment?.text || '').split(/\s+/).filter(Boolean).map((text, index) => ({
      text,
      start: Number(segment?.start ?? 0) + index * 0.25,
      end: Number(segment?.start ?? 0) + (index + 1) * 0.25,
    }));
  }

  function findActiveSegment(currentTime) {
    if (!segments.length) return -1;
    return segments.findIndex((segment) => {
      const start = Number(segment.start ?? 0);
      const end = Number(segment.end ?? start);
      return currentTime >= start && currentTime < end;
    });
  }

  function getActiveWord(segment, currentTime) {
    if (!segment) return null;
    const words = getWordsForSegment(segment);
    return words.find((word) => currentTime >= word.start && currentTime < word.end) || null;
  }

  function renderActiveText(segment, activeWord) {
    if (!segment) {
      overlay.innerHTML = '';
      return;
    }
    const words = getWordsForSegment(segment);
    if (!words.length) {
      overlay.textContent = segment.text || '';
      return;
    }
    const activeText = activeWord ? activeWord.text : null;
    const html = words.map((word) => {
      const cls = word.text === activeText ? 'subtitle-word subtitle-word--active' : 'subtitle-word';
      return `<span class="${cls}">${word.text}</span>`;
    }).join(' ');
    overlay.innerHTML = html;
  }

  function syncSubtitle() {
    if (!player || !segments.length) {
      overlay.innerHTML = '';
      return;
    }
    const currentTime = Number(player.currentTime || 0);
    const index = findActiveSegment(currentTime);
    const segment = index >= 0 ? segments[index] : null;
    const activeWord = segment ? getActiveWord(segment, currentTime) : null;
    renderActiveText(segment, activeWord);

    if (index !== activeIndex) {
      list.children[activeIndex]?.classList.remove('active');
      list.children[index]?.classList.add('active');
      activeIndex = index;
      const row = list.children[index];
      row?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

  function render(data) {
    const busy = data.status === 'queued' || data.status === 'processing';
    button.disabled = busy;
    language.disabled = busy;
    button.textContent = data.status === 'completed' ? 'Розпізнати повторно' : 'Розпізнати мовлення';
    progress.classList.toggle('hidden', !busy);
    if (data.progress > 0) progress.value = data.progress;
    else progress.removeAttribute('value');
    download.classList.toggle('hidden', data.status !== 'completed' || !data.segments?.length);
    download.href = `/api/projects/${encodeURIComponent(projectId)}/subtitles.srt`;
    if (data.status === 'queued') {
      status.textContent = 'Завдання прийнято. Очікування запуску Whisper…';
    } else if (busy) {
      const elapsed = Math.floor(data.elapsed_seconds || 0);
      status.textContent = data.phase === 'transcribing' || data.progress > 0
        ? `Розпізнавання: ${data.progress}%. Обробляється наступний фрагмент. Минуло ${elapsed} с.`
        : 'Підготовка моделі й аудіо… Перший запуск потребує інтернету та може тривати кілька хвилин.';
    } else if (data.status === 'error' || data.status === 'failed') {
      status.textContent = data.error;
    } else if (data.status === 'completed') {
      status.textContent = data.segments.length
        ? `Готово. Мова: ${data.language}. Фрагментів: ${data.segments.length}. Натисніть фрагмент, щоб перейти до нього.`
        : 'Мовлення не знайдено. Перевірте звук або виберіть мову вручну.';
    } else {
      status.textContent = 'Оберіть мову та запустіть розпізнавання.';
    }
    segments = Array.isArray(data.segments) ? data.segments : [];
    activeIndex = -1;
    list.replaceChildren();
    for (const item of segments) {
      const row = document.createElement('button');
      row.type = 'button';
      row.className = 'transcript-segment';
      const time = document.createElement('span');
      time.className = 'segment-time';
      const seconds = Math.floor(Number(item.start ?? 0));
      time.textContent = `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
      const text = document.createElement('span');
      text.className = 'segment-text';
      text.textContent = item.text || '';
      text.contentEditable = true;
      text.spellcheck = false;
      text.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); text.blur(); } });
      text.addEventListener('blur', async (e) => {
        if (!projectId) return;
        const newText = e.target.textContent.trim();
        if (newText === (item.text || '')) return;
        item.text = newText;
        try {
          await apiFetch(`/projects/${encodeURIComponent(projectId)}/transcription`, {
            method: 'PUT', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ segments }),
          });
          syncSubtitle();
        } catch (err) {
          status.textContent = err.message;
        }
      });
      row.append(time, text);
      row.addEventListener('click', (e) => { if (e.target.isContentEditable) return; player.currentTime = Number(item.start ?? 0); syncSubtitle(); });
      list.appendChild(row);
    }
    syncSubtitle();
  }

  async function refresh(id, version) {
    try {
      const data = await apiFetch(`/projects/${encodeURIComponent(id)}/transcription`, { cache: 'no-store' });
      if (version !== generation) return;
      render(data);
      if (data.status === 'queued' || data.status === 'processing') {
        timer = setTimeout(() => refresh(id, version), 1500);
      } else {
        document.dispatchEvent(new Event('projects-changed'));
      }
    } catch (error) {
      if (version !== generation) return;
      status.textContent = `${error.message}. Повторна перевірка через 5 секунд…`;
      timer = setTimeout(() => refresh(id, version), 5000);
    }
  }

  document.addEventListener('project-selected', event => {
    projectId = event.detail.id;
    generation += 1;
    clearTimeout(timer);
    render({ status: 'idle', segments: [] });
    button.disabled = true;
    status.textContent = 'Завантаження субтитрів…';
    refresh(projectId, generation);
  });

  button.addEventListener('click', async () => {
    if (!projectId) return;
    const id = projectId;
    const version = ++generation;
    clearTimeout(timer);
    button.disabled = true;
    language.disabled = true;
    status.textContent = 'Запуск розпізнавання…';
    try {
      const data = await apiFetch(`/projects/${encodeURIComponent(id)}/transcription`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language: language.value }),
      });
      if (version !== generation) return;
      render(data);
      document.dispatchEvent(new Event('projects-changed'));
      timer = setTimeout(() => refresh(id, version), 1500);
    } catch (error) {
      if (version !== generation) return;
      status.textContent = error.message;
      button.disabled = false;
      language.disabled = false;
    }
  });
  player.addEventListener('timeupdate', syncSubtitle);
  player.addEventListener('seeked', syncSubtitle);
});
