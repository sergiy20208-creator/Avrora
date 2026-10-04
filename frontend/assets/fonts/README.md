# Font assets

This project keeps a font-loading strategy for web fonts and local files.

Current implementation loads the font families from a reliable CDN with a local fallback architecture.
The font files themselves are intentionally not stubbed here; add the actual WOFF2 files under each family folder when packaging for distribution.

Example layout:

- frontend/assets/fonts/inter/
- frontend/assets/fonts/montserrat/
- frontend/assets/fonts/poppins/
- frontend/assets/fonts/oswald/
- frontend/assets/fonts/roboto/
- frontend/assets/fonts/nunito/
- frontend/assets/fonts/rubik/
- frontend/assets/fonts/manrope/
- frontend/assets/fonts/bebas-neue/
- frontend/assets/fonts/pt-sans/

The app loads the selected weights only for the active preview, keeping the browser and mobile experience lightweight.
