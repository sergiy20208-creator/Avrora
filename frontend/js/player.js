document.addEventListener('DOMContentLoaded', () => {
  const video = document.getElementById('videoPlayer');
  const currentTimeEl = document.getElementById('currentTime');
  const durationLabel = document.getElementById('durationLabel');
  const playhead = document.getElementById('playhead');

  if (!video) return;

  const formatTime = (seconds) => {
    if (!Number.isFinite(seconds)) return '00:00';
    const total = Math.floor(seconds);
    const minutes = Math.floor(total / 60);
    const secs = total % 60;
    return `${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  video.addEventListener('loadedmetadata', () => {
    durationLabel.textContent = formatTime(video.duration || 0);
  });

  video.addEventListener('timeupdate', () => {
    currentTimeEl.textContent = formatTime(video.currentTime || 0);
    const progress = (video.currentTime / (video.duration || 1)) * 100;
    playhead.style.left = `${Math.min(Math.max(progress, 0), 100)}%`;
  });
});
