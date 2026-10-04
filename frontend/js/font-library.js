(function () {
  const DEFAULT_CONFIG = {
    fontFamily: 'montserrat',
    fontWeight: 700,
    fontSize: 56,
    textColor: '#FFFFFF',
    activeColor: '#FFD400',
    strokeColor: '#000000',
    strokeWidth: 4,
  };

  const FAVORITES_KEY = 'avrora.font-favorites';
  const SETTINGS_KEY = 'avrora.subtitleSettings';
  const LEGACY_SETTINGS_KEY = 'avrora.subtitleFont';
  const PREVIEW_LINES = [
    'Привіт, світ!',
    'Сьогодні створюємо Reels',
  ];

  function getStorageKey() {
    return SETTINGS_KEY;
  }

  function normalizeSettings(settings = {}) {
    const config = window.AvroraFontConfig || { getFontById: () => null, normalizeWeight: (font, weight) => Number(weight) || 400 };
    const font = config.getFontById ? config.getFontById(settings.fontFamily || DEFAULT_CONFIG.fontFamily) : null;
    const normalizedWeight = font ? config.normalizeWeight(font, settings.fontWeight) : Number(settings.fontWeight) || DEFAULT_CONFIG.fontWeight;
    return {
      ...DEFAULT_CONFIG,
      ...settings,
      fontFamily: font ? font.id : (settings.fontFamily || DEFAULT_CONFIG.fontFamily),
      fontWeight: normalizedWeight,
    };
  }

  function getSavedSettings() {
    try {
      const legacyRaw = localStorage.getItem(LEGACY_SETTINGS_KEY);
      const raw = localStorage.getItem(getStorageKey()) || legacyRaw;
      if (!raw) return { ...DEFAULT_CONFIG };
      const parsed = JSON.parse(raw);
      const normalized = normalizeSettings(parsed);
      localStorage.setItem(getStorageKey(), JSON.stringify(normalized));
      if (legacyRaw && !localStorage.getItem(LEGACY_SETTINGS_KEY)) {
        localStorage.setItem(LEGACY_SETTINGS_KEY, JSON.stringify(normalized));
      }
      return normalized;
    } catch (error) {
      return { ...DEFAULT_CONFIG };
    }
  }

  function saveSettings(settings) {
    const normalized = normalizeSettings(settings);
    localStorage.setItem(getStorageKey(), JSON.stringify(normalized));
    localStorage.setItem(LEGACY_SETTINGS_KEY, JSON.stringify(normalized));
    return normalized;
  }

  function getFavorites() {
    try {
      const raw = localStorage.getItem(FAVORITES_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch (error) {
      return [];
    }
  }

  function setFavorites(list) {
    localStorage.setItem(FAVORITES_KEY, JSON.stringify(list));
  }

  function getFontFamily(fontId) {
    const config = window.AvroraFontConfig || { getFontById: () => null };
    const font = config.getFontById ? config.getFontById(fontId) : null;
    return font ? font.family : 'Montserrat';
  }

  function getEffectiveFontConfig(fontId, weight) {
    const font = (window.AvroraFontConfig && window.AvroraFontConfig.getFontById)
      ? window.AvroraFontConfig.getFontById(fontId)
      : null;
    const safeWeight = font ? window.AvroraFontConfig.normalizeWeight(font, weight) : Number(weight) || DEFAULT_CONFIG.fontWeight;

    return {
      fontFamily: font ? font.id : (fontId || DEFAULT_CONFIG.fontFamily),
      fontWeight: safeWeight,
      fontSize: DEFAULT_CONFIG.fontSize,
      textColor: DEFAULT_CONFIG.textColor,
      activeColor: DEFAULT_CONFIG.activeColor,
      strokeColor: DEFAULT_CONFIG.strokeColor,
      strokeWidth: DEFAULT_CONFIG.strokeWidth,
    };
  }

  function quoteFontFamily(name) {
    return name && name.includes(' ') ? `"${name}"` : name;
  }

  function applyFontSettings(settings) {
    const config = window.AvroraFontConfig || { getFontById: () => null };
    const font = config.getFontById ? config.getFontById(settings.fontFamily) : null;
    const fontWeight = font ? config.normalizeWeight(font, settings.fontWeight) : Number(settings.fontWeight) || DEFAULT_CONFIG.fontWeight;
    const fallback = font && Array.isArray(font.fallback) && font.fallback.length ? font.fallback : ['Arial', 'sans-serif'];
    const familyName = font ? font.family : getFontFamily(settings.fontFamily);
    const familyCss = quoteFontFamily(familyName);
    const finalSettings = normalizeSettings(settings);

    document.documentElement.style.setProperty('--subtitle-font-family', familyName);
    document.documentElement.style.setProperty('--subtitle-font-weight', String(fontWeight));

    const overlay = document.getElementById('subtitleOverlay');
    if (overlay) {
      overlay.style.fontFamily = `${familyCss}, ${fallback.map((entry) => (entry.includes(' ') ? `"${entry}"` : entry)).join(', ')}`;
      overlay.style.fontWeight = String(fontWeight);
      overlay.style.fontSize = `${DEFAULT_CONFIG.fontSize}px`;
      overlay.style.lineHeight = '1.15';
      overlay.style.letterSpacing = '0.01em';
      overlay.style.textTransform = 'none';
      overlay.style.setProperty('font-synthesis-weight', 'auto');
    }

    saveSettings(finalSettings);
    document.dispatchEvent(new CustomEvent('subtitle-font-changed', {
      detail: { settings: finalSettings, font: font || null },
    }));

    if (window.AvroraFontLoader && window.AvroraFontLoader.ensureFontLoaded) {
      window.AvroraFontLoader.ensureFontLoaded(finalSettings.fontFamily);
    }

    return finalSettings;
  }

  function initFontLibrary() {
    const modal = document.getElementById('fontLibraryModal');
    const openButton = document.getElementById('fontLibraryBtn');
    const closeButton = document.getElementById('closeFontLibrary');
    const searchInput = document.getElementById('fontSearch');
    const favoriteToggle = document.getElementById('favoriteFontToggle');
    const weightPicker = document.getElementById('fontWeightPicker');
    const fontList = document.getElementById('fontList');
    if (!modal || !openButton || !closeButton || !searchInput || !weightPicker || !fontList) return;

    const fontConfig = window.AvroraFontConfig || { fonts: [] };
    const fontSelect = document.getElementById('subtitleFontSelect');
    const weightSelect = document.getElementById('subtitleWeightSelect');
    const preview = document.getElementById('subtitleFontPreview');
    const weightLabels = { 400: 'Звичайний', 500: 'Середній', 600: 'Напівжирний', 700: 'Жирний', 800: 'Наджирний' };
    if (fontSelect) {
      fontSelect.replaceChildren(...fontConfig.fonts.map(font => new Option(font.name, font.id)));
      fontSelect.addEventListener('change', () => {
        currentSettings.fontFamily = fontSelect.value;
        currentSettings = applyFontSettings(currentSettings);
      });
    }
    weightSelect?.addEventListener('change', () => {
      currentSettings.fontWeight = Number(weightSelect.value);
      currentSettings = applyFontSettings(currentSettings);
    });
    const defaultSettings = getSavedSettings();
    let currentSettings = { ...defaultSettings };
    let searchTerm = '';
    let favoriteMode = false;

    function getSelectedFont() {
      const selectedId = currentSettings.fontFamily || DEFAULT_CONFIG.fontFamily;
      return fontConfig.getFontById ? fontConfig.getFontById(selectedId) : null;
    }

    function updateFavoriteToggle() {
      const font = getSelectedFont();
      const favoriteIds = getFavorites();
      favoriteToggle.textContent = favoriteIds.includes(font?.id) ? '★' : '☆';
      favoriteToggle.title = favoriteIds.includes(font?.id) ? 'Видалити з обраного' : 'Додати до обраного';
    }

    function renderWeightPicker(font) {
      if (!font || !Array.isArray(font.weights) || !font.weights.length) {
        weightPicker.innerHTML = '';
        return;
      }

      const buttons = font.weights.map((weight) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'font-weight-btn';
        if (Number(currentSettings.fontWeight) === Number(weight)) {
          button.classList.add('is-active');
        }
        button.textContent = {
          400: 'Regular',
          500: 'Medium',
          600: 'SemiBold',
          700: 'Bold',
          800: 'ExtraBold',
        }[weight] || `W${weight}`;
        button.addEventListener('click', () => {
          currentSettings.fontWeight = Number(weight);
          applyFontSettings(currentSettings);
          render();
        });
        return button;
      });

      weightPicker.replaceChildren(...buttons);
    }

    function renderFontList() {
      const favorites = new Set(getFavorites());
      const filteredFonts = (fontConfig.fonts || []).filter((font) => {
        const matchesText = `${font.name} ${font.category}`.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesFavorite = !favoriteMode || favorites.has(font.id);
        return matchesText && matchesFavorite;
      });

      fontList.replaceChildren();
      if (!filteredFonts.length) {
        const empty = document.createElement('div');
        empty.className = 'font-item';
        empty.innerHTML = '<div class="font-item__meta">Нічого не знайдено</div>';
        fontList.appendChild(empty);
        return;
      }

      filteredFonts.forEach((font) => {
        const item = document.createElement('button');
        item.type = 'button';
        item.className = 'font-item';
        if (currentSettings.fontFamily === font.id) item.classList.add('is-active');

        const selectedWeight = Number(currentSettings.fontWeight) || font.weights[0] || 400;
        const safeWeight = fontConfig.normalizeWeight ? fontConfig.normalizeWeight(font, selectedWeight) : selectedWeight;
        const previewFamily = quoteFontFamily(font.family);
        const fallbackList = font.fallback ? font.fallback.map((entry) => (entry.includes(' ') ? `"${entry}"` : entry)).join(', ') : 'Arial, sans-serif';

        item.innerHTML = `
          <div class="font-item__row">
            <div>
              <div class="font-item__name">${font.name}</div>
              <div class="font-item__meta">${font.category}</div>
            </div>
            <div class="font-item__favorite">${favorites.has(font.id) ? '★' : ''}</div>
          </div>
          <div class="font-item__preview">
            ${PREVIEW_LINES.map((line, index) => `
              <div class="font-item__preview-line" style="font-weight: ${safeWeight}; ${index === 0 ? 'margin-top: 0;' : ''}">${line}</div>
            `).join('')}
          </div>
        `;
        item.querySelector('.font-item__preview').style.fontFamily = `${previewFamily}, ${fallbackList}`;

        item.addEventListener('click', () => {
          currentSettings.fontFamily = font.id;
          currentSettings.fontWeight = fontConfig.normalizeWeight ? fontConfig.normalizeWeight(font, currentSettings.fontWeight || font.weights[0]) : (currentSettings.fontWeight || font.weights[0]);
          applyFontSettings(currentSettings);
          render();
        });

        fontList.appendChild(item);
      });
    }

    function render() {
      const font = getSelectedFont();
      if (fontSelect) fontSelect.value = font.id;
      if (weightSelect) {
        weightSelect.replaceChildren(...font.weights.map(weight => new Option(weightLabels[weight] || String(weight), String(weight))));
        weightSelect.value = String(currentSettings.fontWeight);
      }
      if (preview) {
        preview.style.fontFamily = [font.family, ...font.fallback].map(quoteFontFamily).join(', ');
        preview.style.fontWeight = String(currentSettings.fontWeight);
      }
      renderWeightPicker(font);
      renderFontList();
      updateFavoriteToggle();
    }

    openButton.addEventListener('click', () => {
      fontConfig.fonts.forEach(font => window.AvroraFontLoader?.ensureFontLoaded(font.id));
      modal.classList.remove('hidden');
      modal.setAttribute('aria-hidden', 'false');
      render();
    });

    closeButton.addEventListener('click', () => {
      modal.classList.add('hidden');
      modal.setAttribute('aria-hidden', 'true');
    });

    modal.addEventListener('click', (event) => {
      if (event.target === modal) {
        modal.classList.add('hidden');
        modal.setAttribute('aria-hidden', 'true');
      }
    });

    searchInput.addEventListener('input', (event) => {
      searchTerm = event.target.value.trim();
      renderFontList();
    });

    favoriteToggle.addEventListener('click', () => {
      const font = getSelectedFont();
      if (!font) return;
      const favorites = getFavorites();
      const exists = favorites.includes(font.id);
      const next = exists ? favorites.filter((id) => id !== font.id) : [...favorites, font.id];
      setFavorites(next);
      favoriteMode = next.includes(font.id) && favoriteMode;
      render();
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && !modal.classList.contains('hidden')) {
        modal.classList.add('hidden');
        modal.setAttribute('aria-hidden', 'true');
      }
    });

    document.addEventListener('subtitle-font-changed', event => {
      currentSettings = { ...event.detail.settings };
      render();
    });
    render();
    applyFontSettings(currentSettings);
  }

  document.addEventListener('DOMContentLoaded', () => {
    if (window.AvroraFontConfig) {
      initFontLibrary();
    }
  });

  window.AvroraSubtitleSettings = {
    DEFAULT_CONFIG,
    getStorageKey,
    getSavedSettings,
    saveSettings,
    normalizeSettings,
    apply: applyFontSettings,
  };

  window.AvroraFontLibrary = {
    DEFAULT_CONFIG,
    getStorageKey,
    getSavedSettings,
    saveSettings,
    applyFontSettings,
    getEffectiveFontConfig,
    getFontFamily,
    getFavorites,
    setFavorites,
    normalizeSettings,
  };
})();
