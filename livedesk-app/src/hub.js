// The Hub tab (plan step A spike, 19/11/2026). The pages stay on WordPress; the
// native HubView plugin (android HubWebActivity, ios HubView.swift) shows them in
// a web view with its own persistent cookies and the MSHLiveDeskApp/<platform>
// user-agent token. Nothing here links to Join, Register, pricing or checkout.
import { registerPlugin } from '@capacitor/core';

export const HubView = registerPlugin('HubView');

export const HUB_ORIGIN = 'https://medsalesintelligencehub.co.uk';
export const HUB_PAGES = [
  { key: 'login', label: 'Log in to the Hub', path: '/login/' },
  { key: 'myhub', label: 'My Hub', path: '/medical-sales-hub/my-hub/' },
  { key: 'urology', label: 'Urology desk', path: '/medical-sales-hub/urology/' },
  { key: 'calendar', label: 'Calendar', path: '/medical-sales-hub/calendar/' },
];

export const hubUrl = (key) => {
  const p = HUB_PAGES.find((x) => x.key === key);
  return p ? HUB_ORIGIN + p.path : null;
};
