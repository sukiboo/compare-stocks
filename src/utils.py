def date_to_idx_range(timestamps, date_range):
    idx_range = (
        timestamps.get_indexer(date_range, method="nearest").tolist()
        if all(date_range)
        else [0, -1]
    )
    return idx_range


def get_date_range(figure_layout):
    date_range = [None, None]
    # check xaxis2 first
    if "xaxis2" in figure_layout and figure_layout["xaxis2"].get("range"):
        date_range = figure_layout["xaxis2"]["range"]
    # if not found, check xaxis1
    elif "xaxis1" in figure_layout and figure_layout["xaxis1"].get("range"):
        date_range = figure_layout["xaxis1"]["range"]
    # else:
    #     print(figure_layout)
    return date_range
