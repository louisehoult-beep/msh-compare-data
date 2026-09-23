# Hub phone app

`app/mobile-app.js` turns one members-only Hub page into a full-screen phone app
with a bottom bar of five big tabs: Prep, Suppliers, Compare, Company, Search.
Each tab runs the same tool file the desktop Hub pages run, so a fix to a tool
reaches the app on the same push. Nothing is copied.

## Who can get it

Paying members only. The page sits under the Hub's subscriber-only parent page on
medsalesintelligencehub.co.uk, so PMS gates it. Do not host it on GitHub Pages:
anyone with the link could use the tools, and Meeting Prep's gated data
(`window.MSH_GATE`) only exists on a logged-in Hub page.

## Setting up the page (once)

1. On medsalesintelligencehub.co.uk, create a page under the subscriber-only parent.
   Suggested title: `App`. Use a blank or full-width template.
2. Add one Custom HTML block containing exactly this:

```html
<div id="msh-mobile-app"></div>
<script>
fetch('https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/app/mobile-app.js?v=' + Date.now(), { cache: 'no-store' })
  .then(function (r) { return r.text(); })
  .then(function (c) { var s = document.createElement('script'); s.textContent = c; document.body.appendChild(s); });
</script>
```

3. Publish, then open the page on a phone while logged in as a member.

The app covers the theme's header and footer, so the page looks like an app, not
a web page.

## Installing on a phone

The top bar has an **Install** button.

* Android (Chrome): opens Chrome's own install prompt where Chrome offers one,
  otherwise shows the menu steps.
* iPhone: shows the steps. Share, then Add to Home Screen.

A home-screen app on iPhone keeps its own login, separate from Safari, so members
log in once the first time they open it.

## App Store / Google Play

Not built. A store listing needs a native wrapper around this page, an Apple
Developer account and Apple review. Apple normally requires in-app purchase for
subscriptions bought inside an app, so the app would have to be log-in only with
no sign-up or pricing inside it. Decide this before any build.

## Phone fixes

The tools were built for desktop. The app applies scoped CSS (only inside
`#msh-app`) rather than editing each tool: form boxes stack full width, inputs
are 16px so iPhone doesn't zoom on tap, buttons are at least 48px tall, and wide
tables scroll sideways inside their own box. If a tool changes its layout, check
it in the app on a phone.
