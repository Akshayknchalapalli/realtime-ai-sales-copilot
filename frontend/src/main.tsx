import {createRoot} from 'react-dom/client';
import App from './App';
import './style.css';

// Avoid the development-only StrictMode mount/unmount cycle prematurely
// closing an in-flight WebSocket handshake in this interview MVP.
createRoot(document.getElementById('root')!).render(<App/>);
