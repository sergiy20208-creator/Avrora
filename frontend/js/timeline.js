document.addEventListener('DOMContentLoaded', () => {
  const timeline = document.querySelector('.timeline-track');
  if (!timeline) return;

  timeline.addEventListener('click', (event) => {
    const video = document.getElementById('videoPlayer');
    if (!video || !video.duration) return;
    const rect = timeline.getBoundingClientRect();
    const percent = (event.clientX - rect.left) / rect.width;
    video.currentTime = video.duration * percent;
  });
});
