import React, { useEffect, useMemo, useRef, useState } from "react";
import { apiUrl, getStatus, type PlayerStatus } from "./api";

const NAME_OVERLAY_MS = 2000;
const POLL_MS = 750;

export function App() {
  const [status, setStatus] = useState<PlayerStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [showName, setShowName] = useState(false);
  const hideTimer = useRef<number | null>(null);
  const lastKey = useRef<string | null>(null);

  // Used to force-refresh the <img> src when the selected GIF changes.
  const [imgNonce, setImgNonce] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const ac = new AbortController();

    async function tick() {
      try {
        const s = await getStatus(ac.signal);
        if (cancelled) return;

        setStatus(s);
        setError(null);

        const key = `${s.index}:${s.current_name ?? ""}:${s.gif_count}`;
        if (lastKey.current !== key) {
          lastKey.current = key;
          setImgNonce((n) => n + 1);
          if (s.current_name) {
            setShowName(true);
            if (hideTimer.current) window.clearTimeout(hideTimer.current);
            hideTimer.current = window.setTimeout(() => setShowName(false), NAME_OVERLAY_MS);
          } else {
            setShowName(false);
          }
        }
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : String(e));
      }
    }

    // Immediate fetch + polling
    void tick();
    const id = window.setInterval(() => void tick(), POLL_MS);

    return () => {
      cancelled = true;
      ac.abort();
      window.clearInterval(id);
      if (hideTimer.current) window.clearTimeout(hideTimer.current);
    };
  }, []);

  const canShowGif = (status?.gif_count ?? 0) > 0 && !!status?.current_name;

  const gifSrc = useMemo(() => {
    // `nonce` busts the browser cache on selection changes.
    return apiUrl(`/api/gif/current?nonce=${imgNonce}`);
  }, [imgNonce]);

  return (
    <div className="page">
      <div className="stage" aria-label="GIF stage">
        {canShowGif ? (
          <img className="gif" src={gifSrc} alt={status?.current_name ?? "Current GIF"} />
        ) : (
          <div className="empty">
            <div className="emptyTitle">No GIFs found</div>
            <div className="emptySub">
              Put <code>.gif</code> files into <code>{status?.gif_dir ?? "GIF_DIR"}</code> then hit <code>POST /api/rescan</code>.
            </div>
          </div>
        )}

        {showName && status?.current_name ? <div className="overlay">{status.current_name}</div> : null}
        {error ? <div className="error">UI error: {error}</div> : null}
        {status?.last_error ? <div className="error">Player error: {status.last_error}</div> : null}
      </div>
    </div>
  );
}

