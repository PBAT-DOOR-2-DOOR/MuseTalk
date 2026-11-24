"""Timeline shared by the TV and iPhone compositors, matched to inputs/voice_final.wav."""

SEGS = [("title", 0.0), ("ngozi", 7.2), ("aisha", 17.55), ("tunde", 25.35), ("choose", 34.85), ("end", 39.1)]
DIP = {"end"}       # slides entered through black instead of a crossfade
XF = 0.4            # crossfade / dip length (s)
TIMES = {           # when named text layers animate in
    "beyond1": 37.0,    # "Beyond the ballot,"
    "beyond2": 38.2,    # "PBAT Cares."
    "approved1": 39.5,  # "This message is brought to you by the"
    "approved2": 41.55, # "PBAT Door to Door Movement"
}
