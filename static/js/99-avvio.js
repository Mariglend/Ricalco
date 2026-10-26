"use strict";

/* ================================================================ avvio */
Tutor.render();
refreshStatus().then(() => { if ($("#warn")) $("#warn").innerHTML = ollamaBanner(); if (App.view === "path") refreshPath(true); if (App.view === "start" && App.Q) quickStatus(); });
route();
// conteggi nella barra laterale (carte da ripassare), una volta all'avvio: la home li aggiorna quando la apri
api("/api/home").then(H => { App.H = App.H || H; navBadge("carte", H.cardsDue); }).catch(() => {});
