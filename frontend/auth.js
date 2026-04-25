/**
 * GuardianLens — Firebase Auth + Firestore Module
 * Handles Google Sign-In and scan history persistence.
 * Uses Firebase v10 modular SDK via CDN (esm.sh).
 */

import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js';
import {
  getAuth,
  signInWithPopup,
  GoogleAuthProvider,
  signOut as firebaseSignOut,
  onAuthStateChanged,
} from 'https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js';
import {
  getFirestore,
  collection,
  addDoc,
  getDocs,
  query,
  where,
  orderBy,
  limit,
  doc,
  setDoc,
  serverTimestamp,
} from 'https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js';

// ── Firebase Config ──────────────────────────────────────────
const firebaseConfig = {
  apiKey: "AIzaSyBeG3MBxkeF42RCSubO0IstHYcziN7vdS8",
  authDomain: "gardianlens.firebaseapp.com",
  projectId: "gardianlens",
  storageBucket: "gardianlens.firebasestorage.app",
  messagingSenderId: "55239754572",
  appId: "1:55239754572:web:a14111a8b03a03029785e9",
  measurementId: "G-HW15MZBED4"
};

const app  = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db   = getFirestore(app);

// ── Auth Functions ───────────────────────────────────────────

/** Open Google Sign-In popup. Returns user or throws. */
export async function signInWithGoogle() {
  const provider = new GoogleAuthProvider();
  provider.setCustomParameters({ prompt: 'select_account' });
  const result = await signInWithPopup(auth, provider);
  return result.user;
}

/** Sign out current user. */
export async function signOut() {
  await firebaseSignOut(auth);
}

/** Subscribe to auth state changes. Callback receives user or null. */
export function onAuth(callback) {
  return onAuthStateChanged(auth, callback);
}

/** Get current signed-in user (sync). */
export function currentUser() {
  return auth.currentUser;
}

// ── Firestore Functions ──────────────────────────────────────

/**
 * Save a scan result to Firestore under users/{uid}/scans/{scan_id}.
 * Safe to call even if user is not signed in (no-op).
 */
export async function saveScanToFirestore(scanData) {
  const user = auth.currentUser;
  if (!user) return false;

  try {
    const scanRef = doc(db, 'users', user.uid, 'scans', scanData.scan_id);
    await setDoc(scanRef, {
      scan_id:           scanData.scan_id,
      filename:          scanData.filename || 'unknown',
      trust_score:       scanData.trust_score ?? 0,
      verdict:           scanData.verdict || 'UNKNOWN',
      confidence:        scanData.confidence ?? 0,
      doc_type_detected: scanData.doc_type_detected || 'other',
      ai_model_used:     scanData.ai_model_used || '',
      processing_time_ms: scanData.processing_time_ms ?? 0,
      anomalies:         scanData.anomalies || [],
      summary:           scanData.summary || scanData.ai_summary || '',
      ela_heatmap_url:   scanData.ela_heatmap_url || null,
      certificate_url:   scanData.certificate_url || null,
      breakdown:         scanData.breakdown || {},
      ela_regions:       scanData.ela_regions || [],
      created_at:        serverTimestamp(),
      user_email:        user.email,
      user_name:         user.displayName,
    });
    return true;
  } catch (e) {
    console.error('Firestore save failed:', e);
    return false;
  }
}

/**
 * Fetch current user's scan history from Firestore.
 * Returns array of scan objects sorted by date desc.
 */
export async function getUserScans(maxCount = 200) {
  const user = auth.currentUser;
  if (!user) return [];

  try {
    const scansRef = collection(db, 'users', user.uid, 'scans');
    const q = query(scansRef, orderBy('created_at', 'desc'), limit(maxCount));
    const snapshot = await getDocs(q);
    return snapshot.docs.map(d => ({ ...d.data(), id: d.id }));
  } catch (e) {
    console.error('Firestore fetch failed:', e);
    return [];
  }
}
