def adjust_offset(var, change):
    try:
        current = float(var.get()) if var.get() else 0.0
        var.set(str(current + change))
    except ValueError:
        var.set(str(change))