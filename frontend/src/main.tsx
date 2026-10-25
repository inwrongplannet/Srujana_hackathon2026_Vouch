import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider } from 'react-router';
import '@fontsource-variable/anek-latin/standard.css';
import '@fontsource-variable/anek-devanagari/standard.css';
import '@fontsource/ibm-plex-sans/400.css';
import '@fontsource/ibm-plex-sans/500.css';
import '@fontsource/ibm-plex-sans/600.css';
import '@fontsource/ibm-plex-mono/400.css';
import '@fontsource/ibm-plex-mono/500.css';
import './styles/index.css';
import { router } from './app/router';
import { DemoProvider } from './state/DemoProvider';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <DemoProvider>
      <RouterProvider router={router} />
    </DemoProvider>
  </StrictMode>,
);
