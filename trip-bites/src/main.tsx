import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App.tsx';
import { load } from './store.ts';
import { requestPersistence } from './db.ts';
import { installViewportHelpers } from './viewport.ts';
import './styles.css';

load();
requestPersistence();
installViewportHelpers();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
