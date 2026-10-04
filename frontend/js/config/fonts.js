(function () {
  const fonts = [
    {
      id: 'inter',
      name: 'Inter',
      family: 'Inter',
      category: 'Clean',
      weights: [400, 500, 600, 700, 800],
      supportsCyrillic: true,
      fallback: ['Segoe UI', 'Arial', 'sans-serif'],
    },
    {
      id: 'montserrat',
      name: 'Montserrat',
      family: 'Montserrat',
      category: 'Modern',
      weights: [400, 500, 600, 700, 800],
      supportsCyrillic: true,
      fallback: ['Arial', 'sans-serif'],
    },
    {
      id: 'poppins',
      name: 'Poppins',
      family: 'Poppins',
      category: 'Modern',
      weights: [400, 500, 600, 700, 800],
      supportsCyrillic: true,
      fallback: ['Arial', 'sans-serif'],
    },
    {
      id: 'oswald',
      name: 'Oswald',
      family: 'Oswald',
      category: 'Bold',
      weights: [400, 500, 600, 700],
      supportsCyrillic: true,
      fallback: ['Arial', 'sans-serif'],
    },
    {
      id: 'roboto',
      name: 'Roboto',
      family: 'Roboto',
      category: 'Clean',
      weights: [400, 500, 700, 800],
      supportsCyrillic: true,
      fallback: ['Arial', 'sans-serif'],
    },
    {
      id: 'nunito',
      name: 'Nunito',
      family: 'Nunito',
      category: 'Clean',
      weights: [400, 500, 600, 700, 800],
      supportsCyrillic: true,
      fallback: ['Arial', 'sans-serif'],
    },
    {
      id: 'rubik',
      name: 'Rubik',
      family: 'Rubik',
      category: 'Modern',
      weights: [400, 500, 600, 700, 800],
      supportsCyrillic: true,
      fallback: ['Arial', 'sans-serif'],
    },
    {
      id: 'manrope',
      name: 'Manrope',
      family: 'Manrope',
      category: 'Modern',
      weights: [400, 500, 600, 700, 800],
      supportsCyrillic: true,
      fallback: ['Arial', 'sans-serif'],
    },
    {
      id: 'bebas-neue',
      name: 'Bebas Neue',
      family: 'Bebas Neue',
      category: 'Display',
      weights: [400],
      supportsCyrillic: true,
      fallback: ['Arial', 'sans-serif'],
    },
    {
      id: 'pt-sans',
      name: 'PT Sans',
      family: 'PT Sans',
      category: 'Clean',
      weights: [400, 700],
      supportsCyrillic: true,
      fallback: ['Arial', 'sans-serif'],
    },
  ];

  const registry = Object.fromEntries(fonts.map((font) => [font.id, font]));

  function normalizeWeight(font, weight) {
    const available = Array.isArray(font?.weights) ? font.weights : [400];
    return available.includes(Number(weight)) ? Number(weight) : available[0] || 400;
  }

  function getFontById(fontId) {
    return registry[fontId] || registry.montserrat;
  }

  window.AvroraFontConfig = {
    fonts,
    registry,
    defaultFontId: 'montserrat',
    defaultWeight: 700,
    getFontById,
    normalizeWeight,
  };
})();
