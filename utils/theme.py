# utils/theme.py  — centralised colour & style tokens

class Theme:
    # Backgrounds
    BG          = (0.05, 0.06, 0.08, 1)
    CARD        = (0.09, 0.11, 0.14, 1)
    CARD2       = (0.12, 0.14, 0.18, 1)

    # Accent
    GREEN       = (0.18, 0.85, 0.55, 1)
    GREEN_DIM   = (0.10, 0.45, 0.30, 1)
    RED         = (0.95, 0.30, 0.30, 1)
    YELLOW      = (1.00, 0.80, 0.20, 1)
    BLUE        = (0.25, 0.60, 1.00, 1)

    # Text
    TEXT        = (0.92, 0.93, 0.95, 1)
    TEXT_DIM    = (0.45, 0.50, 0.58, 1)
    TEXT_LABEL  = (0.65, 0.70, 0.78, 1)

    # Misc
    DIVIDER     = (0.15, 0.18, 0.22, 1)
    RADIUS      = "8dp"

    @staticmethod
    def hex(color_tuple):
        r, g, b, _ = color_tuple
        return "#{:02x}{:02x}{:02x}".format(int(r*255), int(g*255), int(b*255))
