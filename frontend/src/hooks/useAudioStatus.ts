import { useEffect, useState } from "react";

export function useAudioStatus() {
  const [audioEnabled, setAudioEnabled] = useState(true);

  useEffect(() => {
    const fetchAudioStatus = async () => {
      try {
        const res = await fetch("/api/audio_status");
        const data = await res.json();
        setAudioEnabled(data.enabled);
      } catch { /* ignore */ }
    };
    fetchAudioStatus();
    const interval = setInterval(fetchAudioStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  const toggleAudio = async () => {
    try {
      const res = await fetch("/api/audio_toggle", { method: "POST" });
      const data = await res.json();
      setAudioEnabled(data.enabled);
    } catch { /* ignore */ }
  };

  return { audioEnabled, toggleAudio };
}
