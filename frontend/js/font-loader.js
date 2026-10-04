(function () {
  const FALLBACK_URLS = {
    inter: 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap',
    montserrat: 'https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&display=swap',
    poppins: 'https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap',
    oswald: 'https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&display=swap',
    roboto: 'https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700;800&display=swap',
    nunito: 'https://fonts.googleapis.com/css2?family=Nunito:wght@400;500;600;700;800&display=swap',
    rubik: 'https://fonts.googleapis.com/css2?family=Rubik:wght@400;500;600;700;800&display=swap',
    manrope: 'https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap',
    'bebas-neue': 'https://fonts.googleapis.com/css2?family=Bebas+Neue&display=swap',
    'pt-sans': 'https://fonts.googleapis.com/css2?family=PT+Sans:wght@400;700&display=swap',
  };

  const loaded = new Set();

  function ensureLink(fontId) {
    const url = FALLBACK_URLS[fontId];
    if (!url || loaded.has(fontId)) return;

    const existing = document.querySelector(`link[data-font-id="${fontId}"]`);
    if (existing) {
      loaded.add(fontId);
      return;
    }

    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = url;
    link.setAttribute('data-font-id', fontId);
    link.crossOrigin = 'anonymous';
    document.head.appendChild(link);
    loaded.add(fontId);
  }

  function ensureFontLoaded(fontId) {
    const font = window.AvroraFontConfig && window.AvroraFontConfig.getFontById ? window.AvroraFontConfig.getFontById(fontId) : null;
    if (!font) return Promise.resolve();
    ensureLink(fontId);

    if (document.fonts && document.fonts.load) {
      const weightList = Array.isArray(font.weights) && font.weights.length ? font.weights : [400];
      const tasks = weightList.map((weight) => document.fonts.load(`${weight} 1em "${font.family}"`));
      return Promise.all(tasks).catch(() => undefined);
    }

    return Promise.resolve();
  }

  window.AvroraFontLoader = {
    ensureFontLoaded,
    ensureLink,
  };
})();
