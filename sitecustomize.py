import cix.cli as c
_o=c.config_for_level
def f(level):
    x=_o(level)
    if level >= 6 and x.enable_ppm: x.ppm_order=6
    return x
c.config_for_level=f
