import { createRoot } from 'react-dom/client';
import { App } from './App';
import './styles.css';

createRoot(document.getElementById('root')!).render(<App />);
// Service workers only run on https or localhost; elsewhere the call is simply rejected.
navigator.serviceWorker?.register('/sw.js').catch(() => {});
