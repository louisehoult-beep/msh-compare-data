// The app runs only as a native app; the Firebase plugin's web fallback is never
// used. This stands in for the firebase web SDK so it is not bundled.
const no = () => { throw new Error('Firebase web messaging is not used in the Live Desk app'); };
export const deleteToken = no, getMessaging = no, getToken = no, onMessage = no;
export const isSupported = async () => false;
