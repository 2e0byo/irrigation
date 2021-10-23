# Convert values to appropriate types
def convert_vals(v):
    vs = v.split(",")
    for i, v in enumerate(vs):
        try:
            v = int(v)
        except ValueError:
            pass
        try:
            v = float(v)
        except ValueError:
            pass
        if isinstance(v, str):
            if v.lower() == "true":
                v = True
            elif v.lower() == "false":
                v = False
        vs[i] = v
    if len(vs) == 1:
        return vs[0]
    else:
        return vs
