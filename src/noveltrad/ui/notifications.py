"""Notifications fragment (SDD 13.12).

The unique allowed client fragment via streamlit.components.v1.html for
Notification and Web Audio: a 880 Hz sine for 180 ms at max gain 0.1,
played once when completion_sound_enabled is true. Receives only a boolean
trigger and generic FR/EN labels; no business content, no network call.
"""

from __future__ import annotations

_FRAGMENT = """
<script>
const trigger = %(trigger)s;
const sound = %(sound)s;
const message = %(message)r;
if (trigger) {
  if (sound) {
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.frequency.value = 880;
      osc.type = 'sine';
      gain.gain.value = 0.1;
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.18);
    } catch (e) {}
  }
  if (typeof Notification !== 'undefined' && Notification.permission === 'granted') {
    try {
      new Notification('NovelTrad', { body: message });
    } catch (e) {}
  }
}
</script>
"""


def completion_fragment(trigger: bool, sound_enabled: bool, label: str) -> str:
    """Return the client fragment for the terminal completion notice."""
    return _FRAGMENT % {
        "trigger": "true" if trigger else "false",
        "sound": "true" if sound_enabled else "false",
        "message": label,
    }
