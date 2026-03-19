// Optional Firebase integration template. App works in mock mode without these values.
// 1) Add Firebase SDK scripts via bundler or replace imports with compat SDK.
// 2) Fill config below and export initialized services.
export const firebaseReady = false;
export const firebaseApp = null;
export const auth = null;
export const db = null;
export const storage = null;

/* Example (modular SDK):
import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.12.5/firebase-app.js';
import { getAuth } from 'https://www.gstatic.com/firebasejs/10.12.5/firebase-auth.js';
import { getFirestore } from 'https://www.gstatic.com/firebasejs/10.12.5/firebase-firestore.js';
import { getStorage } from 'https://www.gstatic.com/firebasejs/10.12.5/firebase-storage.js';
const firebaseConfig = { apiKey:'', authDomain:'', projectId:'', storageBucket:'', messagingSenderId:'', appId:'' };
export const firebaseApp = initializeApp(firebaseConfig);
export const auth = getAuth(firebaseApp);
export const db = getFirestore(firebaseApp);
export const storage = getStorage(firebaseApp);
export const firebaseReady = true;
*/