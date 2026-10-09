/* Hub icons: one icon set for the whole Medical Sales Hub (Lou, 01/10/2026).
   Every non-speciality page in hub/my-hub-catalogue.json names its own glyph
   in its `icon` field; specialities share `steth`. The same glyph is used on
   My Hub (tools launcher, Your pages tiles), in the nav dropdowns and in the
   page bar under the nav (app/hub-chrome.js), so a page looks the same
   wherever it appears. A new page gets an icon in one place: add a glyph here
   if none fits, and name it in the page's catalogue entry.

   Style: 24px grid, 1.75 stroke, round caps and joins, no fill, drawn with
   currentColor so the surrounding text colour sets it. Attributes inside the
   glyph strings use single quotes so the block below stays valid JSON, which
   test_my_hub_catalogue.py reads between the GLYPHS markers.

   Glyph outlines follow the open-source line set the approved mock-up was
   drawn with, which is ISC licensed: Copyright (c) for portions of Lucide are
   held by Cole Bemis 2013-2022 as part of Feather (MIT); all other copyright
   (c) for Lucide are held by Lucide Contributors 2022. Permission to use,
   copy, modify, and/or distribute this software for any purpose with or
   without fee is hereby granted, provided that the above copyright notice and
   this permission notice appear in all copies. THE SOFTWARE IS PROVIDED "AS
   IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE.

   Loaded with new Function() by app/my-hub.js and app/hub-chrome.js; also
   require()-able under node for the tests. */
(function (root) {
  'use strict';
  if (root.MSH_ICONS && typeof module === 'undefined') { return; }

  var GLYPHS = /*GLYPHS*/{
    "steth": "<path d='M11 2v2M5 2v2'/><path d='M5 3H4a2 2 0 0 0-2 2v4a6 6 0 0 0 12 0V5a2 2 0 0 0-2-2h-1'/><path d='M8 15a6 6 0 0 0 12 0v-3'/><circle cx='20' cy='10' r='2'/>",
    "grid": "<rect x='3' y='3' width='7' height='7' rx='1.5'/><rect x='14' y='3' width='7' height='7' rx='1.5'/><rect x='3' y='14' width='7' height='7' rx='1.5'/><rect x='14' y='14' width='7' height='7' rx='1.5'/>",
    "book": "<path d='M2 4h6a4 4 0 0 1 4 4v13a3 3 0 0 0-3-3H2z'/><path d='M22 4h-6a4 4 0 0 0-4 4v13a3 3 0 0 1 3-3h7z'/>",
    "mail": "<rect x='2' y='4' width='20' height='16' rx='2'/><path d='m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7'/>",
    "star": "<path d='M12 2.5l2.94 5.96 6.56.95-4.75 4.63 1.12 6.53L12 17.5l-5.87 3.07 1.12-6.53L2.5 9.41l6.56-.95z'/>",
    "search": "<circle cx='11' cy='11' r='7.5'/><path d='m20.5 20.5-4.2-4.2'/>",
    "help": "<circle cx='12' cy='12' r='10'/><path d='M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3'/><path d='M12 17h.01'/>",
    "spark": "<path d='M11 3l1.8 4.9L17.7 9.7 12.8 11.5 11 16.4 9.2 11.5 4.3 9.7 9.2 7.9z'/><path d='M19 14v6M16 17h6'/>",
    "home": "<path d='m3 10 9-7 9 7v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z'/><path d='M9 22V13h6v9'/>",
    "down": "<path d='m6 9 6 6 6-6'/>",
    "up": "<path d='m18 15-6-6-6 6'/>",
    "right": "<path d='m9 6 6 6-6 6'/>",
    "x": "<path d='M18 6 6 18M6 6l12 12'/>",
    "minus": "<path d='M5 12h14'/>",
    "plus": "<path d='M12 5v14M5 12h14'/>",
    "check": "<path d='M20 6 9 17l-5-5'/>",
    "cal": "<rect x='3' y='4' width='18' height='18' rx='2'/><path d='M16 2v4M8 2v4M3 10h18'/>",
    "alert": "<path d='m21.7 18-8-14a2 2 0 0 0-3.4 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3z'/><path d='M12 9v4M12 17h.01'/>",
    "clip": "<rect x='8' y='2' width='8' height='4' rx='1'/><path d='M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2'/><path d='M9 12h6M9 16h4'/>",
    "news": "<path d='M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-4 0v-9h4'/><path d='M18 14h-8M15 18h-5M10 6h8v4h-8z'/>",
    "radio": "<path d='M4.9 19.1C1 15.2 1 8.8 4.9 4.9'/><path d='M7.8 16.2c-2.3-2.3-2.3-6.1 0-8.5'/><circle cx='12' cy='12' r='2'/><path d='M16.2 7.8c2.3 2.3 2.3 6.1 0 8.5'/><path d='M19.1 4.9C23 8.8 23 15.1 19.1 19'/>",
    "wrench": "<path d='M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94z'/>",
    "case": "<rect x='2' y='7' width='20' height='14' rx='2'/><path d='M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16'/>",
    "heart": "<path d='M19 14c1.5-1.5 3-3.2 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.8 0-3 .5-4.5 2-1.5-1.5-2.7-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4 3 5.5l7 7z'/><path d='M3.2 12h4.3l1.5-3 2 6 1.5-3h4.3'/>",
    "user": "<circle cx='12' cy='8' r='4'/><path d='M4 21a8 8 0 0 1 16 0'/>",
    "phone": "<rect x='6' y='2' width='12' height='20' rx='2.5'/><path d='M11 18h2'/>",
    "play": "<circle cx='12' cy='12' r='10'/><path d='m10 8 6 4-6 4z'/>",
    "file": "<path d='M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z'/><path d='M14 2v6h6M8 13h8M8 17h5'/>",
    "filter": "<path d='M22 3H2l8 9.46V19l4 2v-8.54z'/>",
    "target": "<circle cx='12' cy='12' r='10'/><circle cx='12' cy='12' r='6'/><circle cx='12' cy='12' r='2'/>",
    "truck": "<path d='M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2'/><path d='M15 18H9'/><path d='M19 18h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.62l-3.48-4.35A1 1 0 0 0 17.52 8H14'/><circle cx='17' cy='18' r='2'/><circle cx='7' cy='18' r='2'/>",
    "shield-alert": "<path d='M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z'/><path d='M12 8v4M12 16h.01'/>",
    "trending-up": "<path d='M22 7 13.5 15.5 8.5 10.5 2 17'/><path d='M16 7h6v6'/>",
    "radar": "<path d='M19.07 4.93A10 10 0 0 0 6.99 3.34'/><path d='M4 6h.01'/><path d='M2.29 9.62A10 10 0 1 0 21.31 8.35'/><path d='M16.24 7.76A6 6 0 1 0 8.23 16.67'/><path d='M12 18h.01'/><path d='M17.99 11.66A6 6 0 0 1 15.77 16.67'/><circle cx='12' cy='12' r='2'/><path d='m13.41 10.59 5.66-5.66'/>",
    "rss": "<path d='M4 11a9 9 0 0 1 9 9'/><path d='M4 4a16 16 0 0 1 16 16'/><circle cx='5' cy='19' r='1'/>",
    "calendar-days": "<rect x='3' y='4' width='18' height='18' rx='2'/><path d='M16 2v4M8 2v4M3 10h18'/><path d='M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01M16 18h.01'/>",
    "hospital": "<path d='M12 6v4M14 14h-4M14 18h-4M14 8h-4'/><path d='M18 12h2a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-9a2 2 0 0 1 2-2h2'/><path d='M18 22V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v18'/>",
    "users": "<path d='M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2'/><circle cx='9' cy='7' r='4'/><path d='M22 21v-2a4 4 0 0 0-3-3.87'/><path d='M16 3.13a4 4 0 0 1 0 7.75'/>",
    "history": "<path d='M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8'/><path d='M3 3v5h5'/><path d='M12 7v5l4 2'/>",
    "package": "<path d='M11 21.73a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73z'/><path d='M12 22V12'/><path d='m3.3 7 8.7 5 8.7-5'/><path d='m7.5 4.27 9 5.15'/>",
    "pound": "<path d='M18 7c0-5.33-8-5.33-8 0'/><path d='M10 7v14'/><path d='M6 21h12'/><path d='M6 13h10'/>",
    "hash": "<path d='M4 9h16M4 15h16M10 3 8 21M16 3l-2 18'/>",
    "scale": "<path d='m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z'/><path d='m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z'/><path d='M7 21h10'/><path d='M12 3v18'/><path d='M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2'/>",
    "badge-check": "<path d='M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76Z'/><path d='m9 12 2 2 4-4'/>",
    "megaphone": "<path d='m3 11 18-5v12L3 14v-3z'/><path d='M11.6 16.8a3 3 0 1 1-5.8-1.6'/>",
    "building": "<rect x='4' y='2' width='16' height='20' rx='2'/><path d='M9 22v-4h6v4'/><path d='M8 6h.01M16 6h.01M12 6h.01M12 10h.01M12 14h.01M16 10h.01M16 14h.01M8 10h.01M8 14h.01'/>",
    "globe": "<circle cx='12' cy='12' r='10'/><path d='M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20'/><path d='M2 12h20'/>",
    "monitor-smartphone": "<path d='M18 8V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h8'/><path d='M10 19v-3.96 3.15'/><path d='M7 19h5'/><rect x='16' y='12' width='6' height='10' rx='2'/>",
    "calculator": "<rect x='4' y='2' width='16' height='20' rx='2'/><path d='M8 6h8M16 14v4M16 10h.01M12 10h.01M8 10h.01M12 14h.01M8 14h.01M12 18h.01M8 18h.01'/>",
    "file-chart": "<path d='M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z'/><path d='M14 2v4a2 2 0 0 0 2 2h4'/><path d='M8 18v-2M12 18v-4M16 18v-6'/>",
    "factory": "<path d='M2 20a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8l-7 5V8l-7 5V4a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z'/><path d='M17 18h1M12 18h1M7 18h1'/>",
    "swords": "<path d='M14.5 17.5 3 6V3h3l11.5 11.5'/><path d='m13 19 6-6M16 16l4 4M19 21l2-2'/><path d='M14.5 6.5 18 3h3v3l-3.5 3.5'/><path d='m5 14 4 4M7 17l-3 3M3 19l2 2'/>",
    "pie-chart": "<path d='M21 12c.55 0 1-.45.98-1A10 10 0 0 0 13 2.02c-.55-.04-1 .41-1 .96V11a1 1 0 0 0 1 1z'/><path d='M21.21 15.89A10 10 0 1 1 8 2.83'/>",
    "notebook-pen": "<path d='M13.4 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-7.4'/><path d='M2 6h4M2 10h4M2 14h4M2 18h4'/><path d='M21.38 5.63a1 1 0 0 0-3-3l-5 5a2 2 0 0 0-.5.85l-.84 2.87a.5.5 0 0 0 .62.62l2.87-.84a2 2 0 0 0 .85-.5z'/>",
    "pill": "<path d='m10.5 20.5 10-10a4.95 4.95 0 1 0-7-7l-10 10a4.95 4.95 0 1 0 7 7Z'/><path d='m8.5 8.5 7 7'/>",
    "droplet": "<path d='M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5C6 11.1 5 13 5 15a7 7 0 0 0 7 7z'/>",
    "gauge": "<path d='m12 14 4-4'/><path d='M3.34 19a10 10 0 1 1 17.32 0'/>",
    "route": "<circle cx='6' cy='19' r='3'/><path d='M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15'/><circle cx='18' cy='5' r='3'/>",
    "bar-chart": "<path d='M3 3v16a2 2 0 0 0 2 2h16'/><path d='M18 17V9M13 17V5M8 17v-3'/>",
    "network": "<rect x='16' y='16' width='6' height='6' rx='1'/><rect x='2' y='16' width='6' height='6' rx='1'/><rect x='9' y='2' width='6' height='6' rx='1'/><path d='M5 16v-3a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v3'/><path d='M12 12V8'/>",
    "library": "<path d='m16 6 4 14M12 6v14M8 8v12M4 4v16'/>",
    "receipt": "<path d='M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1Z'/><path d='M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8'/><path d='M12 17.5v-11'/>",
    "book-a": "<path d='M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H19a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1H6.5a1 1 0 0 1 0-5H20'/><path d='m8 13 4-7 4 7'/><path d='M9.1 11h5.7'/>",
    "id-card": "<path d='M16 10h2M16 14h2'/><path d='M6.17 15a3 3 0 0 1 5.66 0'/><circle cx='9' cy='11' r='2'/><rect x='2' y='5' width='20' height='14' rx='2'/>",
    "leaf": "<path d='M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z'/><path d='M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12'/>",
    "compass": "<circle cx='12' cy='12' r='10'/><path d='m16.24 7.76-1.8 5.41a2 2 0 0 1-1.27 1.27l-5.41 1.8 1.8-5.41a2 2 0 0 1 1.27-1.27z'/>",
    "flask": "<path d='M10 2v7.53a2 2 0 0 1-.21.9L4.72 20.55A1 1 0 0 0 5.6 22h12.8a1 1 0 0 0 .88-1.45l-5.07-10.12a2 2 0 0 1-.21-.9V2'/><path d='M8.5 2h7M7 16h10'/>",
    "footprints": "<path d='M4 16v-2.38C4 11.5 2.97 10.5 3 8c.03-2.72 1.49-6 4.5-6C9.37 2 10 3.8 10 5.5c0 3.11-2 5.66-2 8.68V16a2 2 0 1 1-4 0Z'/><path d='M20 20v-2.38c0-2.12 1.03-3.12 1-5.62-.03-2.72-1.49-6-4.5-6C14.63 6 14 7.8 14 9.5c0 3.11 2 5.66 2 8.68V20a2 2 0 1 0 4 0Z'/><path d='M16 17h4M4 13h4'/>",
    "messages": "<path d='M14 9a2 2 0 0 1-2 2H6l-4 4V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2z'/><path d='M18 9h2a2 2 0 0 1 2 2v11l-4-4h-6a2 2 0 0 1-2-2v-1'/>",
    "graduation-cap": "<path d='M21.42 10.92a1 1 0 0 0-.02-1.84L12.83 5.18a2 2 0 0 0-1.66 0L2.6 9.08a1 1 0 0 0 0 1.83l8.57 3.91a2 2 0 0 0 1.66 0z'/><path d='M22 10v6'/><path d='M6 12.5V16a6 3 0 0 0 12 0v-3.5'/>",
    "video": "<path d='m16 13 5.22 3.48a.5.5 0 0 0 .78-.42V7.87a.5.5 0 0 0-.75-.43L16 10.5'/><rect x='2' y='6' width='14' height='12' rx='2'/>",
    "mic": "<path d='M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z'/><path d='M19 10v2a7 7 0 0 1-14 0v-2'/><path d='M12 19v3'/>",
    "share": "<circle cx='18' cy='5' r='3'/><circle cx='6' cy='12' r='3'/><circle cx='18' cy='19' r='3'/><path d='m8.59 13.51 6.83 3.98M15.41 6.51l-6.82 3.98'/>",
    "award": "<path d='m15.48 12.89 1.52 8.56a.5.5 0 0 1-.81.47l-3.59-2.7a1 1 0 0 0-1.2 0l-3.6 2.7a.5.5 0 0 1-.81-.47l1.52-8.56'/><circle cx='12' cy='8' r='6'/>",
    "download": "<path d='M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4'/><path d='m7 10 5 5 5-5'/><path d='M12 15V3'/>",
    "signpost": "<path d='M12 3v3M12 13v8'/><path d='M18 6a2 2 0 0 1 1.39.56l2.3 2.23a1 1 0 0 1 0 1.42l-2.3 2.23A2 2 0 0 1 18 13H6a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1z'/>",
    "file-user": "<path d='M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z'/><path d='M14 2v4a2 2 0 0 0 2 2h4'/><path d='M16 22a4 4 0 0 0-8 0'/><circle cx='12' cy='15' r='3'/>",
    "coins": "<circle cx='8' cy='8' r='6'/><path d='M18.09 10.37A6 6 0 1 1 10.34 18'/><path d='M7 6h1v4'/><path d='m16.71 13.88.7.71-2.82 2.82'/>",
    "hand-coins": "<path d='M11 15h2a2 2 0 1 0 0-4h-3c-.6 0-1.1.2-1.4.6L3 17'/><path d='m7 21 1.6-1.4c.3-.4.8-.6 1.4-.6h4c1.1 0 2.1-.4 2.8-1.2l4.6-4.4a2 2 0 0 0-2.75-2.91l-4.2 3.9'/><path d='m2 16 6 6'/><circle cx='16' cy='9' r='2.9'/><circle cx='6' cy='5' r='3'/>",
    "presentation": "<path d='M2 3h20'/><path d='M21 3v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V3'/><path d='m7 21 5-5 5 5'/>",
    "headphones": "<path d='M3 14h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-7a9 9 0 0 1 18 0v7a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3'/>",
    "user-search": "<circle cx='10' cy='7' r='4'/><path d='M10.3 15H7a4 4 0 0 0-4 4v2'/><circle cx='17' cy='17' r='3'/><path d='m21 21-1.9-1.9'/>",
    "folder-open": "<path d='m6 14 1.5-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.54 6a2 2 0 0 1-1.95 1.5H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H18a2 2 0 0 1 2 2v2'/>",
    "folder-check": "<path d='M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z'/><path d='m9 13 2 2 4-4'/>",
    "hand-heart": "<path d='M11 14h2a2 2 0 1 0 0-4h-3c-.6 0-1.1.2-1.4.6L3 16'/><path d='m7 20 1.6-1.4c.3-.4.8-.6 1.4-.6h4c1.1 0 2.1-.4 2.8-1.2l4.6-4.4a2 2 0 0 0-2.75-2.91l-4.2 3.9'/><path d='m2 15 6 6'/><path d='M19.5 8.5c.7-.7 1.5-1.6 1.5-2.7A2.73 2.73 0 0 0 16 4a2.78 2.78 0 0 0-5 1.8c0 1.2.8 2 1.5 2.8L16 12Z'/>",
    "bell": "<path d='M10.27 21a2 2 0 0 0 3.46 0'/><path d='M3.26 15.33A1 1 0 0 0 4 17h16a1 1 0 0 0 .74-1.67C19.41 13.96 18 12.5 18 8A6 6 0 0 0 6 8c0 4.5-1.41 5.96-2.74 7.33'/>",
    "message-question": "<path d='M7.9 20A9 9 0 1 0 4 16.1L2 22Z'/><path d='M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3'/><path d='M12 17h.01'/>",
    "locate": "<circle cx='12' cy='12' r='7'/><circle cx='12' cy='12' r='2.5'/><path d='M12 2v3M12 19v3M2 12h3M19 12h3'/>",
    "scan-search": "<path d='M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2'/><circle cx='12' cy='12' r='3'/><path d='m16 16-1.9-1.9'/>",
    "arrow-left-right": "<path d='M8 3 4 7l4 4'/><path d='M4 7h16'/><path d='m16 21 4-4-4-4'/><path d='M20 17H4'/>",
    "clipboard-list": "<rect x='8' y='2' width='8' height='4' rx='1'/><path d='M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2'/><path d='M12 11h4M12 16h4M8 11h.01M8 16h.01'/>",
    "hub-spoke": "<circle cx='12' cy='12' r='2.5'/><circle cx='5' cy='5' r='2'/><circle cx='19' cy='5' r='2'/><circle cx='5' cy='19' r='2'/><circle cx='19' cy='19' r='2'/><path d='m10 10-3.5-3.5M14 10l3.5-3.5M10 14l-3.5 3.5M14 14l3.5 3.5'/>",
    "circle-pound": "<circle cx='12' cy='12' r='10'/><path d='M15 8.5a3 3 0 0 0-6 .5v7'/><path d='M8 16h8M8 12h6'/>",
    "bandage": "<path d='M10 10.01h.01M10 14h.01M14 10.01h.01M14 14.01h.01M18 6v12M6 6v12'/><rect x='2' y='6' width='20' height='12' rx='2'/>",
    "cloud": "<path d='M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z'/>",
    "sprout": "<path d='M7 20h10M10 20c5.5-2.5.8-6.4 3-10'/><path d='M9.5 9.4c1.1.8 1.8 2.2 2.3 3.7-2 .4-3.5.4-4.8-.3-1.2-.6-2.3-1.9-3-4.2 2.8-.5 4.4 0 5.5.8z'/><path d='M14.1 6a7 7 0 0 0-1.1 4c1.9-.1 3.3-.6 4.3-1.4 1-1 1.6-2.3 1.7-4.6-2.7.1-4 1-4.9 2z'/>",
    "chart-candlestick": "<path d='M9 5v4'/><rect width='4' height='6' x='7' y='9' rx='1'/><path d='M9 15v2'/><path d='M17 3v2'/><rect width='4' height='8' x='15' y='5' rx='1'/><path d='M17 13v3'/><path d='M3 3v16a2 2 0 0 0 2 2h16'/>",
    "file-badge": "<path d='M12 22h6a2 2 0 0 0 2-2V7l-5-5H6a2 2 0 0 0-2 2v3'/><path d='M14 2v4a2 2 0 0 0 2 2h4'/><circle cx='5' cy='14' r='3'/><path d='M7 16.5 8 22l-3-1-3 1 1-5.5'/>"
  }/*END-GLYPHS*/;

  function has(name) { return Object.prototype.hasOwnProperty.call(GLYPHS, name); }

  /* An inline SVG for one glyph. `cls` is the class on the <svg>; stroke
     settings sit on the element itself so it draws correctly on pages that
     carry none of My Hub's CSS (the nav, the page bar). */
  function svg(name, cls) {
    var p = has(name) ? GLYPHS[name] : GLYPHS.file;
    return '<svg class="' + (cls || 'i') + '" viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">' + p + '</svg>';
  }

  /* The glyph a catalogue item is drawn with. */
  function forItem(item) {
    if (!item) { return 'file'; }
    if (item.icon) { if (has(item.icon)) { return item.icon; } }
    return item.group === 'specialities' ? 'steth' : 'file';
  }

  var api = { GLYPHS: GLYPHS, has: has, svg: svg, forItem: forItem };
  if (typeof module === 'object') { if (module) { if (module.exports) { module.exports = api; } } }
  root.MSH_ICONS = api;
})(typeof window !== 'undefined' ? window : globalThis);
