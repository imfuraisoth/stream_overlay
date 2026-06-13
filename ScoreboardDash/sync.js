// ════════════════════════════════════════════════════════════════
// LIVE SYNC client — subscribes to the server's /events SSE stream
// and dispatches channel notifications to page-registered handlers.
//
// Usage:  liveSync.on('players', function() { ...refresh... });
//
// Channels: scoreboard, top8, players, commentators
//
// Behavior:
//  - Events are debounced (200ms) so bursts of writes trigger one
//    refresh.
//  - If the operator is mid-edit (an input/select/textarea has
//    focus), the refresh is deferred and retried every 2s until the
//    page is idle, so live updates never clobber typing.
//  - Auto-reconnects if the stream drops; pages may keep a slow
//    polling fallback alongside this.
// ════════════════════════════════════════════════════════════════
(function() {
    var handlers = {};
    var debounce = {};
    var deferred = {};

    function pageIsBusy() {
        var el = document.activeElement;
        if (!el) return false;
        var tag = (el.tagName || '').toUpperCase();
        return tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA';
    }

    function run(channel) {
        if (pageIsBusy()) {
            // Defer until idle; one pending retry per channel
            if (deferred[channel]) return;
            deferred[channel] = setInterval(function() {
                if (!pageIsBusy()) {
                    clearInterval(deferred[channel]);
                    deferred[channel] = null;
                    run(channel);
                }
            }, 2000);
            return;
        }
        (handlers[channel] || []).forEach(function(fn) {
            try { fn(); } catch (e) { console.log('liveSync handler error (' + channel + '):', e); }
        });
    }

    function dispatch(channel) {
        clearTimeout(debounce[channel]);
        debounce[channel] = setTimeout(function() { run(channel); }, 200);
    }

    function connect() {
        var es;
        try {
            es = new EventSource('/events');
        } catch (e) {
            console.log('liveSync unavailable:', e);
            return;
        }
        es.onmessage = function(e) { if (e.data) dispatch(e.data); };
        es.onerror = function() {
            es.close();
            setTimeout(connect, 3000);
        };
    }

    window.liveSync = {
        on: function(channel, fn) {
            (handlers[channel] = handlers[channel] || []).push(fn);
        }
    };

    if (window.EventSource) {
        connect();
    } else {
        console.log('liveSync: EventSource unsupported; pages fall back to polling');
    }
})();